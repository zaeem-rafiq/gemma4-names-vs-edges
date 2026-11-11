# Pre-registration: names vs edges in Gemma 4 code-graph reading

Status: prereg-v1.1, frozen 10 Nov 2026 (UTC). It follows prereg-v1.0, frozen 9 Nov 2026, whose manifest
SHA-256 c4d82769f7607766066ffa8986dd16576499dc7b835cf3d94b8f9a9766be5ced was posted on 9 Nov 2026 at
18:00:14 UTC; this version is the Study B addendum.

prereg-v1.0 was written on 7 Nov 2026 with the Study A code and the Study B task tools and frozen on 9 Nov
2026; this addendum and the rest of the Study B code (adapters, prompt renderer and runner, report) were added
on 9 and 10 Nov. The internal study plan it started from is not released, and every registered rule is stated here or in the package. The points of
Study B that prereg-v1.0 left open (marked TBD-B there) are filled in this version, before any Study B result;
section 13 lists the Study B rules that the code fixes. Numbers called
"estimate" come from simulations or arithmetic, not from our own runs.

Public time-stamp (chosen 7 Nov): hash-only. At the freeze, every file of this package is listed with its
SHA-256 in `prereg/MANIFEST_prereg-v1.0.txt` (section 10; at this addendum's freeze, in
`prereg/MANIFEST_prereg-v1.1.txt`), and only that manifest's SHA-256 is posted on the
paper-track forum from the author's own Kaggle account, under the plain title "Pre-registration hash", so
that nothing reveals the topic. The hashed files are released with the paper. In the paper this is a
"publicly time-stamped pre-registration", not a public one. Its limits: the post fixes when this set of
files existed, but it cannot show that no other set was hashed elsewhere; whether Kaggle marks later edits
of a post was not verified, so the post is never edited; and a manifest's hash cannot be written into the
files it covers, so the paper quotes it from the forum post.
Tools: the code, the tests, the checks and this text were written and run by an AI coding assistant (Claude
Code) working for the author; the checks were automated passes of that assistant; the author approved the
steps and made every decision recorded as the author's.
Authors: Zaeem Khan.

## 1. Question

When Gemma 4 reads a code call graph, how much does it rely on the identifiers (function, class and module
names) and how much on the edges? Does reliance on identifiers hide what a code graph is worth on familiar
public repositories?

## 2. Hypotheses

### Confirmatory (Holm over three tests: thresholds 0.0167, 0.025, 0.05)

- **A1 (Study A).** Interaction I = [Acc(G1) − Acc(G2)] − [Acc(G3) − Acc(G4)], pooled over E2B, E4B, 12B
  and 31B. G1: true edges, real names. G2: true edges, neutral names. G3: one counterfactual edge swap, real
  names. G4: the same swap, neutral names. Two-sided test; predicted direction positive.
- **B1 (Study B).** Acc@1 with real identifiers minus Acc@1 with consistent opaque renaming, with no graph
  context. Pooled over E4B and 31B on the official tasks and E4B on SWE-bench Lite. Two-sided; predicted
  positive. Read as an upper bound on a "familiarity discount", because renaming removes name meaning as
  well as memory.
- **B2 (Study B).** With identifiers renamed, Acc@1 with the official graph's output minus Acc@1 with the same
  output from a degree-preserving rewired copy, on anchored tasks. Two-sided; predicted positive. **Rule:** B2
  stays confirmatory only if at least 35% of tasks are anchored, measured when the Study B tasks are frozen
  (Study B addendum, by Tue 10 Nov 18:00 UTC; section 7), before any Study B result; otherwise it moves to the
  secondary family. (Earlier drafts measured it at checkpoint GNG-2, Sun 8 Nov 12:00 UTC; the competition data
  had not been downloaded by then, and the author moved the check on 8 Nov at 16:57 UTC, before the freeze.)
  Holm then runs over A1 and B1 in the confirmatory family and over six secondary tests.

### Secondary (Holm over five tests, or six if B2 moves here)

- **A2.** Conflict cost CC = Acc(G4) − Acc(G3) is larger on familiar than on fresh repositories
  (associational: different repositories).
