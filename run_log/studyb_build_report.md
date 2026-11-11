# Study B build report (renamer 0.1.3, extractor 0.3.1)

## Outcome

**Complete. I applied the renamer 0.1.3 patch and rebuilt both sets, and every command exited 0. Both sets now have 0 hard leaks.**

- All hashes matched: before patching, the decoded patch, and after patching. The tests gave 1 failed (the expected `test_package_code_sha256_is_current`), 126 passed and 23 skipped.
- Official: all 1,554 prompt hashes are identical to 0.1.2, opaque and real alike, and the summary and every per-task field are the same. mc3.json and graphs_report.json are byte-identical. Only `rename_map_sha256` changed (the export now says 0.1.3).
- Lite: the same 317 task ids. The only summary change is `tasks_with_hard_leaks`, from 7 to 0. All 1,686 real prompts are identical. 8 of 2,248 opaque prompts differ, all in one task: pytest-dev__pytest-8365. In 0.1.2, the URL scrub matched the identity word `py` and replaced a URL on py.readthedocs.io with `<url>`. In 0.1.3, `py` is no longer an identity word, so that URL stays. The task's max_tokens went from 2840 to 2852. No other word differs.
- `frame_names_kept` is non-empty only for sympy__sympy-18621, with `ipython` once in each of its 8 opaque prompts.
- Identity words dropped: `script` (pylint, 6 tasks), `py` (pytest, 15 tasks), `utils` (sphinx, 16 tasks) and `util` (sqlfluff, 5 tasks). These names are still renamable: the number of renamed names per repository did not change.
- Anchored share on confirmatory eligible tasks, unchanged: official 43/111, Lite 131/260, combined 174/371 = 0.469.
- The package file hashes for the addendum are at the end. `CODE_SHA256.txt` is still stale.

Limit of the text comparison: for Lite, I rendered and compared only the 42 eligible tasks of the four repositories whose identity words changed (pylint, sphinx, sqlfluff and pytest). The frozen hashes show that every other Lite task has every prompt identical to 0.1.2. I did not render those tasks again.

## Step 0: the read-only Lite render from the leak check

It was still running (90 of 317 tasks). I stopped it with `kill` at 05:29:33 UTC, and `gemma4-staging/studyb6/run.exit` records exit 143. Its partial files are kept.

## Steps 1 and 2: patch

| File | Before (expected and observed) | Expected after | Observed after |
|---|---|---|---|
| src/ngraph/rename.py | `3e7084b62f8532f0fb5d90ce7cec43f68ae0c44240006f76d3257e4a6ca804f0` MATCH | `16d6aedb1d35d52623aaaa8a0efc24d48e2da99bfe07b42d5e5b9c9a5696f318` | `16d6aedb1d35d52623aaaa8a0efc24d48e2da99bfe07b42d5e5b9c9a5696f318` MATCH |
| src/ngraph/studyb.py | `4d7fff85623320c1ecd35b582190f2e8ab96d6c9fd5c68a55481b8d252ffa8e8` MATCH | `80f54c3b333aaf856249498e8de61f991b2af3b58577ad4cf55fdc43c6f45e1e` | `80f54c3b333aaf856249498e8de61f991b2af3b58577ad4cf55fdc43c6f45e1e` MATCH |
| tests/test_studyb.py | `c6a1f73a4fc6e46a4dfd2a6ad274fffe21cb0fec2e12658b78b8c6da7f470169` MATCH | `c74a99c179124a5561d1fc0e0750b64bebea5cb8ecd75f3ea5197f59af9e9b61` | `c74a99c179124a5561d1fc0e0750b64bebea5cb8ecd75f3ea5197f59af9e9b61` MATCH |

Decoded patch: SHA-256 `0e33673bad3b61355c995b2c482dec90913831753776502d46cfb1e63e26bde8` (expected `0e33673bad3b61355c995b2c482dec90913831753776502d46cfb1e63e26bde8`). It has 187 lines, 18 with a less-than sign, 0 with an exclamation mark. As last time, the relay had XML-escaped `>` as `&gt;`, and I wrote the real character. Backups are in `gemma4-staging/studyb6/base/`, with paths kept.

`patch -p1 -l --dry-run`: exit 0. Real run: exit 0. Output:

```
patching file 'src/ngraph/rename.py'
patching file 'src/ngraph/studyb.py'
patching file 'tests/test_studyb.py'
```
No `.orig` or `.rej` file remains in the package.

