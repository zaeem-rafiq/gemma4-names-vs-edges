#!/bin/bash
# usage: lite_clone.sh P   -- clones each repo in run_log/studyb_lite_repos.txt, no checkout, no submodules
P="$1"; export P GIT_TERMINAL_PROMPT=0; mkdir -p "$P/lite-repos" "$P/run_log/studyb_clone"
one() { r="$1"; d="${r/\//__}"; s=$(date -u +%FT%TZ)
  nice -n 19 git -c pack.threads=4 clone --no-checkout "https://github.com/$r.git" "$P/lite-repos/$d" > "$P/run_log/studyb_clone/$d.log" 2>&1
  echo "$r exit=$? start=$s end=$(date -u +%FT%TZ)"; }
export -f one
xargs -n1 -P4 bash -c 'one "$0"' < "$P/run_log/studyb_lite_repos.txt"