- **A3.** Change of CC with model size. Three predictions registered in advance: "capacity" (shrinks with
  scale), "memory" (grows with scale, mainly on familiar repositories), "flat" (no change; supported only if
  the TOST in section 6 passes). X-axis: effective parameters, that is 2.3B for E2B and 4.5B for E4B (Gemma
  4 model card); 12B and 31B have no separate effective count, so their card totals, 11.95B and 30.7B, are
  used. Sensitivity check: the text-model parameter totals of the GGUF files we run (E2B 4,628,569,635; E4B
  7,463,013,674; 12B 11,907,350,576; 31B 30,697,345,596, as listed by Hugging Face on 7 Nov; compared with
  llama.cpp's own count of each file before the analysis). Both axes order the four models the same way.
  "Flat" is decided on the effective-parameter axis only; the sensitivity axis is reported next to it and
  does not decide. Whether the change is larger on familiar than on fresh repositories (the second half of
  "memory") is reported descriptively, as an estimate with a 95% interval.
- **B3.** Graph value (true − rewired) is larger under renaming than with real identifiers. Likely
  underpowered; reported as an estimate with a confidence interval, and as "no effect" only if its TOST
  passes (section 6), which is unlikely at the expected precision.
- **B4.** The B1 discount is larger for 31B than for E4B on the official tasks.
- **B5.** A model-free scorer (BM25 plus λ times "is a neighbour of an anchor") ranks gold higher with
  true than with rewired edges. Metric: Acc@1 of the scorer's top candidate (score = BM25 / the largest
  BM25 in the task's pool + λ × [shares an edge with an anchor]; ties by BM25 rank). Test: per anchored
  confirmatory task, Acc@1 with the true graph minus Acc@1 with the rewired graph; paired t-test (two-sided;
  the Holm input), sign-flip test, the same bootstraps and TOST as B1. λ is the value of {0.05, 0.1, 0.2,
  0.3, 0.5, 0.75, 1, 1.5, 2} with the best mean true-graph Acc@1 over the anchored SWE-bench Lite dev tasks
  (11 tasks), ties to the smaller value (0 is left out: it ignores the graph). Code: `studyb_report.py`.

### Exploratory (labelled as such in the paper)

Capture of G3 answers by the displaced original answer, against the model's own no-graph preference; uptake
of non-obvious true edges; the official mirrored format on direction-trap items; hop strata; position bias;
the within-module rewired null of Study B (section 4).

## 3. Study A design

**Repositories** (`data/repos_manifest.json`, SHA-256 `c5aadd3c0cb8f15a0a2655d095ebfb36963965df7682093221401a27d2e66673`).
Per group, passing repositories in list order: first 16 confirmatory, the 17th is the pilot, the rest are
reserves. Familiar: commit pinned before 2025-01-01. Fresh: repository created on or after 2025-03-01,
commit pinned before 2026-11-02, README review criteria R1 to R5 and the copyright-header rule (README,
"Design details", item 4). Counts: familiar 16 confirmatory + 1 pilot + 2 reserves; fresh 16 + 1 + 8, and
1 unreviewed.

**Graphs.** `src/ngraph/extract.py` (rules in its docstring): nodes are module-level functions and methods;
an edge is kept only when the call resolves to exactly one in-repository node; tests, docs, examples,
benchmarks, scripts and vendored code are excluded; main-package rule (README, "Design details", item 3).
Extractor version 0.3.0. A `self.m()` call is not resolved when a class in the method order assigns
`self.m` (directly or by `setattr(self, "m", ...)`) or calls `setattr(self, <name expression>, ...)`
outside `__setstate__`; `setattr` calls in static methods are ignored. Screening ran with version 0.2.0,
which also blocked on literal names, in `__setstate__` and in static methods; 0.3.0 only adds edges (220,
in requests, httpx, daily_stock_analysis and nanobot) and changes no screening outcome (README,
"Decisions", item 3).

**Items.** Generator 0.4.0 (`src/ngraph/items.py`): 20 questions per repository, 10 of type QT-A (one hop,
reverse lookup) and 10 of type QT-B (two hops); four options, all nodes of the shown subgraph: the answer, a
trap when one exists (QT-A: a callee of the target that does not call it; QT-B: a direct callee of X that is
not two steps away; otherwise a random non-answer), the most name-similar non-answer, and the swap partner
(rules in the `items.py` docstring); subgraph sizes about 12 and about 24 nodes, kept after the GNG-2 pilot,
which required E4B's G2 accuracy to lie between 0.55 and 0.90 (the results of 8 Nov are in section 7).
Versions G0 to G4 share one option set; G3 and G4 apply one degree-preserving swap inside the shown subgraph.
Neutral names: one pseudo-word per word part within a question, matched to Gemma 4 token counts, then repaired
until the G1 and G2 prompts differ by at most 2 tokens (96% of questions; README "Numbers"). A question whose
names contain a blocked string (offensive words; `OFFENSIVE_SUBSTRINGS` in `names.py`), as written or with "_"
and "-" removed, or a pseudo-word "fok" or "pula" (`WHOLE_WORD_BLOCKED`), is named again with the next seeds;
97 questions were, by the author's choices of 8 Nov (README "Decisions", item 11). Option order 1 for every
model; a second order for E2B and E4B. The digest of the item files is in section 10.

**Models and runtime.** Google's instruction-tuned Gemma 4 GGUF files with quantization-aware Q4_0 weights,
one per size (file names, sizes and SHA-256 in section 10). E2B, E4B and 12B were downloaded and checked on 7
Nov and 31B on 8 Nov. Each prompt's chat template comes from its GGUF file (template hashes in section 10).
Runtime: llama-cpp-python 0.3.36 built with Metal on the author's Mac Studio (Apple M5 Max, 128 GB), Python
3.14.8. Its ggml library carries the build string 0c1e570-dirty, which does not name an exact upstream commit,
so the built libraries' hashes are recorded instead (`data/gng1/mac_environment/llama_cpp_libs_SHA256.txt`).
n_ctx 4,096 (the longest prompt in the final item set is 2,679 tokens, for 12B with the thought block and
"Answer:", counted with the vocabulary file's template; the GNG-2 pilot on the final question files kept the
sizes, section 7); one forward pass per prompt, no sampling.

**Prompt.** Each model's own chat template with thinking off. Empty thought block
(`<|channel>thought\n<channel|>`) after the model turn: pre-filled for 12B and 31B, absent for E2B and E4B,
as in Google's per-size chat templates (Google's Gemma thinking documentation and the templates in Google's
model files, checked 7 Nov 2026; sources in the `runner.py` docstring). The smoke test at GNG-1 scores the
same pilot prompts under both settings and logs the probability of the `<|channel>` token at the answer
position (rule in section 7). Answer instruction: "Answer with the letter of the correct option only."
Answer prefix: the model's turn is pre-filled with "Answer:" for E2B and 12B and left empty for E4B, by the
rule in section 7, which the author chose on 8 Nov (31B: fixed by the same rule at its GNG-1; section 7).

**Scoring.** Next-token logits for each letter, combining the plain and the space-prefixed letter token by
log-sum-exp; the prediction is the arg-max letter; p(correct) is the softmax over the four letters. Letter
probability mass is reported for every prompt.

## 4. Study B design

