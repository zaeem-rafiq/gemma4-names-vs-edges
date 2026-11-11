# Gemma 4 call-graph study: code and data for Study A, and the Study B task tools

Status on 10 Nov 2026, at the freeze of the Study B addendum. The code was built and tested in a cloud workspace without model
weights or competition data. On the author's Mac, on the final question files (Decisions, item 11), E2B, E4B
and 12B passed GNG-1 with their registered answer prefixes, 31B passed with "Answer:", the prefix that the
registered rule chose for it, and the GNG-2 pilot kept the subgraph sizes (the first run and the prefix test
of 7 Nov are in `data/gng1/`, the runs of 8 Nov in `data/gng2/`). 31B was downloaded on 8 Nov, after the
author's OK, and its SHA-256 equals the one in Hugging Face's listing. The pre-registration was frozen as
`prereg-v1.0` on 9 Nov, at about 17:50 UTC; the SHA-256 of its manifest was posted on the forum on 9 Nov at
18:00:14 UTC (section 6). The confirmatory Study A runs started after that post and ended on 9 Nov; no Study B
prompt has been scored. Study B's task tools are here (rewiring, BM25 pools,
anchors, strata, gold mapping, opaque renaming with a leak scan), and since 9 and 10 Nov the adapters for the
official tasks and SWE-bench Lite, the prompt renderer and runner, and the report (B1 to B5); the Study B
addendum (`prereg-v1.1`) was frozen on 10 Nov. The code, the tests
and the checks were written and run by an AI coding assistant (Claude Code) working for the author; the checks
were automated passes of that assistant; the author approved the steps and made every decision recorded as the
author's.

## What is in this folder

