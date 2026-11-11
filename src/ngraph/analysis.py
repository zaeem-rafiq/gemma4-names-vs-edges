"""Confirmatory and secondary analyses for Studies A and B (pre-registration, section 6).

Study A input: one row per (model, item, version, perm) with columns
    model, repo, group ("familiar"/"fresh"), item_id, version ("G0".."G4"), perm,
    and either `correct` (0/1) and `p_correct`, or letter logits `logit_A`..`logit_D`
    plus `correct_letter`.
Study B input: one row per (model, task, naming, graph, order) with columns
    model, task_id, set ("official"/"lite"), repo, naming ("real"/"opaque"),
    graph ("none"/"true"/"rewired"), order, anchored (bool), correct (0/1).

Estimands
  A1  I = [Acc(G1) - Acc(G2)] - [Acc(G3) - Acc(G4)], per repository averaged over items,
      models and permutations; one-sample t-test over repository means (two-sided);
      95% CI from a repository-cluster bootstrap. Sensitivity: GEE logistic model,
      continuous p(correct) outcome, and A1 without the parity-flagged items: items whose
      real-name (G1) and neutral-name (G2) prompts still differ by more than PARITY_TOL (2)
      tokens after the parity repair, i.e. |token_parity["G2_minus_G1"]| > 2 in the item
      files (`parity_flagged_items`).
  A2  conflict cost CC = Acc(G4) - Acc(G3); familiar minus fresh repository means (Welch).
  A3  slope of CC on log10(parameters) across model sizes, per repository (OLS over the models);
      mean slope with a one-sample t-test over repositories and a repository-cluster bootstrap CI.
      Registered axis: effective parameters (A3_PARAMS_EFFECTIVE); sensitivity axis: the GGUF
      files' text-model totals (A3_PARAMS_GGUF_TEXT), reported next to it. "Flat" is decided on
      the registered axis only. The familiar-minus-fresh difference of mean slopes is descriptive
      (estimate with a Welch 95% CI), not a registered test.
  B1  Acc@1(real) - Acc@1(opaque), graph = none; per-task differences averaged over
      orders and models; paired t-test and sign-flip permutation test; CI from a task
      bootstrap stratified by set; repository-cluster bootstrap as sensitivity.
  B2  opaque naming: Acc@1(true) - Acc@1(rewired) on anchored tasks; same tests as B1.
  B3  [true - rewired | opaque] - [true - rewired | real]; reported as an estimate with CI; its
      p-value is one of the secondary Holm tests; "no effect" only through TOST.
  B4  B1 discount for the largest model minus the smallest, official tasks.
  B5  the model-free scorer of Study B; not implemented in this module. Its metric and test are
      fixed in the Study B addendum (prereg-v1.1).
Holm over the confirmatory family (A1, B1, B2) and, separately, the secondary family.
`study_a_report` runs A1, A2 and A3 on the registered models only (REGISTERED_MODELS); rows of any
other model stay in its descriptive accuracy and letter-mass tables.
Equivalence claims only through TOST with bounds +-`bound` (TOST_BOUND = 0.05, i.e. 5 percentage
points) for every test: on the cluster- or task-level differences (A1, B1 to B4), on the
familiar-minus-fresh difference with Welch's standard error (A2), and on the mean slope for A3.
For A3 the bound is read by A3_BOUND_UNIT. "span" (the default): 5 points of CC across the models
run, i.e. a slope bound of TOST_BOUND divided by the log10 span of the parameter counts of the models
present on that axis (log10 of the largest minus log10 of the smallest). "decade" (the earlier
reading): 5 points of CC per tenfold increase in parameters. Both A3 axes use the same reading. Each
TOST is at alpha 0.05 (equivalent when the 90% interval lies inside the bounds), without
multiplicity adjustment.
"""

from __future__ import annotations

import math
import sys

import numpy as np
import pandas as pd
from scipy import stats

from .items import PARITY_TOL

LETTERS = "ABCD"
VERSIONS = ("G0", "G1", "G2", "G3", "G4")

# Models in the registered Study A tests (pre-registration, section 2). Rows of any other model (for
# example 26B-A4B under backup B-3) stay in study_a_report's descriptive tables only.
REGISTERED_MODELS = ("E2B", "E4B", "12B", "31B")

# Registered on 7 Nov 2026 (pre-registration, section 6; the A3 axes below: section 2). Equivalence bound
# for every test.
TOST_BOUND = 0.05
# Reading of TOST_BOUND for A3 (pre-registration, section 6): "span" = TOST_BOUND of CC across the models
# run, i.e. a slope bound of TOST_BOUND / span_decades with span_decades = log10(largest) - log10(smallest
# parameter count) of the models present on that axis; "decade" = TOST_BOUND of CC per tenfold increase in
# parameters (the earlier reading). The author chose "span" on 8 Nov 2026; using the other reading is a
# deviation.
A3_BOUND_UNIT = "span"
A3_BOUND_UNITS = ("span", "decade")
# A3 x-axis. Effective parameters from the Gemma 4 model card (E2B 2.3B, E4B 4.5B); 12B and 31B
# have no separate effective count, so their card totals are used.
A3_PARAMS_EFFECTIVE = {"E2B": 2.3e9, "E4B": 4.5e9, "12B": 11.95e9, "31B": 30.7e9}
# Sensitivity axis: text-model parameter totals of Google's QAT Q4_0 GGUF files, as listed by the
# Hugging Face API on 7 Nov 2026; the runner also records llama.cpp's count from each file it loads.
A3_PARAMS_GGUF_TEXT = {"E2B": 4_628_569_635, "E4B": 7_463_013_674, "12B": 11_907_350_576,
                       "31B": 30_697_345_596}


