"""Study B on SWE-bench Lite: tasks, our official-like graphs and snapshots from local clones.

* Tasks: the SWE-bench Lite test split without psf/requests tasks (requests is a competition
  repository), and the dev split as tuning tasks (role "tune": B5's lambda and the Study B pilot; never
  in a confirmatory analysis). Read from JSON Lines files with the SWE-bench fields (instance_id, repo,
  base_commit, patch, problem_statement, ...).
* Snapshot: `git archive <base_commit>` of a local clone of the task's repository, extracted with the
  "data" filter into a temporary folder. Nothing from the repository is executed: files are parsed
  with `ast`.
* Graph: ngraph.extract on the main package (select_files), in the official-like view (every edge
  mirrored, one "calls" type; extract.mirrored). Library functions are the graph's nodes (functions
  and methods of the selected files); unlike the official graphs, ours has no class nodes and no test
  nodes. The rewired copy is made from this view exactly as for the official graphs.
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import subprocess
import tarfile
import tempfile

from ngraph import extract as ex

EXCLUDED_REPOS = ("psf/requests",)


def load_jsonl(path: str) -> list[dict]:
    out = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                out.append(json.loads(line))
    return out


def clone_dir(repos_dir: str, repo: str) -> str:
    """Local clone of owner/name: <repos_dir>/<owner>__<name>."""
    return os.path.join(repos_dir, repo.replace("/", "__"))


def snapshot(repo_dir: str, sha: str, dest: str) -> str:
    data = subprocess.run(["git", "-C", repo_dir, "archive", "--format=tar", sha], capture_output=True,
                          check=True).stdout
    root = os.path.join(dest, "tree")
    os.makedirs(root)
    with tarfile.open(fileobj=io.BytesIO(data)) as tf:
        tf.extractall(root, filter="data")
    return root


class ExtractorIndex:
    """The SnapshotIndex interface (read, module_of, source, node, stats) over our extractor's graph."""

    def __init__(self, root: str, graph: dict):
        self.root = root
        self.node = {n["id"]: {"path": n["path"], "lineno": n["lineno"], "end_lineno": n["end_lineno"],
                               "kind": "function", "module": n["module"]} for n in graph["nodes"]}
        self.module = {n["path"]: n["module"] for n in graph["nodes"]}
        self._lines = {}
        self.merged = 0
        # Spans as official.SnapshotIndex makes them: from the first decorator, and one span from the first
        # to the last definition when a file defines the same name more than once (property getter and
        # setter, @overload stubs, if/else variants).
        from ngraph.official import local_spans

        for rel, mod in sorted(self.module.items()):
            try:
                spans = local_spans(self.read(rel) or "")
            except (SyntaxError, ValueError):
                continue
            seen = {}
            for name, a, b, kind in spans:
                qn = f"{mod}.{name}"
                r = self.node.get(qn)
                if r is None or kind != "function" or r["path"] != rel:
                    continue
                if qn not in seen:
                    seen[qn] = 1
                    r["lineno"], r["end_lineno"] = a, b
                else:
                    seen[qn] += 1
                    r["lineno"], r["end_lineno"] = min(r["lineno"], a), max(r["end_lineno"], b)
            self.merged += sum(v > 1 for v in seen.values())

    def read(self, rel: str) -> str | None:
        from ngraph.official import read_text

        return read_text(os.path.join(self.root, rel))

    def module_of(self, rel: str) -> str | None:
        return self.module.get(rel)

    def source(self, nid: str) -> str:
        r = self.node[nid]
        if r["path"] not in self._lines:
            txt = self.read(r["path"])
            from ngraph.official import source_lines

            self._lines[r["path"]] = source_lines(txt) if txt is not None else []
        return "\n".join(self._lines[r["path"]][r["lineno"] - 1: r["end_lineno"]])

    def stats(self, node_ids) -> dict:
        ids = list(node_ids)
        return {"files": len(self.module), "nodes_located": sum(i in self.node for i in ids), "nodes": len(ids)}


