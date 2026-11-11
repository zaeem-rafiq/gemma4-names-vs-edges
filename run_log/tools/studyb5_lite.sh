#!/bin/zsh
# Lite build for renamer 0.1.2, detached with nohup so it survives the Claude session. Appends one line to studyb_builds.exit.
P="${P:?set P to the project folder}"; cd "$P/gemma4-paper-code" || exit 9
set -o pipefail
s=$(date -u +%FT%TZ)
PYTHONPATH=src .venv/bin/python -m ngraph.studyb build --set lite --lite-test "$P/lite/swebench_lite_test.jsonl" --lite-dev "$P/lite/swebench_lite_dev.jsonl" --repos-dir "$P/lite-repos" --vocab third_party/llama.cpp/ggml-vocab-gemma-4.gguf --out "$P/studyb-frozen/lite" 2>&1 | tee "$P/run_log/studyb_build_lite.log" >/dev/null
c=$?
echo "build_lite exit=$c start=$s end=$(date -u +%FT%TZ)" >> "$P/run_log/studyb_builds.exit"