# --------------------------------------------------------------------- helpers
def add_scores(df: pd.DataFrame) -> pd.DataFrame:
    """Add `p_correct` (softmax over the four letter logits) and `correct` (argmax) when the
    input carries logits instead of scores. Ties in argmax count as wrong."""
    if "correct" in df and "p_correct" in df:
        return df
    lg = df[[f"logit_{x}" for x in LETTERS]].to_numpy(dtype=float)
    lg = lg - lg.max(axis=1, keepdims=True)
    p = np.exp(lg)
    p /= p.sum(axis=1, keepdims=True)
    idx = df["correct_letter"].map({x: i for i, x in enumerate(LETTERS)}).to_numpy()
    out = df.copy()
    out["p_correct"] = p[np.arange(len(df)), idx]
    top = lg.max(axis=1)
    n_top = (lg == top[:, None]).sum(axis=1)
    out["correct"] = ((lg[np.arange(len(df)), idx] == top) & (n_top == 1)).astype(int)
    out["pred_letter"] = [LETTERS[i] for i in lg.argmax(axis=1)]
    return out


def cluster_bootstrap_mean(values: np.ndarray, n_boot: int = 10_000, seed: int = 0, level: float = 0.95):
    """Percentile CI for the mean of cluster-level values, resampling clusters with replacement."""
    v = np.asarray(values, dtype=float)
    rng = np.random.default_rng(seed)
    draws = rng.integers(0, len(v), size=(n_boot, len(v)))
    boot = v[draws].mean(axis=1)
    a = (1 - level) / 2
    return float(np.quantile(boot, a)), float(np.quantile(boot, 1 - a))


def stratified_bootstrap_mean(values: np.ndarray, strata: np.ndarray, n_boot: int = 10_000, seed: int = 0,
                              level: float = 0.95):
    """Percentile CI for the pooled mean, resampling units within each stratum (sizes kept)."""
    v = np.asarray(values, dtype=float)
    s = np.asarray(strata)
    rng = np.random.default_rng(seed)
    groups = [np.flatnonzero(s == k) for k in sorted(set(s.tolist()))]
    boot = np.zeros(n_boot)
    for g in groups:
        draws = rng.integers(0, len(g), size=(n_boot, len(g)))
        boot += v[g][draws].sum(axis=1)
    boot /= len(v)
    a = (1 - level) / 2
    return float(np.quantile(boot, a)), float(np.quantile(boot, 1 - a))


def sign_flip_p(diffs: np.ndarray, n_perm: int = 10_000, seed: int = 0) -> float:
    """Two-sided sign-flip permutation p-value for mean(diffs) = 0 (Monte Carlo, +1 corrected)."""
    d = np.asarray(diffs, dtype=float)
    rng = np.random.default_rng(seed)
    obs = abs(d.mean())
    signs = rng.choice([-1.0, 1.0], size=(n_perm, len(d)))
    perm = np.abs((signs * d).mean(axis=1))
    return float((1 + np.sum(perm >= obs - 1e-12)) / (1 + n_perm))


def holm(pvals: dict) -> dict:
    """Holm step-down adjusted p-values."""
    keys = sorted(pvals, key=lambda k: pvals[k])
    m = len(keys)
    out, running = {}, 0.0
    for i, k in enumerate(keys):
        adj = min(1.0, (m - i) * pvals[k])
        running = max(running, adj)
        out[k] = running
    return out


def tost_mean(values: np.ndarray, bound: float = TOST_BOUND) -> dict:
    """TOST on the mean of independent cluster-level values with symmetric bounds +-bound."""
    v = np.asarray(values, dtype=float)
    n = len(v)
    m, se = v.mean(), v.std(ddof=1) / math.sqrt(n)
    if se == 0:
        p = 0.0 if abs(m) < bound else 1.0
        return {"p_tost": p, "equivalent_at_0.05": p < 0.05, "ci90": (m, m)}
    t_lo = (m + bound) / se
    t_hi = (m - bound) / se
    p_lo = 1 - stats.t.cdf(t_lo, n - 1)
    p_hi = stats.t.cdf(t_hi, n - 1)
    p = float(max(p_lo, p_hi))
    q = stats.t.ppf(0.95, n - 1)
    return {"p_tost": p, "equivalent_at_0.05": p < 0.05, "ci90": (float(m - q * se), float(m + q * se))}


def _welch(a: np.ndarray, b: np.ndarray) -> tuple[float, float, float | None]:
    """mean(a) - mean(b), Welch's standard error and the Welch-Satterthwaite degrees of freedom.
    A constant group adds nothing to the df formula (one constant group: df = n_other - 1); when both
    groups are constant the standard error is 0 and the df is None."""
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    d = float(a.mean() - b.mean())
    va, vb = a.var(ddof=1) / len(a), b.var(ddof=1) / len(b)
    se = math.sqrt(va + vb)
    if se == 0:
        return d, 0.0, None
    df = (va + vb) ** 2 / ((va ** 2 / (len(a) - 1) if va else 0.0) + (vb ** 2 / (len(b) - 1) if vb else 0.0))
    return d, se, float(df)


