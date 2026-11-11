# Decisions taken before the freeze: evidence and reasons

Written on 7 Nov 2026 (about 16:00 UTC) and updated that evening and on 8 and 9 Nov. Each finding below was gathered by an
automated research pass of the AI coding assistant (Claude Code) that worked for the author, and then checked
by a second automated pass that re-opened the sources or re-ran the code; corrections from the second pass
are applied. The decisions marked as the author's were made by the author. "Estimate" marks numbers that come from simulation or
arithmetic, not from a measurement. The web pages and API listings read on 7 Nov, and the automated review
reports, are not part of the package.

| # | Item | Decision | Decided by |
|---|---|---|---|
| 1 | Public time-stamp of the pre-registration | Hash-only forum post with a plain title | The author, 7 Nov 17:38 UTC |
| 2 | Empty thought block for E2B and E4B | No block for E2B and E4B; block for 12B, 26B-A4B and 31B | Evidence (section 2) |
| 3 | A3 x-axis | Effective parameters; GGUF text-model totals as a sensitivity check | The author, 7 Nov 17:38 UTC |
| 4 | `setattr` extractor rule | Fixed (4 repositories, +220 edges, 80 questions regenerated) | The author, 7 Nov 17:38 UTC |
| 5 | Within-module rewiring control | Exploratory, pre-specified in the Study B addendum | The author, 7 Nov 17:38 UTC |
| 6 | Equivalence (TOST) bound | ±5 percentage points for every test | The author, 7 Nov 17:38 UTC |
| 7 | Candidate-order balancing (Study B) | Order 2 = order 1 reversed | Design detail |
| 8 | Items fixed later by data | See section 8 | Data, GNG-1 to GNG-4 |
| 9 | Answer prefix after the first GNG-1 run | Per model, no prefix first (section 9) | The author, 8 Nov 00:58 UTC |
| 10 | How the ±5 pp bound applies to A3 | 5 points across the models run (section 10) | The author, 8 Nov 00:58 UTC |
| 11 | GNG-1 fallback | The prefix candidates in order under the per-size thought-block setting; if none passes, in the same order under the other setting, which is then used and logged as a deviation; a model for which none passes under either setting is excluded from the confirmatory tests and the exclusion is logged (pre-registration, section 7) | The author, 8 Nov 16:57 UTC |
| 12 | Offensive-looking pseudo-words in the questions | 10 questions named again with the next seeds, then 76 more after a wider check and 11 more after a further scan (section 11) | The author, 8 Nov 01:43, 05:39 and 16:57 UTC |
| 13 | Licence for the package's own code and text | Apache License 2.0 (`LICENSE`); third-party files and the data taken from the repositories keep their own licences | The author, 8 Nov 16:58 UTC |
| 14 | When B2's anchored fraction is measured (Study B) | When the Study B tasks are frozen (addendum, by Tue 10 Nov 18:00 UTC since 9 Nov, row 15), before any Study B result, instead of at GNG-2 (section 8) | The author, 8 Nov 16:57 UTC |
| 15 | Schedule after the first posting date passed | Nothing shrinks: hash by Mon 9 Nov 23:59 UTC, Study B addendum by Tue 10 Nov 18:00 UTC, confirmatory runs by Tue 10 Nov 18:00 UTC (A) and Wed 11 Nov 18:00 UTC (B), hard stop Thu 12 Nov 06:00 UTC; a later post delays runs and drops nothing (only the hard stop applies); backup B-4 removed (section 13) | The author, 9 Nov 17:26 UTC (no shrinking) and 17:28 UTC (dates) |

## 1. Public time-stamp of the pre-registration

**What the rules say** (the competition's rule pages, read through a mirror, and the host's forum replies,
read on 7 Nov):
- Private sharing of code or data outside a team is not allowed; public sharing is allowed if it is made
  available to all participants on the Kaggle forum or notebooks, and publicly shared code counts as licensed
  under an open-source licence that allows commercial use (Foundational Rules 5.d and 6.b).
- The host said on the forum that GitHub is fine for sharing code, that a prior GitHub repository does not
  count as prior publication, and that code may be withheld until the main competition ends.
- No host or staff ruling on pre-registrations, hashes or timestamps was found (forum read up to 7 Nov about
  04:50 UTC; later posts could not be read because Kaggle pages need JavaScript).
- The judging rubric does not mention pre-registration. It can only help through Verifiability, which asks
  whether the paper explains how the data was obtained, analysed and interpreted.

**Options considered:**

| Option | Proof of date | What other participants can see before 12 Nov | Effort |
|---|---|---|---|
| A. Public GitHub release plus forum post | Kaggle post time; a GitHub "immutable release" can lock the tag | Hypotheses, predicted directions, repository list, prompts, analysis code, for about 4 days | Most: clean public repository, tag, two posts |
| B. Hash-only forum post, plain title such as "Pre-registration hash" | Kaggle post time | Nothing | Two short posts (Sun, and before Study B) |
| C. B plus a private OSF registration under embargo | Kaggle post time plus an OSF record that cannot be edited | Nothing (outsiders cannot open an embargoed registration) | B plus a free OSF account and about 30 minutes per registration (estimate) |
| D. No public timestamp | Self-attested only | Nothing | None |

**Decision (the author, 7 Nov): B.** It gives the same independent date as A without showing the design to
other participants for four days. Its limits, stated in the pre-registration: whether Kaggle shows that a
post was edited is not verified, and a hash-only post cannot prove that no other plan was hashed elsewhere.

How B works: one plain-text manifest lists the SHA-256 of every file of the package; the author posts that
manifest's hash on the paper-track forum by Mon 9 Nov 23:59 UTC and the Study B addendum's hash as a reply by
Tue 10 Nov 18:00 UTC (dates moved on 9 Nov from Sun 8 Nov 23:59 UTC and Mon 9 Nov 12:00 UTC; row 15); the
exact files are released with the paper, with the script that re-checks the hashes. In the paper this is a
"publicly time-stamped pre-registration", not a "public pre-registration".

## 2. Empty thought block (settled by evidence)

