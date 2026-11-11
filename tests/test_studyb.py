"""Tests for Study B on the official format: adapter, task records, prompts, runs and the report."""

import io
import json
import os
import tarfile

import numpy as np
import pandas as pd
import pytest

from ngraph import official as of
from ngraph import studyb as sb
from ngraph import studyb_report as sr

CORE = '''import os


def helper(x):
    return x + 1


class Session:
    """A session object."""

    def send(self, request_payload):
        data = helper(request_payload)
        return self.finish_send(data)

    def finish_send(self, data):
        return data


def merge_settings(request_setting, session_setting):
    if session_setting is None:
        return request_setting
    return session_setting
'''

UTIL = '''from .core import helper


def parse_header_links(value):
    return helper(len(value))


def unrelated_thing():
    return 3
'''

DOC = '''def tutorial_main():
    return 1
'''

TEST = '''def test_send():
    assert True
'''

PATCH = '''diff --git a/mypkg/core.py b/mypkg/core.py
--- a/mypkg/core.py
+++ b/mypkg/core.py
@@ -19,6 +19,6 @@ def merge_settings(request_setting, session_setting):
 def merge_settings(request_setting, session_setting):
     if session_setting is None:
-        return request_setting
+        return dict(request_setting)
     return session_setting
'''

ISSUE = ("merge_settings drops the request setting\n\nWhen I call `Session.send` the merged settings "
         "from merge_settings are wrong. The session_setting None case returns the same object.\n")

FILES = {"mypkg/__init__.py": "", "mypkg/core.py": CORE, "mypkg/util.py": UTIL,
         "docs_src/tut/__init__.py": "", "docs_src/tut/main.py": DOC, "tests/__init__.py": "",
         "tests/test_core.py": TEST, "pyproject.toml": "[project]\nname='mypkg'\n"}

NODES = ["mypkg.core.helper", "mypkg.core.Session", "mypkg.core.Session.send", "mypkg.core.Session.finish_send",
         "mypkg.core.merge_settings", "mypkg.util.parse_header_links", "mypkg.util.unrelated_thing",
         "tut.main.tutorial_main", "tests.test_core.test_send"]
EDGES = [("mypkg.core.Session.send", "mypkg.core.helper"), ("mypkg.core.Session.send", "mypkg.core.Session.finish_send"),
         ("mypkg.core.Session", "mypkg.core.Session.send"), ("mypkg.core.Session", "mypkg.core.Session.finish_send"),
         ("mypkg.util.parse_header_links", "mypkg.core.helper"), ("tests.test_core.test_send", "mypkg.core.Session.send")]


def _tgz(path, files, extra=()):
    with tarfile.open(path, "w:gz") as tf:
        for rel, txt in files.items():
            b = txt.encode()
            ti = tarfile.TarInfo("./" + rel)
            ti.size = len(b)
            tf.addfile(ti, io.BytesIO(b))
        for ti, b in extra:
            tf.addfile(ti, io.BytesIO(b) if b is not None else None)


@pytest.fixture
def data(tmp_path):
    d = tmp_path / "comp"
    (d / "graphs").mkdir(parents=True)
    (d / "snapshots").mkdir()
    sha = "a" * 40
    task = {"instance_id": "mypkg_7", "repo": "someorg/mypkg", "base_commit": sha, "patch": PATCH,
            "test_patch": "", "problem_statement": ISSUE, "hints_text": "", "created_at": "2025-01-01T00:00:00Z"}
    (d / "tasks.jsonl").write_text(json.dumps(task) + "\n")
    pairs = set(EDGES) | {(b, a) for a, b in EDGES}
    g = {"directed": True, "multigraph": True, "graph": {"repo_name": f"mypkg_{sha}"},
         "nodes": [{"name": n, "text": "def ...", "id": n} for n in NODES],
         "edges": [{"type": "calls", "source": a, "target": b, "key": 0} for a, b in sorted(pairs)]
         + [{"type": "calls", "source": NODES[0], "target": NODES[0], "key": 0},
            {"type": "calls", "source": NODES[0], "target": NODES[0], "key": 1}]}
    (d / "graphs" / f"mypkg_{sha}.json").write_text(json.dumps(g))
    git = tarfile.TarInfo("./.git/config")
    git.size = 3
    link = tarfile.TarInfo("./mypkg/evil.py")
    link.type = tarfile.SYMTYPE
    link.linkname = "/etc/passwd"
    up = tarfile.TarInfo("./../outside.py")
    up.size = 1
    _tgz(d / "snapshots" / "mypkg_7.tgz", FILES, [(git, b"abc"), (link, None), (up, b"x")])
    return d


