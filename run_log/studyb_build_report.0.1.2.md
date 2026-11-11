# Study B build report (renamer 0.1.2, extractor 0.3.1)

## Outcome

**Complete. I built both sets with renamer 0.1.2 and extractor 0.3.1, and every command exited 0.** The official set has 129 tasks, 111 eligible and 0 hard leaks. The Lite set has 317 tasks, 260 confirmatory eligible plus 21 tune eligible, and 7 tasks with hard leaks.

- The patch hashes matched before and after. The tests passed except the expected `test_package_code_sha256_is_current`.
- The renamer fix works on the earlier failures. matplotlib and sympy now build, and the 3 Django tasks that kept `user` have no leaks.
- Official against 0.1.1: the task ids, eligible, anchored, strata and all per-task fields are the same. 456 of 888 opaque prompts differ, all in fastapi's 57 tasks. All 666 real prompts are identical. Every differing word is the same source name with a new pseudo-word. mc3.json is byte-identical.
- Confirmatory anchored share, official plus Lite: 174/371 = 0.469.
- Remaining hard leaks in Lite, identifiers only: `node_count` in 6 pylint tasks: pylint-dev__pylint-5859, -6506, -7080, -7114, -7228 and -7993. `ipython` in sympy__sympy-18621. Each leak is in the opaque prompts listed below.
- `CODE_SHA256.txt` is stale until the addendum regenerates it.

The Lite build ran twice. The first run reached 298 of 317 tasks with no error in its log. It stopped at about 01:00 UTC because the Claude session that started it ended. I kept that log as `run_log/studyb_build_lite.log.interrupted1`. Its 7 leak tasks are the same 7 as in the final run. I restarted the build detached with nohup, through `run_log/tools/studyb5_lite.sh`. It ran from 01:21 to 03:02 UTC and exited 0. I report it only at 04:55 UTC because my wait job also ended with the session, so I missed the finish.

## Step 1: patch

| File | Expected before | Expected after | Observed after |
|---|---|---|---|
| src/ngraph/rename.py | `258131f8c8d021f9e6afd521d66b9a248ce973fa68ef8327492c5462694fa355` (matched before patching) | `3e7084b62f8532f0fb5d90ce7cec43f68ae0c44240006f76d3257e4a6ca804f0` | `3e7084b62f8532f0fb5d90ce7cec43f68ae0c44240006f76d3257e4a6ca804f0` MATCH |
| src/ngraph/extract.py | `d6eee0ff4769943c2dc67e19705ad28727bf4d34ea16fc43decae68d07dbdee1` (matched before patching) | `b0504b66224fc20732b278e4ff008eccaeebb802750469b6907593a034dc213a` | `b0504b66224fc20732b278e4ff008eccaeebb802750469b6907593a034dc213a` MATCH |
| tests/test_studyb.py | `0ff29a625d3dc1a0afb082561ec1f36e08d9655616ff1619e96d4122feef58df` (matched before patching) | `c6a1f73a4fc6e46a4dfd2a6ad274fffe21cb0fec2e12658b78b8c6da7f470169` | `c6a1f73a4fc6e46a4dfd2a6ad274fffe21cb0fec2e12658b78b8c6da7f470169` MATCH |
| src/ngraph/official.py | `f59753dab15a111cabba87798dd9a2ea665be4fc62fb1fbaa5fa27e6ce66a4d7` (matched before patching) | `f59753dab15a111cabba87798dd9a2ea665be4fc62fb1fbaa5fa27e6ce66a4d7` | `f59753dab15a111cabba87798dd9a2ea665be4fc62fb1fbaa5fa27e6ce66a4d7` MATCH |

Decoded patch SHA-256: `6dc17f364af53925e42ef145342c08890a113dadb3a34aae9a5ac0708ccbb809` (expected `6dc17f364af53925e42ef145342c08890a113dadb3a34aae9a5ac0708ccbb809`). It has 20 lines with a less-than sign, 4 lines with an exclamation mark, and no `{LT}` or `{EX}`. The relay envelope had XML-escaped `>` and `&` as `&gt;` and `&amp;`, and I wrote the real characters. The hash match confirms that reading. Backups of the three files are in `gemma4-staging/studyb5/base/`.

`patch -p1 -l` dry run: exit 0. Real run: exit 0. Output:

```
patching file 'src/ngraph/rename.py'
patching file 'src/ngraph/extract.py'
patching file 'tests/test_studyb.py'
```
No `.orig` or `.rej` file was left in the package.

## Step 2: tests

Exit 1, 2026-11-09T23:50:17Z to 2026-11-09T23:50:24Z.