def tost_two_sample(a: np.ndarray, b: np.ndarray, bound: float = TOST_BOUND) -> dict:
    """TOST on mean(a) - mean(b) with Welch's standard error and degrees of freedom."""
    d, se, df = _welch(a, b)
    if se == 0:
        p = 0.0 if abs(d) < bound else 1.0
        return {"p_tost": p, "equivalent_at_0.05": p < 0.05, "ci90": (d, d)}
    p_lo = 1 - stats.t.cdf((d + bound) / se, df)
    p_hi = stats.t.cdf((d - bound) / se, df)
    p = float(max(p_lo, p_hi))
    q = stats.t.ppf(0.95, df)
    return {"p_tost": p, "equivalent_at_0.05": p < 0.05, "ci90": (float(d - q * se), float(d + q * se)),
            "df_welch": float(df)}


def _ttest_summary(values: np.ndarray, seed: int, n_boot: int) -> dict:
    v = np.asarray(values, dtype=float)
    t = stats.ttest_1samp(v, 0.0)
    lo, hi = cluster_bootstrap_mean(v, n_boot=n_boot, seed=seed)
    return {"estimate": float(v.mean()), "se": float(v.std(ddof=1) / math.sqrt(len(v))), "t": float(t.statistic),
            "df": len(v) - 1, "p": float(t.pvalue), "ci95_boot": (lo, hi), "n_clusters": len(v)}


# ---------------------------------------------------------------------- Study A
def item_version_scores(df: pd.DataFrame, outcome: str = "correct") -> pd.DataFrame:
    """Mean outcome per (repo, group, item, model, version), averaging permutations."""
    cols = ["repo", "group", "item_id", "model", "version"]
    return df.groupby(cols, as_index=False)[outcome].mean()


def interaction_per_repo(df: pd.DataFrame, outcome: str = "correct", models=None) -> pd.DataFrame:
    s = item_version_scores(df, outcome)
    if models is not None:
        s = s[s["model"].isin(models)]
    w = s.pivot_table(index=["repo", "group", "item_id", "model"], columns="version", values=outcome).reset_index()
    w = w.dropna(subset=["G1", "G2", "G3", "G4"])
    w["I"] = (w["G1"] - w["G2"]) - (w["G3"] - w["G4"])
    w["CC"] = w["G4"] - w["G3"]
    w["N_true"] = w["G1"] - w["G2"]
    w["N_swap"] = w["G3"] - w["G4"]
    return w


def a1(df: pd.DataFrame, outcome: str = "correct", n_boot: int = 10_000, seed: int = 0, bound: float = TOST_BOUND) -> dict:
    w = interaction_per_repo(df, outcome)
    repo = w.groupby("repo")["I"].mean()
    res = _ttest_summary(repo.to_numpy(), seed, n_boot)
    res["tost"] = tost_mean(repo.to_numpy(), bound)
    res["per_model"] = w.groupby("model")["I"].mean().to_dict()
    return res


def a1_gee(df: pd.DataFrame):
    """Sensitivity: GEE logistic model correct ~ names * edges * model, exchangeable within repository.
    Returns the fitted result (statsmodels)."""
    import statsmodels.api as sm
    import statsmodels.formula.api as smf

    d = df[df["version"].isin(["G1", "G2", "G3", "G4"])].copy()
    d["names_real"] = d["version"].isin(["G1", "G3"]).astype(int)
    d["edges_swap"] = d["version"].isin(["G3", "G4"]).astype(int)
    model = smf.gee("correct ~ names_real * edges_swap * C(model)", groups="repo", data=d,
                    family=sm.families.Binomial(), cov_struct=sm.cov_struct.Exchangeable())
    return model.fit()


def a2(df: pd.DataFrame, n_boot: int = 10_000, seed: int = 0, bound: float = TOST_BOUND) -> dict:
    w = interaction_per_repo(df)
    repo = w.groupby(["repo", "group"], as_index=False)["CC"].mean()
    fam = repo.loc[repo["group"] == "familiar", "CC"].to_numpy()
    fre = repo.loc[repo["group"] == "fresh", "CC"].to_numpy()
    t = stats.ttest_ind(fam, fre, equal_var=False)
    rng = np.random.default_rng(seed)
    boot = (fam[rng.integers(0, len(fam), size=(n_boot, len(fam)))].mean(axis=1)
            - fre[rng.integers(0, len(fre), size=(n_boot, len(fre)))].mean(axis=1))
    return {"estimate": float(fam.mean() - fre.mean()), "t": float(t.statistic), "p": float(t.pvalue),
            "ci95_boot": (float(np.quantile(boot, 0.025)), float(np.quantile(boot, 0.975))),
            "n_familiar": len(fam), "n_fresh": len(fre), "tost": tost_two_sample(fam, fre, bound)}


def _check_bound_unit(bound_unit: str) -> str:
    if bound_unit not in A3_BOUND_UNITS:
        raise ValueError(f"bound_unit must be one of {A3_BOUND_UNITS}, not {bound_unit!r}")
    return bound_unit


