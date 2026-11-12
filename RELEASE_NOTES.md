# Release notes

This repository is the frozen prereg-v1.1 package tree plus the Study A and Study B run files, reports, run logs and
exploratory scripts. Nothing derived from the competition data or SWE-bench Lite beyond task ids and identifiers is
included (no issue text, code, patches, graphs, snapshots or task files).

## Redacted copies

In the scripts below, only the home-folder prefix of the project path was replaced: shell scripts read the project
folder from the environment variable P (`P="${P:?...}"`, then `$P/...`), Python scripts read `os.environ["P"]`
(with `import os` added). No other line changed. The original column is the SHA-256 of the file as run.

| Released file | Original (as run, path relative to the project folder) | SHA-256 original | SHA-256 released |
|---|---|---|---|
| `exploratory/e1_extract.py` | `P/exploratory-v1.1/e1_extract.py` | `62709fc33c9502385e182d3240a5bd63b62d346ce58740ea2d3738fc771b70df` | `edd560a56407610fe1609efb76b8daa33e9fa9d1930367868d59fb7abca65975` |
| `exploratory/e2_subsets.py` | `P/exploratory-v1.1/e2_subsets.py` | `c5977b35f23884b1ea51e0eae7126cdfdaf68798ebe9cb1a00e2835d7a5555df` | `09e75d76125a7adaa3a838f8ab8b4d320247a0a34a0ca717c1e98bd6e6708d95` |
| `exploratory/run_e1.sh` | `P/exploratory-v1.1/run_e1.sh` | `dd7f63bb76ea7a830775f1d8d072e17e2705681af1019f3831fbac9649c134e2` | `e17025eb8e1a0c33a9a47964153d6f44fdc7418e8e28a3c4fb0ef9f0b9632e53` |
| `run_log/run_studyA.sh` | `P/run_log/run_studyA.sh` | `5adfabb09097b2912979a3ddca63a9f967a0a69490686310a36020f46a6a8412` | `df5a6d71168d0fb51b30afc762c126d4657d02f16372ae4a075baa7af3bae185` |
| `run_log/tools/studyb5_lite.sh` | `P/run_log/tools/studyb5_lite.sh` | `4f896a2afe4f78e1e327e4cae516570016cb24860d3158ed52eeaa6f1db74bd7` | `60ccf82dec04c3c47f7d09d34d7cc287d18c23d095c2b80a39d731932a1b46cb` |
| `run_log/tools/studyb6_build.sh` | `P/run_log/tools/studyb6_build.sh` | `c1b8423f47bd7f2864eaed431c7051d77dd4c588265a14046876f4977e36e5d5` | `7601450c65977aa48fed8b08395f3814e711c9f41ab3eacaf66c8d026fd39282` |
| `runs/studyB/studyb_runs.sh` | `P/studyB-v1.1/runs/studyb_runs.sh` | `847eb9d30b05152771e6cc2f57c7ada581cbd29e067bef72255f678c63d88928` | `ff84d381d8e23c4a89ca698a8548d0c3c3136ff3672c8c0390dd0eb8b92a85e6` |
| `runs/studyB/pilot_timing.sh` | `P/studyB-v1.1/runs/pilot_timing.sh` | `226c25ac7709a28c64921144d7b958bc2dd19c7fcfffc61fa5cd33452d43200f` | `e5fe8722b90aef62de13121271e182da7002f63236f22860628b11a9e401fe17` |

Every log (`*.log`, `runs/*/log_*.txt`, `run_log/studyb_clone/*.log`) and every Markdown report is verbatim and
may still show the original absolute path. The package tree, frozen archives and manifests are unchanged and match
`frozen/MANIFEST_prereg-v1.1.txt`.

## Redacted copies, second batch (exploratory scripts of 11 Nov 2026)

Same rule as above: only the home-folder prefix of the project path was replaced (shell: `P="${P:?...}"`; Python: `os.environ["P"]`).

