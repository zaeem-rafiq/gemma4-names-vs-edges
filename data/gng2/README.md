# GNG-1 rerun and GNG-2 pilot, 8 Nov 2026

This folder holds the outputs of the GNG-1 rerun with the registered answer prefixes (E2B, E4B and 12B), of
31B's GNG-1 and of the GNG-2 pilot (pre-registration, sections 3 and 7). All ran on the author's Mac Studio
before the freeze and before any confirmatory run. GNG-1 of E2B, E4B and 12B and the pilot ran four times: on
the question files as they were before ten questions were named again (`before_rename/`), after that renaming
(`first_rename/`), after a wider check had named 76 more questions again (`second_rename/`), and after a
further scan of the names had named 11 more again (`final/`; README "Decisions", item 11). 31B's GNG-1 here
ran on the final question files (`final/`); its earlier runs are described in `prereg/OPEN_ITEMS.md`, section
12. The pre-registration reports the runs in `final/`; the others are kept as a record. The files were copied
from the Mac byte for byte; the SHA-256 values below were computed on the Mac and again on the copies, and
they are equal. Nothing here was edited. The files contain no user names or home-folder paths.

All times are UTC. "Written" is the file's modification time on the Mac.

Who did what: the author ran this work with an AI coding assistant (Claude Code). The assistant wrote the
code in a cloud workspace and ran the commands on the Mac in a Claude Code session there, under the
author's approval of these runs; the author made every decision recorded as the author's. The times come
from our own records (the Mac's file times and the assistant's message times). Nothing in this package or
in the forum post can confirm their order independently.

## Files

| File here | Where it was written on the Mac (project folder) | Written | Bytes | SHA-256 |
|---|---|---|---|---|
| `final/gng1_rename3_E2B.json` | `gemma4-paper-code/runs/gng1_rename3_E2B.json` | 17:26:51 | 8,770 | `eff6a06c76a548510adbca177289a7958991bbf37877cf109631b9465c0ae3aa` |
| `final/gng1_rename3_E4B.json` | `gemma4-paper-code/runs/gng1_rename3_E4B.json` | 17:30:26 | 8,847 | `6767e9660a4d6f70fd95ffd28dfe2b33cf146e5d574f08c8988af16a35c9f1a6` |
| `final/gng1_rename3_12B.json` | `gemma4-paper-code/runs/gng1_rename3_12B.json` | 17:34:27 | 8,839 | `7947e1b3ab2b6f5230da48335e25017aeea5f64dc85787ec360d884e7873baf5` |
| `final/pilot_gng2_rename3_E4B_G2.jsonl` | `gemma4-paper-code/runs/pilot_gng2_rename3_E4B_G2.jsonl` | 17:34:47 | 64,065 | `bc018b395fae7e62d8210c7f850b3594b7532f8ceb00d9c30a86186caa29836e` |
| `final/gng1_rename3_31B_no_prefix.json` | `gemma4-paper-code/runs/gng1_rename3_31B_no_prefix.json` | 17:42:41 | 9,187 | `f858ed2c3a6d8b16f1b852de7f093789f9ebf3ce4fe759a238a9590e835248d7` |
| `final/gng1_rename3_31B.json` | `gemma4-paper-code/runs/gng1_rename3_31B.json` | 17:50:40 | 8,865 | `d1a1801b5a3dcd9e07592787a705c5194739c61fa9a0457ddd01ff9b00dd7616` |
| `final/pilot_prefix_from_rename3_31B_G2.jsonl` | `gemma4-paper-code/runs/pilot_prefix_from_rename3_31B_G2.jsonl` | 17:51:35 | 33,212 | `b2a4cf7b7dcf2390c98551975f8713409f380fbe14d6c5b3c8c6d45b0ae717f8` |
| `second_rename/gng1_rename2_E2B.json` | `gemma4-paper-code/runs/gng1_rename2_E2B.json` | 05:47:51 | 8,772 | `35464d3e05e15075fbb78e28e71ee703d8ff21ccbe51d38453beaf797a8fda5f` |
| `second_rename/gng1_rename2_E4B.json` | `gemma4-paper-code/runs/gng1_rename2_E4B.json` | 05:51:18 | 8,845 | `298ed0223eb5c9b0ce10b1a5d07a9c3aa49a944c162a9ab2f253857c989ac3cc` |
| `second_rename/gng1_rename2_12B.json` | `gemma4-paper-code/runs/gng1_rename2_12B.json` | 05:55:15 | 8,838 | `e4934944384e7371ee77fab94e66f131219d635c8cbea3697728478891e77045` |
| `second_rename/pilot_gng2_rename2_E4B_G2.jsonl` | `gemma4-paper-code/runs/pilot_gng2_rename2_E4B_G2.jsonl` | 05:55:48 | 64,068 | `5c9e71452eb06fdb977841f7286b4606e81aadbca838520ada5392d6df0140cf` |
| `first_rename/gng1_final_E2B.json` | `gemma4-paper-code/runs/gng1_final_E2B.json` | 02:13:38 | 8,773 | `ed49e71fbb12c62e32779e8725570d1bc71dac4e804b4c8759d30c94c928d79a` |
| `first_rename/gng1_final_E4B.json` | `gemma4-paper-code/runs/gng1_final_E4B.json` | 02:18:03 | 8,846 | `31e113c2e1abc33eca5e426d7ada2a6208fe0cd70a603e735ad240a05698f610` |
| `first_rename/gng1_final_12B.json` | `gemma4-paper-code/runs/gng1_final_12B.json` | 02:22:13 | 8,839 | `6ea0f9d40415dcd6eb923a21de4588c3705701b30010cd6d361e3c7c9ae43657` |
| `first_rename/pilot_gng2_final_E4B_G2.jsonl` | `gemma4-paper-code/runs/pilot_gng2_final_E4B_G2.jsonl` | 02:22:43 | 64,038 | `866dab785e65a0744b2f0073e64349dc654952d23bb3f311baf5bfa5ad652b4b` |
| `before_rename/gng1_rerun_E2B.json` | `gemma4-paper-code/runs/gng1_rerun_E2B.json` | 01:20:07 | 8,772 | `a698b2589573cf12dedbe87d5def513ce5fb7f648eb3c03eb0097c1a53fca4f4` |
| `before_rename/gng1_rerun_E4B.json` | `gemma4-paper-code/runs/gng1_rerun_E4B.json` | 01:24:40 | 8,847 | `54a6639cea4e891b1215a27d3d75b6f6e46afa03205fa851f1bbd5588fd66c5f` |
| `before_rename/gng1_rerun_12B.json` | `gemma4-paper-code/runs/gng1_rerun_12B.json` | 01:29:10 | 8,838 | `686dd03168ae38a2145e947bd15ec1acea32c8a949cb79db360869c4d311c49f` |
| `before_rename/pilot_gng2_E4B_G2.jsonl` | `gemma4-paper-code/runs/pilot_gng2_E4B_G2.jsonl` | 01:29:42 | 64,043 | `6e52d6b657d1caae650e0adf743feef38878f67eacd16d6cbca589cb7e84e1fd` |
| `mac_environment/model_files_SHA256SUMS.txt` | `models/SHA256SUMS.txt` | 01:26:52 | 524 | `be69b273e1c31f6c8b600a152358edfb7340d7a47475c0ea5940a737a660db2a` |