def a3_slopes(df: pd.DataFrame, params: dict) -> pd.DataFrame:
    """Per-repository OLS slope of CC (mean over items and permutations, per model) on
    log10(parameters), over the models in `params`; one row per repository (repo, group, slope).
    Repositories with fewer than two distinct parameter values are left out."""
    w = interaction_per_repo(df[df["model"].isin(params)])
    cc = w.groupby(["repo", "group", "model"], as_index=False)["CC"].mean()
    cc["x"] = np.log10(cc["model"].map(params).astype(float))
    slopes = []
    for (repo, group), g in cc.groupby(["repo", "group"]):
        if g["x"].nunique() < 2:
            continue
        b = np.polyfit(g["x"].to_numpy(), g["CC"].to_numpy(), 1)[0]
        slopes.append((repo, group, float(b)))
    return pd.DataFrame(slopes, columns=["repo", "group", "slope"])


def a3(df: pd.DataFrame, params: dict, n_boot: int = 10_000, seed: int = 0, bound: float | None = TOST_BOUND,
       bound_unit: str = A3_BOUND_UNIT) -> dict:
    """Per-repository OLS slope of CC on log10(parameters) across models (`a3_slopes`); mean slope,
    t-test, bootstrap CI and TOST on the mean slope. `params` maps model -> parameter count
    (A3_PARAMS_EFFECTIVE is the registered axis, A3_PARAMS_GGUF_TEXT the sensitivity axis).

    The TOST bound is read by `bound_unit` (default A3_BOUND_UNIT). "span": `bound` of CC across the
    models run, i.e. a slope bound of bound / span_decades, where span_decades = log10(largest) -
    log10(smallest parameter count) over the models both in `params` and present in `df`. "decade":
    `bound` of CC per tenfold increase in parameters (slope bound = bound). `res["tost"]` records
    bound_unit, span_decades, bound_slope_per_decade and bound_cc_change_over_span (slope bound x span).

    `familiar_minus_fresh` (difference of mean slopes, with a Welch 95% CI) is reported descriptively
    and is not a registered test. Raises ValueError when fewer than two distinct parameter values are
    present (no slope); `study_a_report` checks this first and leaves that A3 out."""
    _check_bound_unit(bound_unit)
    x = {math.log10(float(params[m])) for m in set(params) & set(df["model"].unique())}
    if len(x) < 2:
        raise ValueError("A3 needs at least two distinct parameter values among the models present")
    span = max(x) - min(x)
    sl = a3_slopes(df, params)
    res = _ttest_summary(sl["slope"].to_numpy(), seed, n_boot)
    fam = sl.loc[sl["group"] == "familiar", "slope"].to_numpy()
    fre = sl.loc[sl["group"] == "fresh", "slope"].to_numpy()
    if len(fam) > 1 and len(fre) > 1:
        d, se, dfw = _welch(fam, fre)
        q = stats.t.ppf(0.975, dfw) if se > 0 else 0.0
        res["familiar_minus_fresh"] = {"estimate": d, "ci95": (float(d - q * se), float(d + q * se)),
                                       "descriptive": True}
    if bound is not None:
        b = bound / span if bound_unit == "span" else bound
        res["tost"] = {**tost_mean(sl["slope"].to_numpy(), b), "bound_unit": bound_unit,
                       "span_decades": span, "bound_slope_per_decade": b, "bound_cc_change_over_span": b * span}
    return res


def capture_rate(df: pd.DataFrame, items: dict) -> pd.DataFrame:
    """Exploratory: in G3, how often the prediction is the displaced original answer B, next to the
    model's own G0 preference for B. `items` maps item_id -> {letter of B in G3, letter of B in G0}."""
    d = df[df["version"].isin(["G0", "G3"])].copy()
    d["b_letter"] = [items[i][v] for i, v in zip(d["item_id"], d["version"])]
    d["picked_b"] = (d["pred_letter"] == d["b_letter"]).astype(int)
    return d.groupby(["model", "version"])["picked_b"].mean().unstack()


# ---------------------------------------------------------------------- Study B
def _task_diffs(df: pd.DataFrame, a: dict, b: dict, subset=None) -> pd.DataFrame:
    """Per task: cell a minus cell b, matched within (model, order): only the (model, order) pairs that
    have both cells for the task enter, so models and option orders never mix across the two sides of a
    difference; then the mean over orders within each model and over models."""
    return _matched_diffs(df if subset is None else df[subset(df)], {"a": a, "b": b}, lambda m: m["a"] - m["b"])


def _matched_diffs(d: pd.DataFrame, cells: dict, diff) -> pd.DataFrame:
    key = ["task_id", "set", "repo"]
    mkey = key + [k for k in ("model",) if k in d.columns]
    okey = mkey + [k for k in ("order",) if k in d.columns]
    parts = {}
    for name, sel in cells.items():
        parts[name] = d[np.logical_and.reduce([d[k] == v for k, v in sel.items()])].groupby(okey)["correct"].mean()
    m = pd.concat(parts, axis=1).dropna()
    m["diff"] = diff(m)
    m = m.reset_index()
    cols = list(cells) + ["diff"]
    m = m.groupby(mkey)[cols].mean().reset_index()
    j = m.groupby(key)[cols].mean().reset_index()
    return j