## Step 3: tests

pytest exit=1 start=2026-11-10T05:30:22Z end=2026-11-10T05:30:30Z

```
tests/test_commit.py:554: AssertionError
=========================== short test summary info ============================
FAILED tests/test_commit.py::test_package_code_sha256_is_current - AssertionE...
1 failed, 126 passed, 23 skipped in 7.55s
```
The only failure is the expected `tests/test_commit.py::test_package_code_sha256_is_current`.

## Step 4: moves (mv, nothing deleted)

- `studyb-frozen/official` to `studyb-frozen/official_0.1.2`; `studyb-frozen/lite` to `studyb-frozen/lite_0.1.2`.
- In `run_log`: `studyb_build_official.log`, `studyb_mc3.log` and `studyb_build_lite.log` got the suffix `.0.1.2`. `studyb_builds.exit` became `studyb_builds.exit.0.1.2`, and `studyb_build_report.md` became `studyb_build_report.0.1.2.md`.

## Step 5: commands, exit codes and times (UTC)

Script: `run_log/tools/studyb6_build.sh`, started with nohup at 05:30:46 UTC (PID 2119). Arguments are the same as for the 0.1.2 builds. Exit codes and times come from `run_log/studyb6_builds.exit`.

| Command | Exit | Start | End |
|---|---|---|---|
| studyb build --set official | 0 | 2026-11-10T05:30:43Z | 2026-11-10T05:34:28Z |
| studyb mc3 | 0 | 2026-11-10T05:34:28Z | 2026-11-10T05:34:32Z |
| studyb build --set lite | 0 | 2026-11-10T05:34:32Z | 2026-11-10T07:08:58Z |

## Build: official

Summary:

```json
{
 "anchored": 43,
 "anchored_share": 0.38738738738738737,
 "by_repo": {
  "Textualize/rich": 42,
  "encode/httpx": 1,
  "fastapi/fastapi": 57,
  "psf/requests": 11
 },
 "code_lines_reduced": 0,
 "cut": 0,
 "eligible": 111,
 "eligible_tune": 0,
 "excluded": {
  "no library function in the gold patch": 18
 },
 "injected": 48,
 "max_tokens": 4516,
 "roles": {
  "confirmatory": 129
 },
 "strata": {
  "S0": 19,
  "S1": 7,
  "S2": 3,
  "S3": 82
 },
 "tasks": 129,
 "tasks_with_hard_leaks": 0
}
```
`params` block of tasks.json:

```json
{
 "bm25": [
  1.2,
  0.75
 ],
 "code_lines": 15,
 "max_anchor_degree": 50,
 "max_line_chars": 200,
 "max_neighbors": 50,
 "n_ctx": 8192,
 "order_seed": 1,
 "pool_k": 10,
 "protected_names_sha256": "b4e679dd91c2dc3d8658de32ede961518eb3492d8e82abc8875b364104bcfb29",
 "python": "3.14.8",
 "rename_seed": 1,
 "rewire_seed": 1,
 "set": "official",
 "studyb_version": "0.1.0",
 "token_budget": 7936,
 "tool_chars": 5000
}
```
Output files:

| File | Bytes | SHA-256 |
|---|---|---|
| graphs_report.json | 225174 | `ae9b4cb11e0755fc370f25995bbcafd9f6ec9dac448b182d65656f12ce20dbad` |
| mc3.json | 1356 | `21288d1f1e61b43bd0f7f9963218573fedd6a940fb441fc6627daf295137ac9b` |
| rename_maps.json.gz | 108494 | `d3ff254e2e0cb92f81257fa7631490f543e2758b7bce7a6e9262d253345981bb` |
| tasks.json | 1024176 | `7681800b8dac23f893e5409fe18cb25f0ccbf4b153fae67965aeb8b86695b3cb` |

Tasks with hard leaks: 0.

`frame_names_kept`: non-empty in 0 tasks, 0 prompt keys. Every eligible task has the field: True.

Rename maps per repository (`n_protected_defined`; renamed names = entries in `map`; identity words = keys of `identity_map`):

| Repo | n_protected_defined | Renamed names | rename_version | packages | identity words |
|---|---|---|---|---|---|
| Textualize/rich | 101 | 2285 | 0.1.3 | rich | rich, textualize |
| encode/httpx | 29 | 385 | 0.1.3 | ahttpx, httpx | ahttpx, httpx |
| fastapi/fastapi | 154 | 4329 | 0.1.3 | docs_src, fastapi, pdm_build | docs_src, fastapi, pdm_build |
| psf/requests | 69 | 845 | 0.1.3 | requests | psf, requests |