def test_load_graph_dedups_and_detects_mirroring(data):
    g = of.load_graph(str(next((data / "graphs").iterdir())))
    assert g["stats"]["mirrored"] is True
    assert g["stats"]["self_loops"] == 1 and g["stats"]["duplicate_edges_dropped"] == 1
    assert g["stats"]["edge_types"] == ["calls"]
    assert set(g["nodes"]) == set(NODES)


def test_snapshot_reader_skips_unsafe_members(data):
    files, skipped = of.read_snapshot_py(str(data / "snapshots" / "mypkg_7.tgz"))
    assert "mypkg/core.py" in files and "pyproject.toml" in files
    assert not any(k.startswith(".git") for k in files)
    assert "mypkg/evil.py" not in files and not any(".." in k for k in files)
    assert skipped["not a safe regular file"] >= 2


def test_index_maps_ids_with_dropped_source_root(data, tmp_path):
    files, _ = of.read_snapshot_py(str(data / "snapshots" / "mypkg_7.tgz"))
    root = tmp_path / "tree"
    of.write_tree(files, str(root))
    idx = of.SnapshotIndex(str(root), NODES)
    assert idx.module_of("mypkg/core.py") == "mypkg.core"
    assert idx.module_of("docs_src/tut/main.py") == "tut.main"  # source root dropped, as in the official graphs
    assert idx.node["mypkg.core.Session"]["kind"] == "class"
    assert idx.node["mypkg.core.Session.send"]["kind"] == "function"
    assert "return self.finish_send(data)" in idx.source("mypkg.core.Session.send")
    lib = of.library_functions(idx, of.library_files(str(root))[0])
    assert "mypkg.core.merge_settings" in lib and "mypkg.core.Session" not in lib
    assert "tut.main.tutorial_main" not in lib and "tests.test_core.test_send" not in lib


def test_orders_are_reverses():
    o = sb.candidate_orders("t_1", list("abcdefghij"))
    assert o[2] == list(reversed(o[1])) and sorted(o[1]) == list("abcdefghij")
    assert sb.candidate_orders("t_1", list("abcdefghij")) == o


def test_cap_list_keeps_whole_items():
    items = ["x" * 40] * 200
    kept, cut = sb._cap_list(items, 500)
    assert cut and len(json.dumps(kept)) <= 500 and len(json.dumps(kept + ["x" * 40])) > 500


def test_subgraph_and_neighbours():
    edges = [("a", "b", "calls"), ("b", "a", "calls"), ("b", "c", "calls"), ("c", "b", "calls"), ("a", "a", "calls")]
    ctx = sb.graph_context(["a"], ["c", "b", "a"], edges)
    assert ctx["subgraph"]["nodes"] == ["a", "c", "b"]
    assert ctx["subgraph"]["edges"] == sorted([("a", "a"), ("a", "b"), ("b", "a"), ("b", "c"), ("c", "b")])
    assert ctx["neighbors"]["neighbors"] == ["b"]
    assert sb.graph_context([], ["a"], edges).get("neighbors") is None
    assert sb.anchor_adjacent(["a"], ["b", "c"], edges) == ["b"]


def test_cut_line():
    assert sb.cut_line("x" * 10) == "x" * 10
    long = "alpha beta " * 40
    out = sb.cut_line(long, 50)
    assert out.endswith(" ...") and len(out) <= 54


@pytest.fixture
def built(data):
    src = sb.OfficialSource(str(data))
    count = lambda t: len(t.split())  # noqa: E731
    return src, sb.build_records(src, "official", count, log=lambda s: None)


