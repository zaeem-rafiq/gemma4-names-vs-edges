#!/usr/bin/env python3
"""Reproduce the paper's headline numbers from the released run files only.

Standard library only (no numpy, scipy or pandas). Reads runs/studyA/*.jsonl and runs/studyB/*.jsonl of
https://github.com/zaeem-rafiq/gemma4-names-vs-edges and prints:
  Table 1  Study A accuracy by model and version (G0 to G4)
  A1       names x edges interaction: estimate, SE and t over the 32 repository means, per-model values
  Table 3  Study B Acc@1 by model, task set, naming and graph (mean over the two candidate orders)
  B1, B2   estimate, n tasks, SE and t, pooled and by task set
  extras   gold-injection share, injection strata, and the anchored-only cells

Usage (from the repository root):   python3 reproduce_from_runs.py [--runs runs]

What it does NOT reproduce: p-values, bootstrap confidence intervals, sign-flip tests, TOST, Holm
(the released report used scipy and seeded resampling; see src/ngraph/analysis.py and
src/ngraph/studyb_report.py), and B5, which needs the task files that are not redistributed.

Scoring follows the released analysis code:
  Study A  correct = the correct letter has the single highest of the four letter logits (ties wrong);
           per (repository, item, model, version) the mean over option orders; I = (G1-G2)-(G3-G4) per
           (item, model); mean I per repository; one-sample t over the 32 repository means.
  Study B  correct = the row's pred_letter is in correct_letters; a difference is taken within
           (task, model, order), averaged over orders, then over models; one-sample t over tasks.
           Registered rows: E4B and 31B on the official tasks, E4B on Lite. 12B/official and 31B/Lite are
           descriptive and enter Table 3 only.

Output on 11 Nov 2026 against commit c787276b107401c5bc4fa76a6672e6ed72cdd962 (Python 3, run from the
repository root). The report files give the same values where they overlap: studyA_report.json A1 estimate
0.00546875, se 0.00925, t 0.591; studyB_report.json B1 estimate 0.0802, t 5.129; B2 estimate -0.02155,
t -2.262; by-set estimates 0.0962, 0.0428, -0.0229, -0.0174.

    Study A: 19200 rows from 4 files
    Table 1 (accuracy, %)
    model       G0      G1      G2      G3      G4
    E2B      32.66   57.27   58.44   46.72   50.08
    E4B      36.88   64.84   61.72   54.61   53.98
    12B      40.00   91.56   91.25   89.84   87.66
    31B      46.41   96.41   96.09   93.75   92.81
    A1 interaction: +0.547 points, SE 0.925, t 0.591, 32 repositories
    A1 per model: E2B +2.19, E4B +2.50, 12B -1.88, 31B -0.62
    
    Study B: 10236 main-cell rows (exploratory within-module files not read)
    Table 3 (Acc@1, %, mean over both orders): none / true / rewired
    E4B official (111 tasks)  real 58.6 / 59.9 / 60.4   opaque 55.0 / 52.3 / 55.0
    31B official (111 tasks)  real 74.3 / 75.2 / 75.2   opaque 69.4 / 70.3 / 71.2
    E4B lite     (260 tasks)  real 56.7 / 54.6 / 55.0   opaque 47.1 / 47.3 / 49.8
    12B official (111 tasks)  real 66.7 / 69.4 / 70.3   opaque 62.2 / 64.9 / 64.0
    31B lite     (260 tasks)  real 75.6 / 76.2 / 75.4   opaque 67.9 / 69.2 / 69.4
    B1 real-opaque, no graph       pooled   +8.019 points, n 371, SE 1.563, t 5.129
    B1 real-opaque, no graph       lite     +9.615 points, n 260, SE 2.006, t 4.793
    B1 real-opaque, no graph       official +4.279 points, n 111, SE 2.260, t 1.894
    B2 opaque true-rewired, anchor pooled   -2.155 points, n 174, SE 0.953, t -2.262
    B2 opaque true-rewired, anchor lite     -2.290 points, n 131, SE 1.195, t -1.917
    B2 opaque true-rewired, anchor official -1.744 points, n 43, SE 1.288, t -1.355
    Tasks 371; gold injected at rank 10 in 156 (42.0%); anchored 174 (46.9%)
    Registered rows, opaque, gold injected : true 45.6 vs rewired 47.1 (408 rows each)
    Registered rows, opaque, gold retrieved: true 59.7 vs rewired 62.4 (556 rows each)
    Anchored tasks only, opaque names (rows = tasks x 2 orders): true vs rewired
      E4B official 70.9 vs 74.4  (43 tasks, 86 rows per cell)
      31B official 90.7 vs 90.7  (43 tasks, 86 rows per cell)
      E4B lite     48.1 vs 50.4  (131 tasks, 262 rows per cell)
      12B official 87.2 vs 84.9  (43 tasks, 86 rows per cell)
      31B lite     65.6 vs 66.4  (131 tasks, 262 rows per cell)
"""
import argparse
import glob
import json
import math
import os
from collections import defaultdict

