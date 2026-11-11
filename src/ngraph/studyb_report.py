"""Study B report: B1 to B5, the Holm families with Study A, and the exploratory Study B estimates
(pre-registration, sections 2 and 6; addendum prereg-v1.1).

Input: the Study B run files (`python -m ngraph.studyb run`), the frozen task files, and the Study A
report (for A1's p-value in the confirmatory family and A2's and A3's in the secondary family).

* A prompt is correct when its arg-max letter over A to J is a gold function's letter (a task can have
  several gold candidates). Hit@3 and MRR use the full ranking of the ten letter logits (the best-ranked
  gold letter).
* Models (pre-registration, section 2): B1 to B3 pool E4B and the large model on the official tasks and
  E4B alone on SWE-bench Lite. The large model is 31B; 12B takes its place only when no 31B run exists on
  the official tasks (backup B-3, section 7). Every other model-set pair (12B next to 31B, 31B on Lite, any
  other model) is left out of B1 to B5 and listed in "descriptive_only"; its accuracy is still reported.
* B1 to B4: analysis.b1 to b4 (per task, the difference of the two cells within each model, averaged over
  orders, then over the models that have both cells; paired t-test, sign-flip test, task bootstrap
  stratified by set, repository-cluster bootstrap, TOST +-5 points). B4 compares 31B with E4B on the
  official tasks; with no 31B run on the official tasks, 12B takes its place (backup B-3, section 7).
* Run files: each must name one of the given task files (tasks_sha256 in its first line) and no
  (model, task, naming, graph, order) may appear in two files.
* B2's family follows the registered rule: confirmatory when at least 35% of the eligible confirmatory
  tasks are anchored (measured on the frozen task files), else secondary.
* B5 (model-free; metric and test fixed in the addendum): per candidate, score = BM25 / (largest BM25 in
  the task's pool) + lambda x [the candidate shares an edge with an anchor]; the top score wins, ties by
  BM25 rank. Per anchored confirmatory task, Acc@1 with the true graph minus Acc@1 with the rewired graph;
  the same paired summary as B1 (paired t-test, two-sided, the Holm input; sign-flip test; bootstraps;
  TOST). lambda is chosen on the SWE-bench Lite dev split (tasks with role "tune"): the value of
  B5_LAMBDA_GRID with the best mean Acc@1 with true edges over the anchored tune tasks, ties to the smaller
  value; with no tune tasks, B5_LAMBDA_DEFAULT (logged as a deviation).
* Holm: confirmatory family A1, B1 (and B2 when confirmatory); secondary family A2, A3 (registered axis),
  B3, B4, B5 (and B2 when secondary). The families never shrink: a test with no p-value (not run, or
  NaN) enters with p = 1 and is listed in "holm_missing".
* Exploratory (no tests): opaque true minus opaque within-module rewired (estimate, 95% bootstrap
  interval); accuracy by stratum, by injected flag and by correct-letter position; letter mass.
"""

from __future__ import annotations

import json
import math
import sys

import numpy as np
import pandas as pd

from ngraph import analysis as an
from ngraph.runner import LETTERS10, load_results

B2_ANCHORED_MIN = 0.35
# lambda = 0 is left out: it ignores the graph, so true and rewired would give the same pick by construction.
B5_LAMBDA_GRID = (0.05, 0.1, 0.2, 0.3, 0.5, 0.75, 1.0, 1.5, 2.0)
B5_LAMBDA_DEFAULT = 0.5
B_MODELS = ("E4B", "12B", "31B")
B4_LARGE = ("31B", "12B")  # 31B; 12B only under backup B-3 (no 31B run on the official tasks)
B4_SMALL = "E4B"
ROW_DTYPES = {"model": str, "task_id": str, "set": str, "repo": str, "naming": str, "graph": str, "order": int,
              "anchored": bool, "stratum": str, "injected": bool, "role": str, "correct": int, "hit3": int,
              "rr": float, "letter_mass": float, "gold_pos": int, "file": str}


