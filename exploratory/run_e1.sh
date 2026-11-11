#!/bin/bash
X="${P:?set P to the project folder}/exploratory-v1.1"; cd "$X" || exit 9
s=$(date -u +%FT%TZ)
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$P/studyB-v1.1/src" caffeinate -i -s "$P/gemma4-paper-code/.venv/bin/python" e1_extract.py e1_tasks.jsonl > e1_extract.log 2>&1
echo "e1_extract exit=$? start=$s end=$(date -u +%FT%TZ)" >> run.exit
