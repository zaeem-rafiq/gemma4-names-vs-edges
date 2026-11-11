"""Dry run of the Study B task tools on a repository's own history (no competition data needed).

Pairs: commits whose message says they fix an issue ("fixes #N"), that change non-test Python
files, and whose issue exists on GitHub. For each pair the base is the commit's first parent, the
gold patch is the commit's diff, and the query is the issue title and body. At the base commit the
script extracts the call graph (ngraph.extract), maps gold functions, builds the BM25 pool and finds
anchors and strata on the mirrored (official-like) view.

Issue texts are fetched once with the GitHub search API (`gh api`) into --issues-cache and are
treated as plain text. Nothing from the repository is executed: files are parsed with `ast`.

Example:
  python scripts/studyb_history_check.py --repo-dir repos/requests --gh-repo psf/requests \
      --since 2017-06-01 --issues-cache runs/requests_issues.json --out runs/requests_history.json
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tarfile
import tempfile
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from ngraph import extract as ex  # noqa: E402
from ngraph import localize as lz  # noqa: E402

FIX_RE = re.compile(r"(?i)\b(?:fix(?:es|ed)?|close[sd]?|resolve[sd]?)\s*:?\s*#(\d+)")


def git(repo, *args, text=True):
    return subprocess.run(["git", "-C", repo, *args], capture_output=True, text=text, check=True).stdout


def candidate_commits(repo, since):
    out = git(repo, "log", "--no-merges", f"--since={since}", "--format=%H%x00%P%x00%ad%x00%B%x1e",
              "--date=short")
    for rec in out.split("\x1e"):
        rec = rec.strip("\n")
        if not rec:
            continue
        sha, parents, date, msg = rec.split("\x00", 3)
        nums = sorted(set(FIX_RE.findall(msg)), key=int)
        if not nums or not parents:
            continue
        parent = parents.split()[0]
        files = git(repo, "diff", "--name-only", parent, sha).split()
        lib = [f for f in files if f.endswith(".py") and not ex.is_excluded(f)]
        if lib:
            yield {"sha": sha, "parent": parent, "date": date, "issues": nums, "files": lib,
                   "subject": msg.splitlines()[0][:120]}


def fetch_issue(gh_repo, num):
    q = f"repo:{gh_repo} is:issue {num}"
    res = subprocess.run(["gh", "api", "-X", "GET", "search/issues", "-f", f"q={q}"],
                         capture_output=True, text=True)
    if res.returncode != 0:
        return {"error": res.stderr.strip()[:300]}
    for it in json.loads(res.stdout).get("items", []):
        if str(it.get("number")) == str(num):
            return {"number": it["number"], "title": it.get("title") or "", "body": it.get("body") or ""}
    return None


def snapshot(repo, sha, dest):
    data = subprocess.run(["git", "-C", repo, "archive", "--format=tar", sha], capture_output=True,
                          check=True).stdout
    tar_path = os.path.join(dest, "snap.tar")
    with open(tar_path, "wb") as fh:
        fh.write(data)
    root = os.path.join(dest, "tree")
    os.makedirs(root)
    with tarfile.open(tar_path) as tf:
        tf.extractall(root, filter="data")
    return root


def short_mention(m: str) -> str:
    """Traceback mentions keep only the last two path parts (issue authors' local paths are dropped)."""
    if not m.startswith("frame:"):
        return m
    path, line, func = m[6:].rsplit(":", 2)
    return "frame:" + "/".join(path.replace("\\", "/").split("/")[-2:]) + f":{line}:{func}"


def run_task(repo, cand, issue):
    with tempfile.TemporaryDirectory() as tmp:
        root = snapshot(repo, cand["parent"], tmp)
        files, finfo = ex.select_files(root)
        g = ex.extract(root, files=files, file_info=finfo)
        nodes = g["nodes"]
        ids = [n["id"] for n in nodes]
        mod_of_path = {n["path"]: n["module"] for n in nodes}

        def read(path):
            p = os.path.join(root, path)
            if not os.path.isfile(p):
                return None
            with open(p, encoding="utf-8", errors="replace") as fh:
                return fh.read()

        patch = git(repo, "diff", cand["parent"], cand["sha"], "--", "*.py")
        gold = lz.gold_functions(patch, read, mod_of_path.get, ids)
        docs = lz.function_documents(nodes, read)
        query = issue["title"] + "\n" + issue["body"]
        scores = lz.BM25(docs).scores(query)
        pool = lz.candidate_pool(scores, gold["gold"])
        nb = lz.undirected_neighbours(ex.mirrored(g)["links"])
        anchors = lz.find_anchors(query, lz.NodeIndex(nodes), lambda n: len(nb.get(n, ())))
        anchor_nodes = [a["node"] for a in anchors["anchors"]]
        return {
            "sha": cand["sha"], "date": cand["date"], "issue": issue["number"], "subject": cand["subject"],
            "n_nodes": len(nodes), "n_edges": len(g["links"]),
            "gold": gold["gold"], "gold_files": gold["files"],
            "pool": pool["pool"], "injected": pool["injected"], "gold_ranks": pool["gold_ranks"],
            "anchors": [dict(a, mention=short_mention(a["mention"])) for a in anchors["anchors"]],
            "ambiguous": [short_mention(m) for m in anchors["ambiguous"]],
            "too_connected": anchors["too_connected"],
            "anchored": bool(anchor_nodes),
            "stratum": lz.stratum(anchor_nodes, gold["gold"], lambda n: nb.get(n, ())),
        }


def summarise(rows):
    usable = [r for r in rows if r["gold"]]
    n = len(usable)
    if not n:
        return {"tasks": len(rows), "with_gold": 0}
    best_rank = [min(r["gold_ranks"].values()) for r in usable if r["gold_ranks"]]
    return {
        "tasks": len(rows),
        "with_gold": n,
        "gold_in_top10_share": sum(not r["injected"] for r in usable) / n,
        "gold_top1_share": sum(b == 1 for b in best_rank) / n,
        "median_best_gold_rank": sorted(best_rank)[len(best_rank) // 2] if best_rank else None,
        "anchored_share": sum(r["anchored"] for r in usable) / n,
        "strata": dict(sorted(Counter(r["stratum"] for r in usable).items())),
        "anchored_strata": dict(sorted(Counter(r["stratum"] for r in usable if r["anchored"]).items())),
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--repo-dir", required=True)
    ap.add_argument("--gh-repo", required=True, help="owner/name on GitHub, for the issue texts")
    ap.add_argument("--since", default="2017-06-01")
    ap.add_argument("--issues-cache", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--max", type=int, default=0, help="stop after this many tasks (0 = all)")
    args = ap.parse_args(argv)
    for path in (args.out, args.issues_cache):  # a fresh copy has no runs/ folder
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)

    cache = {}
    if os.path.exists(args.issues_cache):
        with open(args.issues_cache) as fh:
            cache = json.load(fh)
    rows, skipped = [], Counter()
    for cand in candidate_commits(args.repo_dir, args.since):
        issue = None
        for num in cand["issues"]:
            if num not in cache:
                cache[num] = fetch_issue(args.gh_repo, num)
            if cache[num] and "error" not in cache[num]:
                issue = cache[num]
                break
        if issue is None:
            skipped["no issue found (pull request number or missing)"] += 1
            continue
        try:
            rows.append(run_task(args.repo_dir, cand, issue))
        except Exception as exc:  # report and continue: this is a dry run
            skipped[f"{type(exc).__name__}"] += 1
            print(f"{cand['sha'][:8]}: {type(exc).__name__}: {exc}", file=sys.stderr)
        if args.max and len(rows) >= args.max:
            break
    with open(args.issues_cache, "w") as fh:
        json.dump(cache, fh, indent=1)
    summary = summarise(rows)
    summary["skipped"] = dict(skipped)
    with open(args.out, "w") as fh:
        json.dump({"summary": summary, "tasks": rows}, fh, indent=1)
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
