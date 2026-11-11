# GNG-1 evidence, 7 Nov 2026

This folder holds the outputs of the first GNG-1 check (pre-registration, section 7) and of the
answer-prefix test that followed it. Both ran on the author's Mac Studio before the freeze and before
any confirmatory run. The files were copied from the Mac byte for byte; the SHA-256 values below were
computed on the Mac and again on the copies, and they are equal. Nothing here was edited. The files
contain no user names or home-folder paths.

All times are UTC. "Written" is the file's modification time on the Mac, read from the folder listing
on 7 Nov at about 19:40.

Who did what: the author ran this work with an AI coding assistant (Claude Code). The assistant wrote
the code and the test script in a cloud workspace and ran the commands on the Mac in a Claude Code
session there; the author approved each step that needed approval and made every decision recorded
as the author's. The times of sending, writing and receiving below come from our own records (the
assistant's message and edit times, and the Mac's folder listing). Nothing in this package or in the
forum post (made after these events) can confirm their order independently.

## Files

| File here | Where it was written on the Mac (project folder) | Written | Bytes | SHA-256 |
|---|---|---|---|---|
| `first_run_no_prefix/smoke_E2B.json` | `gemma4-paper-code/runs/smoke_E2B.json` | 18:21:47 | 7,550 | `10c732460954de5c509ec46df253d67cf133d5e7799a73e1c06358706337d3e1` |
| `first_run_no_prefix/smoke_E4B.json` | `gemma4-paper-code/runs/smoke_E4B.json` | 18:27:33 | 7,574 | `86b42a55a5cac9186bc55db866572ef82fc20daa651d0e551cda8e80d59a5139` |
| `first_run_no_prefix/smoke_12B.json` | `gemma4-paper-code/runs/smoke_12B.json` | 18:30:38 | 7,699 | `682d96c8865d207a6a01d57f9df6b03e6db5600c1a049dd24761a732904443a6` |
| `prefix_test/diag_prefix.py` | `diag/diag_prefix.py` | 18:36:32 | 4,688 | `3d8006eaaf710f0659addc3349aea88d38fb9876fe06d959431d7923c874e9ec` |
| `prefix_test/diag_prefix.log` | `diag/diag_prefix.log` | 18:43:25 | 3,200 | `698e1e5a0b73de608240dd0db232c60d47b68ea69c23461a8cda78af81455de5` |
| `prefix_test/diag_prefix_results.json` | `diag/diag_prefix_results.json` | 18:43:25 | 24,276 | `70551b03df2302c75e1f83ff53a0a2bf22438760004c677db7c6232dd8ea95b3` |
| `mac_environment/pip_freeze.txt` | `gemma4-paper-code/runs/env_mac_pip_freeze.txt` | 18:10:19 | 484 | `844cb5b22f5e865d73ca7c779eba1d95233034d4fec51a08745c0ae4b9398d1c` |
| `mac_environment/model_files_SHA256SUMS.txt` | `models/SHA256SUMS.txt` | 18:17:00 | 433 | `c252437d028d2ae42df1c387f36cc07925abcc06332a570a2aafb62b331b8e29` |

`mac_environment/llama_cpp_libs_SHA256.txt` (SHA-256
`2b0e486c0109923547bdba54f9acb58fe773116d0d85f7d0d64aaabd75361988`) is the one file made later (7 Nov,
about 19:42): the SHA-256 of each llama.cpp library in the Mac's `.venv` (`site-packages/llama_cpp/lib/`),
computed on the Mac. The libraries themselves are dated 18:10, the time of the build.

## Code and machine

- Code: the package as copied to the Mac on 7 Nov at about 17:50, before the review fixes. SHA-256 of its
  `CODE_SHA256.txt`: `b4d9b674eed3d9baeae09ce8f9d3f52ce6533c2c1f4db3e3d5c670ae4b73d506`. On 7 Nov at about
  19:40, `sha256sum -c CODE_SHA256.txt` on the Mac copy passed for every listed file. The smoke runs used
  `python -m ngraph.runner smoke`; `diag_prefix.py` imports `ngraph.runner` from the same copy.
- Machine (as reported by the Claude Code session on the Mac): Mac Studio, Apple M5 Max, 128 GB,
  macOS 27.0.1 (26A434).
