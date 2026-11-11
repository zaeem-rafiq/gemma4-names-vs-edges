"""Simulation (not data): agreement of the A3 TOST verdicts on the two axes under a flat CC trend,
for the "span" and "decade" readings of the 5 pp bound. Uses ngraph.simulate.simulate_a_arrays with
its default variance assumptions (32 repositories x 20 items, perms 2/2/1/1); flat trend = no model
offsets, so CC has the same expectation for every model. Vectorised slopes and TOST; cross-checked
against ngraph.analysis.a3 on a few seeds. The table in prereg/OPEN_ITEMS.md, section 10, comes from

    PYTHONPATH=src python scripts/a3_bound_sim.py 4000      # about 40 s in our cloud workspace
"""

import math
import sys

import numpy as np
from scipy import stats

from ngraph import analysis as an
from ngraph import simulate as sim

N_SIMS = int(sys.argv[1]) if len(sys.argv) > 1 else 4000
BOUND = 0.05


def cc_per_repo_model(s):
    c, mask = s["correct"], s["mask"]
    m = (c * mask).sum(axis=3) / mask.sum(axis=3)  # (R, N, M, V)
    return (m[..., 4] - m[..., 3]).mean(axis=1)  # (R, M)


def slopes(cc, x):
    xc = x - x.mean()
    return (cc - cc.mean(axis=1, keepdims=True)) @ xc / (xc @ xc)


def tost_p(v, b):
    n = len(v)
    m, se = v.mean(), v.std(ddof=1) / math.sqrt(n)
    return max(1 - stats.t.cdf((m + b) / se, n - 1), stats.t.cdf((m - b) / se, n - 1))


def run(models, n_sims, seed0):
    xe = np.log10([an.A3_PARAMS_EFFECTIVE[m] for m in models])
    xg = np.log10([an.A3_PARAMS_GGUF_TEXT[m] for m in models])
    spans = {"eff": xe.max() - xe.min(), "gguf": xg.max() - xg.min()}
    eq = {(u, a): 0 for u in ("span", "decade") for a in ("eff", "gguf")}
    disagree = {"span": 0, "decade": 0}
    for i in range(n_sims):
        s = sim.simulate_a_arrays(n_repos=32, n_items=20, models=models, seed=seed0 + i)
        cc = cc_per_repo_model(s)
        sl = {"eff": slopes(cc, xe), "gguf": slopes(cc, xg)}
        for u in ("span", "decade"):
            v = {}
            for a in ("eff", "gguf"):
                b = BOUND / spans[a] if u == "span" else BOUND
                v[a] = tost_p(sl[a], b) < 0.05
                eq[(u, a)] += v[a]
            disagree[u] += v["eff"] != v["gguf"]
    return spans, {k: v / n_sims for k, v in eq.items()}, {k: v / n_sims for k, v in disagree.items()}


def crosscheck(models, seeds):
    """The vectorised slopes and TOST p equal the package's a3 on the same simulated data."""
    xe = np.log10([an.A3_PARAMS_EFFECTIVE[m] for m in models])
    xg = np.log10([an.A3_PARAMS_GGUF_TEXT[m] for m in models])
    for sd in seeds:
        cc = cc_per_repo_model(sim.simulate_a_arrays(n_repos=32, n_items=20, models=models, seed=sd))
        df = sim.simulate_a_df(n_repos=32, n_items=20, models=models, seed=sd)
        for params, x in ((an.A3_PARAMS_EFFECTIVE, xe), (an.A3_PARAMS_GGUF_TEXT, xg)):
            for u in ("span", "decade"):
                r = an.a3(df, params, n_boot=50, bound_unit=u)
                v = slopes(cc, x)
                b = BOUND / (x.max() - x.min()) if u == "span" else BOUND
                assert abs(r["estimate"] - v.mean()) < 1e-12, (r["estimate"], v.mean())
                assert abs(r["tost"]["p_tost"] - tost_p(v, b)) < 1e-12
    return True


if __name__ == "__main__":
    for models in (("E2B", "E4B", "12B", "31B"), ("E2B", "E4B", "12B")):
        print("crosscheck", models, crosscheck(models, (1, 2, 3)))
        spans, eq, dis = run(models, N_SIMS, 900_000)
        print(f"models {models}: n_sims {N_SIMS}; span decades eff {spans['eff']:.4f}, gguf {spans['gguf']:.4f}")
        for u in ("span", "decade"):
            print(f"  {u:6s}: P(equivalent) eff {eq[(u, 'eff')]:.3f}, gguf {eq[(u, 'gguf')]:.3f}; "
                  f"verdicts disagree {dis[u]:.3f}")