def registered_rows(df: pd.DataFrame) -> tuple[pd.Series, str | None]:
    """Mask of the rows that enter B1 to B3 (and the large model): E4B and the large model on the official
    tasks, E4B on Lite."""
    off = set(df.loc[(df["set"] == "official") & (df["role"] == "confirmatory"), "model"])
    large = next((m for m in B4_LARGE if m in off), None)
    mask = ((df["set"] == "official") & df["model"].isin([B4_SMALL] + ([large] if large else []))) | (
        (df["set"] == "lite") & (df["model"] == B4_SMALL))
    return mask, large
ROW_KEY = ("model", "task_id", "naming", "graph", "order")


def load_b_runs(paths, tasks_sha256=None) -> tuple[pd.DataFrame, dict]:
    """Rows of the Study B run files. With `tasks_sha256` (a set of task-file hashes), a file whose first
    line names another task file is refused. A (model, task, naming, graph, order) found in two files is
    refused."""
    rows, report = [], {}
    seen = {}
    for p in paths:
        rs, rep = load_results(p)
        h = rep["header"] or {}
        if h.get("study") != "B":
            raise SystemExit(f"{p} is not a Study B run file (study={h.get('study')!r})")
        if tasks_sha256 is not None and h.get("tasks_sha256") not in tasks_sha256:
            raise SystemExit(f"{p} was run on a task file with sha256 {h.get('tasks_sha256')}, not one of the given "
                             "task files")
        tag = str(h.get("model_tag", "")).upper()
        sets = sorted({r.get("set") for r in rs})
        key = (tag, tuple(sets), h.get("cells"))
        if key in seen:
            raise SystemExit(f"{p} and {seen[key]} are both {tag} runs of {sets} ({h.get('cells')}): list one")
        seen[key] = p
        report[p] = {k: rep[k] for k in ("rows", "error_rows", "unresolved_errors", "duplicates", "broken_lines")}
        report[p].update({"model_tag": tag, "tasks_sha256": h.get("tasks_sha256"), "package": h.get("package"),
                          "settings": h.get("settings"), "answer_prefix_source": h.get("answer_prefix_source"),
                          "n_jobs": h.get("n_jobs"), "complete": rep["rows"] == h.get("n_jobs")})
        for r in rs:
            logits = np.array([r[f"logit_{L}"] for L in LETTERS10])
            order = list(np.argsort(-logits, kind="stable"))
            gold = [LETTERS10.index(L) for L in r["correct_letters"]]
            best = min(order.index(g) for g in gold) + 1
            rows.append({"model": tag, "task_id": r["item_id"], "set": r["set"], "repo": r["repo"],
                         "naming": r["naming"], "graph": r["graph"], "order": r["order"],
                         "anchored": bool(r["anchored"]), "stratum": r["stratum"], "injected": bool(r["injected"]),
                         "role": r.get("role", "confirmatory"),
                         "correct": int(r["pred_letter"] in r["correct_letters"]),
                         "hit3": int(best <= 3), "rr": 1.0 / best, "letter_mass": r.get("letter_mass"),
                         "gold_pos": min(gold), "file": p})
    df = pd.DataFrame(rows) if rows else pd.DataFrame({k: pd.Series(dtype=v) for k, v in ROW_DTYPES.items()})
    if len(df):
        dup = df[df.duplicated(list(ROW_KEY), keep=False)]
        if len(dup):
            first = dup.iloc[0]
            raise SystemExit(f"{len(dup)} rows appear in more than one run file, e.g. "
                             f"{tuple(first[k] for k in ROW_KEY)} in {sorted(set(dup['file']))[:3]}")
    return df, report


def anchored_share(task_files) -> dict:
    n = a = 0
    for d in task_files:
        for r in d["tasks"]:
            if r.get("eligible") and r.get("role", "confirmatory") == "confirmatory":
                n += 1
                a += bool(r.get("anchored"))
    share = a / n if n else None
    return {"eligible_confirmatory": n, "anchored": a, "share": share,
            "b2_confirmatory": bool(share is not None and share >= B2_ANCHORED_MIN), "threshold": B2_ANCHORED_MIN}