Graphs in graphs_report.json: 127. graphs_report.json is byte-identical to the 0.1.2 one: True.

| Measure | Value |
|---|---|
| mirrored = true / false / absent | 127 / 0 / 0 |
| self_loops: median / min / max (n=127) | 13 / 0 / 20 |
| duplicate_edges_dropped: median / min / max (n=127) | 13 / 0 / 20 |
| rewired edge_overlap: median / min / max (n=127) | 0.022375215146299483 / 0.008347245409015025 / 0.04718629849702901 |
| within_module edge_overlap: median / min / max (n=110) | 0.6448716744446199 / 0.44013683010262256 / 0.6685796269727403 |
| rewired invariants pass / fail / absent | 127 / 0 / 0 |
| within_module invariants pass / fail / absent | 110 / 0 / 17 |

Where `stats` has no `mirrored` or `self_loops` field (Lite graphs from our extractor), the table uses `rewired.input_mirrored` and `rewired.self_loops`. Those graphs record no `duplicate_edges_dropped`.

Graphs not flagged mirrored: 0.

Failures (rewiring not completed, error, or an invariant false): 0.

Log tail (last 40 lines):

```
rich_3938: eligible=True gold=1 injected=False anchored=False stratum=S3 tokens=2293 cut=None leaks=0
rich_3942: eligible=True gold=3 injected=True anchored=False stratum=S3 tokens=1803 cut=None leaks=0
rich_3944: eligible=True gold=1 injected=True anchored=False stratum=S3 tokens=2335 cut=None leaks=0
rich_3953: eligible=True gold=2 injected=True anchored=False stratum=S3 tokens=2493 cut=None leaks=0
rich_4006: eligible=True gold=1 injected=False anchored=True stratum=S0 tokens=2429 cut=None leaks=0
rich_4070: eligible=True gold=16 injected=False anchored=True stratum=S0 tokens=4311 cut=None leaks=0
rich_4075: eligible=True gold=2 injected=True anchored=False stratum=S3 tokens=2330 cut=None leaks=0
rich_4076: eligible=True gold=1 injected=True anchored=False stratum=S3 tokens=2308 cut=None leaks=0
rich_4077: eligible=False gold=0 injected=None anchored=None stratum=None tokens=None cut=None leaks=0
rich_4079: eligible=True gold=1 injected=True anchored=False stratum=S3 tokens=2355 cut=None leaks=0
{
 "tasks": 129,
 "eligible": 111,
 "roles": {
  "confirmatory": 129
 },
 "eligible_tune": 0,
 "by_repo": {
  "fastapi/fastapi": 57,
  "encode/httpx": 1,
  "psf/requests": 11,
  "Textualize/rich": 42
 },
 "injected": 48,
 "anchored": 43,
 "anchored_share": 0.38738738738738737,
 "strata": {
  "S0": 19,
  "S1": 7,
  "S2": 3,
  "S3": 82
 },
 "cut": 0,
 "code_lines_reduced": 0,
 "tasks_with_hard_leaks": 0,
 "max_tokens": 4516,
 "excluded": {
  "no library function in the gold patch": 18
 }
}
```

## mc3.json

| Task | repo | graph | official_library_functions | our_nodes | common_nodes | official_pairs | our_pairs | common_pairs | ours_in_official | official_in_ours |
|---|---|---|---|---|---|---|---|---|---|---|
| fastapi_15800 | fastapi/fastapi | fastapi_f1d750fddad90e2faad6c3cc5c85c7687b787e89 | 268 | 305 | 268 | 183 | 236 | 153 | 0.6483 | 0.8361 |
| httpx_3672 | encode/httpx | httpx_4acf5c2c37714cc63b5cf71b3e284fca83c90311 | 520 | 618 | 520 | 33 | 248 | 33 | 0.1331 | 1.0 |
| requests_7505 | psf/requests | requests_6f205ff422bccd5e4c4fc0b64c5f3e7df5181db6 | 239 | 239 | 239 | 103 | 208 | 100 | 0.4808 | 0.9709 |
| rich_4079 | Textualize/rich | rich_19c67b9a3479841e9133bea94607c89ee931d3fc | 833 | 833 | 833 | 274 | 657 | 263 | 0.4003 | 0.9599 |