LET4 = "ABCD"
VERSIONS = ["G0", "G1", "G2", "G3", "G4"]
MODELS_A = ["E2B", "E4B", "12B", "31B"]


def rows(path):
    """Yield the result rows of a run file (skips the header line and rows that record an error)."""
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            if "_header" in r or "error" in r:
                continue
            yield r


def mean(xs):
    xs = list(xs)
    return sum(xs) / len(xs)


def t_summary(d):
    n = len(d)
    m = mean(d)
    sd = math.sqrt(sum((x - m) ** 2 for x in d) / (n - 1))
    se = sd / math.sqrt(n)
    return m, se, (m / se if se else float("nan")), n


def study_a(runs):
    files = sorted(glob.glob(os.path.join(runs, "studyA", "studyA_*.jsonl")))
    acc = defaultdict(list)                      # (model, version) -> row scores
    cell = defaultdict(list)                     # (repo, item, model, version) -> scores over option orders
    n = 0
    for p in files:
        for r in rows(p):
            lg = [r["logit_" + x] for x in LET4]
            top = max(lg)
            ok = int(lg[LET4.index(r["correct_letter"])] == top and lg.count(top) == 1)
            acc[(r["model"], r["version"])].append(ok)
            cell[(r["repo"], r["item_id"], r["model"], r["version"])].append(ok)
            n += 1
    print(f"Study A: {n} rows from {len(files)} files")
    print("Table 1 (accuracy, %)")
    print("model   " + "  ".join(f"{v:>6}" for v in VERSIONS))
    for m in MODELS_A:
        if (m, "G0") in acc:
            print(f"{m:<7} " + "  ".join(f"{100 * mean(acc[(m, v)]):6.2f}" for v in VERSIONS))
    inter = defaultdict(list)                    # repo -> I per (item, model)
    per_model = defaultdict(list)
    for (repo, item, model) in sorted({k[:3] for k in cell}):
        g = {v: mean(cell[(repo, item, model, v)]) for v in VERSIONS[1:] if (repo, item, model, v) in cell}
        if len(g) == 4:
            i = (g["G1"] - g["G2"]) - (g["G3"] - g["G4"])
            inter[repo].append(i)
            per_model[model].append(i)
    m, se, t, k = t_summary([mean(v) for v in inter.values()])
    print(f"A1 interaction: {100 * m:+.3f} points, SE {100 * se:.3f}, t {t:.3f}, {k} repositories")
    print("A1 per model: " + ", ".join(f"{mm} {100 * mean(per_model[mm]):+.2f}" for mm in MODELS_A if mm in per_model))


def load_b(runs):
    out = []
    for p in sorted(glob.glob(os.path.join(runs, "studyB", "studyB_*.jsonl"))):
        if os.path.basename(p).startswith("studyB_wm_"):
            continue                              # exploratory within-module runs
        for r in rows(p):
            out.append({"model": r["model"], "task": r["item_id"], "set": r["set"], "naming": r["naming"],
                        "graph": r["graph"], "order": r["order"], "anchored": bool(r["anchored"]),
                        "injected": bool(r["injected"]),
                        "correct": int(r["pred_letter"] in r["correct_letters"])})
    return out


