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
| `exploratory/e2_subsets.py` | `P/exploratory-v1.1/e2_subsets.py` | `c5977b35f23884b1ea51e0eae7126cdfdaf68798ebe9cb1a00e2835d7a5555df` | `75dfc7932738d224333511764921d58ce24960784133b01f3d0207b5574ff858` |
| `exploratory/run_e1.sh` | `P/exploratory-v1.1/run_e1.sh` | `dd7f63bb76ea7a830775f1d8d072e17e2705681af1019f3831fbac9649c134e2` | `e17025eb8e1a0c33a9a47964153d6f44fdc7418e8e28a3c4fb0ef9f0b9632e53` |
| `run_log/run_studyA.sh` | `P/run_log/run_studyA.sh` | `5adfabb09097b2912979a3ddca63a9f967a0a69490686310a36020f46a6a8412` | `df5a6d71168d0fb51b30afc762c126d4657d02f16372ae4a075baa7af3bae185` |
| `run_log/tools/studyb5_lite.sh` | `P/run_log/tools/studyb5_lite.sh` | `4f896a2afe4f78e1e327e4cae516570016cb24860d3158ed52eeaa6f1db74bd7` | `60ccf82dec04c3c47f7d09d34d7cc287d18c23d095c2b80a39d731932a1b46cb` |
| `run_log/tools/studyb6_build.sh` | `P/run_log/tools/studyb6_build.sh` | `c1b8423f47bd7f2864eaed431c7051d77dd4c588265a14046876f4977e36e5d5` | `7601450c65977aa48fed8b08395f3814e711c9f41ab3eacaf66c8d026fd39282` |
| `runs/studyB/studyb_runs.sh` | `P/studyB-v1.1/runs/studyb_runs.sh` | `847eb9d30b05152771e6cc2f57c7ada581cbd29e067bef72255f678c63d88928` | `ff84d381d8e23c4a89ca698a8548d0c3c3136ff3672c8c0390dd0eb8b92a85e6` |
| `runs/studyB/pilot_timing.sh` | `P/studyB-v1.1/runs/pilot_timing.sh` | `226c25ac7709a28c64921144d7b958bc2dd19c7fcfffc61fa5cd33452d43200f` | `e5fe8722b90aef62de13121271e182da7002f63236f22860628b11a9e401fe17` |

Every log (`*.log`, `runs/*/log_*.txt`, `run_log/studyb_clone/*.log`) and every Markdown report is verbatim and
may still show the original absolute path. The package tree, frozen archives and manifests are unchanged and match
`frozen/MANIFEST_prereg-v1.1.txt`.
