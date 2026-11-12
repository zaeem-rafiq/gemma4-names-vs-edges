# Exploratory analyses (EXPLORATORY, not pre-registered)

Everything in this folder was run after the confirmatory Study A and Study B runs, on 11 Nov 2026, and is exploratory: none of it was pre-registered and none of it changes a registered result. Scripts run from the unpacked prereg-v1.1 package with `PYTHONPATH=src` and the environment variable `P` set to the project folder that holds the package, the frozen Study B task files (`studyb-frozen/`), the competition data and SWE-bench Lite (see `data/studyb/README.md`). The original absolute project path in our scripts is replaced by `$P`; `RELEASE_NOTES.md` explains the redaction, and the SHA-256 below are those of the released copies.

Not redistributed: the rebuilt Study B task records and every prompt built from the competition data or SWE-bench Lite (`e3_prompts.jsonl`, `e4c_prompts.jsonl`). They can be rebuilt with the scripts here from the frozen inputs listed in `data/studyb/README.md`; every rebuilt base prompt is checked against its frozen SHA-256. `e5_prompts.jsonl` is included because it is built from our own Study A items. Run files hold ids, cells, letter logits and correctness only.

## E1. Can the call graph reach the bug at all? (no model)

For the 174 anchored confirmatory Study B tasks, hop distances from the issue anchors to the gold functions in the true and the rewired (seed 1) graph, chance rates n_k, and a whole-repository retriever that ranks library functions by hop distance (ties by BM25), compared with BM25 alone. Every task record was regenerated through the package and checked against the frozen task file before anything was computed.

Command: `PYTHONPATH=src python exploratory/e1_extract.py exploratory/e1_tasks.jsonl, then python3 -I exploratory/e1_stats.py exploratory/e1_tasks.jsonl exploratory/e1_stats.json (run_e1.sh)`

| File | SHA-256 |
|---|---|
| `e1_extract.py` | `edd560a56407610fe1609efb76b8daa33e9fa9d1930367868d59fb7abca65975` |
| `e1_stats.py` | `b520eb11097c6b776269e9686230ef904047e58facc1915dbec1600788c1da23` |
| `run_e1.sh` | `e17025eb8e1a0c33a9a47964153d6f44fdc7418e8e28a3c4fb0ef9f0b9632e53` |
| `e1_tasks.jsonl` | `dcfcdf32faaf237fe57fda2de93eb2d310f24a7e73f2d686a9b23b70f5e4a325` |
| `e1_stats.json` | `13a33de830a0e1d1104963cd36a137a16635247ea6abe704131b109b4494dbba` |
| `e1_extract.log` | `708f1888d49058d09cdbb31a1135b4d08b03c1a44553ecbbff537ce61ae5dcb9` |
| `e1_extract.attempt1.log` | `42a64e032fa44b6ad83d479f2a2d64dfc2434254c31880e856f3a886d58fd4d3` |
| `run_e1.exit` | `0952245921cbd520c44fb82bed7dc48bd44ed29510fe92ae8f55169d86a36e55` |
| `run_e1.exit.attempt1` | `eb0880e6b8ffcd491997e317776840fe3b7a6889849d0314860e48ce17e631ac` |

## E2. Does the Study B graph effect appear where the true graph points at the answer? (no new runs)

The registered Study B graph effect (true minus rewired, opaque and real naming) on the tasks where a gold candidate shares an edge with an anchor in the true graph, against the rest; by stratum and model; and how often the predicted letter changes between the true and the rewired graph.

Command: `python3 -I exploratory/e2_subsets.py exploratory/e2_subsets.json`

| File | SHA-256 |
|---|---|
| `e2_subsets.py` | `09e75d76125a7adaa3a838f8ab8b4d320247a0a34a0ca717c1e98bd6e6708d95` |
| `e2_subsets.json` | `ee6a47699339afdd8a7c3324dc13d8e9f1ed249979647989c9c1195090efd247` |
| `e2_subsets.log` | `fc7624c4b8f88e88266331e8cdffb53ce76e814d0792f51f7bae4d9e79789116` |

## E2b. What the graph block shown in the prompts contains (no model)

Per arm (true, rewired) and set, the share of prompts whose tool output shows a gold-anchor edge or any gold edge, and the block size, from the frozen task files' tool outputs.

Command: `python3 -I exploratory/e2b_edges.py exploratory/e2b_edges.json`

| File | SHA-256 |
|---|---|
| `e2b_edges.py` | `fcd8984468c9fdf52b14386f0c7a2afa53c9db72c889c579f795ddb27dca3389` |
| `e2b_edges.json` | `9936524b3eca9576ad1081cb32de70b85796946efafd4e868c390522e6829852` |

## E2c. Are the shown edges mirrored? (no model)

Share of shown directed edges whose reverse is also shown, one-way edges and self-loops, per set and arm, for all 371 eligible confirmatory tasks.

Command: `python3 -I exploratory/e2c_direction.py exploratory/e2c_direction.json`

| File | SHA-256 |
|---|---|
| `e2c_direction.py` | `5e295b89615222e0066d19cfed3ba4aed6c7f53e553d74392de0613b03a5e31e` |
| `e2c_direction.json` | `5b1172843a6bfeadd0fb3e89a9c4c12ea201c82ed9e469bf461436a07b16a918` |

## E3. Positive control: a hint that the answer neighbours a named anchor

19 anchored tasks where a gold candidate neighbours the first anchor in the true graph. The registered opaque prompts (true, rewired, no graph; both orders), each checked against its frozen SHA-256, plus one identical line in every arm: "Hint: the function to edit is a direct neighbour of <first anchor, renamed> in the repository's call graph." Scored with E4B and 31B under the Study B settings and prefixes; all 10 letter logits stored.