| Path | What it is |
|---|---|
| `src/ngraph/extract.py` | Static call-graph extractor for Python repositories (AST; main-package rule) |
| `src/ngraph/screen.py` | Repository screening: clone, pin, history and header checks, line and edge rules |
| `src/ngraph/manifest.py` | Builds `data/repos_manifest.json` (group, role, pinned commit, licence) from the screening logs |
| `src/ngraph/names.py` | Neutral renaming: same word part gives the same pseudo-word, token counts matched, blocked strings avoided |
| `src/ngraph/items.py`, `batch.py` | Question generator (versions G0 to G4, two option orders) and the batch run over the manifest |
| `src/ngraph/tok.py`, `gguf_meta.py` | Gemma 4 token counting from a GGUF file; GGUF metadata reader (no tensors) |
| `src/ngraph/runner.py` | Letter-logit runner on llama-cpp-python: `smoke`, `study-a`, `count`, `make-probe` |
| `src/ngraph/analysis.py`, `simulate.py` | A1 to A3 and B1 to B4, Holm, TOST, bootstraps; simulated data for tests and power |
| `src/ngraph/rewire.py` | Study B "rewired" graphs: degree-preserving swaps, mirrored graphs re-mirrored, swaps kept within node-kind and edge-type classes; invariant checks |
| `src/ngraph/localize.py` | Study B tasks: gold functions from a patch, BM25 candidate pools with gold injection, issue anchors, strata S0 to S3 |
| `src/ngraph/rename.py` | Study B "opaque" condition: one seeded bijection per repository over project-defined names, identity scrubbing, offset mapping for truncation, leak scan |
| `src/ngraph/official.py`, `lite.py` | Study B adapters: the competition's tasks, graphs and snapshots; SWE-bench Lite tasks with our official-like graph view |
| `src/ngraph/studyb.py` | Study B build (tasks, pools, anchors, renaming, leak scan, prompts and their SHA-256), MC3, runs |
| `src/ngraph/studyb_report.py` | Study B report: B1 to B5, the Holm families with Study A, exploratory estimates |
| `src/ngraph/commit.py` | Hash-only time-stamp: `CODE_SHA256.txt`, the checks before a freeze, the freeze manifest and its SHA-256, folder digests, a snapshot archive and the forum post text (section 6) |
| `scripts/studyb_history_check.py`, `studyb_rename_check.py` | Dry runs of the Study B tools on public issues and fixing commits (no competition data) |
| `scripts/power_a1.py`, `power_a1_het.py`, `a3_bound_sim.py` | Simulated power for A1; the simulation behind the A3 bound table in `prereg/OPEN_ITEMS.md`, section 10 |
| `tests/` | 281 tests with the data variables of section 1 set, 150 without (item invariants and a blocked-string check on all 44 question files, runner, analysis, rewiring, localization, renaming, Study B build and report, time-stamp) |
| `third_party/llama.cpp/` | Gemma 4 vocabulary file from llama.cpp (MIT; its Gemma 4 content is under Apache-2.0 according to the model files' metadata), see its `NOTICE.md` |
| `LICENSE` | Apache License 2.0 for this package's own code and text (the author's choice of 8 Nov; Decisions, item 10) |
| `data/repos_manifest.json` | 16 + 16 confirmatory repositories, 2 pilots, 10 reserves, pinned commits, licences |
| `data/graphs/` | Call graphs of those 44 repositories: identifiers, file paths, line numbers and edges only (no code) |
| `data/items/` | 20 questions per repository, all five versions, both option orders |
| `data/items_summary.json`, `data/tokenizer_probe.json`, `data/count_confirmatory_*.json` | Generation summary, tokenizer check strings, token totals |
| `data/screening/` | Screening logs, GitHub candidate list and metadata, README review decisions |
| `data/power/` | Simulated power for A1 |
| `data/studyb_dry/` | Dry-run results of the Study B tools: identifiers, ranks and counts, plus the fixing commits' SHAs, dates and subject lines from the repositories' public history; no issue text |
| `data/gng1/` | First GNG-1 run and the answer-prefix test on the Mac (7 Nov): outputs, test script, environment, file times and hashes (its README) |
| `data/studyb/` | SHA-256 of the frozen Study B task files and their inputs, which stay outside the package (its README) |
| `data/gng2/` | GNG-1 reruns with the registered prefixes and GNG-2 pilots on the Mac (8 Nov), on the question files before the renaming of 8 Nov and after each of its three rounds (`final/`: the final question files, with 31B's GNG-1): outputs, file times and hashes (its README) |
| `prereg/PREREGISTRATION.md` | The pre-registration (a draft until the freeze; its first lines give its status) |
| `prereg/OPEN_ITEMS.md` | Evidence and reasons for the decisions taken before the freeze |
| `prereg/MANIFEST_<label>.txt` | Written at each freeze (section 6): every file here with its SHA-256; the manifest's own SHA-256 is the posted hash |
| `CODE_SHA256.txt` | SHA-256 of every file outside `data/`, `third_party/` and `prereg/` (except the top-level `runs/`, `.venv/` and `.git/`, caches, `.DS_Store` and `*.pyc` files), written by `python -m ngraph.commit code-sha256`; the pre-registration cites this file's own hash, so it leaves `prereg/` out |
| `runs/` | Model outputs; left out of `CODE_SHA256.txt` and of every manifest, so no posted hash covers them. Inputs that a freeze must cover go under `data/`, never here |

## Setup on the Mac

```bash
cd "$HOME/Documents/Projects/Gemma 4 Paper/gemma4-paper-code"
python3.14 -m venv .venv          # Homebrew Python 3.14.8; the system python3 (3.9) is too old
source .venv/bin/activate
pip install -r requirements.txt
CMAKE_ARGS="-DGGML_METAL=on" pip install --no-cache-dir llama-cpp-python==0.3.36
```

- The tests were run in the cloud with Python 3.13.18 and, for the version of 7 Nov 17:50 UTC, on the Mac
  with Python 3.14.8. The Mac's installed versions are in `data/gng1/mac_environment/pip_freeze.txt`. The
  Metal install line above built llama-cpp-python 0.3.36 with Metal on the Mac.
- Model files: keep them outside this folder (on the Mac, in `../models/`). Every file in this folder is
  hashed and archived at a freeze, and a file over 100 MB stops the freeze. File names, sizes and SHA-256 are
  in the pre-registration, section 10, and in `data/gng2/mac_environment/model_files_SHA256SUMS.txt` (the copy
  in `data/gng1/` was made before 31B was downloaded). Check each new file's SHA-256 on download; `study-a`
  records it again in the run file.

## 1. Check the setup (no model needed)

```bash
export PYTHONPATH=src
export NGRAPH_ITEMS_DIR=data/items NGRAPH_GRAPHS_DIR=data/graphs
export NGRAPH_TOKENIZER_GGUF=third_party/llama.cpp/ggml-vocab-gemma-4.gguf
python -m pytest -q tests                        # expected: 281 passed
```

- `test_package_code_sha256_is_current` fails after any edit to a file listed in `CODE_SHA256.txt` (this
  README, the code, the tests, the scripts) until `python -m ngraph.commit code-sha256` is run again.
- Where `sha256sum` is not on the PATH, one test (the comparison with the shell tools) is skipped;
  `shasum -a 256` gives the same hashes.
- The commands below write their outputs under `runs/`. Each tool makes its output folder when it is
  missing, as in a fresh copy unpacked from a snapshot (section 6).

## 2. Smoke test per model (GNG-1)

```bash
python -m ngraph.runner smoke --model ../models/gemma-4-E4B_q4_0-it.gguf --tag E4B \
  --items-dir data/items --manifest data/repos_manifest.json \
  --probe data/tokenizer_probe.json --out runs/smoke_E4B.json
```

It uses only the two pilot repositories (trio, langextract) and checks:

- exactly one BOS token at the start, and the special tokens;
- the model's tokenizer against the vocab file on 4,040 strings (`tokenizer_probe`);
- letter mass: the share of A-D and A-J prompts where the answer letters (with and without a
  leading space) hold at least 0.9 of the next-token probability (pass: at least 95%);
- the same A-D and A-J prompts with the other empty-thought-block setting
  (`AD_other_thought_block`, `AJ_other_thought_block`; `--n-alt` limits how many);
- the probability of the `<|channel>` token at the answer position (`p_channel` in each summary),
  which shows whether a model wants to open a thought channel instead of answering;
- repeatability (same prompt twice) and prompt speed, and projected Study A hours with a 1.3 margin;
- llama.cpp's parameter count of the file (`model_n_params`, for the A3 sensitivity axis);
- `package`: the code hash and the item digest it ran with (section 3).

`checks_ok` covers the BOS, special-token and tokenizer checks; `own_setting_passes` and
`other_setting_passes` the letter mass under each thought-block setting. `gng1_pass` needs
`checks_ok` and `own_setting_passes`.

Answer prefix. The model's turn is pre-filled with the prefix registered for its `--tag` in `ANSWER_PREFIX`
(`runner.py`): "Answer:" for E2B and 12B, none for E4B, set after the first GNG-1 run on 7 Nov by the
per-model rule (no prefix if the model passes without one, otherwise the first candidate that passes), which
the author chose on 8 Nov at 00:58 UTC (pre-registration, section 7). The smoke test scores the pilot prompts
under every candidate in `PREFIX_CANDIDATES` (none, "Answer:", "The correct option is") with the model's own
thought-block setting and reports `prefix_scan`, `prefix_rule_choice` (the first candidate that passes) and
`prefix_matches_rule` (whether the prefix it ran with is that choice); it also records the tag, the model
file's SHA-256, the prompts' count and seed (`prompts`) and the repositories (`repos`). Its other verdicts
(`own_setting_passes`, `thought_block_decision`, `gng1_pass`) are for the prefix it ran with. A model without
a registered prefix (31B so far) is smoke-tested first with none; when the rule chooses another candidate,
smoke runs a second time with `--answer-prefix <the choice>` (the GNG-1 run with the chosen prefix), and the
model's Study A run takes the choice from that second file with `--prefix-from` (section 3). Without either, a
Study A run refuses to start; `--answer-prefix` sets any other prefix, which is a deviation.
`thought_block_decision` applies the pre-registered rule: `keep` the per-size setting if its letter mass
passes; `switch (log a deviation)` only if it fails and the other setting passes; otherwise `neither passes`.
A failed token or tokenizer check never leads to a switch.
Under the GNG-1 fallback (pre-registration, section 7; the author's choice of 8 Nov, 16:57 UTC) the setting is
switched only when no candidate passes under the per-size setting (`prefix_rule_choice` null): smoke then runs
again with `--thought-block` set to the other setting; if its `prefix_rule_choice` is a non-empty prefix,
smoke runs once more with that `--thought-block` and `--answer-prefix <choice>`; the Study A run then uses
`--thought-block <other setting> --prefix-from <the smoke file run with the choice>`. A model for which no
candidate passes under either setting is excluded and the exclusion logged. The switch is entered in the
deviation log by hand: a smoke file run with `--thought-block` set to the other setting reports `keep` when it
passes under that setting, and nothing in the run files marks the switch as a deviation. GNG-1 is run again on
every model with its registered prefix before any confirmatory run.

## 3. Study A run

```bash
python -m ngraph.runner study-a --model ../models/gemma-4-E4B_q4_0-it.gguf --tag E4B \
  --items-dir data/items --manifest data/repos_manifest.json --out runs/studyA_E4B.jsonl
```

- Confirmatory runs start only after the `prereg-v1.0` hash is visible on the forum (section 6;
  pre-registration, section 7), and they run from an unpacked copy of the snapshot (section 6, "After
  posting"). Anything run before that is a pilot: give it a file name that the report's `--runs` list will
  not pick up (for example `runs/pilot_E4B.jsonl`), because the report refuses two files for one model
  (section 4). A file begun before the freeze is never continued after it: its first line records no
  manifest, so a later session that finds `prereg/MANIFEST_prereg-v1.0.txt` is refused, and so is a session
  in which a manifest recorded in the first line is missing or changed (a later manifest, the addendum's,
  may be added).
- A model without a registered prefix (31B so far) takes the prefix rule's choice from its GNG-1 smoke file
  (the per-model rule that the author chose on 8 Nov). Smoke runs first with no prefix; when its
  `prefix_rule_choice` is not the empty string (no prefix), smoke runs again with that choice, and the second
  file is the one given to study-a:

      python -m ngraph.runner smoke --model ../models/gemma-4-31B_q4_0-it.gguf --tag 31B \
        --items-dir data/items --manifest data/repos_manifest.json \
        --probe data/tokenizer_probe.json --out runs/smoke_31B_no_prefix.json
      python -m ngraph.runner smoke --model ../models/gemma-4-31B_q4_0-it.gguf --tag 31B \
        --items-dir data/items --manifest data/repos_manifest.json \
        --probe data/tokenizer_probe.json --answer-prefix "Answer:" --out runs/smoke_31B.json
      python -m ngraph.runner study-a --model ../models/gemma-4-31B_q4_0-it.gguf --tag 31B \
        --items-dir data/items --manifest data/repos_manifest.json \
        --prefix-from runs/smoke_31B.json --out runs/studyA_31B.jsonl

  ("Answer:" stands for whatever the first file chose. For 31B on the final question files these runs were
  made on 8 Nov: the rule chose "Answer:", and the second file is `data/gng2/final/gng1_rename3_31B.json`.)
  The run refuses unless the smoke file is for the same tag and the same model file (SHA-256); its token
  checks and its tokenizer probe passed (so the smoke command needs `--probe`); it used the same thought-block
  setting; it scored the registered GNG-1 pilot prompts (40 prompts, seed 0, the manifest's pilot
  repositories: run smoke without `--n` or `--repos`, and give study-a `--manifest`) drawn from the same item
  files; its `prefix_rule_choice` is not null (null means that no candidate passed under that thought-block
  setting: see the GNG-1 fallback in the pre-registration's section 7; an empty string is the rule's choice of
  no prefix); and it was run with that choice and passed GNG-1 (`prefix_matches_rule` and `gng1_pass` true),
  so the first file is refused when the choice is a prefix. The run file records the smoke file's SHA-256
  (`answer_prefix_source`). This is the registered rule, so it is not a deviation, and it needs no code change
  after the freeze.
- Defaults by `--tag` (read case-insensitively; the run file stores it in upper case): E2B and E4B get
  both option orders and no pre-filled thought block; 12B and 31B get option order 1 and the pre-filled
  empty thought block (Google's per-size chat templates; sources in the `runner.py` docstring).
- Resumable: after any interruption run the same command again. Failed prompts are retried. A session that
  continues a run file must use the same model file (by SHA-256), the same settings (`n_ctx`, `n_batch`,
  `n_ubatch`, `n_gpu_layers`, `flash_attn`, `enable_thinking`, thought block, answer prefix and
  llama-cpp-python version), the same jobs (`--perms`, repositories, `--versions`, number of prompts) and
  the same item files; otherwise it is refused, and a new file is needed. It is also refused when the item
  folder could not be digested (`items_error`), because the item files cannot then be compared. A change of
  code, platform, Python version or the source of the answer prefix between sessions is recorded in the
  file's `_resume` line, not refused.
- The first line of the file records the settings, where the answer prefix came from (`answer_prefix_source`),
  the model file's SHA-256, its GGUF metadata and chat-template hash, llama.cpp's parameter count of the file,
  the letter token ids, the jobs (`perms`, `repos`, `versions`, `n_jobs`), the platform, and `package`: the
  SHA-256 of `CODE_SHA256.txt` and whether it still matches the code, the digest of the item folder (the value
  `python -m ngraph.commit digest data/items` prints) and the SHA-256 of each `MANIFEST_*.txt` under
  `prereg/`. A run made with the frozen files records the code hash and item digest that the `prereg-v1.0`
  manifest lists and the pre-registration cites (after the addendum, in a row of its own; section 6); a code
  hash in no posted manifest, or `code_sha256_current` false, means that other code ran.

## 4. Study A report

```bash
python -m ngraph.analysis --runs runs/studyA_*.jsonl --manifest data/repos_manifest.json \
  --items-dir data/items --out runs/studyA_report.json
```

- One run file per model: two files for the same model (tags compared in upper case), for example a pilot
  or a restarted file next to the confirmatory one, are refused, so list only the confirmatory files. The
  report copies from each file's first line its thought-block setting, answer prefix and the prefix's
  source, the model file's SHA-256 and the `package` hashes.
- `--items-dir` must be the item folder the runs used: the report is refused when a run file records
  another one (`items_folder`, `items_digest`, `items_digest_outside`), or when the folder cannot be
  digested while a run file recorded a digest, and each file's entry says whether it matched
  (`items_dir_matches`; null when the file records no digest of its item folder).
- Each file's entry lists its sessions (`sessions`: the first line, then each `_resume` line, with the
  time, code hash, `code_sha256_current` and manifests). The report warns on stderr about a file whose first
  line records no manifest (begun before any freeze: a pilot), a file written with more than one code hash,
  and a session whose code did not match `CODE_SHA256.txt`.
- A1 is also reported without the items whose real-name and neutral-name prompts still differ by more than
  2 tokens after the parity repair (`A1_excluding_parity_flagged`; the flags are read from `--items-dir`;
  27 of the 640 confirmatory items in the current item set).
- A1, A2 and A3 use only the registered models (E2B, E4B, 12B, 31B; `REGISTERED_MODELS`). Rows of any
  other model, such as 26B-A4B under backup B-3, appear only in the descriptive accuracy and letter-mass
  tables, are listed under `excluded_models` and trigger a warning.
- A3 uses the registered axis by default (settled 7 Nov): effective parameters, that is E2B 2.3B and
  E4B 4.5B from the Gemma 4 model card, and the card totals 11.95B and 30.7B for 12B and 31B, which
  have no separate effective count (`A3_PARAMS_EFFECTIVE` in `analysis.py`). The report repeats A3 on
  the GGUF files' text-model totals as the sensitivity check (`A3_PARAMS_GGUF_TEXT`, as listed by
  Hugging Face; the runner records llama.cpp's own count of each file as `model_n_params`, so compare
  the two before the analysis). "Flat" is decided on the registered axis only; each A3 result carries its
  `role`. The familiar-minus-fresh difference of mean slopes is descriptive (estimate and Welch 95%
  interval, no test). `--params` and `--params-sensitivity` override the axes; using them would be a
  deviation.
- Every test reports TOST with bounds of ±5 percentage points (`TOST_BOUND`): on the repository or task
  differences for A1 and B1 to B4, on the familiar-minus-fresh difference with Welch's standard error for
  A2, and for A3 on the mean slope. Each TOST is at alpha 0.05 (a 90% interval inside the bounds), not
  adjusted for multiplicity. B5's test is fixed in the Study B addendum.
- A3's bound is 5 points of conflict cost across the models run: the slope bound is `TOST_BOUND` divided by
  the log10 span of the parameter counts of the models present on that axis (E2B to 31B: 1.1254 decades on the
  effective axis, 0.8217 on the GGUF axis), so both axes test the same 5-point total change. The author chose
  this reading (`A3_BOUND_UNIT = "span"`) on 8 Nov at 00:58 UTC. The earlier reading, 5 points per tenfold
  increase in parameters, remains available with `--a3-bound-unit decade`, and using it would be a deviation.
  Each A3 result records the bound unit, the span in decades, the slope bound per decade and the change in
  conflict cost that bound allows over the span.

## 5. Study B tools (before the competition data)

Rewire a graph (node-link JSON; `--mirror-first` builds the official-like mirrored view of one of
our graphs; `--kind-key` names the node attribute with library/test/doc kinds once the official
format is known):

    python -m ngraph.rewire data/graphs/requests.json --mirror-first --group-key module \
        --seed 1 --out runs/requests_rewired.json --report runs/requests_rewired_report.json

The command exits non-zero unless every invariant holds (per-node degree per edge type, kinds of
neighbours, edge-type counts, self-loops, no parallel edges) and all swaps were made. On the 44
graphs in `data/graphs` (10 x |E| swaps, seed 1, rewire 0.2.0), all swaps complete and all
invariants hold in both views:

| View | Engine | Edges left in place (median, largest) | Edges inside one module (median before, after) |
|---|---|---|---|
| Mirrored (official-like) | networkx `double_edge_swap` | 1.5%, 6.4% | 67%, 6% |
| Directed (as extracted) | our two-edge directed swap | 2.4%, 8.0% | 67%, 6% |

Rewiring therefore also removes module locality; the paper should say so. For directed graphs,
networkx's `directed_edge_swap` was tried first: it hit its attempt cap on 12 of the 44 graphs and
left a median 43.8% of edges in place (13 and 47.6% on the extractor 0.2.0 graphs), so since rewire
0.2.0 directed graphs use our own two-edge swaps by default (`--engine networkx` still runs it).

Dry runs on the repositories' own history (commits whose message says they fix an issue; the
issue title and body as the query; graph at the parent commit; needs `gh` for the issue texts):

    python scripts/studyb_history_check.py --repo-dir <clone of requests> --gh-repo psf/requests \
        --since 2017-06-01 --issues-cache runs/requests_issues.json --out runs/requests_history.json
    python scripts/studyb_rename_check.py --repo-dir <clone of requests> --repo requests --org psf \
        --issues-cache runs/requests_issues.json --out runs/requests_rename_check.json

Results on 7 Nov with extractor 0.3.0 (small samples from repository history, not SWE-bench or the
competition tasks, so only a check that the tools work and a rough preview). Extractor 0.2.0 gave the
same figures except requests' strata (2 / 0 / 0 / 5): two requests tasks move from S3 to S1, because the
narrower `setattr` rule restores `HTTPAdapter.send`'s calls to `request_url` and `get_connection` (the
gold functions of those tasks), and `HTTPAdapter.send` is a traceback anchor in both issues.