mc3.json SHA-256 `21288d1f1e61b43bd0f7f9963218573fedd6a940fb441fc6627daf295137ac9b`. Byte-identical to the 0.1.2 mc3.json: **True**.

Log tail (last 40 lines):

```
  "ours_in_official": 0.4003044140030441,
  "official_in_ours": 0.9598540145985401
 },
 "httpx_3672": {
  "repo": "encode/httpx",
  "graph": "httpx_4acf5c2c37714cc63b5cf71b3e284fca83c90311",
  "official_library_functions": 520,
  "our_nodes": 618,
  "common_nodes": 520,
  "official_pairs": 33,
  "our_pairs": 248,
  "common_pairs": 33,
  "ours_in_official": 0.13306451612903225,
  "official_in_ours": 1.0
 },
 "fastapi_15800": {
  "repo": "fastapi/fastapi",
  "graph": "fastapi_f1d750fddad90e2faad6c3cc5c85c7687b787e89",
  "official_library_functions": 268,
  "our_nodes": 305,
  "common_nodes": 268,
  "official_pairs": 183,
  "our_pairs": 236,
  "common_pairs": 153,
  "ours_in_official": 0.6483050847457628,
  "official_in_ours": 0.8360655737704918
 },
 "requests_7505": {
  "repo": "psf/requests",
  "graph": "requests_6f205ff422bccd5e4c4fc0b64c5f3e7df5181db6",
  "official_library_functions": 239,
  "our_nodes": 239,
  "common_nodes": 239,
  "official_pairs": 103,
  "our_pairs": 208,
  "common_pairs": 100,
  "ours_in_official": 0.4807692307692308,
  "official_in_ours": 0.970873786407767
 }
}
```

## Build: lite

Summary:

```json
{
 "anchored": 131,
 "anchored_share": 0.5038461538461538,
 "by_repo": {
  "astropy/astropy": 6,
  "django/django": 102,
  "matplotlib/matplotlib": 21,
  "mwaskom/seaborn": 4,
  "pallets/flask": 3,
  "pydata/xarray": 5,
  "pylint-dev/pylint": 6,
  "pytest-dev/pytest": 15,
  "scikit-learn/scikit-learn": 22,
  "sphinx-doc/sphinx": 16,
  "sympy/sympy": 60
 },
 "code_lines_reduced": 0,
 "cut": 2,
 "eligible": 260,
 "eligible_tune": 21,
 "excluded": {
  "no library function in the gold patch": 36
 },
 "injected": 108,
 "max_tokens": 7936,
 "roles": {
  "confirmatory": 294,
  "tune": 23
 },
 "strata": {
  "S0": 62,
  "S1": 9,
  "S2": 6,
  "S3": 183
 },
 "tasks": 317,
 "tasks_with_hard_leaks": 0
}
```
`params` block of tasks.json:

```json
{
 "bm25": [
  1.2,
  0.75
 ],
 "code_lines": 15,
 "max_anchor_degree": 50,
 "max_line_chars": 200,
 "max_neighbors": 50,
 "n_ctx": 8192,
 "order_seed": 1,
 "pool_k": 10,
 "protected_names_sha256": "b4e679dd91c2dc3d8658de32ede961518eb3492d8e82abc8875b364104bcfb29",
 "python": "3.14.8",
 "rename_seed": 1,
 "rewire_seed": 1,
 "set": "lite",
 "studyb_version": "0.1.0",
 "token_budget": 7936,
 "tool_chars": 5000
}
```
Output files:

| File | Bytes | SHA-256 |
|---|---|---|
| graphs_report.json | 663048 | `cb94d8cfeade1beeb0d1ce31e49fa8dd99c539c04f3e08c946eb09a7909e5b0d` |
| rename_maps.json.gz | 2200892 | `af93b86db9eaedc55e6a1add8224e78830cb812dd6d3bfccc43b90bb2d48db59` |
| tasks.json | 2835970 | `52528ac15c66dc62ed8d9ac8a3b0eabf37d5f6493a3e1c3c23df1c8a3a30e497` |

Tasks with hard leaks: 0.