def test_build_record(built):
    src, res = built
    (rec,) = res["records"]
    assert rec["eligible"] and rec["gold"] == ["mypkg.core.merge_settings"]
    assert rec["gold"][0] in rec["pool"] and not rec["injected"]
    assert len(rec["pool"]) == 6  # only six library functions exist here
    assert [a["node"] for a in rec["anchors"]][:2] == ["mypkg.core.merge_settings", "mypkg.core.Session.send"]
    assert rec["stratum"] == "S0" and rec["anchored"]
    assert set(rec["prompt_sha256"]) == {f"{n}/{g}/{o}" for n in sb.NAMINGS for g in sb.GRAPHS for o in sb.ORDERS} | {
        "opaque/within_module/1", "opaque/within_module/2"}
    assert rec["hard_leaks"] == {}
    gold_letters = rec["correct_letters"]
    assert len(gold_letters[1]) == 1 and len(gold_letters[2]) == 1


def test_prompts_render_and_rename(built, data):
    src, res = built
    rec = json.loads(json.dumps(res["records"][0]))
    rec["orders"] = {int(k): v for k, v in rec["orders"].items()}
    with src.task_context("mypkg_7") as c:
        p = sb.render_fixed(rec, c["task"], c["index"], c["renamer"](), None, sb.CODE_LINES)
    real = p[("real", "true", 1)]
    opaque = p[("opaque", "true", 1)]
    assert "merge_settings" in real and "merge_settings" not in opaque
    assert '"status": "ok"' in opaque and '"type": "calls"' in opaque
    assert "get_code_subgraph" in opaque  # tool names are not renamed
    assert "Tool output:" not in p[("real", "none", 1)] and "Tool output:" in real
    assert "Signature: merge_settings(" in real and "Signature: merge_settings(" not in opaque
    assert real.endswith(sb.QUESTION)


def test_render_cuts_issue_to_fit(built):
    src, res = built
    rec = json.loads(json.dumps(res["records"][0]))
    rec["orders"] = {int(k): v for k, v in rec["orders"].items()}
    with src.task_context("mypkg_7") as c:
        t = dict(c["task"], problem_statement=ISSUE + " filler words" * 400)
        r = c["renamer"]()
        count = lambda s: len(s.split())  # noqa: E731
        full = sb.render_task(rec, t, c["index"], r, count, budget=10 ** 6)
        budget = full["meta"]["max_tokens"] - 300
        cut = sb.render_task(rec, t, c["index"], r, count, budget=budget)
    assert cut["meta"]["cut_at"] is not None and cut["meta"]["max_tokens"] <= budget
    assert all(x.count(sb.CUT_MARK) == 1 for x in cut["prompts"].values())


def test_jobs_refuse_changed_prompts(built):
    src, res = built
    d = json.loads(json.dumps({"tasks": res["records"]}))
    for r in d["tasks"]:
        r["orders"] = {int(k): v for k, v in r["orders"].items()}
        r["correct_letters"] = {int(k): v for k, v in r["correct_letters"].items()}
    jobs = sb.study_b_jobs(src, d["tasks"], sb.CELLS["confirmatory"], log=lambda s: None)
    assert len(jobs) == 12 and {j["version"] for j in jobs} == {f"{n}/{g}" for n in sb.NAMINGS for g in sb.GRAPHS}
    d["tasks"][0]["prompt_sha256"]["real/none/1"] = "0" * 64
    with pytest.raises(SystemExit):
        sb.study_b_jobs(src, d["tasks"], sb.CELLS["confirmatory"], log=lambda s: None)


def test_b5_pick_and_lambda():
    rec = {"pool": ["a", "b", "c"], "bm25_pool_scores": {"a": 10.0, "b": 9.0, "c": 1.0}, "gold": ["b"],
           "b5_anchor_neighbours": {"true": ["b"], "rewired": ["c"]}, "eligible": True, "anchored": True}
    assert sb is not None
    assert sr.b5_pick(rec, 0.0, "true") == 0
    assert sr.b5_pick(rec, 0.2, "true") == 1  # 0.9 + 0.2 > 1.0
    assert sr.b5_pick(rec, 0.2, "rewired") == 0
    lam = sr.b5_lambda([rec])
    assert lam["lambda"] == 0.2  # the smallest grid value that wins
    assert sr.b5_lambda([])["source"].startswith("default")


def test_anchored_share_rule():
    tf = {"tasks": [{"eligible": True, "anchored": True}, {"eligible": True, "anchored": False},
                    {"eligible": True, "anchored": False, "role": "tune"}, {"eligible": False}]}
    s = sr.anchored_share([tf])
    assert s["eligible_confirmatory"] == 2 and s["share"] == 0.5 and s["b2_confirmatory"]