def paired_summary(j: pd.DataFrame, n_boot: int = 10_000, n_perm: int = 10_000, seed: int = 0,
                   bound: float = TOST_BOUND) -> dict:
    d = j["diff"].to_numpy()
    t = stats.ttest_1samp(d, 0.0)
    lo, hi = stratified_bootstrap_mean(d, j["set"].to_numpy(), n_boot=n_boot, seed=seed)
    repo_means = j.groupby("repo")["diff"].agg(["sum", "count"])
    rng = np.random.default_rng(seed + 1)
    idx = rng.integers(0, len(repo_means), size=(n_boot, len(repo_means)))
    s, c = repo_means["sum"].to_numpy(), repo_means["count"].to_numpy()
    boot = s[idx].sum(axis=1) / c[idx].sum(axis=1)
    return {"estimate": float(d.mean()), "n_tasks": len(d), "t": float(t.statistic), "p": float(t.pvalue),
            "p_signflip": sign_flip_p(d, n_perm, seed), "ci95_stratified": (lo, hi),
            "ci95_repo_cluster": (float(np.quantile(boot, 0.025)), float(np.quantile(boot, 0.975))),
            "tost": tost_mean(d, bound)}


def b1(df: pd.DataFrame, **kw) -> dict:
    j = _task_diffs(df, {"naming": "real", "graph": "none"}, {"naming": "opaque", "graph": "none"})
    return paired_summary(j, **kw)


def b2(df: pd.DataFrame, **kw) -> dict:
    j = _task_diffs(df, {"naming": "opaque", "graph": "true"}, {"naming": "opaque", "graph": "rewired"},
                    subset=lambda d: d["anchored"].astype(bool))
    return paired_summary(j, **kw)


def b3(df: pd.DataFrame, **kw) -> dict:
    # all four cells matched within (model, order), so one model's opaque graph value is never set
    # against another model's real graph value
    d = df[df["anchored"].astype(bool)]
    cells = {"ot": {"naming": "opaque", "graph": "true"}, "or": {"naming": "opaque", "graph": "rewired"},
             "rt": {"naming": "real", "graph": "true"}, "rr": {"naming": "real", "graph": "rewired"}}
    j = _matched_diffs(d, cells, lambda m: (m["ot"] - m["or"]) - (m["rt"] - m["rr"]))
    return paired_summary(j, **kw)


def b4(df: pd.DataFrame, large: str, small: str, **kw) -> dict:
    off = df[df["set"] == "official"]
    jl = _task_diffs(off[off["model"] == large], {"naming": "real", "graph": "none"}, {"naming": "opaque", "graph": "none"})
    js = _task_diffs(off[off["model"] == small], {"naming": "real", "graph": "none"}, {"naming": "opaque", "graph": "none"})
    j = jl.merge(js[["task_id", "diff"]], on="task_id", suffixes=("_l", "_s"))
    j["diff"] = j["diff_l"] - j["diff_s"]
    return paired_summary(j, **kw)


def confirmatory(df_a: pd.DataFrame, df_b: pd.DataFrame, b2_confirmatory: bool = True, **kw) -> dict:
    res = {"A1": a1(df_a, **{k: v for k, v in kw.items() if k in ("n_boot", "seed", "bound")}),
           "B1": b1(df_b, **kw)}
    fam = {"A1": res["A1"]["p"], "B1": res["B1"]["p"]}
    r2 = b2(df_b, **kw)
    res["B2"] = r2
    if b2_confirmatory:
        fam["B2"] = r2["p"]
    res["holm"] = holm(fam)
    return res


# ------------------------------------------------------------------ run files
A_KEEP = ["model", "repo", "group", "item_id", "qtype", "size", "version", "perm", "correct_letter",
          "n_tokens", "letter_mass"] + [f"logit_{x}" for x in LETTERS]


# The A1 sensitivity check without parity-flagged items (pre-registration, section 6).
PARITY_FLAG_RULE = (f"|token_parity['G2_minus_G1']| > PARITY_TOL ({PARITY_TOL}) in the item files: the real-name (G1) "
                    "and neutral-name (G2) prompts still differ by more than PARITY_TOL tokens after the parity repair")


def parity_flagged_items(items_dir: str) -> set:
    """Ids of the parity-flagged items in the item files (*.json) of `items_dir`: items whose real-name
    (G1) and neutral-name (G2) prompts, in option order 1 and counted with the item files' token
    counter, still differ by more than PARITY_TOL tokens after the parity repair, i.e.
    |token_parity["G2_minus_G1"]| > PARITY_TOL. Raises FileNotFoundError when `items_dir` is not a
    folder or holds no *.json file, and ValueError, naming the file, when a *.json file there is not an
    item file (not JSON, or no "items" list whose entries have token_parity.G2_minus_G1)."""
    import glob
    import json
    import os

    if not os.path.isdir(items_dir):
        raise FileNotFoundError(f"no folder {items_dir}")
    paths = sorted(glob.glob(os.path.join(items_dir, "*.json")))
    if not paths:
        raise FileNotFoundError(f"no item files (*.json) in {items_dir}")
    out = set()
    for p in paths:
        try:
            with open(p, encoding="utf-8") as fh:
                items = json.load(fh)["items"]
            for it in items:
                if abs(it["token_parity"]["G2_minus_G1"]) > PARITY_TOL:
                    out.add(it["item_id"])
        except (KeyError, TypeError, ValueError) as e:
            raise ValueError(f"{p} is not an item file (no items with token_parity.G2_minus_G1; "
                             f"{type(e).__name__}: {str(e)[:120]})") from e
    return out