Command: `PYTHONPATH=src python exploratory/e3_prepare.py e3_prompts.jsonl e3_tasks.json; run_e3.sh (e3_run.py); python3 -I exploratory/e3_analyze.py exploratory/e3_results.json`

| File | SHA-256 |
|---|---|
| `e3_prepare.py` | `3fc7784cf6c4db43d1279b989c1535727a0fc90f47cf3c5ee6e3182d3dba3d21` |
| `e3_tasks.json` | `4f41114aa5890c7482a79cf6f54ba84e5180d9077605239694d6595ae9599332` |
| `e3_run.py` | `d1b7705d3729659075fddad83511cbe720e7c0ec2998766afb022cafd1a4c7c0` |
| `run_e3.sh` | `adf44de452823cca7110e60df598ad05e6789eb343dc2585391c5a9120fffda8` |
| `e3_E4B.jsonl` | `9290db315229975cab21c9ff8175dd64a84a05ce52e059ed907c818df6bb79f8` |
| `e3_31B.jsonl` | `a56b46fd3baf6e90c6a8c0f408a7d9ab03882edbadf09a30be99e4c9e90b7c79` |
| `e3_analyze.py` | `02e5dc20b3a75fcfff837e424d7abf6a4275e9d37846acd952ffb577556b4638` |
| `e3_results.json` | `33b486d4d7961e2e92bfb0bbef94a5e1b1cecddd4f47f2d4dd0967cbeec52761` |

## E4c. Density-matched graph arms

174 anchored tasks, opaque naming, both orders. true_thinned: the true block thinned at random (seed per task) to the rewired block's directed edge count. random_dense: the true block's nodes with the true block's edge count, drawn at random but never joining a gold candidate and an anchor. Neighbour lists are consistent with each arm's own subgraph. Prompts equal the registered opaque/true prompt outside the tool block (checked); a gate refused to launch until every check passed. Scored with E4B and 31B; all 10 letter logits stored.

Command: `PYTHONPATH=src python exploratory/e4c_prepare.py e4c_prompts.jsonl exploratory/e4c_checks.json; run_e4c.sh (gate, then e3_run.py --study E4c); python3 -I exploratory/e4_analyze.py exploratory/e4c_results.json`

| File | SHA-256 |
|---|---|
| `e4c_prepare.py` | `575e4252543c74ab31e2d40a366a5e78eef8ce38c65f909414bde8f3ee16d9a8` |
| `e4c_checks.json` | `8760392b9514a3bef61c69342c19219ee3802d25b816fcf2ea69ca502455f6a6` |
| `run_e4c.sh` | `55f002006ca752628581219a94d00c86586f4f6f076541b71ed3c286c180cc07` |
| `e4c_E4B.jsonl` | `b00c4987dc31820c5acc73a2b4c52d22116237aa94d63ab5cfe31a1f4a815958` |
| `e4c_31B.jsonl` | `b739a12a3f3810fbe46aef018d0c13debc19090fefb04a572f1955f1f50f64b1` |
| `e4_analyze.py` | `da05f60902cc28786ea2ef16298ff830f0049bffc687e2f003a5d6f6a709313e` |
| `e4c_results.json` | `b9aaaa908e1ee7b4289867929e86bd5e92253ec9e5be5bf232c3be2e26db7f9d` |

## E5. Format bridge: Study A items with the graph as Study B's JSON tool output

The Study A items each model was scored on, with G1 (true graph) and G3 (swapped graph) re-rendered as a get_code_subgraph JSON block (directed edges, no explanation line) instead of "F -> G, H" lines; question, options and footer byte-identical to the registered prompts (checked for all 10,240 rows). 31B: G1J and G3J, perm 1; E4B: G1J, perms 1 and 2. Scored like Study A and compared with the registered cells.

Command: `PYTHONPATH=src python exploratory/e5_prepare.py data/items runs/studyA exploratory/e5_prompts.jsonl exploratory/e5_summary.json; run_e5.sh (e5_run.py); python3 -I exploratory/e5_analyze.py exploratory/e5_results.json`

| File | SHA-256 |
|---|---|
| `e5_prepare.py` | `ff31e3db25ae287082a756d8958fabfeb68f072c1b475a870f15d60709c47358` |
| `e5_prompts.jsonl` | `69b6b7da88780fd062cd4731a1a7b2139410f614c9d574392c8276e8e6d0c919` |
| `e5_summary.json` | `5f2be5911f5b826ab62b96101c70b9034d0b71bb6cfaeeaac3ad117844d75a55` |
| `e5_run.py` | `ba4d6fa98ac5eadb015515227dc12e39681c5de56bc8c55e29ed053f4e3d7eca` |
| `run_e5.sh` | `d87c4d0e87c07f47d6454ce1b940c2279b79c64da2da3fcacf69e899becc22f9` |
| `e5_31B.jsonl` | `640bf2cdb95ffab312f8ef9dd533ef1589977db6b299f7202773c93e922f82f2` |
| `e5_E4B.jsonl` | `5eaa315c0527f9b2b9c698746b233ee7d6d8d38b396e3c6df022597a375d5b22` |
| `e5_analyze.py` | `9a54a1f5b8a6078717939a6aac78ca10970fa556cbdc33060427be874a0ce672` |
| `e5_results.json` | `db4322a45238e0def6d1f70ffc9561df369466a054d61ff150fb81ff8d40195b` |