| Repository | Pairs with library gold | Gold in BM25 top 10 | Anchored | S0 / S1 / S2 / S3 |
|---|---|---|---|---|
| requests | 7 | 71% | 86% | 2 / 2 / 0 / 3 |
| flask | 22 | 91% | 45% | 8 / 0 / 1 / 13 |
| httpx | 10 | 60% | 70% | 3 / 1 / 0 / 6 |
| fastapi | 5 | 80% | 60% | 2 / 0 / 0 / 3 |

The renamer check renamed 50 issues and the source of 1,215 graph functions with zero hard leaks.
Residual cues it reports and does not remove: identity words inside other tokens (`.flaskenv`,
`flasktest`) and project methods whose names are protected (for example `Response.json`, because
`json` is a standard-library module name, and `get`, an attribute of `dict`).

These commands write to `runs/`, which no posted hash covers. The frozen Study B inputs (task list,
candidate pools, anchors, renaming maps, and each task's tool outputs on the true, rewired and within-module
graphs) stay outside the package, because they derive from the competition's data and from SWE-bench Lite,
which we do not redistribute; `data/studyb/README.md` lists each file and input with its SHA-256. The
rewired graphs are not stored or hashed: they are regenerated with seed 1 (pre-registration, section 11,
row 8).

Rules that the code fixes (pre-registration items): see the docstrings at the top of
`rewire.py`, `localize.py` and `rename.py` (one sentence of the `rename.py` docstring is wrong: pytest's
"py", shorter than 3 characters, is never renamed; pre-registration, section 13).

