import json, sys, time
sys.path.insert(0, "src")
from ngraph.simulate import power_a1
rows = []
t0 = time.time()
for vsd in (0.25, 0.5, 1.0):
    for acc in ((0.85, 0.80), (0.70, 0.65)):
        for d in (0.0, 0.04, 0.05, 0.056, 0.07):
            r = power_a1(d, n_sims=1000, alpha=0.05/3, seed=1, version_sd=vsd,
                         acc_true_neutral=acc[0], acc_swap_neutral=acc[1], readability=0.02)
            r.update(version_sd=vsd, acc_true_neutral=acc[0], acc_swap_neutral=acc[1])
            rows.append(r)
            print(json.dumps({k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()}), flush=True)
json.dump(rows, open("data/power/power_a1.json", "w"), indent=1)
print("secs", round(time.time() - t0))