**Tasks.** (1) The competition's public tasks with at least one library function in the gold patch: 111
of the 129 tasks (18 have none; eligible by repository: fastapi 57, rich 42, requests 11, httpx 1). (2) The
SWE-bench Lite test split minus psf/requests tasks, because requests is a competition repository: 294 tasks
from 11 repositories, 260 of them eligible (34 have no library function in the gold patch; eligible by
repository: django 102, sympy 60, scikit-learn 22, matplotlib 21, sphinx 16, pytest 15, astropy 6, pylint 6,
xarray 5, seaborn 4, flask 3). Input: the problem statement only, as the agent sees it (hints_text is
empty in every competition task). Pilot tasks: the SWE-bench Lite dev split minus requests, 23 tasks (21 eligible, 11
of them anchored), role "tune": they set B5's λ and enter nothing confirmatory.

**Gold.** The innermost enclosing non-test function of each changed line at the base commit
(`src/ngraph/localize.py`): removed lines located in the base file, added lines in the patched file; a span
starts at the first decorator; a line in a nested function counts for the enclosing node; functions created
by the patch are not gold.

**Anchors and strata.** Identifier-shaped mentions in the issue (inline code, dotted paths, CamelCase,
snake_case, `_private` names, traceback frames) that match exactly one graph node of degree 50 or less;
matching rules in `localize.py`. Strata: S0 an anchor is gold; S1 gold one hop from an anchor; S2 two hops;
S3 other, including tasks without anchors. "Anchored" means at least one anchor.

**Candidate pool.** BM25 (k1 1.2, b 0.75, Lucene-style idf) over library functions; document = qualified
name plus function source; query = the set of tokens of the issue. Top 10, ties by node id. If no gold
function is in the top 10, the best-ranked gold function replaces rank 10 and the task is flagged
"injected" (analysed separately). Computed once on the original text and reused in every condition.

**Display.** Qualified name, signature and at most the first 15 lines per candidate, labelled A to J. Two
candidate orders per task: order 1 is a seeded random permutation of the ten candidates (seed derived by
hashing (1, task id, "order"), as `stable_seed` in `items.py` does for Study A; section 8), and order 2 is
order 1 reversed, so a candidate at position p moves to position 11 − p. A gold function in the first half
(A to E) under one order is therefore in the second half (F to J) under the other, and every candidate's
mean position is 5.5. The same two orders are used in every naming and graph
condition and for every model, so position effects cancel in the paired differences. Balancing follows
Rafi et al., "Order Matters!" (arXiv 2412.18750), who found a large order effect in LLM fault localization.

**Graph context.** The subgraph tool on anchors plus candidates and the neighbours tool on the first anchor,
rendered in the official format: from the official graph for official tasks, from our official-like view
for Lite (every edge mirrored, one "calls" type, nodes are the library functions of the main package, no
class or test nodes). Our rendering shows node ids and edges only (the per-node source text of the official graphs is never
shown), so every arm sees structure only.
Delivered as an inline "Tool output:" block after the candidates. A replayed native tool-response turn was to
be used only if its format was verified at GNG-1; GNG-1 did not check it, so it is not used.

**Conditions.** Naming {real, opaque} × graph {none, true, rewired} × order {1, 2}: 12 prompts per task
per model.

**Opaque renaming** (`src/ngraph/rename.py`, rules in its docstring). One seeded bijection per repository
(seed 1) over project-defined names; keywords, builtins, dunders, standard-library module names, attributes
of builtin types, third-party names and names shorter than 3 characters are never renamed; repository,
organisation and package names are scrubbed. Requirement before the freeze: zero hard leaks in every
task's renamed text (leak scan). The share of tokens changed is logged per task as a covariate. Credit: the
SchrodingerRepo ("Schrödinger's Code Repository: Have LLMs Learned SWE-bench or Memorized It?", arXiv
2609.27891, 2026), which remaps a repository's names on SWE-bench, is the precedent; our renamer is our own
code. Built
with renamer 0.1.3: zero hard leaks in all 392 eligible tasks, the 371 confirmatory and the 21 tune tasks
(an ineligible task gets no prompt; section 11, rows 3 and 5; section 13).

**Rewiring** (`src/ngraph/rewire.py`, version 0.2.0). A copy of the whole repository graph with 10 × |E|
degree-preserving swaps (seed 1): a mirrored graph is rewired as its undirected projection (networkx's
`double_edge_swap` when there is one swap class) and mirrored again; a directed graph is rewired with
two-edge swaps that keep every in- and out-degree (our own loop: on our 44 Study A graphs networkx's
`directed_edge_swap` stopped early on 12 graphs and left a median 43.8% of edges in place, against all 44
completed and a median 2.4% for the two-edge loop). Swaps stay within one node-kind pair and edge type when
kinds or types are labelled. Invariants checked per graph: per-node degree per edge type, kinds of
neighbours, edge-type counts, self-loops, no parallel edges. Reciprocity is kept at 1.0 for mirrored graphs
(they are mirrored again) and reported, not kept, for directed graphs: on our 44 Study A graphs (seed 1)
directed rewiring changed it on 26, by a median of 0.002 and at most 0.013. Rewiring also removes module
locality (on our 44 Study A graphs, same-module edges fall from a median of 67% to 6% in both views); the
paper reports this.

**Within-module null (exploratory).** A second rewired copy in which a swap only exchanges edges that join
the same pair of modules, so the share of same-module edges stays as it is (it leaves many edges in place,
because many module pairs have too few edges to swap; `OPEN_ITEMS.md`, section 5). Opaque naming
only, both candidate orders, run after every confirmatory cell and cut first if time runs short; reported
as an estimate with a 95% interval and no significance test; dropped if the official graphs carry no module
information. Its exact settings are fixed in the Study B addendum (`prereg-v1.1`).

**Context length and truncation.** n_ctx 8,192. Truncation is decided on spans of the original text and
mapped onto the renamed text (`rename.map_offset`), so both naming conditions carry the same content.

**Models.** E4B on the official tasks and Lite; 31B on the official tasks (and Lite if capacity allows);
12B as a stretch goal.

**Scoring.** Logits over A to J give a full ranking. Primary metric Acc@1; secondary Hit@3 and MRR.