## 6. Freeze and public time-stamp (hash-only)

Chosen on 7 Nov: at each freeze only one SHA-256 is posted on the paper-track forum, from the author's own
Kaggle account, under the plain title "Pre-registration hash". The files stay private until the writeup,
which releases them with `src/ngraph/commit.py` so that anyone can recompute the hash. Every file in this
folder at a freeze is listed and will be released, so keep model files, competition data, issue texts and
anything personal outside it.

Before the Study A freeze (the hash is due by Mon 9 Nov 23:59 UTC; pre-registration, section 7), from this folder:

1. Settle the open items in the pre-registration's last section and delete that section. Replace the draft
   line at the top with `Status: prereg-v1.0, frozen <date> (UTC)`. Fill every bracketed TBD marker (Study B's
   TBD-B markers may stay until the addendum). Rewrite every passage that still calls a decision open, with
   the decision, who made it and when; step 3 lists each such passage by its draft-only marker (on 8 Nov,
   about 18:35 UTC, none is left outside that last section).

   The GNG-1 runs with the registered prefixes, 31B's GNG-1 and the GNG-2 pilots are in `data/gng2/` (those on
   the final question files in its `final/` folder), which has a row in section 10. Do all this before step 2:
   this README, `runner.py` and `analysis.py` are in `CODE_SHA256.txt`.
