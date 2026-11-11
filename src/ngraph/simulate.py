"""Simulated Study A and Study B data, used to test the analysis code and to estimate power.

All numbers produced here are simulation estimates under the stated assumptions, not
predictions about Gemma 4. The pilot recalibrates the variance inputs before the freeze.

Study A model (logit scale):
    logit p = beta_v + u_repo + w_item,model + e_item,model,version + offset_model
    u ~ N(0, repo_sd^2); w has SD item_sd and correlation model_corr between models;
    e ~ N(0, version_sd^2). Optional heterogeneity of the interaction itself: per-repository
    and per-item deviations (SDs delta_repo_sd, delta_item_sd, probability scale, mean zero).
    beta_v is calibrated so that the marginal accuracy of version v
    equals its target:
        G2 = acc_true_neutral, G4 = acc_swap_neutral,
        G1 = G2 + readability + delta/2, G3 = G4 + readability - delta/2, G0 = acc_no_graph,
    so the expected interaction I = (G1-G2) - (G3-G4) is exactly delta.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
from scipy import optimize, stats

VERSIONS = ("G0", "G1", "G2", "G3", "G4")
MODELS = ("E2B", "E4B", "12B", "31B")
PERMS = {"E2B": 2, "E4B": 2, "12B": 1, "31B": 1}


def _expit(x):
    return 1.0 / (1.0 + np.exp(-x))


def calibrate_intercept(target: float, sigma: float) -> float:
    """beta such that E[expit(beta + sigma Z)] = target for Z ~ N(0, 1) (Gauss-Hermite)."""
    x, w = np.polynomial.hermite_e.hermegauss(60)
    w = w / math.sqrt(2 * math.pi)
    f = lambda b: float(np.sum(w * _expit(b + sigma * x)) - target)  # noqa: E731
    return optimize.brentq(f, -20, 20)


def version_targets(acc_true_neutral=0.85, acc_swap_neutral=0.80, readability=0.02, delta=0.0, acc_no_graph=0.45):
    t = {"G0": acc_no_graph, "G1": acc_true_neutral + readability + delta / 2, "G2": acc_true_neutral,
         "G3": acc_swap_neutral + readability - delta / 2, "G4": acc_swap_neutral}
    for k, v in t.items():
        if not 0.0 < v < 1.0:
            raise ValueError(f"target accuracy for {k} out of range: {v}")
    return t


def simulate_a_arrays(n_repos=32, n_items=20, models=MODELS, perms=PERMS, repo_sd=0.4, item_sd=1.0,
                      model_corr=0.6, version_sd=0.5, model_offsets=None, delta_repo_sd=0.0, delta_item_sd=0.0,
                      seed=0, **targets):
    rng = np.random.default_rng(seed)
    M, P, V = len(models), max(perms[m] for m in models), len(VERSIONS)
    t = version_targets(**targets)
    sigma = math.sqrt(repo_sd ** 2 + item_sd ** 2 + version_sd ** 2)
    beta = np.array([calibrate_intercept(t[v], sigma) for v in VERSIONS]).reshape(1, 1, 1, 1, V)
    u = rng.normal(0, repo_sd, size=(n_repos, 1, 1, 1, 1))
    a = rng.normal(size=(n_repos, n_items, 1, 1, 1))
    b = rng.normal(size=(n_repos, n_items, M, 1, 1))
    w = item_sd * (math.sqrt(model_corr) * a + math.sqrt(1 - model_corr) * b)
    e = rng.normal(0, version_sd, size=(n_repos, n_items, M, 1, V))
    off = np.zeros((1, 1, M, 1, 1)) if model_offsets is None else np.asarray(
        [model_offsets.get(m, 0.0) for m in models]).reshape(1, 1, M, 1, 1)
    # heterogeneity of the interaction between repositories and items (mean zero), applied on the
    # logit scale as +h/2 to G1 and -h/2 to G3 with h = deviation / (pbar (1 - pbar))
    h = np.zeros((n_repos, n_items, 1, 1, 1))
    if delta_repo_sd or delta_item_sd:
        pbar = float(np.mean([t[v] for v in ("G1", "G2", "G3", "G4")]))
        dev = rng.normal(0, delta_repo_sd, size=(n_repos, 1, 1, 1, 1)) + rng.normal(
            0, delta_item_sd, size=(n_repos, n_items, 1, 1, 1))
        h = dev / (pbar * (1 - pbar))
    shift = np.zeros((1, 1, 1, 1, V))
    shift_g1, shift_g3 = shift.copy(), shift.copy()
    shift_g1[..., 1] = 0.5
    shift_g3[..., 3] = -0.5
    p = _expit(beta + u + w + e + off + h * (shift_g1 + shift_g3))
    p = np.broadcast_to(p, (n_repos, n_items, M, P, V))
    correct = (rng.random((n_repos, n_items, M, P, V)) < p).astype(float)
    mask = np.zeros((1, 1, M, P, 1))
    for j, m in enumerate(models):
        mask[0, 0, j, : perms[m], 0] = 1.0
    return {"correct": correct, "p": np.asarray(p), "mask": mask, "models": list(models), "targets": t}


def a1_from_arrays(sim) -> np.ndarray:
    """Per-repository mean of I (items and models equally weighted, permutations averaged)."""
    c, mask = sim["correct"], sim["mask"]
    s = (c * mask).sum(axis=3) / mask.sum(axis=3)  # (R, N, M, V)
    i = (s[..., 1] - s[..., 2]) - (s[..., 3] - s[..., 4])
    return i.mean(axis=(1, 2))


def simulate_a_df(seed=0, **kw) -> pd.DataFrame:
    sim = simulate_a_arrays(seed=seed, **kw)
    c, p, mask, models = sim["correct"], sim["p"], sim["mask"], sim["models"]
    R, N, M, P, V = c.shape
    rows = []
    for r in range(R):
        group = "familiar" if r < R // 2 else "fresh"
        for n in range(N):
            for j, m in enumerate(models):
                for q in range(P):
                    if mask[0, 0, j, q, 0] == 0:
                        continue
                    for v in range(V):
                        rows.append((m, f"repo{r:02d}", group, f"repo{r:02d}/{n:03d}", VERSIONS[v], q + 1,
                                     int(c[r, n, j, q, v]), float(p[r, n, j, q, v])))
    return pd.DataFrame(rows, columns=["model", "repo", "group", "item_id", "version", "perm", "correct", "p_correct"])


def power_a1(delta: float, n_sims: int = 1000, alpha: float = 0.05 / 3, seed: int = 0, **kw) -> dict:
    rej, est, ses = 0, [], []
    for s in range(n_sims):
        sim = simulate_a_arrays(seed=seed * 100_003 + s, delta=delta, **kw)
        v = a1_from_arrays(sim)
        t = stats.ttest_1samp(v, 0.0)
        rej += t.pvalue < alpha
        est.append(v.mean())
        ses.append(v.std(ddof=1) / math.sqrt(len(v)))
    return {"delta": delta, "alpha": alpha, "power": rej / n_sims, "mean_estimate": float(np.mean(est)),
            "mean_se": float(np.mean(ses)), "n_sims": n_sims}


# ---------------------------------------------------------------------- Study B
B_CELLS = [("real", "none"), ("opaque", "none"), ("real", "true"), ("real", "rewired"),
           ("opaque", "true"), ("opaque", "rewired")]


def b_targets(base_real=0.35, discount=0.07, graph_gain_opaque=0.09, graph_gain_real=0.05, rewired_cost=0.0):
    """Marginal Acc@1 per (naming, graph) cell; on anchored tasks the graph gain applies to `true`."""
    return {("real", "none"): base_real, ("opaque", "none"): base_real - discount,
            ("real", "true"): base_real + graph_gain_real / 2, ("real", "rewired"): base_real - graph_gain_real / 2 - rewired_cost,
            ("opaque", "true"): base_real - discount + graph_gain_opaque / 2,
            ("opaque", "rewired"): base_real - discount - graph_gain_opaque / 2 - rewired_cost}


def simulate_b_df(official_repo_sizes=(60, 45, 12, 1), lite_repo_sizes=(114, 77, 23, 23, 16, 16, 11, 6, 5, 4, 3, 2),
                  official_models=("E4B", "31B"), lite_models=("E4B",), anchored_frac=0.4, task_sd=1.5,
                  repo_sd=0.4, cell_sd=0.4, seed=0, **targets) -> pd.DataFrame:
    """Binary Acc@1 per (model, task, naming, graph, order). Graph effects act on anchored tasks only;
    on anchor-free tasks true and rewired share the no-graph accuracy of their naming."""
    rng = np.random.default_rng(seed)
    t = b_targets(**targets)
    sigma = math.sqrt(task_sd ** 2 + repo_sd ** 2 + cell_sd ** 2)
    beta = {k: calibrate_intercept(v, sigma) for k, v in t.items()}
    rows = []
    for set_name, sizes, models in (("official", official_repo_sizes, official_models),
                                    ("lite", lite_repo_sizes, lite_models)):
        for ri, n in enumerate(sizes):
            repo = f"{set_name}_r{ri}"
            u = rng.normal(0, repo_sd)
            for k in range(n):
                task = f"{repo}/t{k:03d}"
                anchored = bool(rng.random() < anchored_frac)
                z = rng.normal(0, task_sd)
                for m in models:
                    zm = z + rng.normal(0, 0.3)
                    for naming, graph in B_CELLS:
                        cell = (naming, graph) if (anchored or graph == "none") else (naming, "none")
                        lp = beta[cell] + u + zm + rng.normal(0, cell_sd)
                        pr = _expit(lp)
                        for order in (1, 2):
                            rows.append((m, task, set_name, repo, naming, graph, order, anchored,
                                         int(rng.random() < pr)))
    return pd.DataFrame(rows, columns=["model", "task_id", "set", "repo", "naming", "graph", "order", "anchored", "correct"])