def test_load_b_runs_scores(tmp_path):
    p = tmp_path / "run.jsonl"
    rows = [{"_header": {"study": "B", "model_tag": "E4B", "n_jobs": 1, "cells": "confirmatory", "tasks_sha256": "x"}}]
    logits = {f"logit_{L}": float(-i) for i, L in enumerate("ABCDEFGHIJ")}
    rows.append({"item_id": "t", "version": "real/none", "perm": 1, "set": "official", "repo": "r", "naming": "real",
                 "graph": "none", "order": 1, "anchored": True, "stratum": "S0", "injected": False,
                 "correct_letters": ["C"], "pred_letter": "A", "letter_mass": 0.95, **logits})
    p.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    df, rep = sr.load_b_runs([str(p)])
    assert df.loc[0, "correct"] == 0 and df.loc[0, "hit3"] == 1 and df.loc[0, "rr"] == pytest.approx(1 / 3)
    assert rep[str(p)]["complete"]

    with pytest.raises(SystemExit):
        sr.load_b_runs([str(p)], tasks_sha256={"y"})
    q = tmp_path / "run2.jsonl"
    q.write_text(p.read_text())
    with pytest.raises(SystemExit):  # the same row in two files
        sr.load_b_runs([str(p), str(q)])


def _rows(model, task, cell_a, cell_b):
    out = []
    for (n, g), acc in ((("real", "none"), cell_a), (("opaque", "none"), cell_b)):
        for o, c in zip((1, 2), acc):
            out.append({"model": model, "task_id": task, "set": "official", "repo": "r", "naming": n, "graph": g,
                        "order": o, "anchored": True, "correct": c})
    return out


def test_task_diffs_stay_within_model():
    from ngraph import analysis as an

    # E4B has both cells for t1 (diff 1); 31B has only the real cell for t1 and must not enter t1.
    rows = _rows("E4B", "t1", (1, 1), (0, 0)) + [r for r in _rows("31B", "t1", (0, 0), (0, 0)) if r["naming"] == "real"]
    rows += _rows("E4B", "t2", (1, 0), (1, 0)) + _rows("31B", "t2", (1, 1), (0, 0))
    j = an._task_diffs(pd.DataFrame(rows), {"naming": "real", "graph": "none"}, {"naming": "opaque", "graph": "none"})
    d = dict(zip(j["task_id"], j["diff"]))
    assert d == {"t1": 1.0, "t2": 0.5}


def test_holm_families_never_shrink():
    rows = []
    for i in range(6):
        rows += _rows("E4B", f"t{i}", (1, i % 2), (0, 0))
    df = pd.DataFrame(rows)
    df["role"], df["stratum"], df["injected"], df["hit3"], df["rr"] = "confirmatory", "S0", False, 1, 1.0
    df["letter_mass"], df["gold_pos"] = 0.95, 0
    df = pd.concat([df, df.assign(model="E2B")])  # an unregistered model is left out
    tf = {"tasks": [{"eligible": True, "anchored": False, "task_id": f"t{i}"} for i in range(6)]}
    res = sr.study_b_report(df, [tf], None, n_boot=200)
    assert res["descriptive_only"] == ["E2B/official"] and res["B1"]["n_tasks"] == 6
    assert set(res["B1_by_set"]) == set(res["B2_by_set"]) == set(res["B3_by_set"]) == {"official"}
    assert res["B1_by_set"]["official"]["n_tasks"] == 6
    assert res["large_model"] is None and "not_run" in res["B4"]
    assert "B4" in res["holm_missing"] and "A1" in res["holm_missing"]
    assert set(res["holm_confirmatory"]) == {"A1", "B1"}
    assert set(res["holm_secondary"]) == {"A2", "A3", "B2", "B3", "B4", "B5"}


def test_resume_refuses_other_tasks(tmp_path):
    p = tmp_path / "run.jsonl"
    h = {"study": "B", "tasks_sha256": "a", "set": "official", "cells": "confirmatory", "roles": "confirmatory"}
    p.write_text(json.dumps({"_header": h}) + "\n")
    sb.check_resume(str(p), dict(h))
    with pytest.raises(SystemExit):
        sb.check_resume(str(p), dict(h, tasks_sha256="b"))
    sb.check_resume(str(tmp_path / "new.jsonl"), dict(h, set="lite"))