ITEMS_KEYS = ("items_folder", "items_digest", "items_digest_outside")


def recorded_items_digest(record: dict) -> bool:
    """True when a run file's report (or header) records a digest of its item folder."""
    pkg = record.get("package") or {}
    return bool(pkg.get("items_digest") or pkg.get("items_digest_outside"))


def items_dir_matches(report: dict, items_dir: str, mine: dict | None = None) -> dict:
    """{run file: match} for the per-file `report` of load_runs: True when the item folder recorded in
    the file's header (package items_folder, items_digest and items_digest_outside) equals that of
    `items_dir`, computed the same way (runner.items_state, or `mine` when given); False when it
    differs; None when no comparison is possible (a header without a digest of its item folder, or an
    items_error in the header or for `items_dir`; main refuses the second case when any run file
    recorded a digest)."""
    from .runner import items_state

    mine = items_state(items_dir) if mine is None else mine
    out = {}
    for p, r in report.items():
        pkg = r.get("package") or {}
        if mine.get("items_error") or pkg.get("items_error") or not recorded_items_digest(r):
            out[p] = None
        else:
            out[p] = all(pkg.get(k) == mine.get(k) for k in ITEMS_KEYS)
    return out


def _session(utc, record: dict) -> dict:
    pkg = record.get("package") or {}
    return {"utc": utc, "code_hash": pkg.get("code_hash"), "code_sha256_current": pkg.get("code_sha256_current"),
            "manifests": pkg.get("manifests")}


def session_warnings(report: dict) -> list[str]:
    """Warnings about the sessions of each run file in a load_runs report: a file whose first line
    records no manifest (begun before any freeze, so a pilot unless the report is itself a pilot), a
    file written in sessions with different code hashes, and a session whose code did not match
    CODE_SHA256.txt (code_sha256_current not true)."""
    out = []
    for p, r in report.items():
        ss = r.get("sessions") or []
        if not ss:
            continue
        if not ss[0].get("manifests"):
            out.append(f"{p}: its first line records no manifest in prereg/ (begun before any freeze: a pilot)")
        hashes = sorted({s["code_hash"] for s in ss if s.get("code_hash")})
        if len(hashes) > 1:
            out.append(f"{p}: written in sessions with {len(hashes)} different code hashes "
                       f"({', '.join(h[:12] + '...' for h in hashes)}; see its sessions)")
        stale = [i for i, s in enumerate(ss) if s.get("code_sha256_current") is not True]
        if stale:
            out.append(f"{p}: in session(s) {', '.join(str(i + 1) for i in stale)} of {len(ss)} the code did not "
                       "match CODE_SHA256.txt (code_sha256_current not true)")
    return out


def load_runs(paths, manifest_path: str, roles=("confirmatory",)) -> tuple[pd.DataFrame, dict]:
    """Study A rows from runner output files, one file per model: the first successful row per
    (item, version, order), the familiar/fresh group from the manifest, only repositories with
    the given roles, model tags in upper case ('e4b' -> 'E4B'), scored with `add_scores`. Also
    returns a per-file report: row counts and completeness, and from the file's header: model (the
    header's model_tag), n_jobs, thought_block and answer_prefix (from settings),
    answer_prefix_source, model_sha256 (model_gguf.sha256) and package; and `sessions`, one entry per
    session that wrote to the file (the header, then each "_resume" line) with its utc (None for the
    first), code_hash, code_sha256_current and manifests (`session_warnings` from main reads these).

    Raises ValueError, naming the files, when a file has no header line, when a file's rows carry
    more than one model value or a model other than its header's model_tag, or when two files are
    for the same model. A file's model is its header's model_tag, or its rows' model when the header
    has none, compared in upper case: a pilot or restarted file next to the confirmatory file of the
    same model is refused, and so is a file tagged 'e4b' next to one tagged 'E4B'."""
    import json

    from .runner import load_results

    with open(manifest_path) as fh:
        man = json.load(fh)
    group = {r["label"]: r["group"] for r in man["repos"] if r["role"] in roles}
    frames, report, files_of, problems = [], {}, {}, []
    for p in paths:
        rows, rep = load_results(p)
        head, resumes = rep.pop("header"), rep.pop("resumes", [])
        if head is None:
            problems.append(f"{p} has no header line")
            head = {}
        row_models = sorted({str(r.get("model")).upper() for r in rows})
        tag = str(head["model_tag"]).upper() if head.get("model_tag") is not None else None
        if len(row_models) > 1:
            problems.append(f"the rows of {p} carry more than one model ({', '.join(row_models)})")
        elif row_models and tag is not None and row_models != [tag]:
            problems.append(f"the rows of {p} are for {row_models[0]}, its header for {tag}")
        tag = tag if tag is not None else (row_models[0] if len(row_models) == 1 else None)
        if tag is not None:
            files_of.setdefault(tag, []).append(p)
        d = pd.DataFrame(rows)
        n_kept = int(d["repo"].isin(group).sum()) if len(d) else 0
        settings = head.get("settings") or {}
        report[p] = dict(rep, model=head.get("model_tag"), n_jobs=head.get("n_jobs"), rows_in_roles=n_kept,
                         complete=(head.get("n_jobs") == rep["rows"] and rep["unresolved_errors"] == 0),
                         thought_block=settings.get("thought_block"), answer_prefix=settings.get("answer_prefix"),
                         answer_prefix_source=head.get("answer_prefix_source"),
                         model_sha256=(head.get("model_gguf") or {}).get("sha256"), package=head.get("package"),
                         sessions=[_session(None, head)] + [_session(r.get("utc"), r) for r in resumes])
        frames.append(d)
    for tag, ps in sorted(files_of.items()):
        if len(ps) > 1:
            problems.append(f"{len(ps)} run files for model {tag}: {', '.join(ps)} (one run file per model; leave "
                            "pilot and restarted files out)")
    if problems:
        raise ValueError("; ".join(problems))
    df = pd.concat(frames, ignore_index=True)
    df = df[df["repo"].isin(group)].copy()
    df["group"] = df["repo"].map(group)
    df["model"] = df["model"].astype(str).str.upper()
    return add_scores(df[A_KEEP].reset_index(drop=True)), report