# ----------------------------------------------------------------------------- B5
def b5_pick(rec: dict, lam: float, graph: str) -> int:
    """1 when the B5 scorer's top candidate is a gold function."""
    pool = rec["pool"]
    sc = rec["bm25_pool_scores"]
    top = max(sc.values()) or 1.0
    nb = set(rec["b5_anchor_neighbours"][graph])
    rank = {c: i for i, c in enumerate(pool)}  # pool order is the BM25 rank (injected gold last)
    best = max(pool, key=lambda c: (sc[c] / top + lam * (c in nb), -rank[c]))
    return int(best in set(rec["gold"]))


def b5_lambda(tune_recs: list) -> dict:
    recs = [r for r in tune_recs if r.get("eligible") and r.get("anchored")]
    if not recs:
        return {"lambda": B5_LAMBDA_DEFAULT, "source": "default (no tune tasks: a deviation)", "grid": None}
    grid = {lam: float(np.mean([b5_pick(r, lam, "true") for r in recs])) for lam in B5_LAMBDA_GRID}
    best = max(grid.items(), key=lambda kv: (kv[1], -kv[0]))[0]
    return {"lambda": best, "source": f"tuned on {len(recs)} anchored tune tasks", "grid": grid}


def b5(recs: list, lam: float, **kw) -> dict:
    rows = []
    for r in recs:
        if r.get("eligible") and r.get("anchored") and r.get("role", "confirmatory") == "confirmatory":
            rows.append({"task_id": r["task_id"], "set": r["set"], "repo": r["repo"],
                         "a": b5_pick(r, lam, "true"), "b": b5_pick(r, lam, "rewired")})
    if not rows:
        return {"not_run": "no anchored eligible confirmatory tasks", "p": None, "n_tasks": 0, "lambda": lam}
    j = pd.DataFrame(rows)
    j["diff"] = j["a"] - j["b"]
    out = an.paired_summary(j, **kw)
    out.update({"lambda": lam, "acc_true": float(j["a"].mean()), "acc_rewired": float(j["b"].mean())})
    return out


# ----------------------------------------------------------------------------- report
def exploratory(df: pd.DataFrame, n_boot: int = 10_000, seed: int = 0) -> dict:
    out = {}
    wm = df[(df["naming"] == "opaque") & df["graph"].isin(["true", "within_module"]) & df["anchored"]]
    if (wm["graph"] == "within_module").any():
        j = an._task_diffs(wm, {"naming": "opaque", "graph": "true"}, {"naming": "opaque", "graph": "within_module"})
        d = j["diff"].to_numpy()
        lo, hi = an.stratified_bootstrap_mean(d, j["set"].to_numpy(), n_boot=n_boot, seed=seed)
        out["within_module_null"] = {"estimate": float(d.mean()), "ci95": (lo, hi), "n_tasks": len(d),
                                     "note": "exploratory: opaque true minus opaque within-module rewired; no test"}
    conf = df[df["graph"] != "within_module"]
    out["accuracy"] = conf.groupby(["model", "set", "naming", "graph"])[["correct", "hit3", "rr"]].mean().round(4).reset_index().to_dict("records")
    out["by_stratum"] = conf.groupby(["naming", "graph", "stratum"])["correct"].mean().round(4).reset_index().to_dict("records")
    out["by_injected"] = conf.groupby(["injected", "naming", "graph"])["correct"].mean().round(4).reset_index().to_dict("records")
    out["by_gold_position"] = conf.groupby(["gold_pos"])["correct"].mean().round(4).to_dict()
    out["letter_mass_share_ge_0.9"] = conf.groupby("model")["letter_mass"].apply(lambda s: float((s >= 0.9).mean())).to_dict()
    return out