With thinking off, Google's per-size templates put the empty block `<|channel>thought\n<channel|>` after the
model turn for 12B, 26B-A4B and 31B, and not for E2B and E4B. Sources that agree:
- Google's thinking page (ai.google.dev/gemma/docs/capabilities/thinking, updated 4 Jun 2026; on 7 Nov the
  page carried a deprecation notice pointing to gemma.ai, which has the same text): a table with the E2B/E4B
  row ending at the model turn and the 12B/26B/31B row ending with the empty block, plus the sentence that the
  empty token was added to the chat template for gemma-4-12B-it, gemma-4-26B-A4B-it and gemma-4-31B-it.
- The chat templates of all five instruction-tuned Hugging Face repositories, the five Google QAT GGUF files
  and the five ggml-org GGUF files (read through the Hugging Face API).
- Hugging Face transformers' converter selects the 31B template for 31B and 26B-A4B and the E4B template for
  E2B and E4B.

A model-card sentence about thinking describes what the models generate, not what the prompt contains, and is
consistent with this. Our vocabulary file's template adds the block for every size because it is the
large-model template (byte-identical to the 31B template), so it says nothing about E2B and E4B.

The runner follows this rule. The smoke test also scores every pilot prompt with the other setting and records
the probability of the `<|channel>` token at the answer position. In the first GNG-1 run (`data/gng1/`), the
other setting failed for all three models, and 12B without the block put about 0.99999 of the probability on
`<|channel>`.

## 3. A3 x-axis

Verified on the Gemma 4 model card (and the same cells on gemma.ai and the Hugging Face model pages):

| Model | Effective | Card total | Text-model total in Google's QAT GGUF (Hugging Face API) |
|---|---|---|---|
| E2B | 2.3B | 5.1B with embeddings | 4,628,569,635 |
| E4B | 4.5B | 8B with embeddings | 7,463,013,674 |
| 12B | none given (dense; use the card total) | 11.95B | 11,907,350,576 |
| 31B | none given (dense; use the card total) | 30.7B | 30,697,345,596 |

The card's E2B and E4B totals appear to include the vision and audio encoders (they match the full checkpoint
counts), while its 31B total matches the text-only count. That observation is our own arithmetic (from the
checking pass), not a statement of the card, which does not give its basis. So any "total" axis should use one basis for every model.

**Decision (the author, 7 Nov):** effective parameters as the registered axis (it matches how Google names and
sizes the models and what each token costs to compute); text-model totals of the GGUF files we run as the
sensitivity check. Both axes order the four models the same way, so the choice changes the slope's size more
than its sign. How the ±5 pp equivalence bound applies on these axes: section 10.

## 4. The `setattr` extractor rule

**What the rule did (extractor 0.2.0):** any `setattr(self, ...)` call in a class blocked every `self.m()` edge
of that class. The audit re-extracted all 44 repositories and first reproduced every stored graph exactly.
Findings:
- The rule fired in 25 classes. The calls were mostly harmless: `__setstate__` restoring pickled state
  (requests, httpx: 46 edges), a literal attribute name for a lock (daily_stock_analysis: 78 edges), and a bug
  where a `@staticmethod`'s first parameter was read as `self` (nanobot: 96 edges; the call-resolution code
  already skipped static methods, but this step did not). Only 2 classes could really overwrite a called
  method (tornado's WebSocketHandler, trio's AsyncIOWrapper).
- Measured effect: 355 edges in 12 Study A repositories if every dynamic `setattr` were ignored (an earlier
  README figure, "about 361", was slightly off and has been corrected).
- No question had a wrong or ambiguous answer under any variant. But in 13 questions (10 in requests, 3 in
  httpx) the shown graph lacked 1 or 2 real calls between the shown functions.

**Options considered:**
- Fix it (chosen by the author on 7 Nov; extractor 0.3.0): a literal name blocks only that name;
  `__setstate__` is ignored; static methods are not read as `self`. Every other dynamic `setattr` still
  blocks. Four confirmatory repositories change: requests 170 → 200 edges, httpx 323 → 339,
  daily_stock_analysis 6,800 → 6,878, nanobot 7,559 → 7,655 (confirmatory and pilot total 76,424 → 76,644).
  Their 80 questions were regenerated, and the token counts, summary files, rewiring statistics, Study B dry
  runs and code hashes were rebuilt.
- Keep the rule: nothing changes; the 13 questions keep their incomplete graphs.
- Ignore every dynamic `setattr`: 12 repositories change (+355 edges), including 4 edges to methods that are
  overwritten at run time.

## 5. Within-module rewiring control

The standard rewiring keeps a median 1.5% of edges and cuts same-module edges from 67% to 6%, so a model could
spot the rewired graph by its non-local edges. A null that only swaps edges between the same pair of modules
was run on all 44 graphs (seed 1; seeds 2 and 3 agree):
- All 44 completed and passed every invariant; the same-module share stays at 67% exactly.
- It keeps a median 45% of edges in place (above 50% in 16 of 44 graphs), because many module pairs have too
  few edges to swap. In a rough check on 24 dry-run tasks, about 65% of the displayed edges survived.
- Cost: 2 more prompts per task per model if run under opaque naming only (12 → 14, about +17% prompts).

**Decision (the author, 7 Nov):** pre-specify it in the Study B addendum as exploratory (estimate and 95%
interval, no significance test), opaque naming only, run after the confirmatory cells and cut first if time
runs short. It is too close to the true graph for a powered secondary test, and its contrast measures "the
wiring this null can move", not a clean split between module structure and exact calls. It is dropped if the
official graphs carry no module information.

Related design detail: if the official graphs turn out to be directed rather than mirrored, networkx's
directed swap is a weak null on call graphs (median 44% of edges left in place, and it did not finish on 12 of
44 graphs; 48% and 13 on the extractor 0.2.0 graphs). Our own two-edge directed swap leaves a median 2.4% (largest 8%) and finishes on all 44, so the
rewiring code uses it for directed graphs (rewire 0.2.0).

## 6. Equivalence (TOST) bound

Probability that TOST declares "no effect" when the true effect is exactly zero, using the standard errors
implied by the minimum detectable effects in the pre-registration's section 6 (estimates; the pilot
recalibrates them). Only A1 has a power level there (standard error 1.6 pp). For the others the table gives
a minimum detectable effect but no power level, so 80% power at an alpha between 0.01 and 0.05 was assumed
(standard error = MDE / (z of 1 − alpha/2 + z of 0.8), that is MDE / 3.42 to MDE / 2.80). Normal
approximation: TOST passes when the absolute estimate is below the bound minus 1.645 standard errors.
Recomputed on 8 Nov with scipy. The first version of this table gave B1 65 to 81% and B2 20 to 38% at ±5
pp; how those were computed was not recorded, and they do not follow from the assumption stated above.