Each file keeps its name from the Mac, so the "final" in the names of the files in `first_rename/` predates
the wider check.

`mac_environment/CODE_SHA256_at_final_runs.txt` is the package's `CODE_SHA256.txt` as delivered on 8 Nov at
about 17:12, `mac_environment/CODE_SHA256_at_second_rename_runs.txt` the same file as delivered at about 05:43
and `mac_environment/CODE_SHA256_at_these_runs.txt` as delivered at about 02:08 (all copied from the cloud
workspace, not from the Mac). Their own SHA-256 values are the code hashes that the run files record:
`b17ac80a3adbcaa2cd75d727e27e6b03b22cfbd630862ac27d7491df04722d3f` in every file in `final/`,
`ac53a1781412d62914f808ef0c85d88b95201b6ecb27146693e26978ca9eb971` in every file in `second_rename/` and
`25e40de4b7b478a1f94055c341ab1c96b3cb0bb4795e12467bddd23c374a72c0` in every file in `first_rename/`. Comparing
them line by line with the frozen `CODE_SHA256.txt` shows which code files changed between these runs and the
freeze.

## Code, items and machine

- `final/`: the package as delivered on 8 Nov at about 17:12 (code hash `b17ac80a...04722d3f` as above, item
  digest `511b839ff70e2106c85bdfa5e726e7a5d4b3712ec52e0c6ec750c29f15b782b7`), the question files after the
  further scan of the names, the third renaming (pre-registration, section 3; README "Decisions", item 11). On
  the Mac, `sha256sum -c` of all 173 package files passed at about 17:12 UTC, before these runs; in the
  session of the runs, `shasum -a 256 CODE_SHA256.txt` and `python -m ngraph.commit digest data/items` gave
  the values above, and the tests gave "248 passed". The author approved these runs at 17:21 UTC.