def registered(r):
    return (r["set"] == "official" and r["model"] in ("E4B", "31B")) or (r["set"] == "lite" and r["model"] == "E4B")


def task_diffs(rs, a, b):
    """Per task: cell a minus cell b within (model, order), mean over orders, then over models."""
    c = {}
    for r in rs:
        c[(r["task"], r["set"], r["model"], r["order"], r["naming"], r["graph"])] = r["correct"]
    by_model = defaultdict(list)
    for (task, st, model, order) in sorted({k[:4] for k in c}):
        ka, kb = (task, st, model, order) + a, (task, st, model, order) + b
        if ka in c and kb in c:
            by_model[(task, st, model)].append(c[ka] - c[kb])
    by_task = defaultdict(list)
    for (task, st, model), ds in by_model.items():
        by_task[(task, st)].append(mean(ds))
    return {k: mean(v) for k, v in by_task.items()}


def show(name, d):
    for label, sel in (("pooled", None), ("lite", "lite"), ("official", "official")):
        v = [x for (task, st), x in d.items() if sel is None or st == sel]
        m, se, t, n = t_summary(v)
        print(f"{name} {label:<8} {100 * m:+.3f} points, n {n}, SE {100 * se:.3f}, t {t:.3f}")


def cell_acc(rs, **sel):
    v = [r["correct"] for r in rs if all(r[k] == x for k, x in sel.items())]
    return 100 * mean(v), len(v)


def study_b(runs):
    rs = load_b(runs)
    print(f"\nStudy B: {len(rs)} main-cell rows (exploratory within-module files not read)")
    print("Table 3 (Acc@1, %, mean over both orders): none / true / rewired")
    for model, st in (("E4B", "official"), ("31B", "official"), ("E4B", "lite"), ("12B", "official"), ("31B", "lite")):
        parts = []
        for naming in ("real", "opaque"):
            parts.append(naming + " " + " / ".join(
                f"{cell_acc(rs, model=model, set=st, naming=naming, graph=g)[0]:.1f}" for g in ("none", "true", "rewired")))
        n_tasks = len({r["task"] for r in rs if r["model"] == model and r["set"] == st})
        print(f"{model} {st:<8} ({n_tasks} tasks)  " + "   ".join(parts))
    reg = [r for r in rs if registered(r)]
    show("B1 real-opaque, no graph      ", task_diffs(reg, ("real", "none"), ("opaque", "none")))
    show("B2 opaque true-rewired, anchor", task_diffs([r for r in reg if r["anchored"]], ("opaque", "true"), ("opaque", "rewired")))
    tasks = {(r["task"], r["set"]): (r["injected"], r["anchored"]) for r in reg}
    inj = sum(1 for v in tasks.values() if v[0])
    anc = sum(1 for v in tasks.values() if v[1])
    print(f"Tasks {len(tasks)}; gold injected at rank 10 in {inj} ({100 * inj / len(tasks):.1f}%); anchored {anc} ({100 * anc / len(tasks):.1f}%)")
    for flag in (True, False):
        a = cell_acc(reg, naming="opaque", graph="true", injected=flag)
        b = cell_acc(reg, naming="opaque", graph="rewired", injected=flag)
        print(f"Registered rows, opaque, gold {'injected ' if flag else 'retrieved'}: true {a[0]:.1f} vs rewired {b[0]:.1f} ({a[1]} rows each)")
    print("Anchored tasks only, opaque names (rows = tasks x 2 orders): true vs rewired")
    for model, st in (("E4B", "official"), ("31B", "official"), ("E4B", "lite"), ("12B", "official"), ("31B", "lite")):
        a = cell_acc(rs, model=model, set=st, naming="opaque", graph="true", anchored=True)
        b = cell_acc(rs, model=model, set=st, naming="opaque", graph="rewired", anchored=True)
        print(f"  {model} {st:<8} {a[0]:.1f} vs {b[0]:.1f}  ({a[1] // 2} tasks, {a[1]} rows per cell)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--runs", default="runs", help="the repository's runs/ folder")
    args = ap.parse_args()
    study_a(args.runs)
    study_b(args.runs)