class LiteSource:
    """Same interface as studyb.OfficialSource, for SWE-bench Lite."""

    def __init__(self, test_jsonl: str, repos_dir: str, dev_jsonl: str | None = None):
        self.repos_dir = repos_dir
        self.tasks, self.roles = {}, {}
        for path, role in ((test_jsonl, "confirmatory"), (dev_jsonl, "tune")):
            if not path:
                continue
            for t in load_jsonl(path):
                if t["repo"] in EXCLUDED_REPOS:
                    continue
                self.tasks[t["instance_id"]] = t
                self.roles[t["instance_id"]] = role
        self.graphs, self.reports = {}, {}

    def task_context(self, tid: str):
        from ngraph import rename as rn
        from ngraph.studyb import _rewire

        t = self.tasks[tid]

        @contextlib.contextmanager
        def ctx():
            with tempfile.TemporaryDirectory() as tmp:
                root = snapshot(clone_dir(self.repos_dir, t["repo"]), t["base_commit"], tmp)
                gname = f"{t['repo'].replace('/', '__')}_{t['base_commit']}"
                files, finfo = ex.select_files(root)
                g = ex.mirrored(ex.extract(root, files=files, file_info=finfo))
                edges = [(e["source"], e["target"], e.get("type", "calls")) for e in g["links"]]
                graph = {"name": gname, "nodes": {n["id"]: "" for n in g["nodes"]}, "edges": edges}
                if gname not in self.graphs:
                    rew, rep = _rewire(edges)
                    self.graphs[gname] = rew
                    self.reports[gname] = {"stats": {"nodes": len(g["nodes"]), "edges": len(edges),
                                                     "extractor_version": ex.EXTRACTOR_VERSION,
                                                     "file_selection": finfo}, "rewired": rep}
                index = ExtractorIndex(root, g)
                if gname + "#within_module" not in self.graphs:
                    mod = {n: index.node[n]["module"] for n in index.node}
                    wm, wrep = _rewire(edges, kind_of=mod.get)
                    self.graphs[gname + "#within_module"] = wm
                    self.reports[gname]["within_module"] = {k: wrep[k] for k in (
                        "engine", "nswap", "swaps_done", "completed", "edge_overlap", "invariants",
                        "same_group_share")}
                names = self.repo_names(t["repo"])
                yield {"task": t, "gname": gname, "graph": graph, "rewired": self.graphs[gname], "index": index,
                       "lib_ids": sorted(index.node), "finfo": finfo, "skipped": {}, "names": names,
                       "renamer": lambda: self.renamer(t["repo"]), "role": self.roles[tid]}
        return ctx()

    def _snapshot_names(self, tid: str):
        from ngraph import rename as rn

        t = self.tasks[tid]
        owner, name = t["repo"].split("/")
        with tempfile.TemporaryDirectory() as tmp:
            root = snapshot(clone_dir(self.repos_dir, t["repo"]), t["base_commit"], tmp)
            return rn.collect_names(root, repo=name, org=owner)

    def repo_names(self, repo: str):
        """ProjectNames of a repository: the union over the snapshots of all its tasks (cached; the
        snapshots of tasks that share a base commit are read once)."""
        from ngraph.studyb import merge_names

        if not hasattr(self, "_names"):
            self._names = {}
        if repo not in self._names:
            by_commit = {}
            for i in sorted(self.tasks):
                if self.tasks[i]["repo"] == repo:
                    by_commit.setdefault(self.tasks[i]["base_commit"], i)
            self._names[repo] = merge_names([self._snapshot_names(i) for _, i in sorted(by_commit.items())])
        return self._names[repo]

    def renamer(self, repo: str):
        from ngraph import rename as rn

        if not hasattr(self, "_renamers"):
            self._renamers = {}
        if repo not in self._renamers:
            self._renamers[repo] = rn.OpaqueRenamer(self.repo_names(repo), seed=1)
        return self._renamers[repo]

    def within_module(self, gname: str, index):
        """Within-module null (exploratory): rewiring only between edges that join the same module pair."""
        from ngraph.studyb import _rewire

        key = gname + "#within_module"
        if key not in self.graphs:
            raise KeyError(f"{gname}: call task_context first")
        return self.graphs[key]
