# Study B frozen inputs (kept outside this package)

The Study B task files were built on 10 Nov 2026 with renamer 0.1.3, extractor 0.3.1 and `studyb.py` 0.1.0
(Python 3.14.8; build checks in the pre-registration, sections 5 and 13).
They derive from the competition's data (Kaggle competition rules; not redistributed) and from SWE-bench Lite
and clones of its repositories (the dataset card shows no licence), so they stay outside this package, and
only their SHA-256 is frozen here. Paths are relative to the project folder that holds this package.

## Outputs

| Set | File | Bytes | SHA-256 |
|---|---|---|---|
| official | `studyb-frozen/official/tasks.json` | 1,024,176 | `7681800b8dac23f893e5409fe18cb25f0ccbf4b153fae67965aeb8b86695b3cb` |
| official | `studyb-frozen/official/graphs_report.json` | 225,174 | `ae9b4cb11e0755fc370f25995bbcafd9f6ec9dac448b182d65656f12ce20dbad` |
| official | `studyb-frozen/official/rename_maps.json.gz` | 108,494 | `d3ff254e2e0cb92f81257fa7631490f543e2758b7bce7a6e9262d253345981bb` |
| official | `studyb-frozen/official/mc3.json` | 1,356 | `21288d1f1e61b43bd0f7f9963218573fedd6a940fb441fc6627daf295137ac9b` |
| Lite | `studyb-frozen/lite/tasks.json` | 2,835,970 | `52528ac15c66dc62ed8d9ac8a3b0eabf37d5f6493a3e1c3c23df1c8a3a30e497` |
| Lite | `studyb-frozen/lite/graphs_report.json` | 663,048 | `cb94d8cfeade1beeb0d1ce31e49fa8dd99c539c04f3e08c946eb09a7909e5b0d` |
| Lite | `studyb-frozen/lite/rename_maps.json.gz` | 2,200,892 | `af93b86db9eaedc55e6a1add8224e78830cb812dd6d3bfccc43b90bb2d48db59` |
| both | `run_log/studyb_build_report.md` (build report: summaries, checks, comparison with renamer 0.1.2) | | `5add08cf99c02029efd13d88df3505582ce820fd98169cfd9ed5ce037ee74bf6` |

## Inputs

| Input | File | Bytes | SHA-256 |
|---|---|---|---|
| competition tasks | `competition-data/tasks.jsonl` | 1,984,455 | `e4b3fd60f69dbc2b9213e54eeb9636db78aefe92c1d06269d73d9f5f8f3c8ad6` |
| competition graphs (127 files; SHA-256 of the sorted `shasum -a 256 ./file` lines) | `competition-data/graphs/` | 422,050,109 | `1b5e464d0bf9ebf7a0f2cc8e292be963b67f88446493669285b825c823e8d342` |
| competition snapshots (129 files; same digest rule) | `competition-data/snapshots/` | 21,496,844,379 | `f7d14a68d0bbcfef9b098772813534a3cba86921fcd1b69937193dbf42d9c357` |
| SWE-bench Lite, test split | `lite/swebench_lite_test.jsonl` | 3,690,305 | `c8b7405cefc53d1a138956fcd791ed63003ac8fcd6a6b1c25988ad8e52f5d49f` |
| SWE-bench Lite, dev split | `lite/swebench_lite_dev.jsonl` | 244,823 | `c446a167a6feac6179be2db8c2f144a97d0e1a4fff8495149c2ad89adb9d22e1` |

The task files hold each task's pool, anchors, per-prompt SHA-256 and tool outputs on the true, rewired and
within-module graphs; the rewired graphs themselves are not stored or hashed (they are regenerated with
seed 1, from the official graphs and, for Lite, from our extractor's graph of each snapshot), their invariant
reports are in `graphs_report.json`, and at run time every prompt is rebuilt from the task files and the
frozen inputs (task statements, snapshots or clones) and checked against its frozen SHA-256 before scoring.

Commands, run from this package with `PYTHONPATH=src` and `P` the project folder:

    python -m ngraph.studyb build --set official --data "$P/competition-data" \
        --vocab third_party/llama.cpp/ggml-vocab-gemma-4.gguf --out "$P/studyb-frozen/official"
    python -m ngraph.studyb mc3 --data "$P/competition-data" --out "$P/studyb-frozen/official/mc3.json"
    python -m ngraph.studyb build --set lite --lite-test "$P/lite/swebench_lite_test.jsonl" \
        --lite-dev "$P/lite/swebench_lite_dev.jsonl" --repos-dir "$P/lite-repos" \
        --vocab third_party/llama.cpp/ggml-vocab-gemma-4.gguf --out "$P/studyb-frozen/lite"

The Lite snapshots are `git archive` of each task's base commit from clones of the 17 repositories in
`lite-repos/`; the base commits are in the two Lite files. The vocab file used for token counts is in this
package (`third_party/llama.cpp/ggml-vocab-gemma-4.gguf`).