2. Regenerate the question files with the command under "Numbers" into `runs/items_check` (about 3 to 4
   minutes; the tests regenerate only 7 of the 44 files) and check that
   `diff -r data/items runs/items_check && cmp data/items_summary.json runs/items_check_summary.json` prints
   nothing. Then `python -m ngraph.commit code-sha256` (prints `code_hash`) and
   `python -m ngraph.commit digest data/items`; write both values into section 10 of the pre-registration.
3. `python -m ngraph.commit manifest --label prereg-v1.0 --check-only` lists, in one run, everything that
   still blocks the freeze: `CODE_SHA256.txt` out of date, a cited hash that is no longer current, no Status
   line, TBD markers, draft-only text (the strings in `DRAFT_ONLY` in `commit.py`) in `prereg/*.md`, this
   README, `runner.py` or `analysis.py`, a manifest already at the target path, an earlier trial manifest
   anywhere under `prereg/`, every refused file (over 100 MB, a symbolic link, a name with a line break)
   and every hidden file or folder (a name starting with `.`, such as `.env` or `.github/`; every listed
   file is released). Fix and repeat until it reports `"ok": true`.
4. Run the tests (section 1).

Freeze:

    python -m ngraph.commit manifest --label prereg-v1.0
    python -m ngraph.commit verify --manifest prereg/MANIFEST_prereg-v1.0.txt
    python -m ngraph.commit snapshot --manifest prereg/MANIFEST_prereg-v1.0.txt \
        --out ../frozen/prereg-v1.0.tar.gz

`snapshot` re-checks every file, then reads each listed file once, checks it against its manifest line and
only then writes it into the archive (outside this folder); if anything changed in between it stops and
leaves no archive. It prints the post text from the manifest bytes it archived. Copy the snapshot off the
Mac as well and note its `archive_sha256`. Post nothing before the snapshot exists.

Posting (the author, from their own Kaggle account): start a new topic with the printed title and text,
exactly as printed. Then copy the hash back from the forum page and check it:

    python -m ngraph.commit verify --manifest prereg/MANIFEST_prereg-v1.0.txt --expect <hash copied from the forum>

Never edit or delete the post (whether Kaggle shows edits was not verified); post no other hash anywhere;
note the post's URL and time for the paper, outside this folder (a file added here would show up as added
in the addendum's manifest). `verify` also lists files that are here but not in the manifest (`not_listed`,
and `not_listed_refused` for symbolic links, names with line breaks or files over 100 MB); neither makes the
check fail.

After posting, until every confirmatory Study A run is finished: run Study A (any smoke rerun, the runs
and the report) from an unpacked copy of the snapshot, not from this folder, so that every run file records
the frozen code while Study B is built here. From the folder that holds this one, `models/` and `frozen/`:

    mkdir studyA-v1.0 && tar -xzf frozen/prereg-v1.0.tar.gz -C studyA-v1.0
    cd studyA-v1.0 && source ../gemma4-paper-code/.venv/bin/activate && export PYTHONPATH=src
    python -m ngraph.commit verify --manifest prereg/MANIFEST_prereg-v1.0.txt --expect <hash copied from the forum>

then the commands of sections 2 to 4 there (`../models/` is the same model folder, and the tools make
`runs/`). If Study A has to run in this folder instead, edit no file listed in `CODE_SHA256.txt` and do not
run `code-sha256` until those runs are done.