def test_task_diffs_match_orders():
    from ngraph import analysis as an

    # pure position bias (order 1 right, order 2 wrong) and no naming effect; opaque order 2 missing
    rows = [r for r in _rows("E4B", "t1", (1, 0), (1, 0)) if not (r["naming"] == "opaque" and r["order"] == 2)]
    j = an._task_diffs(pd.DataFrame(rows), {"naming": "real", "graph": "none"}, {"naming": "opaque", "graph": "none"})
    assert list(j["diff"]) == [0.0]


def test_b3_keeps_models_apart():
    from ngraph import analysis as an

    rows = []
    for i in range(6):
        for n in ("real", "opaque"):
            for g, c in (("true", 1), ("rewired", 0)):
                for o in (1, 2):
                    rows.append({"model": "E4B", "task_id": f"t{i}", "set": "official", "repo": f"r{i}",
                                 "naming": n, "graph": g, "order": o, "anchored": True, "correct": c})
                    if n == "opaque":  # 31B has only the opaque graph cells, so it must not enter B3
                        rows.append({**rows[-1], "model": "31B", "correct": 1 if g == "true" else 0})
    rows[0]["correct"] = 0
    res = an.b3(pd.DataFrame(rows), n_boot=50, n_perm=50)
    e4b_only = an.b3(pd.DataFrame([r for r in rows if r["model"] == "E4B"]), n_boot=50, n_perm=50)
    assert res["estimate"] == pytest.approx(e4b_only["estimate"])


def test_registered_rows():
    df = pd.DataFrame([{"model": m, "set": s, "role": "confirmatory"} for m, s in
                       [("E4B", "official"), ("31B", "official"), ("12B", "official"), ("E4B", "lite"), ("31B", "lite")]])
    mask, large = sr.registered_rows(df)
    assert large == "31B" and list(mask) == [True, True, False, True, False]
    mask, large = sr.registered_rows(df[df["model"] != "31B"])
    assert large == "12B" and list(mask) == [True, True, True]


def test_signature_and_display_survive_column0_lines():
    src = '    def f(self, a, *, b=1):\n        x = """\ncol0\n"""\n        return a\n'
    assert sb.signature(src, "m.C.f") == "f(self, a, *, b)"
    assert sb.display_code(src).splitlines()[0] == "def f(self, a, *, b=1):"
    merged = "    @property\n    def v(self):\n        return 1\n\n    @v.setter\n    def v(self, x):\n        pass\n"
    assert sb.signature(merged, "m.C.v") == "v(self)"


def test_lite_index_spans_match_official(tmp_path):
    from ngraph import extract as ex
    from ngraph import lite

    pkg = tmp_path / "mypkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "m.py").write_text("import functools\n\n\nclass C:\n    @property\n    def v(self):\n        return 1\n\n"
                              "    @v.setter\n    def v(self, x):\n        self._v = x\n\n\n"
                              "@functools.lru_cache()\ndef g(a):\n    return C().v + a\n")
    files, finfo = ex.select_files(str(tmp_path))
    gr = ex.mirrored(ex.extract(str(tmp_path), files=files, file_info=finfo))
    idx = lite.ExtractorIndex(str(tmp_path), gr)
    off = of.SnapshotIndex(str(tmp_path), list(idx.node))
    for nid in idx.node:
        assert idx.source(nid) == off.source(nid), nid
    assert idx.source("mypkg.m.g").startswith("@functools.lru_cache()")


def test_url_scrub_uses_whole_words():
    from ngraph import rename as rn

    r = rn.OpaqueRenamer(rn.ProjectNames(identity=["encode", "httpx"]), seed=1)
    keep = "see https://docs.python.org/3/library/urllib.parse.html#urllib.parse.urlencode here"
    assert "urlencode" in r.rename_issue(keep).text
    assert "<url>" in r.rename_issue("see https://github.com/encode/httpx here").text


def test_collect_names_skips_hidden_folders(tmp_path):
    from ngraph import rename as rn

    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "__init__.py").write_text("def real_function():\n    pass\n")
    (tmp_path / ".circleci").mkdir()
    (tmp_path / ".circleci" / "fetch_logs.py").write_text("def tool_function():\n    pass\n")
    names = rn.collect_names(str(tmp_path), repo="proj", org="org")
    assert "" not in names.packages and "" not in names.identity and names.packages == ["pkg"]
    assert "real_function" in names.defined and "tool_function" not in names.defined
    rn.OpaqueRenamer(names, seed=1)  # no error