`frame_names_kept`: non-empty in 1 tasks, 8 prompt keys. Every eligible task has the field: True.
- sympy__sympy-18621: {"opaque/none/1": {"ipython": 1}, "opaque/none/2": {"ipython": 1}, "opaque/rewired/1": {"ipython": 1}, "opaque/rewired/2": {"ipython": 1}, "opaque/true/1": {"ipython": 1}, "opaque/true/2": {"ipython": 1}, "opaque/within_module/1": {"ipython": 1}, "opaque/within_module/2": {"ipython": 1}}

Rename maps per repository (`n_protected_defined`; renamed names = entries in `map`; identity words = keys of `identity_map`):

| Repo | n_protected_defined | Renamed names | rename_version | packages | identity words |
|---|---|---|---|---|---|
| astropy/astropy | 552 | 16810 | 0.1.3 | ah_bootstrap, astropy, ez_setup | ah_bootstrap, astropy, ez_setup |
| django/django | 465 | 32423 | 0.1.3 | django | django |
| marshmallow-code/marshmallow | 66 | 1592 | 0.1.3 | marshmallow | marshmallow, marshmallow-code |
| matplotlib/matplotlib | 251 | 12367 | 0.1.3 | matplotlib, mpl_toolkits, pylab, setupext | matplotlib, mpl_toolkits, pylab, setupext |
| mwaskom/seaborn | 110 | 3026 | 0.1.3 | seaborn | mwaskom, seaborn |
| pallets/flask | 120 | 1318 | 0.1.3 | flask | flask, pallets |
| pvlib/pvlib-python | 60 | 2295 | 0.1.3 | pvlib, versioneer | pvlib, pvlib-python, versioneer |
| pydata/xarray | 304 | 4361 | 0.1.3 | versioneer, xarray | pydata, versioneer, xarray |
| pydicom/pydicom | 94 | 3720 | 0.1.3 | dicom, pydicom | dicom, pydicom |
| pylint-dev/astroid | 153 | 3153 | 0.1.3 | astroid | astroid, pylint-dev |
| pylint-dev/pylint | 300 | 8331 | 0.1.3 | pylint, script | pylint, pylint-dev |
| pytest-dev/pytest | 243 | 5813 | 0.1.3 | _pytest, py, pytest | _pytest, pytest, pytest-dev |
| pyvista/pyvista | 122 | 5051 | 0.1.3 | pyvista | pyvista |
| scikit-learn/scikit-learn | 446 | 14225 | 0.1.3 | sklearn | scikit-learn, sklearn |
| sphinx-doc/sphinx | 338 | 6096 | 0.1.3 | sphinx, utils | sphinx, sphinx-doc |
| sqlfluff/sqlfluff | 69 | 2177 | 0.1.3 | sqlfluff, util | sqlfluff |
| sympy/sympy | 669 | 39780 | 0.1.3 | isympy, setupegg, sympy | isympy, setupegg, sympy |

Graphs in graphs_report.json: 314. graphs_report.json is byte-identical to the 0.1.2 one: True.

| Measure | Value |
|---|---|
| mirrored = true / false / absent | 314 / 0 / 0 |
| self_loops: median / min / max (n=314) | 0.0 / 0 / 0 |
| duplicate_edges_dropped: median / min / max (n=0) | None / None / None |
| rewired edge_overlap: median / min / max (n=314) | 0.007339527585246523 / 0.0018323408153916628 / 0.06936416184971098 |
| within_module edge_overlap: median / min / max (n=314) | 0.47029373570087235 / 0.2628968253968254 / 0.6983729662077597 |
| rewired invariants pass / fail / absent | 314 / 0 / 0 |
| within_module invariants pass / fail / absent | 314 / 0 / 0 |

Where `stats` has no `mirrored` or `self_loops` field (Lite graphs from our extractor), the table uses `rewired.input_mirrored` and `rewired.self_loops`. Those graphs record no `duplicate_edges_dropped`.

Graphs not flagged mirrored: 0.

Failures (rewiring not completed, error, or an invariant false): 0.

Log tail (last 40 lines):