def _jsonable(x):
    if isinstance(x, dict):
        return {str(k): _jsonable(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_jsonable(v) for v in x]
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (np.floating,)):
        return float(x)
    if isinstance(x, (np.bool_,)):
        return bool(x)
    return x


A3_ROLES = {"A3": "registered axis: decides 'flat'",
            "A3_sensitivity": "sensitivity axis: reported next to A3; does not decide 'flat'"}


def _upper_keys(axis: dict) -> dict:
    out = {str(k).upper(): v for k, v in axis.items()}
    if len(out) != len(axis):
        raise ValueError(f"model tags {sorted(axis)} collide when upper-cased")
    return out


def study_a_report(df: pd.DataFrame, params: dict | None = None, n_boot: int = 10_000, seed: int = 0,
                   params_sensitivity: dict | None = None, bound_unit: str = A3_BOUND_UNIT,
                   flagged_items=None) -> dict:
    """Descriptive accuracy and letter mass per model and version for every model in `df`; A1 (with
    the continuous-outcome and GEE sensitivity checks), A2 and A3 on the registered models only
    (REGISTERED_MODELS). With `flagged_items` (item ids, from `parity_flagged_items`), also the A1
    sensitivity check without those items, "A1_excluding_parity_flagged" (A1 on the registered-model
    rows of the other items), and "parity_flagged_items": the number of those items among the
    registered-model rows ("n") and the rule (PARITY_FLAG_RULE).

    Model tags are upper-cased first ('e4b' -> 'E4B'), in `df` and in the keys of both axes. Rows
    of any other model (for example 26B-A4B under backup B-3) stay in the descriptive tables, are
    listed in `excluded_models` and trigger a warning on stderr. A3 runs on the registered axis
    (`params`, default A3_PARAMS_EFFECTIVE; it decides 'flat') and on the sensitivity axis
    (`params_sensitivity`, default A3_PARAMS_GGUF_TEXT; reported next to A3, does not decide 'flat'),
    each when the registered models present on that axis have at least two distinct parameter
    counts, both with the same `bound_unit` (default A3_BOUND_UNIT). Each A3 result carries its
    `role`, its `axis` and `models_not_on_axis` (registered models present in the data but missing
    from that axis; normally empty)."""
    _check_bound_unit(bound_unit)
    df = df.assign(model=df["model"].astype(str).str.upper())
    params = _upper_keys(A3_PARAMS_EFFECTIVE if params is None else params)
    params_sensitivity = _upper_keys(A3_PARAMS_GGUF_TEXT if params_sensitivity is None else params_sensitivity)
    models = sorted(df["model"].unique().tolist())
    excluded = [m for m in models if m not in REGISTERED_MODELS]
    if excluded:
        print(f"warning: {', '.join(excluded)} not in REGISTERED_MODELS {REGISTERED_MODELS}: kept in the "
              "descriptive accuracy and letter-mass tables, left out of A1, A2 and A3", file=sys.stderr)
    reg = df[df["model"].isin(REGISTERED_MODELS)]
    if reg.empty:
        raise ValueError(f"no rows of the registered models {REGISTERED_MODELS}")
    res = {"n_rows": len(df), "models": models, "excluded_models": excluded,
           "repos": {g: int(n) for g, n in df.groupby("group")["repo"].nunique().items()},
           "accuracy": df.groupby(["model", "version"])["correct"].mean().unstack().round(4).to_dict("index"),
           "letter_mass_share_ge_0.9": df.groupby("model")["letter_mass"].apply(lambda s: float((s >= 0.9).mean())).to_dict(),
           "A1": a1(reg, n_boot=n_boot, seed=seed), "A1_p_correct": a1(reg, outcome="p_correct", n_boot=n_boot, seed=seed),
           "A2": a2(reg, n_boot=n_boot, seed=seed)}
    try:
        fit = a1_gee(reg)
        res["A1_gee"] = {k: {"coef": float(fit.params[k]), "p": float(fit.pvalues[k])}
                         for k in fit.params.index if "names_real:edges_swap" in k}
    except Exception as e:  # noqa: BLE001 - reported, not hidden
        res["A1_gee"] = {"error": str(e)[:300]}
    if flagged_items is not None:
        flagged = reg["item_id"].isin(set(flagged_items))
        res["A1_excluding_parity_flagged"] = a1(reg[~flagged], n_boot=n_boot, seed=seed)
        res["parity_flagged_items"] = {"n": int(reg.loc[flagged, "item_id"].nunique()), "rule": PARITY_FLAG_RULE}
    present = sorted(reg["model"].unique().tolist())
    for key, axis in (("A3", params), ("A3_sensitivity", params_sensitivity)):
        on_axis = [m for m in present if m in axis]
        if len({axis[m] for m in on_axis}) >= 2:
            r = a3(reg[reg["model"].isin(on_axis)], axis, n_boot=n_boot, seed=seed, bound=TOST_BOUND,
                   bound_unit=bound_unit)
            r["role"] = A3_ROLES[key]
            r["axis"] = {m: axis[m] for m in on_axis}
            r["models_not_on_axis"] = [m for m in present if m not in axis]
            res[key] = r
    return res