Study B addendum (by Tue 10 Nov 18:00 UTC): list the frozen Study B inputs and their SHA-256 in
`data/studyb/README.md` (the files stay outside the package); copy every
GNG-1 smoke file made after the first freeze (for example a rerun) from the unpacked copy's `runs/` into
`data/gng2/after_freeze/` and list each, with its SHA-256 and write time, in `data/gng2/README.md`, so that
the addendum's hash covers them; fill the TBD-B markers; change the Status line to
`Status: prereg-v1.1, frozen <date> (UTC)`; in section 10, keep the `prereg-v1.0` code hash, which every Study
A run file records, in a row of its own whose text names no package file (for example "Study A code as frozen
in prereg-v1.0 and recorded by the Study A runs"), so that step 2 can write the new code hash into the Code
row; then repeat steps 2 to 4 with
`--label prereg-v1.1 --follows <hash of the first post, copied from the forum>`, then:

    python -m ngraph.commit manifest --label prereg-v1.1 --follows <hash of the first post>
    python -m ngraph.commit verify --manifest prereg/MANIFEST_prereg-v1.1.txt
    python -m ngraph.commit snapshot --manifest prereg/MANIFEST_prereg-v1.1.txt \
        --out ../frozen/prereg-v1.1.tar.gz

The addendum's manifest lists the first manifest, names its hash in a `# follows:` header line, and lists in
`# changed:`, `# added:` and `# removed:` header lines every file that differs from the first freeze, so the
two posts form a chain that shows what changed; `verify` checks that the counts in its `# changes since` line
and the label in `# follows:` match. Its post is a reply in the first topic (`snapshot` and `post` print the
reply text; `post --reply` refuses a manifest that follows nothing). After the reply is posted, copy its hash
back from the forum and check it with
`python -m ngraph.commit verify --manifest prereg/MANIFEST_prereg-v1.1.txt --expect <hash copied from the forum>`.
Each Study A file (the pre-registration's section 11 says which files those are) in the changed, added or
removed lists is entered in the pre-registration's deviation log; for this README and the pre-registration,
which also hold Study B text, compare their Study A parts (named in that section) with the copies in the first
snapshot and enter each change. A model without a registered prefix (31B) needs no code change, whether its
GNG-1 comes before or after the freeze: its run takes the rule's choice with `--prefix-from` (section 3).

Details:

- A manifest lists every file in this folder except itself, the top-level `runs/`, `.venv/` and `.git/`
  folders, caches (`__pycache__`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`) at any depth, and
  `.DS_Store` and `*.pyc` files; one `sha256sum` line each (path from this folder, sorted bytewise), after
  a short `#` header that is part of the hashed text. Symbolic links and names with a line break (such as
  the `Icon` file Finder makes for a custom folder icon) are refused, and a listed file or folder whose name
  starts with `.` stops the freeze.
- `manifest` never overwrites an existing manifest, except with `--force`, which is only for a manifest
  that was never posted and that no later manifest follows. The first freeze must find no other manifest
  anywhere under `prereg/`, so `--check-only` is the way to try a freeze in advance.
- `python -m ngraph.commit diff --manifest prereg/MANIFEST_prereg-v1.0.txt` lists the files changed, added
  or removed since a freeze.
- Anyone can re-check with standard tools: `sha256sum prereg/MANIFEST_prereg-v1.0.txt` gives the posted
  hash, and `grep -v '^#' prereg/MANIFEST_prereg-v1.0.txt | sha256sum -c` checks every file
  (`shasum -a 256` where `sha256sum` is missing).
- Later edits here make an earlier manifest impossible to re-check from the live folder, which is why the
  snapshots are kept. To re-check one, unpack it into an empty folder, go there and run
  `PYTHONPATH=src python -m ngraph.commit verify --manifest prereg/MANIFEST_prereg-v1.0.txt --expect <hash>`.
  `--root <folder>` works before or after the subcommand, and a relative `--manifest` is read from it.
- The release at the writeup publishes the snapshots unchanged, so readers get exactly the hashed files.

## Numbers from the vocab tokenizer (not from a model)

- 32 confirmatory repositories x 20 questions x 5 versions = 3,200 prompts per option order.
  Mean prompt about 600 tokens with the chat template (E4B: G1 to G4 about 719, G0 about 118); longest
  2,679 (12B, with the thought block and "Answer:"; 31B without a prefix: 2,677).
- Study A prompt tokens with each model's thought-block setting and registered answer prefix (counted on 8
  Nov): about 3.85M for E2B (3,848,820) and 3.84M for E4B (3,836,020), two option orders each; about 1.94M for
  12B (1,937,210); for 31B about 1.93M without a prefix (1,930,810) and 1.94M with "Answer:" (1,937,210). All
  use the vocab file's chat template (the large-model template), so each model's own template may give
  slightly different counts; the smoke test checks that each model's tokenizer matches.
- Token balance between real-name and neutral-name versions of a question: at most 2 tokens apart
  for 96% of questions, more than 10 apart for 1.7% (largest gap 55 tokens, tornado, where one class
  name repeats 51 times). The gap is identical in G3 vs G4, so it cancels in the A1 interaction.

Rebuild the token totals and the tokenizer probe after any change to the question files:

    V=third_party/llama.cpp/ggml-vocab-gemma-4.gguf
    python -m ngraph.runner count --model $V --tag E4B --items-dir data/items \
        --manifest data/repos_manifest.json --out data/count_confirmatory_E4B.json   # and --tag 31B
    python -m ngraph.runner make-probe --model $V --tag vocab --items-dir data/items \
        --manifest data/repos_manifest.json --out data/tokenizer_probe.json

Regenerate the question files with the package's generator. With the default `--roles` and `--per-cell` this
writes the 44 files of `data/items/` and `data/items_summary.json` again, byte for byte (the run time per
repository is printed, not stored):

    python -m ngraph.batch --manifest data/repos_manifest.json --graphs-dir data/graphs \
        --tokenizer-gguf third_party/llama.cpp/ggml-vocab-gemma-4.gguf \
        --out-dir runs/items_check --summary runs/items_check_summary.json

## Decisions

Evidence and reasons for each item: `prereg/OPEN_ITEMS.md`. Items 1 to 6 were settled on 7 Nov 2026; items 2
to 6 are the author's choices of that afternoon (17:38 UTC). Items 7 and 8 were put to the author that evening
and are the author's choices of 8 Nov (00:58 UTC); item 11 was put to the author on 8 Nov and is the author's
choice of 01:43 UTC that day, widened by the author's choices of 05:39 UTC and 16:57 UTC. Items 9, 10 and 12
were put to the author on 8 Nov and are the author's choices of 16:57 UTC (items 9 and 12) and 16:58 UTC (item
10) that day.