def test_namer_escapes_one_letter_collisions():
    import itertools
    import string

    from ngraph import rename as rn

    letters = string.ascii_lowercase
    taken = {a + "11" for a in letters} | {a + b + "11" for a, b in itertools.product(letters, repeat=2)}
    nm = rn.OpaqueNamer(1, reject=lambda w: False, taken_names=taken)
    nm.fit(["a11"])
    assert nm.map["a11"] not in taken and nm.map["a11"].endswith("11")


def test_handles_skip_decorators_and_dotted_names():
    from ngraph import rename as rn

    names = rn.ProjectNames(defined={n: ["function"] for n in ("user", "admin", "register", "unique", "Thing")},
                            packages=["mypkg"], identity=["mypkg"])
    r = rn.OpaqueRenamer(names, seed=1)
    for text in ("Use @admin.register(Thing) on the model.", "Add @enum.unique to the class.",
                 "The string '////]@N.AN' fails.", "@property\ndef f(): pass", "use the @property decorator",
                 "(M+N)@v", ">>> class A:\n...     @property\n...     def x(self): return 1"):
        out = r.rename_issue(text).text
        assert "@user" not in out, (text, out)
        assert not r.leak_scan(out)["hard"], (text, out)
    out = r.rename_issue("cc @someone please, thanks @other.").text
    assert out == "cc @user please, thanks @user.", out
    # one mention per line, mentions before prose that starts with a keyword-like word
    out = r.rename_issue("cc\n@alice\n@bob\nReported by @carol\nclass-based views fail").text
    assert out == "cc\n@user\n@user\nReported by @user\nclass-based views fail", out
    # "@" glued to a URL must not undo the URL scrub
    out = r.rename_issue("Docs are @https://github.com/mypkg/mypkg/issues/12 here").text
    assert "<url>" in out and not r.leak_scan(out)["hard"], out


def test_identity_tops_need_a_module_or_an_import(tmp_path):
    from ngraph import rename as rn

    def tops(layout):
        root = tmp_path / str(len(list(tmp_path.iterdir())))
        for rel, text in layout.items():
            (root / rel).parent.mkdir(parents=True, exist_ok=True)
            (root / rel).write_text(text)
        return rn.collect_names(str(root), repo="proj", org="org").packages

    # a namespace package (no __init__.py) that tests import is still the project's name
    assert tops({"acme/core.py": "def load_widget():\n    pass\n",
                 "tests/test_core.py": "from acme.core import load_widget\n"}) == ["acme"]
    # a package whose __init__.py sits one level deeper, imported with "import"
    assert tops({"acme/sub/__init__.py": "", "acme/core.py": "import acme.sub\n"}) == ["acme"]
    # a folder of scripts that nothing imports is not, even when a nested folder name ends with it
    assert tops({"bin/tool.py": "x = 1\n", "bin/cabin/__init__.py": "", "realpkg/__init__.py": ""}) == ["realpkg"]


def test_long_fallback_counts_rounds_not_names():
    from ngraph import rename as rn

    comps = [f"q{i}" for i in range(1, 9)]
    free = rn.OpaqueNamer(1, reject=lambda w: False)
    free.fit(comps)
    first = free.sub_map["q"]
    nm = rn.OpaqueNamer(1, reject=lambda w: False, taken_names={f"{first}{i}" for i in range(1, 9)})
    nm.fit(comps)
    assert len(nm.sub_map["q"]) == 1 and nm._redraws["q"] < rn.LONG_AFTER, (nm.sub_map, dict(nm._redraws))