| Test | Implied standard error | ±3 pp | ±5 pp |
|---|---|---|---|
| A1 | 1.6 pp | 18% | 86% |
| B1 | 1.8 to 2.5 pp | 0 to 5% | 28 to 77% |
| B2 | 2.6 to 3.2 pp | about 0% | 0 to 20% |
| A2 | 2.5 to 3.0 pp | about 0% | 0 to 29% |
| B3 | 2.9 to 4.3 pp | about 0% | 0 to 5% |

**Decision (the author, 7 Nov):** ±5 percentage points for every test (the analysis code's default). A null on
A1 can then usually be called equivalence, and one on B1 in about a quarter to three quarters of studies
(this sentence was corrected on 8 Nov: it said "A1 or B1 ... usually" before the B1 row was recomputed);
nulls on B2, A2 and B3 will mostly have to be reported as inconclusive, which the paper says plainly. A3 is
not in this table; see section 10.

## 7. Candidate order in Study B (settled)

Order 1 is a seeded random permutation of the ten candidates; order 2 is order 1 reversed. A candidate at
position p moves to 11 − p, so a gold function in A to E under one order is in F to J under the other, and
every candidate's mean position is 5.5. The same orders are used in every condition and for every model.
Written into the pre-registration (section 4).

## 8. Fixed later by data

- **Model files** (Google's QAT Q4_0 GGUFs, Apache 2.0, not gated): E2B `gemma-4-E2B_q4_0-it.gguf` 3.35 GB,
  E4B `gemma-4-E4B_q4_0-it.gguf` 5.15 GB and 12B `gemma-4-12b-it-qat-q4_0.gguf` 6.98 GB were downloaded to the
  author's Mac on 7 Nov; their names, sizes and SHA-256 matched Hugging Face's API listing (pre-registration,
  section 10). 31B `gemma-4-31B_q4_0-it.gguf` (17.65 GB) was downloaded to the author's Mac on 8 Nov, after
  the author's OK of 00:58 UTC, and its size and SHA-256 equal those in Hugging Face's API listing, read on 8
  Nov (pre-registration, section 10; `data/gng2/README.md`); 26B-A4B (`gemma-4-26B_q4_0-it.gguf`, 14.44 GB) is
  used only under backup B-3. Hugging Face updated the E2B, E4B and 12B tokenizer files on 30 Oct to 3 Nov
  ("glitch tokens"); the GGUF files date from 17 Jul. Neither the first GNG-1 run nor the reruns of 8 Nov
  found a tokenizer mismatch on the 4,040 probe strings for E2B, E4B or 12B.
- **Runtime:** llama-cpp-python 0.3.36, built with Metal on the author's Mac. The only commit string found
  is the ggml build string 0c1e570-dirty, so the built libraries' hashes are recorded
  (`data/gng1/mac_environment/`).
- **Subgraph sizes:** kept at about 12 and about 24 nodes by the pilot rule (E4B G2 accuracy between 0.55 and
  0.90): the GNG-2 pilot of 8 Nov gave 0.6625 (53 of 80 prompts; `data/gng2/final/`) on the final question
  files, as on those of 05:43 UTC, and 0.65 (52 of 80) on those of 02:08 UTC (section 11).
- **Official graph format, node kinds, anchored fraction, task counts, harness input:** need the competition
  data (main competition); the anchored fraction for B2's rule is measured when the Study B tasks are frozen,
  before any Study B result, not at GNG-2 (row 14). **SWE-bench Lite counts:** need a download on the author's
  Mac (Hugging Face is blocked from the cloud workspace).

## 9. Answer prefix (after the first GNG-1 run, 7 Nov evening)

In the first GNG-1 run (no answer prefix), E4B passed and E2B and 12B failed the letter-mass check under both
thought-block settings, while their token and tokenizer checks passed. A test of three prefixes (none,
"Answer:", "The correct option is") on the same pilot prompts found that "Answer:" lets E2B and 12B pass
(letter mass of at least 0.9 on every pilot prompt) but drops E4B to 92.5% of the A-D prompts, below the 95%
bar, while E4B passes with no prefix. No single option passes for all three models. The rule written before
the test's results were seen (one prefix for every model) would have excluded E4B. Proposed instead: a model
keeps no prefix if it passes without one; otherwise it uses the first of "Answer:" and "The correct option
is" under which it passes. This gives E2B "Answer:", E4B none and 12B "Answer:". The full timeline, both rules
and every number are in the pre-registration's section 7 and in `data/gng1/`. The author chose this rule on
8 Nov at 00:58 UTC; GNG-1 is run again with the registered prefixes before any confirmatory run. A model
without a registered prefix (31B) is smoke-tested with no prefix and, if the rule chooses one, a second
time with it; its Study A run takes the choice from that second file, whose verdicts are for the prefix the
run uses (added on 8 Nov after the final automated check).

## 10. How the ±5 pp bound applies to A3 (after the first automated review)

A3's TOST is on the mean slope of conflict cost against log10(parameters). The first implementation read the
bound as 5 points of conflict cost per tenfold increase in parameters. The two axes span different ranges
(E2B to 31B: 1.1254 decades on the effective axis, 0.8217 on the GGUF axis), so that reading makes the
sensitivity axis test a stricter total change (4.1 points against 5.6), and the two verdicts would often
disagree for reasons of units alone. The proposed reading is 5 points across the models run: the slope bound
is 0.05 divided by the log10 span of the models present on that axis, so both axes test the same 5-point
total change. Both readings are in `analysis.py` (`A3_BOUND_UNIT`, default "span"; `--a3-bound-unit decade`).

Simulation (estimates, not data): probability that A3's TOST declares "flat" when the true trend is exactly
flat, and how often the two axes disagree. `ngraph.simulate.simulate_a_arrays` with its default variances
(32 repositories, 20 items, option orders 2/2/1/1), 4,000 simulated studies per row
(`scripts/a3_bound_sim.py`):

| Models | Reading | "Flat", effective axis | "Flat", GGUF axis | Axes disagree |
|---|---|---|---|---|
| E2B to 31B | across the models run | 0.33 | 0.27 | 0.10 |
| E2B to 31B | per tenfold increase | 0.50 | 0.06 | 0.44 |
| E2B to 12B (backup B-3) | across the models run | 0.23 | 0.25 | 0.05 |
| E2B to 12B (backup B-3) | per tenfold increase | 0.01 | 0.00 | 0.01 |

The cost of the proposed reading: with all four models, "flat" passes less often on the registered axis
(about 0.33 against 0.50), because 0.05 / 1.1254 = 0.044 per decade is stricter than 0.05. In both readings
"flat" is decided on the registered axis only. The author chose this reading on 8 Nov at 00:58 UTC.

## 11. Offensive-looking pseudo-words (8 Nov)

The question files are released, so on 8 Nov every generated name (each pseudo-word, each new name and each
neutral repository handle) was compared, in lower case, with a list of offensive words. Six questions
contained such a string: OpenManus/B/S24/018 ("nazizes"), Vibe-Trading/A/S12/003 ("TeNaZi"), nanobot/A/S24/005
("pisso", "_PissoDol"), openai-agents-python/A/S24/008 ("raper", "ku_raper"), tornado/B/S24/018 ("PEDok") and
werkzeug/B/S24/015 ("pedo", "_pedo_soldun"). A second scan with shorter stems found four borderline ones:
iFixAi/A/S12/000 ("nigi"), trio/B/S24/019 ("nigu"), iFixAi/B/S12/010 ("posmilfas") and starlette/B/S12/013
("disperme"). Of the ten, seven are confirmatory questions, two are reserve questions and one (trio) is a
pilot question.

The generator now checks each question's finished names against `OFFENSIVE_SUBSTRINGS` (`names.py`, which
includes the stems "nig", "milf" and "sperm") and, on a match, names the question again, names and parity
re-draws together, with seeds that add the attempt number (`items.py`). A question with clean names keeps its
seeds, so this renaming left the other 870 questions unchanged. In the ten, only the neutral names changed,
and with them the G2 and G4 texts in both option orders; the answers, options, edges and the G0, G1 and G3
texts are the same, and each question was clean at the first new attempt (`neutral_naming_attempt` 1). Among
the 640 confirmatory questions the parity figures were unchanged by this first renaming (615 within 2 tokens,
25 more than 2 apart, 11 more than 10 apart, largest gap 55 tokens); the token totals and the tokenizer probe
were rebuilt. GNG-1 scores only real-name (G1) prompts, which did not change; the GNG-2 pilot scores G2
prompts and was run on the renamed files (`data/gng2/`).

The author chose to rename the six questions and the four borderline ones on 8 Nov at 01:43 UTC, before any
confirmatory run.

**The wider check (8 Nov).** A further check of the renamed files by the AI coding assistant found two gaps.
First, the comparison kept "_" and "-", so a blocked string split by them passed: with them removed, the list
matched 38 distinct name parts (41 occurrences) in 34 questions (30 confirmatory, 2 reserve, 2 pilot), for
example "kir_na_zi" (flask/A/S12/004), "kil_ra_pe" (flask/A/S12/002), "ki_ke_dul" (PageIndex/A/S24/009) and
"ni_ga" (PageIndex/A/S12/002), while "TeNaZi" had been caught only because case, not a separator, joins its
parts. Second, the list lacked words that the generator can write: "fuk" is a whole pseudo-word in eight
questions and is the neutral repository name in strix/A/S12/001 ("... of the Python repository fuk."); "pute"
and "putes" (French), "figa" (Italian) and "gorputo" (Spanish "puto") occur in four more. The generator writes
only the letters b, d, f, g, k, l, m, n, p, r, s, t, v, z and a, e, i, o, u, so 12 entries of the list (for
example "fuck" and "hitler") can never match. Two passes of the assistant judged these names differently: the
first rated the split words high; the second reproduced every string and count, judged the split names at most
faintly suggestive (for example "kir_na_zi") or harmless (for example "ko_ni_gol") and only "fuk" clearly
offensive, and proposed narrower rules (these words only as whole syllables; 24 questions in all).

The author chose the wider check on 8 Nov at 05:39 UTC, before any confirmatory run. `offensive()` now also
reads each name with "_" and "-" removed, and 26 words made only of letters that the generator writes were
added to the list (`names.py`; `UNWRITABLE_BLOCKED` names the 12 entries that cannot match). Dots between the
parts of a qualified name are not removed, so a string split by a dot is not matched (for example "dara.pe" in
fastapi/A/S24/009). Digits kept from the original name are not removed either, so "Ni1g" (VoxCPM/A/S12/002,
from "Snake1d") is not matched. The check named 76 more questions again (59 confirmatory, 11 reserve, 6
pilot): 34 for an entry of the first list that "_" or "-" had split and 42 for an added word, which, as part
of a longer name, also catches harmless strings such as "FuKO". Of the 76, 67 were clean at the first new
attempt and 9 at the second; none of the ten renamed first changed again. As before, only the neutral names
and the G2 and G4 texts changed. Among the 640 confirmatory questions, 613 are now within 2 tokens, 27 more
than 2 apart and 11 more than 10 apart (largest gap 55 tokens, as before); the token totals and the tokenizer
probe were rebuilt (README, "Numbers"). Six pilot questions changed (langextract/A/S12/003 and A/S24/006;
trio/A/S24/007, B/S24/015, B/S24/017 and B/S24/018), so GNG-1 and the GNG-2 pilot were run again on these
question files (delivered at 05:43 UTC): E2B, E4B and 12B passed GNG-1 with the same letter masses as before,
and the pilot gave 0.6625 (53 of 80), so the sizes stay (pre-registration, section 7; `data/gng2/`). A scan of
these names with the first pass's own list (720 strings in several languages) and its verdicts found no word
that it judged offensive or borderline except across dots; some that it judged mild remain (for example
"seksi", which reads as "sexy" in some languages).

**The review's scan (8 Nov).** An independent review of the package of 05:43 UTC by the AI coding assistant
scanned the names again with its own word list. It found three words that the list did not block and that the
first pass had judged harmless as syllables: "fok" (Afrikaans; a whole pseudo-word in 7 questions, 4
confirmatory and 3 reserve, and in one of them, boltons/A/S24/005, also the neutral repository name), "pula"
(Romanian; in the pilot question langextract/A/S24/005, as "pula", "pula_tok" and "PulaZoBi") and "puki"
(Malay and Tagalog; in the neutral repository name "pukin" in boltons/B/S24/019 and as "_pu_ki" in
laya/B/S24/018 and mcp-for-blender/B/S24/015). It also listed "dikes" (the neutral repository name in the
pilot question trio/A/S24/007), "Pu_Ke" (the neutral repository name in Agent-Reach/A/S24/007; "puke" is also
Tagalog), milder strings such as "salak2" (jinja/B/S24/015) and "dirfapus" (DeepTutor/B/S24/016), and short
syllables that are vulgar in some language: dik, kok, fak, kuk, pik, lul, kus, sik, kir, kak, pis and bok are
whole pseudo-words in 605 of the 880 questions (441 confirmatory), and "zobi", close to the French slang
"zob", is the neutral repository name in httpcore/A/S24/008. Blocked as substrings, each of these syllables
would rename 92 to 135 questions.

The author chose on 8 Nov at 16:57 UTC, before any confirmatory run, to rename the questions with "fok",
"pula" and "puki". "puki" was added to the list; "fok" and "pula" are blocked only where a whole pseudo-word
equals one of them (`WHOLE_WORD_BLOCKED` in `names.py`, checked in `items.py`), the narrowest rule that
renames the questions in which they were found. This named 11 more questions again (5 confirmatory, 5 reserve,
1 pilot): boltons/A/S24/005, boltons/B/S24/019, iFixAi/B/S12/012, mempalace/B/S24/018 and PageIndex/A/S24/005
(confirmatory); anyio/A/S12/004, cattrs/A/S24/005, laya/B/S24/018, mcp-for-blender/A/S24/006 and
mcp-for-blender/B/S24/015 (reserve); langextract/A/S24/005 (pilot). Of the 11, 10 were clean at the first new
attempt and mempalace/B/S24/018 at the second. "dikes", "Pu_Ke", "zobi", the short syllables and the milder
strings stay, by the same choice; the new names of 8 of the 11 questions contain such syllables as whole
pseudo-words too, and 605 questions (442 confirmatory) contain one in the final question files. "fok" and
"pula" also remain inside longer pseudo-words, which the rule allows (for example "fokal" in iFixAi/B/S12/010
and "pulal" in mcp-for-blender/A/S12/001). As before, only the neutral names and the G2 and G4 texts changed.
Among the 640 confirmatory questions, 613 are within 2 tokens, 27 more than 2 apart and 11 more than 10 apart
(largest gap 55 tokens), as before; the token totals and the tokenizer probe were rebuilt (README, "Numbers").
The probe strings changed, and so did one pilot question, so GNG-1 and the GNG-2 pilot were run again on the
final question files, with 31B's GNG-1, after the author's OK of 17:21 UTC: E2B, E4B and 12B passed with their
registered prefixes and 31B with "Answer:", and the pilot gave 0.6625 again, so the sizes stay
(pre-registration, section 7; `data/gng2/final/`).

## 12. 31B's GNG-1 runs on the question files from before the first renaming (8 Nov)

On 8 Nov at 01:14 UTC the AI coding assistant started a Claude Code session on the author's Mac with steps
that ended with 31B's GNG-1: a smoke run with no prefix (`runs/smoke_31B_no_prefix.json`); only if the rule
chose a non-empty prefix, a second smoke run with it (`runs/smoke_31B.json`); and only if that file passed
GNG-1 with the rule's choice, a check that `study-a --prefix-from` accepts it on the G2 pilot prompts
(`runs/pilot_prefix_from_31B_G2.jsonl`). After the author's choice to rename ten questions (section 11), the
assistant stopped the session at 01:44:22 UTC, because its runs used the question files from before the
renaming, and told the author that it would hold 31B's GNG-1 until the GNG-1 fallback (row 11) was answered.
The first file had been written at 01:37:54 UTC; the other two appeared after the stop, at 01:45:58 and
01:47:02 UTC (the files' times on the Mac), apparently written by commands that were still running. All three
were made with the question files from before the first renaming. They are not in the package, and
`--prefix-from` would refuse them for a run on the final files, because it checks the digest of the item
files. Of the three, only the model-file fields of the first were read (for the SHA-256 and the chat template
in the pre-registration's section 10); none of their results was opened.

Their existence alone says something about the results. Under the steps above, the second file is written only
when the rule chose a prefix, and `study-a` writes the third only after accepting the second, which requires
that it passed GNG-1 with the rule's choice. So, if the session followed those steps, 31B passed GNG-1 with
"Answer:" or "The correct option is" under its per-size setting. This is an inference from the files' names,
not a reading of them. The assistant told the author so on 8 Nov at 02:08 UTC, while the GNG-1 fallback, which
matters only for a model with no passing candidate under its per-size setting, was still with the author; the
author's answer on the fallback (8 Nov, 16:57 UTC; row 11) is therefore not blind to this hint. After that
answer, 31B's GNG-1 ran on the final question files (its output files were written between 17:42 and 17:51
UTC): under its per-size setting the rule chose "Answer:", as the hint suggested, and 31B passed with it, so
the fallback was not used (`data/gng2/final/`; pre-registration, section 7). The three earlier files were not
read and are not in the package.

## 13. The schedule after the first posting date passed (9 Nov)

The first freeze (README section 6) was made on 8 Nov: its manifest, made at 18:54 UTC, has the SHA-256
`557cd2bf0eefc3bf9af4feb742588fabcc3de4b76bdb591253b6f4e0273bf6da`, and its snapshot archive
`4290c853e561b501ac79d39cfaf627770e76996a62e1ee33d2e7e02994be3a7f`. The author did not post that hash by the
checkpoint GNG-3 (Sun 8 Nov 23:59 UTC), and it was never posted. By that text's checkpoints, a missed GNG-3
left Study A with one-hop items only, three sizes and no mirrored-format arm, and a missed GNG-4 (Mon 9 Nov
12:00 UTC) left Study B with the official tasks only and B1 on E4B (backup B-4). On 9 Nov at 17:26 UTC the
author asked that neither study shrink, and at 17:27 UTC confirmed that nothing had been posted. No
confirmatory run had started (none of Study A, and the Study B runner does not exist yet). So the plan was
changed before any time-stamp, as for any other change before the freeze: the AI coding assistant proposed new
dates from the measured run speed (Study A's confirmatory runs take about 2.2 hours on the Mac in all, an
estimate from the speeds in the GNG-1 files of `data/gng2/final/`, with a factor of 1.3), and the author
accepted them at 17:28 UTC: the hash is due by Mon 9 Nov 23:59 UTC, the Study B addendum by Tue 10 Nov 18:00
UTC, the confirmatory runs by Tue 10 Nov 18:00 UTC (Study A) and Wed 11 Nov 18:00 UTC (Study B), with a hard
stop at Thu 12 Nov 06:00 UTC. A later post now delays the runs and drops nothing (cells unfinished at the hard
stop are still reported as "not run"), and backup B-4 is removed. The 8 Nov manifest and archive were moved
out of the package and kept; the manifest made after this change is the one posted. Its text differs from the
8 Nov one only by these dates and rules (pre-registration, sections 2 and 7; README, section 6 and Decisions
items 12 and 13; rows 14 and 15, section 1 and the first line of this file), by this section, by the freeze
date and time (the pre-registration's header and the README's status line) with a change-log entry for this
second freeze, and by the hashes that follow from these edits (the README's line in `CODE_SHA256.txt` and the
code hash in the pre-registration's section 10).

## Status after this file was first written (7 Nov, about 16:45 UTC)

- Thought block: the smoke test scores every pilot prompt under both settings, logs the probability of
  `<|channel>` at the answer position, and applies the rule in the pre-registration's section 7
  (`thought_block_decision`: keep, switch with a logged deviation, or neither passes).
- Directed rewiring: done (rewire 0.2.0). Directed graphs use the two-edge swap by default; networkx's
  directed swap stays available with `--engine networkx`. On the extractor 0.3.0 graphs networkx's swap
  stops early on 12 graphs and leaves a median 43.8% of edges in place (13 and 47.6% on the 0.2.0 graphs).
- The `setattr` fix is applied (extractor 0.3.0). Checked: only the 4 repositories named in section 4
  change; the other 40 question files are byte-identical; no screening outcome changes (the 12 repositories
  excluded for fewer than 150 edges keep the same edge counts); in the requests history dry run, two tasks
  move from S3 to S1. The rule also applies to our graphs for the SWE-bench Lite arm of Study B.
- `data/tokenizer_probe.json` was rebuilt from the confirmatory question files with the command in the
  README (the previous file did not reproduce with the current code; its metadata showed an older version of
  the template check). `data/studyb_dry/httpx_rename_check.json` was refreshed because it also did not
  reproduce: only its residual-cue counts for the organisation name "encode" differ, which the current
  renamer protects as a method of Python strings.

## The author's choices (7 Nov, 17:38 UTC) and what changed

- Time-stamp (section 1): option B, a hash-only forum post with a plain title. Built: `src/ngraph/commit.py`
  writes the manifest of every file with its SHA-256, checks the package before a freeze, gives one hash per
  folder, archives each freeze outside the package and prints the post text (README, section 6).
- Technical choices: all four adopted. The `setattr` fix is applied (section 4). A3 (section 3): the
  effective-parameter axis and the GGUF text-model totals are registered in `analysis.py`, which reports A3
  on both. TOST (section 6): ±5 pp for every test; `analysis.py` also reports TOST for A2 (Welch, two-sample)
  and A3 (on the mean slope; see section 10). Within-module null (section 5): exploratory, in the Study B
  addendum.
- `CODE_SHA256.txt` is written by `python -m ngraph.commit code-sha256`, which leaves out the top-level
  `runs/`, `.venv/` and `.git/` folders and caches; an earlier `find` command would have listed a virtual
  environment made inside the package.
- Model files (section 8): E2B, E4B and 12B were downloaded and checked on the author's Mac. The runner
  records llama.cpp's parameter count of each file (`model_n_params`), to check the A3 sensitivity values
  against the files themselves.

## After the first automated review (7 Nov, about 19:30 UTC)

Four automated review passes of the AI coding assistant, each finding re-checked by a second pass, covered
the hash scheme and post text, the commit tool, the statistics and the documents: 43 findings, 39 confirmed
on re-check, none rated serious. Changes made:
- Before writing a manifest, the commit tool now checks that `CODE_SHA256.txt` is current byte for byte, that
  every hash cited next to a package file in `prereg/` is current, that a Status line names the freeze, that no TBD marker is left
  (Study B's TBD-B markers may stay until the addendum), that no draft-only text is left in `prereg/` or the
  README, that earlier manifests form one chain, that no file is over 100 MB, and that there are no symbolic
  links or file names with line breaks. `manifest --check-only` lists everything that still blocks a freeze.
- The addendum's manifest names the first manifest's hash (`--follows`) and lists every file changed, added
  or removed since; `verify` checks that chain, `verify --expect` checks a hash copied back from the forum,
  and the addendum's post text is a reply in the first topic. The snapshot is written outside the package
  and streamed to disk; `--root` works before or after the subcommand.
- Each Study A run file records the code hash and the digest of the item files it used, and a run file is
  never extended with other item files.
- A1 to A3 use only the registered models (E2B, E4B, 12B, 31B; tags read case-insensitively); the
  familiar-minus-fresh difference of A3 slopes is reported descriptively; A3's bound reading is section 10.
- Documents: the model files stay outside the package folder; the README has a freeze checklist; the GNG-1
  evidence is in `data/gng1/`; and the time of the first answer-prefix rule was corrected from 18:40 to
  18:36 UTC.

## After the second automated review (7 Nov, about 22:00 UTC)

Five automated review passes of the AI coding assistant covered the commit tool, the runner and the report,
the documents and the release rules: 38 findings, 37 confirmed or partly confirmed on re-check, none rated
high severity. Two further passes re-checked the code changes (one for the commit tool, one for the runner
and the report), and the gaps they found were fixed. Changes made:
- Commit tool: the snapshot archives exactly the bytes it checked against the manifest and is written only
  if every file matches; `post` refuses a manifest that changed while it was being checked; `verify` also
  reports paths it refuses (such as symbolic links) that the manifest does not list; `manifest --check-only`
  lists every problem at once; a manifest in a subfolder of `prereg/` is refused; and the Status line must
  name the label exactly.
- Runner: a model without a registered answer prefix (31B so far) takes the rule's choice from its own GNG-1
  smoke file (`study-a --prefix-from`). That file must be for the same model file (SHA-256) and thought-block
  setting, must have passed its token and tokenizer checks, and must have scored the registered pilot
  prompts from the same item files; the run file records where its prefix came from (`answer_prefix_source`).
  Extending a run file is refused when the model file, any setting, the jobs or the item files differ.
- Report: one run file per model (a second file for the same model is refused); A1 is also reported without
  the parity-flagged items (25 of the 640 confirmatory items; pre-registration, section 6); and `--items-dir`
  must be the item folder that the run files recorded.
- Documents: the pre-registration is now `prereg/PREREGISTRATION.md` (it was `PREREGISTRATION_DRAFT.md`).
  Each passage that still waits for the author's choice carries a marker that `manifest --check-only` lists
  until the passage is rewritten. The README and this file say what the AI coding assistant did. The licence
  of the package's own files is not decided yet.

## After the final automated check (8 Nov, about 01:00 UTC)

Four automated review passes of the AI coding assistant (the code, the documents, a full rehearsal of the
freeze, and the release rules), each finding re-checked by a second pass: 28 findings, 22 confirmed and 4
partly confirmed (7 of them rated medium, none high), 2 refuted. Changes made:
- Runner: a smoke file given to `study-a --prefix-from` must have been run with the rule's choice and have
  passed GNG-1, so a prefix chosen by the rule is tested in a second smoke run (pre-registration, section 7);
  a run file begun before a freeze is not continued after it, and one whose recorded manifest is missing or
  changed is not continued either; the code hash is kept in the run file when the package holds a path the
  commit tool refuses; the runner, the report, rewire and the two Study B scripts make their output folders.
- Report: each run file's sessions are listed, with warnings for a file begun before any freeze, more than
  one code hash, or code that did not match `CODE_SHA256.txt`; an item folder that cannot be digested, or a
  JSON file in it that is not an item file, is refused with a message.
- Commit tool: a listed file or folder whose name starts with "." stops the freeze; every command prints
  errors as a message; the snapshot names the files that no longer match; the chain check prints the full
  hashes.
- Documents: the GNG-1 fallback is stated as one rule (the prefix candidates under the per-size setting, then
  under the other setting, then exclusion; at that time still open for the author); reciprocity is described
  as kept only for mirrored graphs; the TOST table above was recomputed; "Study A files" are defined in the
  pre-registration's section 11; the README says to run Study A from an unpacked copy of the snapshot after
  the post, how to fill the 31B rows if 31B is not downloaded by the freeze, and to check the addendum's hash
  after its reply is posted; the token totals now include the registered answer prefixes; the Apache License
  2.0 text is added next to the vocabulary file (`third_party/llama.cpp/`).

## After the re-checks of 8 Nov (about 06:13 UTC)

Three automated passes of the AI coding assistant re-checked the package as it was at 01:10 UTC (the code, the
documents, and a rehearsal of the whole freeze, from the check to a trial addendum): 19 findings, some found
by more than one pass, 4 of them rated medium and none high. A second pass confirmed the code and document
findings (one of them only in part); the rehearsal's findings were checked against the files. A further pass
checked the renaming of 01:43 UTC on a copy of the package of 02:08 UTC: it regenerated the question files
(equal byte for byte), recounted the token totals and the probe (equal), and scanned every generated name with
its own list; it found the gaps described in section 11, which a second pass confirmed in part. Changes made:
- Passages that call a decision open: each now carries the draft-only marker, so `manifest --check-only` lists
  it (the intro and items 9 and 10 of the README's Decisions list, and the note at the end of this file), and
  README section 6, step 1, lists them; `data/gng1/README.md` no longer reads as if the author had chosen
  exclusion at 00:58 UTC; the runner's docstring and refusal message point to the pre-registration for the
  GNG-1 fallback instead of stating it; README section 2 gives every step of the proposed fallback and says
  that a switch of the thought-block setting is entered in the deviation log by hand.
- 31B: the documents say that it was downloaded (pre-registration, section 3; section 8 above); the
  pre-registration's section 10 gives its size, SHA-256 and chat template, and its SHA-256 equals the one in
  Hugging Face's API listing; its GNG-1 runs on the question files from before the first renaming are
  described in section 12.
- Pre-registration: section 7 says that 31B's Study A run takes the rule's choice from the smoke file run with
  that choice, before or after the freeze; the determinism check is stated as the code performs it; section 8
  says what each seed hashes; section 11 counts the README's Study A text and the pre-registration's section
  12 among the Study A files whose changes enter the deviation log.
- Freeze steps (README, section 6): GNG-1 outputs made after the freeze are copied into
  `data/gng2/after_freeze/` at the addendum, so that the addendum's hash covers them; the addendum keeps the
  `prereg-v1.0` code hash, which every Study A run file records, in a row of its own.
- Results of 8 Nov from the author's Mac (`data/gng2/`): E2B, E4B and 12B passed GNG-1 again with their
  registered prefixes, on the question files of 02:08 UTC and again on those of 05:43 UTC; the GNG-2 pilot
  gave 0.65 and, on the question files of 05:43 UTC, 0.6625, so the subgraph sizes stay (pre-registration,
  sections 3 and 7).
- Names (the author's choice of 05:39 UTC; section 11): the wider check named 76 more questions again; the
  token totals and the tokenizer probe were rebuilt, and the tests check joined names and the entries that
  cannot match (247 tests). `batch.py` no longer stores run times in `data/items_summary.json`, so
  regenerating the question files reproduces that file byte for byte, and its docstring and the README give
  the command (README, "Numbers").

## After the review of the package of 05:43 UTC (about 17:40 UTC)

Three automated review passes of the AI coding assistant (the documents, the data and the names), each finding
re-checked by a second pass, covered the package as delivered at 05:43 UTC: 23 findings, 3 of them found on
re-check, 18 confirmed and 5 confirmed in part, 3 rated medium after the re-check and none high. The passes
confirmed every count and hash in the documents that they could check against the files, and reproduced the
question files, `data/items_summary.json`, the token totals and the probe byte for byte. Four findings had
been resolved in the package of 06:13 UTC: two on the folder for the runs on the question files of 05:43 UTC
(README, section 6, step 1, and `data/gng2/README.md`), one on the README's status line and one on the
pre-registration's list of open items (its last section, removed at the freeze). Before delivery, further
checks by the assistant reviewed this update as prepared (the documents, the code and the new names); their
points are included. Changes made:
- Documents: wording corrections ("fuk" is the neutral repository name in one question, not of one repository;
  the wider check matched 38 distinct name parts, 41 occurrences; the blocked list holds offensive words in
  general, not only slurs and sexual or violent words; section 11 says that digits are not removed either, and
  why the first pass's scan missed the words of the review's scan); the pre-registration's section 3 points to
  section 7 for the pilot results.
- Runs still to be made: the documents say plainly that GNG-1 of E2B, E4B and 12B and the GNG-2 pilot still
  have to be run again on the final question files; the README's freeze step 1 lists these runs, what to
  record about them in `data/gng2/README.md` and the passages to rewrite after them, and the
  pre-registration's list of open items (its last section, removed at the freeze) names them. The runs on the
  question files of 05:43 UTC moved from `data/gng2/final/` to `data/gng2/second_rename/` (with
  `mac_environment/CODE_SHA256_at_second_rename_runs.txt`), so that `final/` holds the runs on the final
  question files.
- Freeze steps (README, section 6, step 2): the question files are regenerated and compared with `data/items/`
  before the hashes are taken, because the tests regenerate only 7 of the 44 files.
- Tests: a blocked string whose parts are joined by "-" alone is checked.
- Names (the author's choice of 16:57 UTC; section 11): the review's scan found "fok", "pula" and "puki"; 11
  more questions were named again, the token totals and the tokenizer probe were rebuilt, and a test checks
  the whole-word rule: a blocked pseudo-word is drawn again, and a pseudo-word that only contains a blocked
  word is not (248 tests).
- The author's answers of 16:57 and 16:58 UTC (rows 11, 13 and 14): the GNG-1 fallback is recorded as chosen
  (pre-registration, section 7; README, section 2 and Decisions, item 9); B2's anchored-task check moves from
  GNG-2 to the Study B freeze (pre-registration, sections 2 and 7; README, Decisions, item 12); the Apache
  License 2.0 is added as `LICENSE` (README, Decisions, item 10). The pre-registration's list of open items
  now holds the post, the runs on the final question files, the authors and Study B.

## After the runs on the final question files (8 Nov, about 18:35 UTC)

The author approved the runs on the final question files at 17:21 UTC. On the Mac, in one session, E2B, E4B
and 12B passed GNG-1 with their registered prefixes, the GNG-2 pilot gave 0.6625 (53 of 80) again, and 31B
passed GNG-1 with "Answer:", the registered rule's choice for it, so the GNG-1 fallback was not used. Changes
made:
- `data/gng2/final/`: the seven output files, and `mac_environment/CODE_SHA256_at_final_runs.txt`;
  `data/gng2/README.md` lists them with their SHA-256 and write times and describes the results.
- Pre-registration: section 7 reports these runs in place of its two markers for them, and section 3 points to
  the pilot on the final question files; its list of open items no longer names these runs.
- README: the status line (whose previous version gave the time as about 17:40 UTC; that package was delivered
  at about 17:12 UTC), the `data/gng2/` row, freeze step 1, the 31B paragraph of section 3, the addendum steps
  and Decisions items 7 and 11; this file: sections 8, 11 and 12.
- The "Authors" line of the pre-registration's header: Zaeem Khan, as the author gave it at 18:21 UTC. The
  pre-registration's list of open items and README freeze step 1 no longer name it.

## The Study A freeze (8 Nov, about 18:55 UTC)

README section 6, steps 1 to 4. Pre-registration: the header now starts with the line
`Status: prereg-v1.0, frozen 8 Nov 2026 (UTC)` in place of the draft line, and its paragraph says that only
the TBD-B markers of Study B are left; the last section, the list of open items, was deleted (its two
remaining items were the post of the hash, which the author makes after the freeze, and Study B, whose open
points stay as TBD-B markers until the addendum); section 10 gives the code hash (SHA-256 of
`CODE_SHA256.txt`) and the digest of `data/items/`. A read of the frozen text before the manifest led to three
wording changes in it: section 2 said that the author moved B2's check "before this file was posted" (the file
is not posted, only its manifest's hash; now "before the freeze"); and section 4 said that a replayed native
tool-response turn is used for the graph context only if its format is verified at GNG-1, while section 7
listed graph-context delivery as "fixed (inline by default)" at GNG-1. GNG-1 did not check the native turn, so
by that rule the graph context is delivered inline; both places now say so. README: the status line. The
question files were regenerated and compared byte for byte before the code hash was taken, and the tests
passed.

## The second Study A freeze (9 Nov, about 17:50 UTC)

The manifest of the first freeze was not posted; section 13 gives its hash and the reasons. After the changes
listed there, README section 6, steps 1 to 4 were run again: the Status line and the header now give 9 Nov
2026 as the freeze date, the README's status line gives the time of this freeze, and section 10 of the
pre-registration gives the new code hash (the README is one of the files in `CODE_SHA256.txt`); the item
digest is unchanged. The question files were regenerated and compared byte for byte before the code hash was
taken, and the tests passed.

## The author's choices of 8 Nov (00:58, 01:43, 05:39, 16:57 and 16:58 UTC)

The author chose the per-model answer-prefix rule (row 9, section 9), the A3 bound of 5 points across the
models run (row 10, section 10) and the download of the 31B model file at 00:58 UTC, the renaming of the ten
questions with offensive-looking or borderline pseudo-words (row 12, section 11) at 01:43 UTC, the wider check
of the names, which renamed 76 more questions (row 12, section 11), at 05:39 UTC, and, at 16:57 UTC, the
renaming of 11 more questions after a further scan (row 12, section 11), the GNG-1 fallback (row 11) and the
measuring of B2's anchored fraction when the Study B tasks are frozen instead of at GNG-2 (row 14). At 16:58
UTC the author chose the Apache License 2.0 for the package's own code and text (row 13).
