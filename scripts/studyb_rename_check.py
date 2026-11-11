"""Check the Study B opaque renamer on real public issues and code (no competition data needed).

For one repository snapshot: collect project names, build the renamer (seed 1), rename every cached
issue (title + body, as fetched by studyb_history_check.py) and the source of every graph node
function, and run the leak scan on all of it. Writes a JSON report with counts and leak examples;
with --examples it also writes a few original/renamed pairs for eyeballing (keep these private:
they contain issue text).

Example:
  python scripts/studyb_rename_check.py --repo-dir repos/requests --repo requests --org psf \
      --issues-cache runs/requests_issues.json --out runs/requests_rename_check.json
"""

import argparse
import json
import os
import random
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from ngraph import extract as ex  # noqa: E402
from ngraph import rename as rn  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--repo-dir", required=True)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--org")
    ap.add_argument("--extra-identity", default="", help="comma-separated names to scrub (e.g. maintainers)")
    ap.add_argument("--issues-cache", required=True)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--out", required=True)
    ap.add_argument("--examples", help="write a few original/renamed pairs here")
    args = ap.parse_args(argv)
    for path in (args.out, args.examples):  # a fresh copy has no runs/ folder
        if path:
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)

    t0 = time.time()
    extra = [x.strip() for x in args.extra_identity.split(",") if x.strip()]
    names = rn.collect_names(args.repo_dir, repo=args.repo, org=args.org, extra_identity=extra)
    r = rn.OpaqueRenamer(names, seed=args.seed)
    build_secs = time.time() - t0
    with open(args.issues_cache) as fh:
        issues = [v for v in json.load(fh).values() if v and "error" not in v]

    def tally(kind, texts, render):
        agg = {"n": 0, "hard_texts": 0, "hard": {}, "soft": {}, "residual_identity": {}, "share_changed": []}
        pairs = []
        for t in texts:
            res = render(t)
            scan = r.leak_scan(res.text)
            agg["n"] += 1
            agg["share_changed"].append(res.share_changed)
            agg["hard_texts"] += not scan["ok"]
            for key in ("hard", "soft", "residual_identity"):
                for w, c in scan[key].items():
                    agg[key][w] = agg[key].get(w, 0) + c
            pairs.append((t, res.text))
        sc = sorted(agg["share_changed"])
        agg["share_changed"] = {"median": sc[len(sc) // 2] if sc else None, "max": sc[-1] if sc else None}
        for key in ("hard", "soft", "residual_identity"):
            agg[key] = dict(sorted(agg[key].items(), key=lambda kv: -kv[1])[:25])
        return agg, pairs

    issue_texts = [i["title"] + "\n\n" + i["body"] for i in issues]
    issue_rep, issue_pairs = tally("issue", issue_texts, r.rename_issue)
    files, finfo = ex.select_files(args.repo_dir)
    g = ex.extract(args.repo_dir, files=files, file_info=finfo)
    code_texts = []
    for n in g["nodes"]:
        with open(os.path.join(args.repo_dir, n["path"]), encoding="utf-8", errors="replace") as fh:
            lines = fh.read().splitlines()
        code_texts.append("\n".join(lines[n["lineno"] - 1: n["end_lineno"]]))
    code_rep, code_pairs = tally("code", code_texts, r.rename_code)
    report = {
        "repo": args.repo, "seed": args.seed, "build_secs": round(build_secs, 2),
        "names_defined": len(names.defined), "names_renamed": len(r.map),
        "third_party_names": len(names.third_party), "packages": names.packages, "identity": names.identity,
        "fallback_subtokens": len(r.namer.fallback), "parse_errors": len(names.parse_errors),
        "issues": issue_rep, "code": code_rep,
    }
    with open(args.out, "w") as fh:
        json.dump(report, fh, indent=1)
    if args.examples:
        rng = random.Random(0)
        ex_pairs = rng.sample(issue_pairs, min(3, len(issue_pairs))) + rng.sample(code_pairs, min(2, len(code_pairs)))
        with open(args.examples, "w") as fh:
            for a, b in ex_pairs:
                fh.write("=" * 30 + " ORIGINAL\n" + a[:3000] + "\n" + "-" * 30 + " RENAMED\n" + b[:3000] + "\n")
    print(json.dumps({k: report[k] for k in ("repo", "build_secs", "names_defined", "names_renamed",
                                             "fallback_subtokens")}),
          "| issues: n", issue_rep["n"], "with hard leaks", issue_rep["hard_texts"], "share", issue_rep["share_changed"],
          "| code: n", code_rep["n"], "with hard leaks", code_rep["hard_texts"], "share", code_rep["share_changed"])


if __name__ == "__main__":
    main()