def test_lib_folder_is_a_layout_prefix(tmp_path):
    from ngraph import extract as ex
    from ngraph import rename as rn

    root = tmp_path / "a"
    (root / "lib" / "pkg").mkdir(parents=True)
    (root / "lib" / "pkg" / "__init__.py").write_text("")
    (root / "lib" / "pkg" / "core.py").write_text("from pkg.util import helper\n\n\ndef run():\n    return helper()\n")
    (root / "lib" / "pkg" / "util.py").write_text("def helper():\n    return 1\n")
    files = ex.list_python_files(str(root))
    assert ex.strip_prefixes(str(root), files) == ("src", "lib")
    assert ex.module_name_for("lib/pkg/core.py", ex.strip_prefixes(str(root), files))[0] == "pkg.core"
    names = rn.collect_names(str(root), repo="proj", org="org")
    assert names.packages == ["pkg"] and "helper" in names.defined and "helper" not in names.third_party
    g = ex.extract(str(root), files=files)
    assert {"pkg.core.run", "pkg.util.helper"} <= {n["id"] for n in g["nodes"]}
    # a lib/ that is itself a package keeps its name
    other = tmp_path / "b"
    (other / "lib").mkdir(parents=True)
    (other / "lib" / "__init__.py").write_text("")
    (other / "lib" / "x").mkdir()
    (other / "lib" / "x" / "__init__.py").write_text("")
    assert "lib" not in ex.strip_prefixes(str(other), ex.list_python_files(str(other)))


def test_round2_review_cases(tmp_path):
    from ngraph import extract as ex
    from ngraph import rename as rn

    # a foreign module path that contains the project's name does not make it third-party
    (tmp_path / "proj").mkdir()
    (tmp_path / "proj" / "__init__.py").write_text("def line():\n    pass\n\n\ndef bad():\n    pass\n")
    (tmp_path / "proj" / "compat.py").write_text("from sage.interfaces.proj import init\n")
    names = rn.collect_names(str(tmp_path), repo="proj", org="encode")
    assert "proj" not in names.third_party
    r = rn.OpaqueRenamer(names, seed=1)
    out = r.rename_issue("The proj module fails. cc @encode @mark").text
    assert "proj" not in out and out.endswith("cc @user @user"), out
    # traceback frame words stay; handles on a ...Warning line are still handles
    tb = 'Traceback (most recent call last):\n  File "/x/y.py", line 12, in <module>\n    main()\n'
    assert r.rename_issue(tb).text.startswith('Traceback (most recent call last):\n  File "/x/y.py", line 12, in <module>')
    assert r.rename_issue("UserWarning is emitted since 3.8, cc @alice").text.endswith("cc @user")
    # lib/ holds two libraries: file selection keeps both (one group), module names drop lib/
    root = tmp_path / "m"
    for rel in ("lib/aa/__init__.py", "lib/aa/core.py", "lib/bb/__init__.py", "lib/bb/tool.py"):
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text("def f():\n    pass\n")
    files, info = ex.select_files(str(root))
    assert info["kept_groups"] == ["lib"] and len(files) == 4
    assert {"aa.core.f", "bb.tool.f"} <= {n["id"] for n in ex.extract(str(root), files=files)["nodes"]}


def test_local_example_packages_are_project_imports(tmp_path):
    from ngraph import rename as rn

    layout = {
        "proj/__init__.py": "def core():\n    pass\n",
        "examples/tutorial/flaskr/__init__.py": "def create_app():\n    pass\n",
        "examples/tutorial/tests/conftest.py": "from flaskr import create_app\n",
        "examples/celery/src/task_app/__init__.py": "from celery import Celery\n",
        "examples/celery/README.py": "x = 1\n",
    }
    for rel, text in layout.items():
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_text(text)
    names = rn.collect_names(str(tmp_path), repo="proj", org="org")
    assert "create_app" not in names.third_party and "flaskr" not in names.third_party
    assert "Celery" in names.third_party  # examples/celery is two levels above task_app: not a local root
    assert names.packages == ["proj"]
    r = rn.OpaqueRenamer(names, seed=1)
    tb = '  File "<frozen importlib._bootstrap>", line 1176, in _find_and_load\n'
    assert r.rename_issue(tb).text.startswith('  File "<frozen importlib._bootstrap>", line 1176')


