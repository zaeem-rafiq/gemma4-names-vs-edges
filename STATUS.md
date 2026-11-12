# Status

Status on 12 Nov 2026. Both pre-registered studies are complete. Study A (four Gemma 4 models, 19,200 scored prompts) ran on 9 Nov after the prereg-v1.0 hash was posted on the paper-track forum (9 Nov, 18:00:14 UTC). Study B (11,200 scored prompts: E4B and 31B on the competition tasks, E4B on SWE-bench Lite, the exploratory within-module runs, and the descriptive 12B and 31B-on-Lite runs) ran on 10 Nov after the prereg-v1.1 addendum hash was posted (10 Nov, 12:38:04 UTC). Every run file is complete, with 0 error rows and passed determinism checks; the reports are `runs/studyA/studyA_report.json` and `runs/studyB/studyB_report.json`. The exploratory controls of 11 Nov (E1 to E5, not pre-registered) are in `exploratory/`.

`README.md`, `prereg/` and the rest of the package tree are left exactly as frozen in `frozen/MANIFEST_prereg-v1.1.txt`, so `python -m ngraph.commit verify --manifest prereg/MANIFEST_prereg-v1.1.txt` still passes on this repository; their status lines describe the package at its freeze on 10 Nov. This file is the current status.

## Paper tables and the files behind them

| Paper item | Files | How to recompute |
|---|---|---|
| Table 1 and A1 to A3 (Study A) | `runs/studyA/`, `runs/studyA/studyA_report.json` | `python -m ngraph.analysis` (see `run_log/run_studyA.sh`) |
| Tables 2 and 3, B1 to B5 (Study B) | `runs/studyB/`, `runs/studyB/studyB_report.json` | `python -m ngraph.studyb_report` (see `runs/studyB/studyb_runs.sh` and `data/studyb/README.md`) |
| Figure 1 | `fig/fig1.py` | `python fig/fig1.py` |
| Recompute notebook | `notebooks/names_vs_edges_recompute.ipynb` | open and run all cells |
| Exploratory controls (E1 to E5) | `exploratory/` | `exploratory/README.md` |

## Added 12 Nov 2026

- `notebooks/names_vs_edges_recompute.ipynb`: recomputes Tables 1 and 3, A1, B1, B2, the B2 injected split and the letter-logit analysis from the run files at commit c787276. It clones the public repository.
- `reproduce_from_runs.py`: the same recomputation as a script, standard library only.
- `fig/fig1.py` and `fig/figure1.png`: Figure 1 of the paper (`cd fig && python fig1.py`, needs matplotlib).