def main(argv=None):
    import argparse
    import json

    ap = argparse.ArgumentParser(description="Study A report from runner output files")
    ap.add_argument("--runs", nargs="+", required=True,
                    help="one JSONL run file per model; a second file for the same model is refused")
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--items-dir", default="data/items",
                    help="the item folder of the runs (default: data/items; it must exist and hold the item "
                         "files, and it is refused when a run file records another one): its parity-flagged items "
                         "(|token_parity.G2_minus_G1| > PARITY_TOL) are left out in the registered A1 sensitivity "
                         "check, A1_excluding_parity_flagged")
    ap.add_argument("--params", help='JSON {"E2B": 2.3e9, ...}; default: the registered A3 axis '
                    '(effective parameters, A3_PARAMS_EFFECTIVE)')
    ap.add_argument("--params-sensitivity", help="JSON; default: the GGUF text-model totals (A3_PARAMS_GGUF_TEXT)")
    ap.add_argument("--a3-bound-unit", choices=A3_BOUND_UNITS, default=A3_BOUND_UNIT,
                    help=f"reading of the A3 TOST bound on both axes: 'span' = TOST_BOUND of CC across the models "
                         f"run, 'decade' = TOST_BOUND of CC per tenfold increase in parameters; default "
                         f"{A3_BOUND_UNIT!r} (A3_BOUND_UNIT); changing it is a deviation")
    ap.add_argument("--n-boot", type=int, default=10_000)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    import os

    from .runner import items_state

    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    try:
        flagged = parity_flagged_items(a.items_dir)
    except (FileNotFoundError, ValueError) as e:
        ap.error(f"--items-dir: {e}; the item files are needed for the registered A1 sensitivity check without "
                 "parity-flagged items")
    df, report = load_runs(a.runs, a.manifest)
    mine = items_state(a.items_dir)
    recorded = [p for p, r in report.items() if recorded_items_digest(r)]
    if mine.get("items_error") and recorded:
        ap.error(f"--items-dir {a.items_dir} cannot be digested ({mine['items_error']}), so it cannot be compared "
                 f"with the item folder that {', '.join(recorded)} recorded in their first lines; give the item "
                 "folder the runs used")
    matches = items_dir_matches(report, a.items_dir, mine)
    other = [p for p, m in matches.items() if m is False]
    if other:
        ap.error(f"--items-dir {a.items_dir} holds other item files than the run files {', '.join(other)} recorded "
                 "(items_folder, items_digest and items_digest_outside in their first lines); give the item "
                 "folder the runs used")
    for p, m in matches.items():
        report[p]["items_dir_matches"] = m
    for w in session_warnings(report):
        print(f"warning: {w}", file=sys.stderr)
    params = json.loads(a.params) if a.params else None
    params_s = json.loads(a.params_sensitivity) if a.params_sensitivity else None
    res = {"files": report, **study_a_report(df, params, n_boot=a.n_boot, params_sensitivity=params_s,
                                             bound_unit=a.a3_bound_unit, flagged_items=flagged)}
    with open(a.out, "w") as fh:
        json.dump(_jsonable(res), fh, indent=1)
    # the console summary leaves out each file's package state and sessions (both are in the written report)
    files = {p: {k: v for k, v in r.items() if k not in ("package", "sessions")} for p, r in report.items()}
    print(json.dumps(_jsonable({"files": files, "repos": res["repos"], "A1": res["A1"]}), indent=1)[:3000])
    a3_summary = {key: ({k: res[key][k] for k in ("role", "axis", "estimate", "tost")} if key in res else None)
                  for key in ("A3", "A3_sensitivity")}
    a1_flagged = {k: res["A1_excluding_parity_flagged"][k] for k in ("estimate", "p", "ci95_boot")}
    print(json.dumps(_jsonable({**a3_summary, "excluded_models": res["excluded_models"],
                                "A1_excluding_parity_flagged": a1_flagged,
                                "parity_flagged_items": res["parity_flagged_items"]}), indent=1))


if __name__ == "__main__":
    main()