def study_b_report(df: pd.DataFrame, task_files: list, a_report: dict | None, n_boot: int = 10_000,
                   seed: int = 0) -> dict:
    kw = {"n_boot": n_boot, "n_perm": 10_000, "seed": seed}
    mask, large = registered_rows(df)
    keep = df[mask & (df["role"] == "confirmatory")]
    conf = keep[keep["graph"] != "within_module"]
    other = df[~mask]
    share = anchored_share(task_files)
    res = {"anchored": share, "n_rows": len(df), "models": sorted(df["model"].unique().tolist()),
           "large_model": large, "backup_b3": large == "12B",
           "descriptive_only": sorted({f"{m}/{s}" for m, s in zip(other["model"], other["set"])}),
           "sets": sorted(df["set"].unique().tolist()),
           "B1": an.b1(conf, **kw), "B2": an.b2(conf, **kw), "B3": an.b3(conf, **kw)}
    # each set also reported alone (pre-registration, section 6); B4 uses the official tasks only
    for k, f in (("B1", an.b1), ("B2", an.b2), ("B3", an.b3)):
        res[f"{k}_by_set"] = {s: f(conf[conf["set"] == s], **kw) for s in sorted(conf["set"].unique())}
    off_models = set(conf.loc[conf["set"] == "official", "model"])
    if large and {large, B4_SMALL} <= off_models:
        res["B4"] = {**an.b4(conf, large, B4_SMALL, **kw), "large": large, "small": B4_SMALL,
                     "backup_b3": large != B4_LARGE[0]}
    else:
        res["B4"] = {"not_run": f"needs {B4_SMALL} and one of {B4_LARGE} on the official tasks"}
    recs = [r for d in task_files for r in d["tasks"]]
    lam = b5_lambda([r for r in recs if r.get("role") == "tune"])
    res["B5_lambda"] = lam
    res["B5"] = b5(recs, lam["lambda"], **kw)
    pa = lambda k: (a_report or {}).get(k, {}).get("p")  # noqa: E731
    fam_c = {"A1": pa("A1"), "B1": res["B1"]["p"]}
    fam_s = {"A2": pa("A2"), "A3": pa("A3"), "B3": res["B3"]["p"], "B4": res["B4"].get("p"), "B5": res["B5"]["p"]}
    (fam_c if share["b2_confirmatory"] else fam_s)["B2"] = res["B2"]["p"]

    def bad(v):
        return v is None or (isinstance(v, float) and math.isnan(v))

    missing = sorted(k for k, v in {**fam_c, **fam_s}.items() if bad(v))
    res["holm_confirmatory"] = an.holm({k: (1.0 if bad(v) else v) for k, v in fam_c.items()})
    res["holm_secondary"] = an.holm({k: (1.0 if bad(v) else v) for k, v in fam_s.items()})
    res["holm_missing"] = missing
    res["exploratory"] = exploratory(keep, n_boot=n_boot, seed=seed)
    desc = df[(df["role"] == "confirmatory") & (df["graph"] != "within_module")]
    res["accuracy_all_models"] = desc.groupby(["model", "set", "naming", "graph"])[["correct", "hit3", "rr"]].mean().round(4).reset_index().to_dict("records") if len(desc) else []
    return res


def main(argv=None) -> int:
    import argparse
    import os

    ap = argparse.ArgumentParser(description="Study B report")
    ap.add_argument("--runs", nargs="+", required=True)
    ap.add_argument("--tasks", nargs="+", required=True, help="the frozen task files (official and Lite)")
    ap.add_argument("--study-a-report", help="runs/studyA_report.json (A1, A2, A3 p-values for Holm)")
    ap.add_argument("--n-boot", type=int, default=10_000)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    from ngraph.studyb import load_task_file

    import hashlib

    tfs = [load_task_file(p) for p in a.tasks]
    shas = set()
    for p in a.tasks:
        with open(p, "rb") as fh:
            shas.add(hashlib.sha256(fh.read()).hexdigest())
    df, files = load_b_runs(a.runs, tasks_sha256=shas)
    ar = None
    if a.study_a_report:
        with open(a.study_a_report) as fh:
            ar = json.load(fh)
    else:
        print("warning: no Study A report: A1, A2 and A3 are left out of the Holm families", file=sys.stderr)
    res = {"files": files, **study_b_report(df, tfs, ar, n_boot=a.n_boot)}
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w") as fh:
        json.dump(an._jsonable(res), fh, indent=1)
    print(json.dumps(an._jsonable({k: res[k] for k in ("anchored", "B1", "B2", "B5_lambda", "holm_confirmatory",
                                                         "holm_secondary", "holm_missing")}), indent=1)[:4000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