```
sympy__sympy-24213: eligible=True gold=1 injected=False anchored=True stratum=S0 tokens=3739 cut=None leaks=0
sympy__sympy-24909: eligible=True gold=2 injected=False anchored=False stratum=S3 tokens=2887 cut=None leaks=0
{
 "tasks": 317,
 "eligible": 260,
 "roles": {
  "confirmatory": 294,
  "tune": 23
 },
 "eligible_tune": 21,
 "by_repo": {
  "astropy/astropy": 6,
  "django/django": 102,
  "matplotlib/matplotlib": 21,
  "mwaskom/seaborn": 4,
  "pallets/flask": 3,
  "pydata/xarray": 5,
  "pylint-dev/pylint": 6,
  "pytest-dev/pytest": 15,
  "scikit-learn/scikit-learn": 22,
  "sphinx-doc/sphinx": 16,
  "sympy/sympy": 60
 },
 "injected": 108,
 "anchored": 131,
 "anchored_share": 0.5038461538461538,
 "strata": {
  "S0": 62,
  "S1": 9,
  "S2": 6,
  "S3": 183
 },
 "cut": 2,
 "code_lines_reduced": 0,
 "tasks_with_hard_leaks": 0,
 "max_tokens": 7936,
 "excluded": {
  "no library function in the gold patch": 36
 }
}
```

## Anchored counts on confirmatory eligible tasks

Rule used: `task["role"] == "confirmatory"` and `task["eligible"] is True`; anchored means `task["anchored"] is True`.

| Set | Confirmatory tasks | Confirmatory eligible | Anchored | Share |
|---|---|---|---|---|
| official | 129 | 111 | 43 | 0.3874 |
| lite | 294 | 260 | 131 | 0.5038 |
| **combined** | | **371** | **174** | **0.469** (174/371) |

Tasks by role:

```
{"official": {"confirmatory": 129}, "lite": {"confirmatory": 294, "tune": 23}}
```

Lite non-confirmatory tasks: 23, of which eligible 21 and anchored 11.


## official: 0.1.3 against 0.1.2 (`official_0.1.2`)

- Same task ids: True (129 old, 129 new).
- Summary keys that differ: [].
- params keys that differ: [].

Per-task fields (all except `rename_map_sha256` and `frame_names_kept`): number of tasks that differ.

| Field | Tasks that differ |
|---|---|
| anchored | 0 |
| anchors | 0 |
| b5_anchor_neighbours | 0 |
| base_commit | 0 |
| bm25_pool_scores | 0 |
| context | 0 |
| correct_letters | 0 |
| eligible | 0 |
| excluded_reason | 0 |
| gold | 0 |
| gold_all | 0 |
| gold_files | 0 |
| gold_in_pool | 0 |
| gold_ranks | 0 |
| graph | 0 |
| hard_leaks | 0 |
| index | 0 |
| injected | 0 |
| library_groups | 0 |
| n_ambiguous_mentions | 0 |
| n_library_functions | 0 |
| orders | 0 |
| pool | 0 |
| prompt_sha256 | 0 |
| renamer | 0 |
| render | 0 |
| repo | 0 |
| role | 0 |
| set | 0 |
| share_changed_issue | 0 |
| snapshot_skipped | 0 |
| stratum | 0 |
| studyb_version | 0 |
| task_id | 0 |
| too_connected | 0 |

`rename_map_sha256` differs in 111 tasks (by repository: {"fastapi/fastapi": 57, "encode/httpx": 1, "psf/requests": 11, "Textualize/rich": 42}).

Prompt hashes (`prompt_sha256`, keys `naming/graph/order`):

| Group | Compared | Differ | Tasks with a difference, by repository |
|---|---|---|---|
| opaque | 888 | 0 | {} |
| real | 666 | 0 | {} |

Text-level comparison: I rendered the prompts with the 0.1.2 code (the kept copy in `gemma4-staging/studyb6/old_src`, made from the backed-up `rename.py` and `studyb.py`) and with the 0.1.3 code, then compared them word by word. The dumps stay in staging. `dump_sha_matches_frozen` checks each dump's hashes against `official_0.1.2/tasks.json` (old) and `official/tasks.json` (new). Scope: all 111 eligible official tasks.

```json
{
 "categories": {},
 "differing_prompts_by_repo": {},
 "dump_sha_matches_frozen": {
  "new": 1554,
  "old": 1554,
  "total": 1554
 },
 "opaque_prompts_differ": 0,
 "prompts_compared": 1554,
 "prompts_differ": 0,
 "prompts_with_changed_token_count": 0,
 "real_prompts_differ": 0,
 "tasks_with_a_difference": 0
}
```
Non-pseudo-word differences as identifier pairs (old side -> new side, source name where the map gives one; counts; top 40 per category):

```json
{}
```

## lite: 0.1.3 against 0.1.2 (`lite_0.1.2`)