def test_round4_leak_scan_and_common_word_packages(tmp_path):
    from ngraph import rename as rn

    layout = {
        "pylint/__init__.py": "def node_count(tree):\n    return 1\n\n\ndef run(ipython=None):\n    return node_count(ipython)\n",
        "pylint/console.py": "ipython = None\n",
        "script/__init__.py": "",
        "script/bump_changelog.py": "import pylint\n",
    }
    for rel, text in layout.items():
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_text(text)
    names = rn.collect_names(str(tmp_path), repo="pylint", org="pylint-dev")
    # a package named by a common word is not an identity word, but stays a renamable module name
    assert "script" not in names.identity and "pylint" in names.identity
    assert "script" in names.packages
    r = rn.OpaqueRenamer(names, seed=1)
    out = r.rename_issue("This script fails when pylint runs `script.bump_changelog`.").text
    assert out.startswith("This script fails when ") and "pylint" not in out and "bump_changelog" not in out, out
    # the fixed keys of the tool output are not leaks; a name left in a value still is
    ctx = {"subgraph": {"nodes": ["pylint.node_count", "pylint.run"], "edges": [["pylint.run", "pylint.node_count"]],
                        "is_truncated": False}, "n_anchors": 1, "n_candidates": 10,
           "neighbors": {"node": "pylint.run", "neighbors": ["pylint.node_count"], "is_truncated": False}}
    tool = sb.render_tool_output(ctx, lambda x: r.rename_code(x).text)
    assert "node_count" in r.leak_scan(tool)["hard"]
    assert r.leak_scan(sb.leak_text(tool))["ok"], r.leak_scan(sb.leak_text(tool))
    raw = sb.render_tool_output(ctx, lambda x: x)
    assert "node_count" in r.leak_scan(sb.leak_text(raw))["hard"]
    assert len(sb.leak_text(tool)) == len(tool)
    # a renamable name inside an interpreter-made frame file name is left alone and is not a hard leak ...
    tb = 'Traceback (most recent call last):\n  File "<ipython-input-3-ab12>", line 1, in <module>\n    run(ipython=1)\n'
    out = r.rename_issue(tb).text
    assert '"<ipython-input-3-ab12>"' in out and "run(" not in out and "ipython=1" not in out, out
    scan = r.leak_scan(out)
    assert scan["ok"] and scan["frame"] == {"ipython": 1}, scan
    # ... but an identity word there still is, and so is a name in any other "<...>" file name (doctest)
    assert not r.leak_scan('  File "<pylint-input>", line 1, in <module>\n')["ok"]
    out = r.rename_issue('Traceback (most recent call last):\n  File "<doctest pylint.run[0]>", line 1, in <module>\n'
                         '    run(1)\n').text
    assert r.leak_scan(out)["hard"].get("run") == 1, r.leak_scan(out)
    # a name that contains an identity word stays hard inside an interpreter-made file name too
    names.defined["pylint_ipython"] = ["module_variable"]
    r2 = rn.OpaqueRenamer(names, seed=1)
    assert r2.leak_scan('  File "<ipython-input-1-ab>", line 1, in <module>\n')["frame"] == {"ipython": 1}
    sc = r2.leak_scan('  File "<ipython-input-1-ab>", line 1, in <module>\n    pylint_ipython.x\n')
    assert "pylint_ipython" in sc["hard"], sc
    sc = r2.leak_scan('  File "<stdin>", line 1, in <module>\n')
    assert sc["ok"] and sc["frame"] == {}, sc
    # the hash tail of an IPython file name is scanned as usual
    names.defined["ecdf"] = ["function"]
    r3 = rn.OpaqueRenamer(names, seed=1)
    assert "ecdf" in r3.leak_scan('  File "<ipython-input-2-0ecdf>", line 1, in <module>\n')["hard"]


def test_short_top_level_names_are_not_identity_words(tmp_path):
    from ngraph import rename as rn

    layout = {"src/_pytest/__init__.py": "def fixture():\n    pass\n", "src/pytest/__init__.py": "from _pytest import fixture\n",
              "src/py.py": "import _pytest\n"}
    for rel, text in layout.items():
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_text(text)
    names = rn.collect_names(str(tmp_path), repo="pytest", org="pytest-dev")
    assert "py" in names.packages and "py" not in names.identity
    (tmp_path / "utils").mkdir()
    (tmp_path / "utils" / "release.py").write_text("import pytest\n")
    (tmp_path / "utils" / "__init__.py").write_text("")
    assert "utils" not in rn.collect_names(str(tmp_path), repo="pytest", org="pytest-dev").identity
    r = rn.OpaqueRenamer(names, seed=1)
    out = r.rename_issue("Running pytest on test_foo.py with `py.path.local` fails.").text
    assert "test_foo.py" in out and "py.path.local" in out and "pytest" not in out, out
    assert r.leak_scan(out)["ok"]