```

    def test_package_code_sha256_is_current():
        """CODE_SHA256.txt must match the code and docs; regenerate with `python -m ngraph.commit code-sha256`."""
        res = cm.check_code_sha256(PKG)
>       assert res["ok"], res
E       AssertionError: {'ok': False, 'stale_or_missing': ['./src/ngraph/analysis.py', './src/ngraph/extract.py', './src/ngraph/lite.py', './s...dyb.py', ...], 'no_longer_matching': ['./src/ngraph/analysis.py', './src/ngraph/extract.py', './src/ngraph/rename.py']}
E       assert False

tests/test_commit.py:554: AssertionError
=========================== short test summary info ============================
FAILED tests/test_commit.py::test_package_code_sha256_is_current - AssertionE...
1 failed, 124 passed, 23 skipped in 5.44s
```
The only failure is the expected `tests/test_commit.py::test_package_code_sha256_is_current`.

## Commands: exit codes and times (UTC)

| Command | Exit | Start | End |
|---|---|---|---|
| studyb build --set official | 0 | 2026-11-09T23:50:39Z | 2026-11-09T23:54:20Z |
| studyb mc3 | 0 | 2026-11-09T23:54:20Z | 2026-11-09T23:54:23Z |
| studyb build --set lite | 0 | 2026-11-10T01:21:07Z | 2026-11-10T03:02:38Z |

Step 3 moves (mv, nothing deleted): `studyb-frozen/official` to `official_prefix_0.1.1`; `studyb-frozen/lite` (an empty folder) to `lite_failed_0.1.1`; the four old logs and report gained the suffix `.0.1.1`. The old `studyb_builds.exit` also gained that suffix.

Official `--data` was `P/competition-data`, the folder that holds `tasks.jsonl`, `graphs`, `snapshots`.


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
| rename_maps.json.gz | 108494 | `227c6ed9600de904414d9dea7e20d9a0236fb800ee8b6a57429198a9cb3a5249` |
| tasks.json | 1021179 | `fc93f435d70ad9ddd953619ff3b9a66f4e375773626ba1d709c0d10505a53a5d` |

Tasks with hard leaks: 0.

Rename maps per repository (`n_protected_defined`; `map` = names in the rename map):

| Repo | n_protected_defined | Renamed names | rename_version | packages |
|---|---|---|---|---|
| Textualize/rich | 101 | 2285 | 0.1.2 | rich |
| encode/httpx | 29 | 385 | 0.1.2 | ahttpx, httpx |
| fastapi/fastapi | 154 | 4329 | 0.1.2 | docs_src, fastapi, pdm_build |
| psf/requests | 69 | 845 | 0.1.2 | requests |

Graphs in graphs_report.json: 127.

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
Extractor versions in `stats`: ['None'].

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

mc3.json byte-identical to the 0.1.1 mc3.json: True.

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
 "tasks_with_hard_leaks": 7
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
| rename_maps.json.gz | 2200915 | `c8a4d4f345d1e178bd36b42541ff0b42f301ce5ace440e2363ea2f696dd1f9ff` |
| tasks.json | 2830925 | `f3cbbf095168b30fa9ef3063b83f6df87061ae49ab02d6b82bc000a8a9c4d9f5` |

Tasks with hard leaks: 7.
- pylint-dev__pylint-5859: {"opaque/rewired/1": {"node_count": 1}, "opaque/rewired/2": {"node_count": 1}, "opaque/true/1": {"node_count": 1}, "opaque/true/2": {"node_count": 1}, "opaque/within_module/1": {"node_count": 1}, "opaque/within_module/2": {"node_count": 1}}
- pylint-dev__pylint-6506: {"opaque/rewired/1": {"node_count": 1}, "opaque/rewired/2": {"node_count": 1}, "opaque/true/1": {"node_count": 1}, "opaque/true/2": {"node_count": 1}, "opaque/within_module/1": {"node_count": 1}, "opaque/within_module/2": {"node_count": 1}}
- pylint-dev__pylint-7080: {"opaque/rewired/1": {"node_count": 1}, "opaque/rewired/2": {"node_count": 1}, "opaque/true/1": {"node_count": 1}, "opaque/true/2": {"node_count": 1}, "opaque/within_module/1": {"node_count": 1}, "opaque/within_module/2": {"node_count": 1}}
- pylint-dev__pylint-7114: {"opaque/rewired/1": {"node_count": 1}, "opaque/rewired/2": {"node_count": 1}, "opaque/true/1": {"node_count": 1}, "opaque/true/2": {"node_count": 1}, "opaque/within_module/1": {"node_count": 1}, "opaque/within_module/2": {"node_count": 1}}
- pylint-dev__pylint-7228: {"opaque/rewired/1": {"node_count": 1}, "opaque/rewired/2": {"node_count": 1}, "opaque/true/1": {"node_count": 1}, "opaque/true/2": {"node_count": 1}, "opaque/within_module/1": {"node_count": 1}, "opaque/within_module/2": {"node_count": 1}}
- pylint-dev__pylint-7993: {"opaque/rewired/1": {"node_count": 1}, "opaque/rewired/2": {"node_count": 1}, "opaque/true/1": {"node_count": 1}, "opaque/true/2": {"node_count": 1}, "opaque/within_module/1": {"node_count": 1}, "opaque/within_module/2": {"node_count": 1}}
- sympy__sympy-18621: {"opaque/none/1": {"ipython": 1}, "opaque/none/2": {"ipython": 1}, "opaque/rewired/1": {"ipython": 1}, "opaque/rewired/2": {"ipython": 1}, "opaque/true/1": {"ipython": 1}, "opaque/true/2": {"ipython": 1}, "opaque/within_module/1": {"ipython": 1}, "opaque/within_module/2": {"ipython": 1}}