- Same task ids: True (317 old, 317 new).
- Summary keys that differ: ['tasks_with_hard_leaks'].
  - `tasks_with_hard_leaks`: old 7, new 0
- params keys that differ: [].

Per-task fields (all except `rename_map_sha256` and `frame_names_kept`): number of tasks that differ.

| Field | Tasks that differ |
|---|---|
| anchored | 0 |
| anchors | 0 |
| b5_anchor_neighbours | 0 |
| base_commit | 0 |
| bm25_pool_scores | 0 |
| context | 0 |
| correct_letters | 0 |
| eligible | 0 |
| excluded_reason | 0 |
| gold | 0 |
| gold_all | 0 |
| gold_files | 0 |
| gold_in_pool | 0 |
| gold_ranks | 0 |
| graph | 0 |
| hard_leaks | 7 |
| index | 0 |
| injected | 0 |
| library_groups | 0 |
| n_ambiguous_mentions | 0 |
| n_library_functions | 0 |
| orders | 0 |
| pool | 0 |
| prompt_sha256 | 1 |
| renamer | 42 |
| render | 1 |
| repo | 0 |
| role | 0 |
| set | 0 |
| share_changed_issue | 0 |
| snapshot_skipped | 0 |
| stratum | 0 |
| studyb_version | 0 |
| task_id | 0 |
| too_connected | 0 |

`rename_map_sha256` differs in 281 tasks (by repository: {"astropy/astropy": 6, "django/django": 102, "marshmallow-code/marshmallow": 2, "matplotlib/matplotlib": 21, "mwaskom/seaborn": 4, "pallets/flask": 3, "pvlib/pvlib-python": 5, "pydata/xarray": 5, "pydicom/pydicom": 4, "pylint-dev/astroid": 4, "pylint-dev/pylint": 6, "pytest-dev/pytest": 15, "pyvista/pyvista": 1, "scikit-learn/scikit-learn": 22, "sphinx-doc/sphinx": 16, "sqlfluff/sqlfluff": 5, "sympy/sympy": 60}).

Prompt hashes (`prompt_sha256`, keys `naming/graph/order`):

| Group | Compared | Differ | Tasks with a difference, by repository |
|---|---|---|---|
| opaque | 2248 | 8 | {"pytest-dev/pytest": 1} |
| real | 1686 | 0 | {} |

Text-level comparison: I rendered the prompts with the 0.1.2 code (the kept copy in `gemma4-staging/studyb6/old_src`, made from the backed-up `rename.py` and `studyb.py`) and with the 0.1.3 code, then compared them word by word. The dumps stay in staging. `dump_sha_matches_frozen` checks each dump's hashes against `lite_0.1.2/tasks.json` (old) and `lite/tasks.json` (new). Scope: the 42 eligible Lite tasks of pylint, sphinx, sqlfluff and pytest, the repositories whose identity words the patch changes; their tasks include every Lite task whose prompt hash differs (1 task), and every other Lite task has all prompt hashes equal to 0.1.2.

```json
{
 "categories": {
  "unaligned_span": 8
 },
 "differing_prompts_by_repo": {
  "pytest-dev/pytest": 8
 },
 "dump_sha_matches_frozen": {
  "new": 588,
  "old": 588,
  "total": 588
 },
 "opaque_prompts_differ": 8,
 "prompts_compared": 588,
 "prompts_differ": 8,
 "prompts_with_changed_token_count": 8,
 "real_prompts_differ": 0,
 "tasks_with_a_difference": 1
}
```
Non-pseudo-word differences as identifier pairs (old side -> new side, source name where the map gives one; counts; top 40 per category):

```json
{
 "unaligned_span (checked by hand from the token diff)": {
  "<url> -> a URL on py.readthedocs.io (the 0.1.2 URL scrub matched the identity word py)": 8
 }
}
```

## Package file hashes for the addendum

| File | SHA-256 |
|---|---|
| README.md | `e530d92ac61b7af4051f72418bd5d15c6a0e28abcdb06d2e275e7f49108dd597` |
| prereg/PREREGISTRATION.md | `c909a62accb5121b332e4deab4fbbd380f4bc332bde5c5a4715bab2c038980eb` |
| prereg/OPEN_ITEMS.md | `e6859cf8cda5b1b22099ec008f631a225f457e8a601e3276efef03834f329f0f` |
| CODE_SHA256.txt | `983e343e3c1db31d58d172e2192bbb02ba3bc3e7e12353ddc426fff5994d9f70` |
