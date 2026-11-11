import json, sys
sys.path.insert(0, "src")
from ngraph.simulate import power_a1
rows = []
for acc in ((0.85, 0.80), (0.70, 0.65)):
    for drs, dis in ((0.0, 0.0), (0.03, 0.0), (0.05, 0.0), (0.03, 0.10), (0.05, 0.15)):
        for d in (0.0, 0.05, 0.056):
            r = power_a1(d, n_sims=600, alpha=0.05/3, seed=2, version_sd=0.5, acc_true_neutral=acc[0],
                         acc_swap_neutral=acc[1], readability=0.02, delta_repo_sd=drs, delta_item_sd=dis)
            r.update(acc=acc, delta_repo_sd=drs, delta_item_sd=dis)
            rows.append(r)
            print(acc, drs, dis, d, "power", round(r["power"], 3), "se", round(r["mean_se"], 4), "est", round(r["mean_estimate"], 4), flush=True)
json.dump(rows, open("data/power/power_a1_heterogeneity.json", "w"), indent=1)