- `second_rename/`: the package as delivered on 8 Nov at about 05:43 (code hash `ac53a178...ca9eb971` as
  above, item digest `78146cf671fb60d7c9c778d6e70f0d176a16225fc6273762f39630e1cca06c57`), the question files
  after the wider check of the names, the second renaming (pre-registration, section 3; README "Decisions",
  item 11). These runs were repeated on the final question files (`final/`). On the Mac, `sha256sum -c` of all
  167 package files passed at 05:43 UTC, before these runs; in the session of the runs,
  `shasum -a 256 CODE_SHA256.txt` and `python -m ngraph.commit digest data/items` gave the values above, and
  the tests gave "247 passed".
- `first_rename/`: the package as delivered on 8 Nov at about 02:08 (code hash `25e40de4...a72c0` as above,
  item digest `a8443d637b12da9047091823786a12502c65b73da716f56e74d71a3dd9423062`), the question files after
  ten questions were named again in the first renaming (pre-registration, section 3; README "Decisions", item
  11). These runs were repeated on the question files of the second renaming (`second_rename/`). On the Mac,
  `sha256sum -c` of all 156 package files passed before these runs, and the tests gave "246 passed" in the
  same session.
- `before_rename/`: the package as delivered on 8 Nov at about 01:10 (code hash
  `25b01b0249f959d86de9724df1d8c615ff20129ccfcd28b80a22eb7bc3f82150`, item digest
  `8338be99418dfd89747d8354fe2f694e44ac1d377f3675dc5d053026e4ff75d1`). These runs were superseded by the ones
  in `first_rename/` and are kept as a record.
- Machine, Python and llama-cpp-python: as in `data/gng1/README.md` (Mac Studio, Apple M5 Max, 128 GB; Python
  3.14.8; llama-cpp-python 0.3.36 built with Metal); the first line of each pilot file records the platform
  and the Python version.
- Model files: each smoke file records its model file's SHA-256 (`model_file.sha256`), equal to the values in
  `mac_environment/model_files_SHA256SUMS.txt` and in section 10 of the pre-registration. The last line of
  that file was added on 8 Nov after the 31B download finished (the model file's time on the Mac is 01:22:37).
  On 8 Nov, in the Mac session of about 02:09 to 02:23, Hugging Face's API listing for
  `google/gemma-4-31B-it-qat-q4_0-gguf` (repository commit `59dde24573e7e61570dba08b18a2e1fe246955ed`, last
  modified 2026-07-17T21:26:48Z) gave 17,651,001,568 bytes and LFS SHA-256
  `179cfb99212709597eae5929112cfca677e1bbf566178b479ae1da0c4772874b` for `gemma-4-31B_q4_0-it.gguf`, equal to
  the downloaded file's size and SHA-256. The listing itself was not saved here.

## What the runs show

GNG-1 of E2B, E4B and 12B on the final question files (`final/gng1_rename3_E2B.json`,
`final/gng1_rename3_E4B.json` and `final/gng1_rename3_12B.json`;
`python -m ngraph.runner smoke ... --probe data/tokenizer_probe.json`, registered prefixes from
`ANSWER_PREFIX`): each model passes with its registered prefix and its per-size thought-block setting
(`thought_block_decision` "keep", `prefix_matches_rule` true). Letter mass was at least 0.9 on all 40
four-option and all 36 ten-option pilot prompts for each model (smallest letter mass: E2B 0.952 and 0.930, E4B
0.902 and 0.912, 12B 0.957 and 0.977). The tokenizer check found 0 mismatches in 4,040 strings, and the repeat
check gave the same arg-max on 10 of 10 prompts with a largest logit difference of 0.0. Pilot accuracy is in
the files, printed next to the letter mass; it was not used for any decision. Compared with `second_rename/`,
every recorded number is the same except the timing fields, the package state (code hash and item digest) and
the projected prompt-token totals (12, 12 and 6 tokens fewer), as expected, because GNG-1 scores only
real-name (G1) prompts and the third renaming changed only neutral names. The same holds between the earlier
runs: the totals differ by 24, 24 and 12 tokens between `first_rename/` and `second_rename/`, and by 4, 4 and
2 tokens between `before_rename/` and `first_rename/`.

31B's GNG-1 on the final question files (`final/gng1_rename3_31B_no_prefix.json`, then
`final/gng1_rename3_31B.json`), by the registered procedure (pre-registration, section 7; README, section 3):
with no prefix and its per-size setting (the empty thought block), 31B failed the letter-mass check (share of
prompts with letter mass of at least 0.9: 0.80 on the 40 A-D and 0.69 on the 36 A-J pilot prompts); without
the block it failed too, putting almost all of the probability on `<|channel>` (more than 0.1 on every prompt,
0.9999998 on average on A-D). Its prefix scan passed only with "Answer:" (every prompt at least 0.9 on both
sets; "The correct option is": none), so the rule chose "Answer:" under the per-size setting, and the GNG-1
fallback was not needed. Run again with "Answer:", 31B passed (`thought_block_decision` "keep",
`prefix_matches_rule` and `gng1_pass` true; smallest letter mass 0.9996 on A-D and 0.99999 on A-J); the token
checks passed, the tokenizer matched the vocabulary file on all 4,040 probe strings, and the repeat check gave
the same arg-max on 10 of 10 prompts with a largest logit difference of 0.0. `study-a --prefix-from` accepted
the second file for the 40 G2 pilot prompts (option order 1, the only order registered for 31B;
`final/pilot_prefix_from_rename3_31B_G2.jsonl`, whose first line records that file's SHA-256 as
`answer_prefix_source`); its accuracy is in the file and was not used for any decision.

