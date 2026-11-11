#!/bin/bash
# usage: studyb_build.sh P official|lite   -- runs the frozen Study B builds; records real exit codes
set -o pipefail
P="$1"; cd "$P/gemma4-paper-code" || exit 9; export PYTHONPATH=src
V=third_party/llama.cpp/ggml-vocab-gemma-4.gguf; PY=.venv/bin/python
run() { name="$1"; log="$2"; shift 2; s=$(date -u +%FT%TZ); "$@" 2>&1 | tee "$P/run_log/$log" > /dev/null; e=$?; echo "$name exit=$e start=$s end=$(date -u +%FT%TZ)" >> "$P/run_log/studyb_builds.exit"; return $e; }
if [ "$2" = official ]; then
  mkdir -p "$P/studyb-frozen/official"
  run build_official studyb_build_official.log $PY -m ngraph.studyb build --set official --data "$P/competition-data" --vocab $V --out "$P/studyb-frozen/official"; a=$?
  run mc3 studyb_mc3.log $PY -m ngraph.studyb mc3 --data "$P/competition-data" --out "$P/studyb-frozen/official/mc3.json"; b=$?
  exit $((a|b))
else
  mkdir -p "$P/studyb-frozen/lite"
  run build_lite studyb_build_lite.log $PY -m ngraph.studyb build --set lite --lite-test "$P/lite/swebench_lite_test.jsonl" --lite-dev "$P/lite/swebench_lite_dev.jsonl" --repos-dir "$P/lite-repos" --vocab $V --out "$P/studyb-frozen/lite"
fi