- Python 3.14.8 from Homebrew (the `.venv`'s `pyvenv.cfg` says `version = 3.14.8`). Package versions:
  `mac_environment/pip_freeze.txt` (llama_cpp_python 0.3.36, numpy 2.5.4, among others).
- llama-cpp-python 0.3.36, built on the Mac with Metal. The string `0c1e570-dirty` is embedded in its
  `libggml-base.0.25.3.dylib` (ggml 0.25.3); the build log reported it as the ggml commit. A "-dirty"
  suffix usually means the source tree had uncommitted changes at build time, so this string does not
  name an exact upstream commit; the library hashes above pin the binaries that ran.
- Model files: `mac_environment/model_files_SHA256SUMS.txt` (SHA-256, file name, size and expected
  size of each file; "expected" is the size in Hugging Face's API listing). The Claude Code session
  on the Mac reported that each name, size and SHA-256 also matched that listing; the listing itself
  was not saved here. The files stay outside the package, in a `models/` folder
  next to it. Chat-template SHA-256, as recorded in the smoke files: E2B and E4B
  `0a2c8073c878ab1da004bee933a998606537bbb62016310352c7285c3f01c5b5`, 12B
  `ae53464bf3be25802b3a5b37def7fd89667067d7577049b3b2d74c4d8de4c6d4`.

## What happened

1. First GNG-1 run, no answer prefix (files finished 18:21 to 18:31; a first attempt for E4B and 12B
   stopped within a second on a shell error, before any prompt was scored, and was rerun). Pilot
   prompts from the two pilot
   repositories (trio and langextract): 40 A-D prompts and the 36 A-J prompts those repositories allow.
   Share of prompts with letter mass of at least 0.9 under each model's own thought-block setting:

   | Model | Own setting | A-D | A-J | Other setting: A-D, A-J | Token and tokenizer checks | Result |
   |---|---|---|---|---|---|---|
   | E2B | no block | 0.175 | 0.028 | 0.000, 0.000 | pass | fail |
   | E4B | no block | 1.000 | 1.000 | 0.000, 0.000 | pass | pass |
   | 12B | block | 0.675 | 0.639 | 0.000, 0.000 | pass | fail |

   Without the block, 12B put a mean probability of about 0.99999 on `<|channel>` at the answer position.

2. The prefix test (`prefix_test/`). The script was written in the cloud workspace at about 18:34 and
   run there once on random numbers instead of a model, only to catch errors (those outputs mean
   nothing and are not included). It was sent to the Mac at 18:36:08 and saved there at 18:36:32. It
   scores the same pilot
   prompts under three prefixes (none, "Answer:", "The correct option is") and both thought-block
   settings. Its docstring says "40 A-J prompts"; the pilot repositories allow 36, which is what it
   scored (`n_AJ` in the results).

3. A rule for choosing the prefix was written into the pre-registration draft at 18:36:31, 23 seconds
   after the test was sent, and refined at 18:36:40. No result of the test had been seen: the results
   came back from the Mac at 18:44:11. The rule as it stood at 18:36:40, verbatim (the bracket was a
   placeholder for the author's approval):

   > Rule fixed at 18:40 UTC, before any remedy was tried: the model turn is pre-filled with an answer
   > prefix, the same text for every model and both studies, chosen on the same pilot prompts by letter
   > mass alone (never by accuracy), trying "Answer:" first and "The correct option is" second. The first
   > prefix under which every model passes with its per-size setting is used. If none does, the option
   > under which the most models pass is used, in the order no prefix, "Answer:", "The correct option
   > is" (a tie goes to the earlier one); the thought-block rule above then applies to each model under
   > that option, and a model that still fails is handled by the fallback above (exclusion; [TBD: your
   > OK]).

   The time "18:40" in that text was wrong: the text was written at 18:36:31. The version written nine
   seconds earlier differed only in its fallback sentence: it said "the prefix under which the most
   models pass" and did not list "no prefix" as an option.

4. Results (`prefix_test/diag_prefix_results.json`; share with letter mass of at least 0.9, A-D / A-J):

   | Model | Setting | None | "Answer:" | "The correct option is" |
   |---|---|---|---|---|
   | E2B | own (no block) | 0.175 / 0.028 | **1.000 / 1.000** | 0.000 / 0.000 |
   | E2B | other (block) | 0.000 / 0.000 | **1.000 / 1.000** | 0.000 / 0.000 |
   | E4B | own (no block) | **1.000 / 1.000** | 0.925 / 0.972 | 0.000 / 0.083 |
   | E4B | other (block) | 0.000 / 0.000 | 0.925 / 0.972 | 0.900 / 0.750 |
   | 12B | own (block) | 0.675 / 0.639 | **1.000 / 1.000** | 0.000 / 0.000 |
   | 12B | other (no block) | 0.000 / 0.000 | **1.000 / 1.000** | 0.525 / 0.528 |

   Bold: passes (at least 0.95 on both sets). No single option passes for all three models. Under the
   rule above, "Answer:" (two models pass) would have been used for every model and E4B, which passes
   with no prefix, would have been excluded.

5. At 18:45:20 the assistant proposed a per-model rule to the author, and at 18:47:05 it was written
   into the draft, pending the author's choice: a model keeps no prefix if it passes without one; otherwise it
   uses the first of "Answer:" and "The correct option is" under which it passes with its per-size
   setting; a model that passes under none is excluded. It gives E2B "Answer:", E4B none and 12B
   "Answer:". This change was made after seeing the letter-mass results above and before any
   confirmatory run. The pre-registration records it in section 7.

6. On 8 Nov 2026 at 00:58 UTC the author chose the prefix part of this per-model rule (no prefix if the model
   passes without one, otherwise the first of "Answer:" and "The correct option is" under which it passes with
   its per-size setting), in answer to the proposal of 18:45:20. What happens when no candidate passes,
   including the exclusion in item 5, is the GNG-1 fallback, which was put to the author separately on 8 Nov;
   the pre-registration's section 7 records the decision.

Pilot accuracy is in the files, printed next to the letter mass. It was not used for any decision.