GNG-2 pilot on the final question files (`final/pilot_gng2_rename3_E4B_G2.jsonl`;
`python -m ngraph.runner study-a --tag E4B --repos trio,langextract --versions G2`): 80 prompts (the 40 pilot
questions in both option orders), no errors, accuracy 0.6625 (53 of 80). By subgraph size 0.60 (about 12
nodes, 24 of 40) and 0.725 (about 24 nodes, 29 of 40); by question type 0.925 (QT-A, 37 of 40) and 0.40 (QT-B,
16 of 40); mean letter mass 0.885. The accuracy lies between 0.55 and 0.90, so by the pre-registered rule
(section 3) the subgraph sizes stay at about 12 and about 24 nodes. Apart from timing and the package state in
the first line, the file differs from the run on the files of the second renaming only in the two prompts of
the one pilot question that the third renaming changed (`langextract/A/S24/005`), which E4B answered correctly
in both option orders in both runs (letter mass 0.9995 and 0.9992 before, 0.9998 and 0.9996 after).

The pilot on the files of the second renaming (`second_rename/pilot_gng2_rename2_E4B_G2.jsonl`), kept as a
record, gave the same totals: 80 prompts (the 40 pilot questions in both option orders), no errors, accuracy
0.6625 (53 of 80). By subgraph size 0.60 (about 12 nodes, 24 of 40) and 0.725 (about 24 nodes, 29 of 40); by
question type 0.925 (QT-A, 37 of 40) and 0.40 (QT-B, 16 of 40); mean letter mass 0.885. That accuracy also
lies between 0.55 and 0.90. Apart from timing and the package state in the first line, the file differs from
the run on the files of the first renaming only in the 12 prompts of the six pilot questions that the second
renaming changed (`langextract/A/S12/003`, `langextract/A/S24/006`, `trio/A/S24/007`, `trio/B/S24/015`,
`trio/B/S24/017` and `trio/B/S24/018`): E4B now answered `langextract/A/S24/006` correctly in both option
orders and `trio/B/S24/015` in one (both wrong in both orders before), and `trio/B/S24/017` wrongly in both
(right in both before); it answered the other three correctly in both orders in both runs.

Earlier pilots, kept as a record: on the files of the first renaming
(`first_rename/pilot_gng2_final_E4B_G2.jsonl`), accuracy 0.65 (52 of 80; by subgraph size 0.60 and 0.70, that
is 24 and 28 of 40; by question type 0.875 for QT-A, 35 of 40, and 0.425 for QT-B, 17 of 40; mean letter mass
0.886), also between 0.55 and 0.90. The run before the first renaming
(`before_rename/pilot_gng2_E4B_G2.jsonl`) also gave 0.65 (mean letter mass 0.892); apart from timing and the
package state in the first line, the two files differ only in the two prompts of the renamed pilot question
`trio/B/S24/019`, which E4B answered correctly in both option orders in both runs (letter mass 0.86 and 0.92
before, 0.66 and 0.64 after).

31B's GNG-1 smoke runs on the question files from before the first renaming are not in this folder
(`prereg/OPEN_ITEMS.md`, section 12).