| Released file | Original (as run, path relative to the project folder) | SHA-256 original | SHA-256 released |
|---|---|---|---|
| `exploratory/e2b_edges.py` | `P/exploratory-v1.1/e2b_edges.py` | `66f5e19883c24aeed49d5961e8aaa37b0ebfe342f81ff9d9b51ee543bca02b18` | `fcd8984468c9fdf52b14386f0c7a2afa53c9db72c889c579f795ddb27dca3389` |
| `exploratory/e2c_direction.py` | `P/exploratory-v1.1/e2c_direction.py` | `2763b2959730d31435692b63231bf037f43251d6c44825ce51466c991515164e` | `5e295b89615222e0066d19cfed3ba4aed6c7f53e553d74392de0613b03a5e31e` |
| `exploratory/e3_prepare.py` | `P/exploratory-v1.1/e3_prepare.py` | `f5b7f947dadb4b7325e8d690ed619ebdb0aef3604dd9ae4ec883b4d9ba93824d` | `3fc7784cf6c4db43d1279b989c1535727a0fc90f47cf3c5ee6e3182d3dba3d21` |
| `exploratory/run_e3.sh` | `P/exploratory-v1.1/run_e3.sh` | `8d848f6e54b5fb6c33efe8a37c2fb7bb0e8debe692a6a41b3578800617ed8321` | `adf44de452823cca7110e60df598ad05e6789eb343dc2585391c5a9120fffda8` |
| `exploratory/e3_analyze.py` | `P/exploratory-v1.1/e3_analyze.py` | `553c4b690277facde78c73a56e08a5d4f3500b316298c58a398d3b152166bb31` | `02e5dc20b3a75fcfff837e424d7abf6a4275e9d37846acd952ffb577556b4638` |
| `exploratory/run_e5.sh` | `P/exploratory-v1.1/run_e5.sh` | `49c8c89b6a32913dcf6759692aea70976e1f83b123a12193b37d408afc749b6b` | `d87c4d0e87c07f47d6454ce1b940c2279b79c64da2da3fcacf69e899becc22f9` |
| `exploratory/e5_analyze.py` | `P/exploratory-v1.1/e5_analyze.py` | `9f32635232dbd757205e470c58572feea5de73a9c24003a84694b298a7370796` | `9a54a1f5b8a6078717939a6aac78ca10970fa556cbdc33060427be874a0ce672` |
| `exploratory/e4c_prepare.py` | `P/exploratory-v1.1/e4c_prepare.py` | `544d094c3448889fa80ce00e36b9bac5ea18630c1dc9c762c684e676920233cb` | `575e4252543c74ab31e2d40a366a5e78eef8ce38c65f909414bde8f3ee16d9a8` |
| `exploratory/run_e4c.sh` | `P/exploratory-v1.1/run_e4c.sh` | `2874688b58f235ca7abea463d8fc00e198922fd57006b2d87e6474bd2a0af71c` | `55f002006ca752628581219a94d00c86586f4f6f076541b71ed3c286c180cc07` |
| `exploratory/e4_analyze.py` | `P/exploratory-v1.1/e4_analyze.py` | `e90a13f2a5cdecf3cda47c690f9c040ce64f3c3a6fc3345d5594dfc1817191b6` | `da05f60902cc28786ea2ef16298ff830f0049bffc687e2f003a5d6f6a709313e` |

Every other file in `exploratory/` is a byte-identical copy of the file as produced.

## Added 12 Nov 2026

- `notebooks/names_vs_edges_recompute.ipynb`: recomputes Tables 1 and 3, A1, B1, B2, the B2 injected split and the letter-logit analysis from the run files at commit c787276 (clones the public repository).
- `reproduce_from_runs.py`: standard library only.
- `fig/fig1.py` and `fig/figure1.png`: Figure 1 of the paper (`figure1.png` regenerated with matplotlib 3.9.2, 2200 x 1056 px).

## Fix of 12 Nov 2026 (no result changes)

In `exploratory/e2_subsets.py`, `e3_analyze.py`, `e4_analyze.py` and `e5_analyze.py`, the redaction left the `R =` / `X =` folder assignment inside the comment on the `P =` line, so the scripts stopped with a NameError; the assignment is now on its own line. `exploratory/e3_prepare.py` now holds the hint text the scored E3 prompts use ("... in the repository's call graph."), with a comment on how those prompts were made from the first version. Re-run on 12 Nov with `P` set, the four analysis scripts reproduce `e2_subsets.json`, `e3_results.json`, `e4c_results.json` and `e5_results.json` byte for byte. The SHA-256 above and in `exploratory/README.md` are those of the fixed copies.
