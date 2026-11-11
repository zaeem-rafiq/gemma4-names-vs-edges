#!/bin/zsh
# Study B rebuild for renamer 0.1.3: official, mc3, lite (same arguments as the 0.1.2 builds). Run with nohup.
P="${P:?set P to the project folder}"; cd "$P/gemma4-paper-code" || exit 9
EX="$P/run_log/studyb6_builds.exit"; set -o pipefail
run(){ n=$1; shift; s=$(date -u +%FT%TZ); "$@"; c=$?; echo "$n exit=$c start=$s end=$(date -u +%FT%TZ)" >> "$EX"; return $c; }
b_off(){ PYTHONPATH=src .venv/bin/python -m ngraph.studyb build --set official --data "$P/competition-data" --vocab third_party/llama.cpp/ggml-vocab-gemma-4.gguf --out "$P/studyb-frozen/official" 2>&1 | tee "$P/run_log/studyb_build_official.log" >/dev/null; }
b_mc3(){ PYTHONPATH=src .venv/bin/python -m ngraph.studyb mc3 --data "$P/competition-data" --out "$P/studyb-frozen/official/mc3.json" 2>&1 | tee "$P/run_log/studyb_mc3.log" >/dev/null; }
b_lite(){ PYTHONPATH=src .venv/bin/python -m ngraph.studyb build --set lite --lite-test "$P/lite/swebench_lite_test.jsonl" --lite-dev "$P/lite/swebench_lite_dev.jsonl" --repos-dir "$P/lite-repos" --vocab third_party/llama.cpp/ggml-vocab-gemma-4.gguf --out "$P/studyb-frozen/lite" 2>&1 | tee "$P/run_log/studyb_build_lite.log" >/dev/null; }
run build_official b_off && run mc3 b_mc3; run build_lite b_lite
echo "all done $(date -u +%FT%TZ)" >> "$EX"