Rename maps per repository (`n_protected_defined`; `map` = names in the rename map):

| Repo | n_protected_defined | Renamed names | rename_version | packages |
|---|---|---|---|---|
| astropy/astropy | 552 | 16810 | 0.1.2 | ah_bootstrap, astropy, ez_setup |
| django/django | 465 | 32423 | 0.1.2 | django |
| marshmallow-code/marshmallow | 66 | 1592 | 0.1.2 | marshmallow |
| matplotlib/matplotlib | 251 | 12367 | 0.1.2 | matplotlib, mpl_toolkits, pylab, setupext |
| mwaskom/seaborn | 110 | 3026 | 0.1.2 | seaborn |
| pallets/flask | 120 | 1318 | 0.1.2 | flask |
| pvlib/pvlib-python | 60 | 2295 | 0.1.2 | pvlib, versioneer |
| pydata/xarray | 304 | 4361 | 0.1.2 | versioneer, xarray |
| pydicom/pydicom | 94 | 3720 | 0.1.2 | dicom, pydicom |
| pylint-dev/astroid | 153 | 3153 | 0.1.2 | astroid |
| pylint-dev/pylint | 300 | 8331 | 0.1.2 | pylint, script |
| pytest-dev/pytest | 243 | 5813 | 0.1.2 | _pytest, py, pytest |
| pyvista/pyvista | 122 | 5051 | 0.1.2 | pyvista |
| scikit-learn/scikit-learn | 446 | 14225 | 0.1.2 | sklearn |
| sphinx-doc/sphinx | 338 | 6096 | 0.1.2 | sphinx, utils |
| sqlfluff/sqlfluff | 69 | 2177 | 0.1.2 | sqlfluff, util |
| sympy/sympy | 669 | 39780 | 0.1.2 | isympy, setupegg, sympy |

Graphs in graphs_report.json: 314.

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
Extractor versions in `stats`: ['0.3.1'].

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
 "tasks_with_hard_leaks": 7,
 "max_tokens": 7936,
 "excluded": {
  "no library function in the gold patch": 36
 }
}
```

## Anchored counts on confirmatory tasks

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


## Official set: 0.1.2 against 0.1.1 (`official_prefix_0.1.1`)

- Same task ids: True (129 old, 129 new).
- `eligible`: old 111, new 111, same: True.
- `anchored`: old 43, new 43, same: True.
- `strata`: old {"S0": 19, "S1": 7, "S2": 3, "S3": 82}, new {"S0": 19, "S1": 7, "S2": 3, "S3": 82}, same: True.
- `injected`: old 48, new 48, same: True.
- `by_repo`: old {"Textualize/rich": 42, "encode/httpx": 1, "fastapi/fastapi": 57, "psf/requests": 11}, new {"Textualize/rich": 42, "encode/httpx": 1, "fastapi/fastapi": 57, "psf/requests": 11}, same: True.
- `excluded`: old {"no library function in the gold patch": 18}, new {"no library function in the gold patch": 18}, same: True.
- `cut`: old 0, new 0, same: True.
- `code_lines_reduced`: old 0, new 0, same: True.
- `max_tokens`: old 4516, new 4516, same: True.
- `tasks_with_hard_leaks`: old 0, new 0, same: True.

Per-task fields that differ (tasks with any difference):

| Field | Tasks that differ |
|---|---|
| eligible | 0 |
| anchored | 0 |
| injected | 0 |
| stratum | 0 |
| gold | 0 |
| gold_files | 0 |
| pool | 0 |
| orders | 0 |
| anchors | 0 |
| correct_letters | 0 |

Prompt hashes (`prompt_sha256`, keys `naming/graph/order`):

| Group | Compared | Differ |
|---|---|---|
| opaque | 888 | 456 |
| real | 666 | 0 |

Tasks with at least one differing prompt hash: 57, by repository: {"fastapi/fastapi": 57}. The other repositories' prompts are byte-identical.

Text-level comparison. I rendered every prompt under the 0.1.1 code (a copy in `gemma4-staging/studyb5/old_src`) and under the 0.1.2 code, then compared them word by word. The dumps stay in staging. Each dump's hashes were checked against its frozen `tasks.json`.

```json
{
 "categories": {
  "same_name_new_pseudoword": 19228
 },
 "dump_sha_matches_frozen": {
  "new": 1554,
  "old": 1554,
  "total": 1554
 },
 "opaque_prompts_differ": 456,
 "prompts_compared": 1554,
 "prompts_differ": 456,
 "prompts_with_changed_token_count": 0,
 "real_prompts_differ": 0,
 "tasks_with_a_difference": 57
}
```
Non-pseudo-word differences, as identifier pairs (source name or token, old side -> new side, with counts; top 40 per category):

```json
{}
```