1. Settled: the empty thought block. Google's per-size templates add it for 12B, 26B-A4B and 31B
   and not for E2B and E4B (sources in the `runner.py` docstring); `--thought-block auto` follows
   that rule, and the smoke test checks it on each model with the pre-registered switch rule above.
2. Settled (the author's choice): the A3 parameter axis is effective parameters, with the GGUF files'
   text-model totals as a sensitivity check (both registered in `analysis.py`; section 4).
3. Settled (the author's choice): the extractor's `setattr` rule (extractor 0.3.0). Version 0.2.0 blocked
   every `self.m()` edge in a class and its subclasses when any method called `setattr(<first
   parameter>, ...)`, also for a literal attribute name, in `__setstate__` (which only restores
   pickled state) and for a static method's first parameter. Now a literal name blocks only that
   name, `__setstate__` and static methods are ignored, and any other name expression still blocks
   (rule 3 in the `extract.py` docstring). This adds 220 edges in 4 confirmatory repositories
   (requests 170 to 200, httpx 323 to 339, daily_stock_analysis 6,800 to 6,878, nanobot 7,559 to
   7,655; confirmatory and pilot total 76,424 to 76,644) and replaces their 80 questions; the other
   40 graphs keep the same nodes and edges and their question files are byte-identical. Screening
   ran with 0.2.0, so the node and edge counts in `data/repos_manifest.json` and `data/screening/`
   are the screening-time counts; 0.3.0 changes no screening outcome (the 12 repositories excluded
   for fewer than 150 edges have the same counts under 0.3.0). The rule does not affect the official
   graphs, but it does apply to our graphs for the SWE-bench Lite arm of Study B.
4. Settled (the author's choice): a second Study B null that rewires only within module pairs is
   exploratory: opaque naming only, pre-specified in the Study B addendum, reported as an estimate with a
   95% interval and no test, run after the confirmatory cells, cut first if time runs short, and dropped
   if the official graphs carry no module information. Not built yet (Study B build).
5. Settled (the author's choice): equivalence ("no effect") only through TOST with bounds of ±5
   percentage points, for every test; `analysis.py` also reports it for A2 and A3 (section 4).
6. Settled (the author's choice): the public time-stamp is a hash-only forum post with a plain title
   (section 6).
7. Settled (the author's choice, 8 Nov): the answer-prefix rule after the first GNG-1 run is per model, no
   prefix first, which gives E2B "Answer:", E4B none and 12B "Answer:" (`ANSWER_PREFIX`); a model without a
   registered prefix (31B) takes the rule's choice from its smoke file (`--prefix-from`, with the smoke run
   made with that choice; section 3). The rule was proposed after the first GNG-1 results were seen and before
   any confirmatory run (pre-registration, section 7; `data/gng1/`). E2B, E4B and 12B passed GNG-1 again with
   these prefixes on 8 Nov, and 31B passed with "Answer:", the rule's choice for it, all on the final question
   files (`data/gng2/final/`).
8. Settled (the author's choice, 8 Nov): the ±5 pp bound applies to A3 as 5 points across the models run
   (`A3_BOUND_UNIT = "span"`; section 4; `prereg/OPEN_ITEMS.md`, section 10).
9. Settled (the author's choice, 8 Nov, 16:57 UTC): the GNG-1 fallback (pre-registration, section 7): try the
   prefix candidates in order under the per-size thought-block setting; if none passes, try them in the same
   order under the other setting (`smoke --thought-block`), which is then used and logged as a deviation; a
   model for which no candidate passes under either setting is excluded from the confirmatory tests and the
   exclusion is logged.
10. Settled (the author's choice, 8 Nov, 16:58 UTC): this package's own code and text are under the Apache
    License 2.0 (`LICENSE`, the same text as `third_party/llama.cpp/LICENSE-Apache-2.0.txt`); third-party
    files (`third_party/`) and the data taken from the repositories keep their own licences (each repository's
    licence is in `data/repos_manifest.json`, `license_spdx`).
11. Settled (the author's choices, 8 Nov): questions whose generated names contain an offensive-looking string
    are named again with the next seeds (design detail 2). At 01:43 UTC the author chose to rename ten: six
    had a clear match ("raper", "nazizes", "TeNaZi", "pedo", "PEDok", "pisso") and four a borderline one,
    found with the shorter stems "nig", "milf" and "sperm" ("nigi", "nigu", "posmilfas", "disperme"). A later
    check found blocked strings split by "_" or "-" (for example "kir_na_zi" and "kil_ra_pe") and words that
    the generator can write but the list lacked (for example "fuk", the neutral repository name in one
    question); at 05:39 UTC the author chose to check each name also with "_" and "-" removed and to add such
    words, which named 76 more questions again. A further scan, with another word list, found "fok"
    (Afrikaans), "pula" (Romanian) and "puki" (Malay); at 16:57 UTC the author chose to add "puki" to the list
    and to block "fok" and "pula" as whole pseudo-words (they remain inside longer ones, such as "fokal" and
    "pulal"), which named 11 more questions again, and to keep the rest of its finds, among them short
    syllables that are vulgar in some language (for example "kok" and "dik"). In all, 97 questions were named
    again (71 confirmatory, 18 reserve and 8 pilot questions). Only their neutral names, and so their G2 and
    G4 texts, changed; the token totals and the tokenizer probe were rebuilt (Numbers). GNG-1 and the GNG-2
    pilot were run again on the final question files (E2B, E4B and 12B passed, and 31B with "Answer:"; pilot
    accuracy 0.6625, so the sizes stay). Evidence: `prereg/OPEN_ITEMS.md`, section 11.
12. Settled (the author's choice, 8 Nov, 16:57 UTC): B2's rule (B2 stays confirmatory only if at least 35% of
    the Study B tasks are anchored) is checked when the Study B tasks are frozen, in the Study B addendum (by
    Tue 10 Nov 18:00 UTC, the date set on 9 Nov; item 13) and before any Study B result, instead of at GNG-2
    (Sun 8 Nov 12:00 UTC), because the competition data had not been downloaded by then (pre-registration,
    section 2).

13. Settled (the author's instruction, 9 Nov, 17:26 UTC, and the author's OK of the dates at 17:28 UTC):
    neither study shrinks. The Study A hash was not posted by Sun 8 Nov 23:59 UTC, and by the first freeze's
    checkpoints Study A would then have kept only one-hop items and three sizes, and Study B only the official
    tasks with B1 on E4B. Nothing had been posted and no confirmatory run had started, so the plan was changed
    before its time-stamp: the hash is due by Mon 9 Nov 23:59 UTC, the Study B addendum by Tue 10 Nov 18:00
    UTC, the confirmatory runs by Tue 10 Nov 18:00 UTC (Study A) and Wed 11 Nov 18:00 UTC (Study B), with a
    hard stop at Thu 12 Nov 06:00 UTC; a later post delays the runs and drops nothing (cells unfinished at the
    hard stop are reported as "not run"); backup B-4 is removed (pre-registration, section 7;
    `prereg/OPEN_ITEMS.md`, row 15). A manifest made on 8 Nov at 18:54 UTC from the earlier text was never
    posted; its SHA-256 is given in `prereg/OPEN_ITEMS.md`.

## Design details fixed while building the code (cited by the pre-registration)

1. Graph lines are in one seeded random order per question, shared by all versions, instead of
   sorted order (sorting would put real and neutral names in different orders).
2. Neutral names: each word part maps to one pseudo-word within a question; case pattern, underscores, hyphens
   and digits are kept; Python's own protocol dunders are kept and every other dunder is renamed; pseudo-words
   are matched to Gemma 4 token counts; common English words are rejected with wordfreq 3.1.1 (Zipf 3.0 or
   more; 4.5 or more for two-letter strings); then single word parts are re-drawn until the whole real-name
   and neutral-name prompts differ by at most 2 tokens (up to 900 draws). A question whose finished names
   contain a blocked string (`OFFENSIVE_SUBSTRINGS` in `names.py`: offensive words, compared in lower case, in
   each name as written and with "_" and "-" removed; dots between the parts of a qualified name, and digits,
   are not removed), or one of whose pseudo-words is, in lower case, "fok" or "pula" (`WHOLE_WORD_BLOCKED`),
   is named again, names and re-draws together, with seeds that add the attempt number
   (`neutral_naming_attempt` in its item record); 97 questions were, 87 at the first new attempt and 10 at the
   second (Decisions, item 11).
3. Files: only the repository's main package (the top-level folder with the most function
   definitions, plus any folder with at least 20% of them); tests, docs, examples, benchmarks,
   scripts and vendored code are excluded. A `src/` folder is a package only if it has
   `__init__.py` or the code imports `src.`.
4. Fresh repositories: README review criteria R1 to R5 (collections of skills or plugins;
   tutorials and courses; generated code; stated ports or rewrites of pre-2025 code; model code
   largely copied from earlier code), and files whose first 40 lines carry a copyright year before
   2025 are skipped (the repository is excluded if they exceed 25% of its Python lines).
5. The pilot is the 17th passing repository of each group.
6. Token counts come from llama.cpp's Gemma 4 vocab file, checked against each model file.
7. Folder names that are not Python identifiers (for example `options-strategy`) stay as module
   path components (affects deer-flow and the reserve Vibe-Trading).
8. Rewiring: when nodes carry kinds or edges carry several types, swaps run in our own loop (same
   acceptance rule as networkx: no self-loops, no parallel edges) so that each swap stays within one
   kind pair and edge type; networkx's `double_edge_swap` runs only for a mirrored graph with a
   single class. Directed graphs always use our two-edge swaps, not networkx's `directed_edge_swap`
   (see section 5 for why). |E| counts the swapped edges (unordered pairs for a mirrored graph).
   Self-loops stay; edge attributes that are constant within a class are copied, others dropped.
9. BM25: k1 1.2, b 0.75, Lucene-style idf; document = qualified name plus function source; the
   query is the set of tokens in the issue (identifiers split on underscores and case, lower case,
   a short stop list). Ties at the cut are broken by node id.
10. Gold: removed lines are located in the base file and added lines in the patched file; a span
    starts at the first decorator; a line in a nested function counts for the enclosing node;
    functions created by the patch are not gold.
11. Anchors: mentions are identifiers in inline code, dotted paths, CamelCase, snake_case and
    `_private` names, and traceback frames; matching tries the full trailing name, then the package
    plus trailing name; the match must be unique and have degree 50 or less. S3 includes tasks
    without anchors; an `anchored` flag is reported separately.
12. Opaque renaming: names shorter than 3 characters, generic folder names (src, tests, docs ...),
    builtins, keywords, dunders, standard-library module names, attributes of builtin types and
    every name the repository reads from a third-party import stay unchanged. In prose, a project
    name is renamed only if it is identifier-shaped, part of a dotted path or not a common English
    word (wordfreq Zipf below 3); inline code, fenced code and traceback lines count as code. The
    repository, organisation and package names are scrubbed in every case pattern, also as whole
    sub-tokens of other names (`FLASK_APP`); URLs that contain them become `<url>`; GitHub handles
    in prose become `@user`. From 0.1.3 a top-level package named by a common English word, a generic
    word (`util`, `utils`) or fewer than 3 characters is not scrubbed unless it is the repository or
    organisation name (pylint's `script`, sphinx's `utils`, pytest's `py`); `script` and `utils` stay
    renamable module names, and `py`, shorter than 3 characters, stays unrenamed. The leak scan ignores the fixed words of the tool-output format and counts a
    project-defined interpreter word (`ipython`, `input`, `stdin`, `string`, `console`) inside an
    interpreter-made frame file name (`<ipython-input-…>`, `<stdin>`) under `frame` instead of hard.