**B5 control.** λ tuned on SWE-bench Lite's separate dev split (23 tasks without requests, role "tune"; the
11 anchored eligible ones set λ; section 2, B5), so every test task stays in the confirmatory analysis.

## 5. Manipulation checks

- **MC1.** Exactly one correct option per version; rewired graphs keep the degree sequence per edge type,
  the kinds of neighbours and the edge-type counts, and mirrored graphs keep a reciprocity of 1.0 (directed
  graphs' reciprocity is reported); no self-loops or duplicate edges introduced.
- **MC2.** No original project identifier survives renaming (leak scan); BM25 pools and anchors identical
  across naming conditions by construction.
- **MC3.** Our extractor's edges against the official graph on the four competition repositories.
  Result (`studyb mc3`, on the latest snapshot per repository): every official library-function node is
  one of ours in all four repositories; 84% to 100% of the official call pairs are among ours (fastapi 153
  of 183, httpx 33 of 33, requests 100 of 103, rich 263 of 274), and 13% to 65% of ours are in the official
  graph (ours has 236, 248, 208 and 657 pairs).
- **Determinism.** Study A: each model's smoke test scores 10 of its GNG-1 prompts a second time (`repeat`);
  the arg-max must agree on all 10, and the largest logit difference is reported (0.0 in every GNG-1 run up to
  8 Nov). Study B: 100 prompts per model re-scored under the registered cache regime, at least 99% arg-max
  agreement, the largest logit difference reported (in the Study B runner; addendum).

## 6. Analysis plan (`src/ngraph/analysis.py`)

- **Units.** Study A: the item, clustered within 32 repositories. Study B: the task. Only E2B, E4B, 12B
  and 31B enter A1 to A3; another model run under backup B-3 (26B-A4B) is reported descriptively only.
- **A1.** Per-repository mean of I over items, models and option orders; one-sample t-test over the 32
  repository means; 95% CI from a repository-cluster bootstrap (10,000 resamples). Sensitivity: GEE
  logistic model (correct ~ names × edges × model, exchangeable correlation within repository); the
  continuous p(correct) outcome; excluding the items whose real-name and neutral-name prompts still differ
  by more than 2 tokens after the parity repair (27 of the 640 confirmatory items in the current item set;
  `analysis.parity_flagged_items`).
- **A2.** Familiar minus fresh repository means of CC (Welch test; bootstrap CI).
- **A3.** Per-repository OLS slope of CC on log10(parameters) on the registered axis (section 2); mean
  slope with a t-test over repositories and a repository-cluster bootstrap CI. The same analysis on the
  sensitivity axis is reported next to it and does not decide "flat". The familiar-minus-fresh difference
  of mean slopes is reported with a Welch 95% interval and no test.
- **B1, B2, B3, B4.** Per-task differences averaged over orders and models; paired t-test and a sign-flip
  permutation test (10,000); 95% CI from a task bootstrap stratified by set; repository-cluster bootstrap
  as sensitivity; each set also reported alone.
- **Equivalence.** "No effect" only through TOST with bounds of ±5 percentage points, for every
  confirmatory and secondary test: on the repository or task differences for A1 and B1 to B4 (B5: in the
  Study B addendum), on the familiar-minus-fresh difference with Welch's standard error for A2, and for A3
  on the mean slope, as 5 points of CC across the models run. For A3 the slope bound is 0.05 divided by
  the log10 span of the parameter counts of the models present on that axis (E2B to 31B: 1.1254 decades on
  the effective axis, 0.8217 on the GGUF axis; E2B to 12B: 0.7156 and 0.4104), so both axes test the same
  5-point total change (the author's choice, 8 Nov; the earlier reading, 5 points per tenfold increase in
  parameters, stays in the code as an option, and using it would be a deviation). Each TOST
  is at alpha 0.05 (90% interval inside the bounds), without multiplicity adjustment. At the expected
  precision (estimates, `OPEN_ITEMS.md` sections 6 and 10) a null on A1 can usually be called equivalence
  (in about 86% of studies with no true effect), one on B1 in about 28 to 77%; nulls on B2, A2, A3 and B3
  will mostly be reported as inconclusive (for A3, a truly flat trend passes the TOST in about one
  simulated study in three).
- **Minimum detectable effects (estimates; recomputed after the pilot, frozen table in the paper).**

| Test | MDE (estimate) | Note |
|---|---|---|
| A1 | about 5 pp | power about 0.87 for 5.6 pp at alpha 0.0167 (normal approximation, standard error 1.6 pp); the simulations in `data/power/` give 0.80 to 0.98 at 5.6 pp (`scripts/power_a1.py`, `scripts/power_a1_het.py`) |
| B1 | about 6-7 pp Acc@1 | official tasks alone about 9-10 pp |
| B2 | about 9 pp, anchored tasks | |
| B3 | about 10-12 pp | secondary test; likely underpowered |
| A2 | about 8.5 pp | |

## 7. Decision rules

- **GNG-1 (Sat 7 Nov; run again with the registered prefixes before any confirmatory run).** Letter
  probability mass at least 0.9 on at least 95% of the pilot prompts per model (40 A-D prompts and the 36
  A-J prompts that the two pilot repositories allow), each set separately; letter tokens with and without
  a leading space handled; exactly one beginning-of-sequence token; special tokens parsed as special;
  tokenizer identical to the vocabulary file on the probe strings. Graph-context delivery fixed: inline
  (section 4).
  Thought-block rule: the per-size setting (section 3) stays if it passes the letter-mass check; if it
  fails and the other setting passes on the same prompts, the other setting is used for that model and
  logged as a deviation before any confirmatory run; if neither passes, the model is excluded from the
  confirmatory tests and the exclusion is logged. A failed token or tokenizer check is fixed, never
  answered by switching the setting.
  **First GNG-1 run (7 Nov, before the freeze; no answer prefix; files finished 18:21 to 18:31 UTC).** E4B
  passed. E2B and 12B failed the letter-mass check under both thought-block settings (share of prompts with
  letter mass of at least 0.9: E2B 0.175 on A-D and 0.028 on A-J; 12B 0.675 and 0.639); their token,
  special-token and tokenizer checks passed. Without the block, 12B put about 0.99999 of the probability on
  `<|channel>`. A test of answer prefixes on the same pilot prompts was sent to the Mac at 18:36:08 UTC. At
  18:36:31 (its fallback sentence refined at 18:36:40), before any of its results was seen (they came back at
  18:44), a rule was written into this draft: pre-fill one answer prefix, the same for every model, chosen by
  letter mass alone, trying "Answer:" first and "The correct option is" second; if no prefix lets every model
  pass, use the option (no prefix, "Answer:" or "The correct option is"; ties to the earlier) under which the
  most models pass, apply the thought-block rule under it, and exclude a model that still fails. (That text
  gave its time as 18:40 UTC, which was wrong. These times come from our own records, listed in
  `data/gng1/README.md`; nothing in the package or in the forum post can confirm their order.) Result (own
  setting): with "Answer:", E2B and 12B passed (1.0 on both sets) but E4B fell to 0.925 on A-D (0.972 on A-J),
  so it failed; with "The correct option is", all three failed (most of the remaining probability went to
  " **"). Under that rule E4B, which passes without a prefix, would have been excluded. After seeing these
  letter-mass results and before any confirmatory run, the AI coding assistant proposed a per-model rule to
  the author at 18:45 UTC, written here at 18:47 UTC and chosen by the author on 8 Nov at 00:58 UTC: a model
  keeps no prefix if it passes without one; otherwise it uses the first of "Answer:" and "The correct option
  is" under which it passes with its per-size setting. GNG-1 fallback under this rule (proposed to the author
  on 8 Nov and chosen by the author at 16:57 UTC that day, before any confirmatory run): if no candidate
  passes under the per-size setting, the candidates are tried in the same order under the other setting, which
  is then used for that model and logged as a deviation before any confirmatory run (the thought-block rule
  above, applied after the prefix scan); a model for which no candidate passes under either setting is
  excluded from the confirmatory tests and the exclusion is logged.
  Result: E2B "Answer:", E4B none, 12B "Answer:" (registered in `runner.py`); 31B is tested the same way at
  its GNG-1: smoke first with no prefix and then, if the rule chooses a prefix, a second time with that
  prefix, whose verdicts (letter mass, thought-block decision, GNG-1 pass) are the ones for the prefix the run
  uses. Before or after this freeze, its Study A run takes the rule's choice from the smoke file run with that
  choice (the first file when the rule chooses no prefix; `study-a --prefix-from`, which checks the model
  file's SHA-256, the token and tokenizer checks, the thought-block setting, that the smoke test scored these
  pilot prompts (40, seed 0, the two pilot repositories) from the same item files, and that the file was run
  with the choice and passed GNG-1, and records the smoke file's SHA-256 in the run file): the registered
  rule, not a deviation. The smoke test re-checks the rule on every model (`prefix_scan`,
  `prefix_rule_choice`). Pilot accuracy was printed next to the letter mass but was not used. The outputs of
  both runs, the test script, the first rule verbatim and the file times are in `data/gng1/`.
  **GNG-1 again, with the registered prefixes (8 Nov, before the freeze).** On the final question files, after
  the third renaming (README "Decisions", item 11), E2B ("Answer:"), E4B (no prefix) and 12B ("Answer:")
  passed with their per-size thought-block settings (`thought_block_decision` `keep`): every one of the 40 A-D
  and 36 A-J pilot prompts had a letter mass of at least 0.9 (smallest values: E2B 0.952 and 0.930, E4B 0.902
  and 0.912, 12B 0.957 and 0.977); the token checks passed, and the tokenizer matched the vocabulary file on
  all 4,040 probe strings. Runs on the question files from before the renaming and after its first and second
  rounds (02:08 and 05:43 UTC) gave the same letter masses and checks; GNG-1 scores only real-name (G1)
  prompts, which the renaming did not change (it changed only neutral names, and with them the probe strings).
  31B, at its GNG-1 on the final question files: with no prefix and its per-size setting it failed the
  letter-mass check (share of prompts with letter mass of at least 0.9: 0.80 on A-D and 0.69 on A-J); the rule
  chose "Answer:" under that setting, so the fallback was not needed; with "Answer:" 31B passed (every prompt
  at least 0.9; smallest values 0.9996 and 0.99999; `thought_block_decision` `keep`), the token checks passed,
  and the tokenizer matched on all 4,040 probe strings. `study-a --prefix-from` accepted that smoke file
  (`data/gng2/final/gng1_rename3_31B.json`), from which 31B's Study A run takes "Answer:". The outputs and
  file times are in `data/gng2/`.
- **GNG-2 (Sun 8 Nov 12:00 UTC).** Items generated for at least 30 repositories under the size rule. E4B G2
  pilot accuracy between 0.55 and 0.90; otherwise change question type or size and re-pilot for at most 6
  hours, then backup B-1 (Study B becomes the headline; Study A descriptive on p(correct)). The anchored
  fraction for the B2 rule is measured when the Study B tasks are frozen, not at this checkpoint (section 2;
  the author's choice of 8 Nov, 16:57 UTC). **Pilot result (8 Nov; output in `data/gng2/final/`):** on the
  final question files, E4B's G2 accuracy on the 80 pilot prompts (the 40 pilot questions in both option
  orders) was 0.6625 (53 of 80; 0.60 at about 12 nodes and 0.725 at about 24 nodes), so the sizes stay;
  question files exist for all 44 repositories (section 3). It was also 0.6625 on the question files of 05:43
  UTC, before the third renaming changed one pilot question (langextract/A/S24/005, answered correctly in both
  option orders in both runs), and 0.65 (52 of 80) on those of 02:08 UTC, before the second renaming changed
  six. **Anchored fraction (10 Nov, on the frozen Study B task files, before any Study B result):** 174 of
  the 371 eligible confirmatory tasks are anchored (46.9%; official 43 of 111, Lite 131 of 260), so B2 stays
  confirmatory (threshold 35%).
- **GNG-3 (hard, Mon 9 Nov 23:59 UTC).** Study A hash posted. Confirmatory Study A runs start only after the
  post is visible on the forum; each run file records the code hash and the digest of the item files it used
  (README, sections 2 and 3). If the post is later, the runs wait for it and nothing is dropped (only GNG-5's
  hard stop applies); the delay is reported. (The dates of GNG-3 to GNG-5 were set on 9 Nov: the hash was not
  posted by the first date, Sun 8 Nov 23:59 UTC, the author asked at 17:26 UTC that neither study shrink, and
  the author accepted these dates at 17:28 UTC; `prereg/OPEN_ITEMS.md`, row 15.)
- **GNG-4 (hard, Tue 10 Nov 18:00 UTC).** Study B frozen (addendum `prereg-v1.1` with hashes of the task list,
  pools, anchors, renaming maps and rewired graphs), its hash posted as a reply to the first post.
  Confirmatory Study B runs start only after that reply is visible. If it is later, the runs wait for it and
  nothing is dropped (only GNG-5's hard stop applies); the delay is reported.
- **GNG-5.** Confirmatory Study A runs done by Tue 10 Nov 18:00 UTC, Study B runs by Wed 11 Nov 18:00 UTC;
  hard stop for every confirmatory run at Thu 12 Nov 06:00 UTC; cells unfinished at the hard stop are reported
  as "not run".
- **Backups.** B-2 (no competition data): Study B on SWE-bench Lite only (E4B and 31B), with our graphs in the
  official-like format; the four competition repositories still appear in Study A through their public source.
  B-3 (no workable 31B path): the E2B to 12B ladder, with 12B replacing 31B in Study B; optionally 26B-A4B,
  reported descriptively only (it is not one of the models of A1 to A3). (An earlier backup B-4, Study A plus
  B1 on E4B only, was removed on 9 Nov at the author's instruction; GNG-3 and GNG-4 no longer drop any part of
  either study.)

## 8. Seeds, determinism and caching

- Item sampling seed 20261108. Each draw's seed hashes it with further parts, in the order of each
  `stable_seed` call in `items.py`: the candidate order per repository with the repository and "candidates";
  each candidate question (subgraph, options and swap partner) with the repository, question type, size and
  the candidate's node ids, with no purpose label; the option orders, rendering, neutral names and parity
  repair with the item id and a purpose label ("perm1", "perm2", "render", "neutral", "parity"), and for a
  question named again (section 3) also the attempt number.
- Study B: renaming seed 1; candidate order 1 from a per-task seed derived by hashing (1, task id, "order")
  and order 2 its reverse; rewiring seed 1 per repository graph.
- No cache reuse in Study B: every prompt is scored from scratch (the runner resets the model's state
  before each prompt), in the fixed order task id, naming, graph, order. This replaces the earlier plan of a
  shared cached prefix for "true" and "rewired", which the runner does not implement.

## 9. Exclusions and missing data

Pilot repositories and tasks are excluded from confirmatory analyses. No optional stopping: every
registered item and task is run. Infrastructure failures are retried twice, then excluded and reported.
Logit scoring has no parse failures.

## 10. Frozen artifacts (filled at the freeze)

`python -m ngraph.commit manifest --label prereg-v1.0` (`src/ngraph/commit.py`; steps in the README, section
6) writes `prereg/MANIFEST_prereg-v1.0.txt`: every file of this package with its SHA-256, in `sha256sum`
format and sorted by path, except the manifest itself, the top-level `runs/` (model outputs), `.venv/` and
`.git/` folders, caches, `.DS_Store` and `*.pyc` files. The SHA-256 of that manifest file is the hash
posted on the forum; it cannot be written into the files it covers, so it is not in this table. Anyone can
re-check it with `python -m ngraph.commit verify` or with `sha256sum` alone. The Study B addendum gets its
own manifest (`prereg-v1.1`), which lists the first one, names its hash and lists every file changed,
added or removed since; its hash is posted as a reply to the first post. The model files and the
competition data stay outside the package, so their hashes are given here (model files) and in
`data/studyb/README.md` (competition data and SWE-bench Lite). The table repeats the main
values for readers.

| Artifact | File | SHA-256 |
|---|---|---|
| Repository manifest | `data/repos_manifest.json` | `c5aadd3c0cb8f15a0a2655d095ebfb36963965df7682093221401a27d2e66673` |
| Code (extractor, generator, renamer, rewiring, runner, analysis, time-stamp) | `CODE_SHA256.txt` | `2a1a3c36f38607f0be3253e4446fe4307aa58afc71adbc39e76f6dc69793a8e1` |
| Study A code as frozen in prereg-v1.0 and recorded by the Study A runs | n/a | `983e343e3c1db31d58d172e2192bbb02ba3bc3e7e12353ddc426fff5994d9f70` |
| Study A item files | `data/items/` (`python -m ngraph.commit digest data/items`) | `511b839ff70e2106c85bdfa5e726e7a5d4b3712ec52e0c6ec750c29f15b782b7` |
| GNG-1 evidence | `data/gng1/` (its README lists each file's hash) | in the manifest |
| GNG-1 rerun and GNG-2 pilot | `data/gng2/` (its README lists each file's hash) | in the manifest |
| Model file, E2B | gemma-4-E2B_q4_0-it.gguf, 3,349,516,256 bytes | `fa401b55b07ee70a54c6dae3903c783a6e65064312529ea57175cb5f8dec6634` |
| Model file, E4B | gemma-4-E4B_q4_0-it.gguf, 5,154,941,280 bytes | `676c35070db6dbe52f93e9c864ee0fba4eddea94b9c875d9cb10daff453fbaee` |
| Model file, 12B | gemma-4-12b-it-qat-q4_0.gguf, 6,975,879,296 bytes | `93567e57a8fe10b23569b9d9ec38cd005deedf71e29477c421a4b83f418a538b` |
| Model file, 31B | gemma-4-31B_q4_0-it.gguf, 17,651,001,568 bytes; downloaded on 8 Nov; SHA-256 computed on the Mac, equal to the LFS SHA-256 in Hugging Face's API listing, read on 8 Nov | `179cfb99212709597eae5929112cfca677e1bbf566178b479ae1da0c4772874b` |
| Chat template, E2B and E4B | inside the GGUF files | `0a2c8073c878ab1da004bee933a998606537bbb62016310352c7285c3f01c5b5` |
| Chat template, 12B | inside the GGUF file | `ae53464bf3be25802b3a5b37def7fd89667067d7577049b3b2d74c4d8de4c6d4` |
| Chat template, 31B | inside the GGUF file (the same template as 12B) | `ae53464bf3be25802b3a5b37def7fd89667067d7577049b3b2d74c4d8de4c6d4` |
| Runtime | llama-cpp-python 0.3.36 with Metal, Python 3.14.8; library hashes in `data/gng1/mac_environment/llama_cpp_libs_SHA256.txt` | n/a |
| Study B task list, pools, anchors, renaming maps (rewired graphs: not hashed; section 11, row 8) | outside the package (derived from the competition data and SWE-bench Lite, which we do not redistribute); `data/studyb/README.md` lists each file and input with its SHA-256. The task files hold the pools, anchors, per-prompt SHA-256 and each task's tool outputs on the true, rewired and within-module graphs; the rewired graphs themselves are not stored or hashed (they are regenerated with seed 1, from the official graphs and, for Lite, from our extractor's graph of each snapshot; row 8 of section 11), their invariant reports are in `graphs_report.json`, and at run time every prompt is rebuilt from the task files and the frozen inputs (task statements, snapshots or clones) and checked against its frozen SHA-256 before scoring | in the manifest |

## 11. Deviation log (kept from the hash onward; every entry listed in the paper)

| # | Date (UTC) | Change | Reason | Hypotheses affected | Before or after seeing outcome data |
|---|---|---|---|---|---|
| 1 | 10 Nov | `analysis._task_diffs` and B3 (`_matched_diffs`): per task, each difference is taken within each (model, option order) pair that has both cells (for B3, all four cells), then averaged over orders and then over models, instead of averaging each cell over models and orders first; `_task_diffs` is also used by the exploratory within-module estimate | with incomplete runs, the two sides of a difference could mix models or orders | B1 to B4 and the exploratory within-module estimate (no Study A test) | before any Study B outcome data |
| 2 | 10 Nov | Holm families keep every registered test; a test with no p-value enters with p = 1 | a family must not shrink when a test is not run | B4, B5, and A1 to A3 only if one is missing | before any Study B outcome data |
| 3 | 9 Nov | renamer (`rename.py`; the prereg-v1.0 file declares version 0.1.0) to 0.1.2, including the change marked 0.1.1 in the code, made after prereg-v1.0: (0.1.1) a URL becomes `<url>`, and the leak scan flags it, only when it contains an identity name as a whole word, not as a substring (such as "urlencode"); (a) a sub-token redrawn in 8 rounds without success (in practice a one-letter one) gets a longer pseudo-word; (b) files under hidden folders are skipped; (c) identity words are top-level names that are a module or package or are imported by project code; (d) "@word" is a handle only if word is not a standard decorator or a renamed project name, never inside a dotted name, call or URL or after "]" or ")", and handles in traceback lines are now replaced too (only fenced and inline code is skipped); (e) Python's frame words ("File", "line", `<module>`, `<frozen ...>`) are kept; (f) the project's own top-level names and packages imported locally by examples or tests are never third-party | the Lite build failed on sympy and matplotlib; 3 Django prompts leaked "user"; three code reviews found handles kept in cc lists, "sympy" never renamed, example packages treated as third-party | Study B opaque prompts only (`rename.py` is not a Study A file) | before any Study B outcome data |
| 4 | 9 Nov | `extract.py` 0.3.0 to 0.3.1: a top-level lib/ folder that holds packages but is not one is dropped from module names, like src/ (file selection unchanged) | matplotlib's lib/matplotlib made its own imports look third-party, so Axes, pyplot and others were never renamed and its absolute imports did not resolve | Study B graphs of matplotlib only; no Study A graph has a lib/ folder (0 nodes under lib/ in `data/graphs/`) | before any Study B outcome data |
| 5 | 10 Nov | renamer 0.1.2 to 0.1.3 and the leak scan in `studyb.py`: (a) the scan blanks the fixed words of the tool-output format (JSON keys, "ok", "calls", true and false, the tool names); (b) the interpreter's own words (ipython, input, stdin, string, console) inside an interpreter-made frame file name, which the renamer keeps, are recorded per task (`frame_names_kept`) instead of counted as hard leaks; (c) a top-level package named by a common English word, by util or utils, or by fewer than 3 characters is not an identity word unless it is the repository or organisation name (a common or generic name stays a renamable module name; a name under 3 characters stays unrenamed, as every such name does) | the 0.1.2 build flagged 7 Lite tasks: "node_count" in 6 pylint tasks was only the tool-output key and "ipython" in sympy__sympy-18621 only an IPython console file name (0 other occurrences in the rendered prompts); pylint's maintenance package "script" would have scrubbed the ordinary word (no rendered prompt contained it); pytest's "py" shim made the URL scrub remove a py.readthedocs.io link | 8 opaque prompts of one pytest task (pytest-dev__pytest-8365) and the leak counts; no other prompt and no real prompt changed | before any Study B outcome data |
| 6 | 10 Nov | Study B cache regime: no prefix reuse in any cell (the runner resets the model before each prompt), instead of a shared cached prefix for "true" and "rewired" (section 8) | the runner never reuses a prefix (`runner.py`: Gemma 4's sliding-window attention makes partial cache removal unsafe) | B1 to B4 and the determinism check (scores do not depend on the order of prompts) | before any Study B outcome data |
| 7 | 10 Nov | Section 2: B5's metric, test and λ rule written in (prereg-v1.0 said they are fixed in this addendum); section 11's list of Study A text includes section 2, but this text concerns Study B only | clarification | B5 | before any Study B outcome data |
| 8 | 10 Nov | prereg-v1.0 named hashes of the rewired graphs (GNG-4 in section 7, the Study B row of section 10, README section 5); the rewired graphs are not stored or hashed. Hashed instead: the task files, which hold each task's tool outputs on the rewired and within-module graphs, and `graphs_report.json`, which holds each rewired graph's invariant report; the graphs are regenerated with seed 1 (official: from the competition graphs; Lite: from our extractor's graph of each snapshot) | a rewired graph is fixed by its input graph and the seed, and what a prompt shows of it is in the task files; the Lite graphs derive from repositories we do not redistribute | none (B1 to B4 prompts are checked against their frozen SHA-256 at run time) | before any Study B outcome data |
| 9 | 10 Nov | README section 1: expected test count 248 to 281 (with the data variables set; 150 tests without them) | the Study B tests were added | none | before any Study B outcome data |

Study A files: `data/items/`, `data/graphs/`, `data/repos_manifest.json`, `data/tokenizer_probe.json`, the
Study A code (`src/ngraph/` `extract.py`, `screen.py`, `manifest.py`, `names.py`, `items.py`, `batch.py`,
`tok.py`, `gguf_meta.py`, `runner.py`, `analysis.py` and `simulate.py`, with their tests and scripts), the
Study A text of this file (sections 2 and 3, the Study A parts of sections 5 to 10, and section 12 as far as
it cites design details 1 to 7) and the Study A text of the README (sections 1 to 4, "Numbers", "Decisions"
items 1 to 3, 5, 7 to 9 and 11, and "Design details" items 1 to 7). `CODE_SHA256.txt` is derived from the
code, so a change in it is not a change of its own. A Study A file that is changed, added or removed between
`prereg-v1.0` and the addendum appears in the addendum manifest's `# changed:`, `# added:` or `# removed:`
header lines, and each such change is entered here; for this file and the README, which also hold Study B
text, only changes to their Study A text are entered.

## 12. Design details fixed while building the code

See README, "Design details", items 1 to 12 (graph line order, neutral-name rules, file selection,
fresh-repository review, pilot choice, token counting, folder names, rewiring engine, BM25 details, gold
rule, anchor matching, opaque-renaming rules).

## 13. Study B addendum: rules fixed in the code (`studyb.py` 0.1.0, renamer 0.1.3, extractor 0.3.1)

- Token budget: n_ctx 8,192 minus a 256-token margin. Per task the issue is cut once (at a space or newline;
  " [...]" marks the cut and an open code fence is closed) so that the longest of the 12 confirmatory prompts
  fits; floor 1,000 characters, then code lines 15 down to 5, then a cut below the floor. The same cut is used
  in every cell. Two Lite tasks are cut; no official task is.
- Candidate block: "X. qualified.name", "Signature: name(params)", then the first 15 or fewer lines (each cut
  at 200 characters), fenced. Each list in the tool output (subgraph nodes, subgraph edges, neighbours) capped at 5,000 JSON
  characters of the real names (whole items; the same items in every naming); neighbours also at 50, sorted. The subgraph's node list is in candidate order 1 (anchors first), never in BM25 rank order.
- Renaming: one bijection per repository over the union of its snapshots' names; the Python version and a
  fingerprint of the protected names are recorded at build; at run the fingerprint is compared (a run stops
  if it differs). Names that a project also
  imports from a third-party library stay unrenamed by design (for example matplotlib's Figure, which it also
  reads from docutils, and sympy's Symbol and Basic, also read from symengine); `n_protected_defined` per
  repository is in the renaming maps. The renaming changes no real prompt. One sentence of the 0.1.3
  docstring of `rename.py` is wrong: it says that pytest's "py" stays a renamable module name; like every
  name shorter than 3 characters (the docstring's "Never renamed" list, `MIN_LEN` = 3), "py" is never
  renamed. The code is left as built, so that the frozen task files can be rebuilt from the frozen code (every
  prompt is rebuilt and checked against its frozen SHA-256 before scoring); the rule is the code's.
- Within-module null: opaque naming only, both orders, the same cut; anchored tasks and the B1 to B3 models;
  estimate = opaque true minus opaque within-module with a set-stratified 95% bootstrap interval, no test;
  scored in a separate run (`--cells within_module`) after the confirmatory runs.
- Run files refuse resumption under another task file, set, cells or roles; the report refuses run files of
  another task file and rows found in two files. B1 to B4 use E4B and 31B on the official tasks and E4B on
  Lite; 12B replaces 31B in all four only when no 31B run exists on the official tasks (backup B-3); every
  other model and set (12B next to 31B, 31B on Lite) is descriptive only.
- Determinism: 100 prompts per model re-scored, at least 99% arg-max agreement.
- Build checks (frozen task files): 0 hard leaks in the 371 eligible confirmatory tasks and in the 21 eligible
  tune tasks (the build summary counts only the confirmatory ones; the tune count is read from the per-task
  records; the tune tasks enter no confirmatory analysis, B5's λ uses no prompt, and their prompts are
  scored only in a pilot run with `--roles tune`); one task (sympy__sympy-18621) keeps an interpreter word in
  a frame file name (`frame_names_kept`); every rewired graph passed its invariants (127 official, 314
  Lite); every graph is mirrored; MC3 as in section 5.
