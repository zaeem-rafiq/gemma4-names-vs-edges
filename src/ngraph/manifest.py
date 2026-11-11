"""Build repos_manifest.json (group, role, pinned commit, licence) from the screening logs.

Roles follow the registered order. Within each group, repositories that pass the screen are
taken in list order (familiar: the planned list, then reserves by GitHub stars; fresh: the frozen
candidate list by stars). The first 16 are confirmatory, the next one is the pilot, and the rest
are reserves, used in order if a confirmatory repository has to be dropped. A fresh repository
that passed the automatic screen but has no README decision is 'unreviewed' and is not used.

Licences: `license_spdx` is what the GitHub API reported when queried (current licence of the
repository, not necessarily the licence at the pinned commit); `license_file_head` is the start
of the LICENSE file at the pinned commit, which is the record that matters for release.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time

KEEP = ("url", "commit", "commit_date", "license_file", "py_files", "py_lines", "py_defs", "kept_groups",
        "nodes", "edges", "flags", "stars", "created_at", "license", "earliest_commit_date", "old_header_share",
        "full_name")


def _jsonl(path):
    with open(path) as fh:
        return [json.loads(x) for x in fh if x.strip()]


def _sha(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def _assign(rows, group, n_conf, meta=None):
    out, k = [], 0
    for r in rows:
        if r["status"] == "needs_review":
            role = "unreviewed"
        elif r["status"] != "passed":
            continue
        else:
            role = "confirmatory" if k < n_conf else ("pilot" if k == n_conf else "reserve")
            k += 1
        e = {"label": r["label"], "group": group, "role": role}
        e.update({x: r[x] for x in KEEP if x in r})
        if "license_file" in e:
            e["license_file_head"] = e.pop("license_file")
        if "license" in e:
            e["license_spdx"] = e.pop("license")
        if meta is not None:
            m = meta.get(e["url"].rstrip("/").removesuffix(".git").split("github.com/")[1].lower())
            if m:
                e["full_name"] = m["full_name"]
                e["license_spdx"] = m.get("license")
                e["stars"] = m.get("stars")
                e["created_at"] = m.get("created_at")
                e["github_queried_at"] = m.get("queried_at")
                if m.get("note"):
                    e["note"] = m["note"]
        out.append(e)
    return out


def build(familiar_log, fresh_log, familiar_meta=None, n_conf=16) -> dict:
    meta = None
    if familiar_meta:
        meta = {}
        for m in _jsonl(familiar_meta):
            meta[m["full_name"].lower()] = m
            if m.get("requested"):
                meta[m["requested"].lower()] = m
    repos = _assign(_jsonl(familiar_log), "familiar", n_conf, meta) + _assign(_jsonl(fresh_log), "fresh", n_conf)
    counts = {}
    for r in repos:
        counts.setdefault(r["group"], {}).setdefault(r["role"], 0)
        counts[r["group"]][r["role"]] += 1
    return {"built_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "rule": "per group, passing repositories in list order: first 16 confirmatory, next one pilot, rest reserves",
            "sources": {"familiar_log": {"file": familiar_log, "sha256": _sha(familiar_log)},
                        "fresh_log": {"file": fresh_log, "sha256": _sha(fresh_log)},
                        "familiar_github_meta": ({"file": familiar_meta, "sha256": _sha(familiar_meta)}
                                                 if familiar_meta else None)},
            "counts": counts, "repos": repos}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--familiar-log", required=True)
    ap.add_argument("--fresh-log", required=True)
    ap.add_argument("--familiar-meta")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    man = build(a.familiar_log, a.fresh_log, a.familiar_meta)
    with open(a.out, "w") as fh:
        json.dump(man, fh, indent=1, ensure_ascii=False)
    print(json.dumps(man["counts"]))
    for g in ("familiar", "fresh"):
        for role in ("confirmatory", "pilot", "reserve", "unreviewed"):
            names = [r["label"] for r in man["repos"] if r["group"] == g and r["role"] == role]
            if names:
                print(f"{g} {role}: {', '.join(names)}")


if __name__ == "__main__":
    main()
