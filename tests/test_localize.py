"""Tests for Study B task tools: gold mapping, BM25 pools, anchors and strata."""

import math

import pytest

from ngraph import localize as lz

OLD = '''import os


def helper(x):
    return x + 1


class Session:
    """A session."""

    timeout = 5

    @staticmethod
    def build(a):
        def inner(b):
            return b * 2
        return inner(a)

    def send(self, req):
        data = helper(req)
        return data

    class Adapter:
        def close(self):
            pass


def last():
    return None
'''

PATCH = '''diff --git a/pkg/core.py b/pkg/core.py
--- a/pkg/core.py
+++ b/pkg/core.py
@@ -13,7 +13,7 @@ class Session:
     @staticmethod
     def build(a):
         def inner(b):
-            return b * 2
+            return b * 3
         return inner(a)
 
     def send(self, req):
@@ -22,7 +22,10 @@ class Session:
 
     class Adapter:
         def close(self):
             pass
 
+    def brand_new(self):
+        return 1
+
 
 def last():
@@ -29,1 +32,2 @@ def last():
-    return None
+    x = 1
+    return x
diff --git a/tests/test_core.py b/tests/test_core.py
--- a/tests/test_core.py
+++ b/tests/test_core.py
@@ -1,1 +1,1 @@
-assert True
+assert 1
'''


def test_parse_and_apply_patch():
    files = lz.parse_unified_diff(PATCH)
    assert [f.old_path for f in files] == ["pkg/core.py", "tests/test_core.py"]
    fp = files[0]
    assert len(fp.hunks) == 3
    old, new = lz.changed_lines(fp)
    assert old == {16, 29}
    new_text = lz.apply_patch(OLD, fp)
    assert "return b * 3" in new_text and "def brand_new(self):" in new_text and "x = 1" in new_text
    assert new == {16, 27, 28, 29, 32, 33}
    bad = lz.parse_unified_diff(PATCH.replace("-            return b * 2", "-            return b * 9"))[0]
    with pytest.raises(ValueError):
        lz.apply_patch(OLD, bad)


def test_function_spans_follow_extractor_nodes():
    spans = {n: (a, b) for n, a, b in lz.function_spans(OLD)}
    assert set(spans) == {"helper", "Session.build", "Session.send", "Session.Adapter.close", "last"}
    assert spans["Session.build"] == (13, 17)  # starts at the decorator
    assert lz.innermost(lz.function_spans(OLD), 16) == "Session.build"  # nested def counts for build
    assert lz.innermost(lz.function_spans(OLD), 11) is None  # class attribute


def test_gold_functions_maps_changed_lines():
    ids = {"pkg.core.helper", "pkg.core.Session.build", "pkg.core.Session.send",
           "pkg.core.Session.Adapter.close", "pkg.core.last"}
    res = lz.gold_functions(PATCH, lambda p: OLD if p == "pkg/core.py" else None,
                            lambda p: "pkg.core" if p == "pkg/core.py" else None, ids)
    assert res["gold"] == ["pkg.core.Session.build", "pkg.core.last"]
    core, test = res["files"]
    assert core["new_functions"] == ["Session.brand_new"] and core["skipped"] is None
    assert test["skipped"] == "test or excluded file"


def test_code_tokens():
    toks = lz.code_tokens("The HTTPAdapter.send_request() of getUserName, v2 _x")
    assert "httpadapter" in toks and "http" in toks and "adapter" in toks
    assert "send_request" in toks and "send" in toks and "request" in toks
    assert "getusername" in toks and "user" in toks and "the" not in toks and "x" not in toks


def test_bm25_matches_hand_computation():
    docs = {"d1": "alpha beta beta", "d2": "alpha gamma", "d3": "delta"}
    bm = lz.BM25(docs)
    s = bm.scores("beta alpha alpha")
    n, avgdl = 3, (3 + 2 + 1) / 3

    def term(df, f, dl):
        idf = math.log(1 + (n - df + 0.5) / (df + 0.5))
        return idf * f * (lz.K1 + 1) / (f + lz.K1 * (1 - lz.B + lz.B * dl / avgdl))

    assert s["d1"] == pytest.approx(term(2, 1, 3) + term(1, 2, 3))
    assert s["d2"] == pytest.approx(term(2, 1, 2))
    assert s["d3"] == 0.0
    assert lz.rank(s) == ["d1", "d2", "d3"]


def test_candidate_pool_injection_and_ties():
    scores = {f"f{i:02d}": float(20 - i) for i in range(20)}
    scores["f05"] = scores["f04"]  # tie: broken by id
    res = lz.candidate_pool(scores, {"f03"})
    assert res["pool"] == [f"f{i:02d}" for i in range(10)] and not res["injected"]
    res = lz.candidate_pool(scores, {"f15", "f12", "zz"})
    assert res["injected"] and res["pool"][-1] == "f12" and res["pool"][:9] == [f"f{i:02d}" for i in range(9)]
    assert res["gold_ranks"] == {"f12": 13, "f15": 16} and res["gold_missing"] == ["zz"]
    assert lz.candidate_pool(scores, {"zz"})["pool"] == [f"f{i:02d}" for i in range(10)]


NODES = [
    {"id": "requests.sessions.Session.send", "module": "requests.sessions", "path": "src/requests/sessions.py",
     "lineno": 600, "end_lineno": 680},
    {"id": "requests.sessions.Session.request", "module": "requests.sessions", "path": "src/requests/sessions.py",
     "lineno": 500, "end_lineno": 590},
    {"id": "requests.adapters.HTTPAdapter.send", "module": "requests.adapters", "path": "src/requests/adapters.py",
     "lineno": 400, "end_lineno": 520},
    {"id": "requests.utils.get_encoding_from_headers", "module": "requests.utils", "path": "src/requests/utils.py",
     "lineno": 10, "end_lineno": 30},
    {"id": "requests.models.Response.json", "module": "requests.models", "path": "src/requests/models.py",
     "lineno": 900, "end_lineno": 960},
    {"id": "requests.models.PreparedRequest.prepare_body", "module": "requests.models",
     "path": "src/requests/models.py", "lineno": 450, "end_lineno": 520},
    {"id": "requests.api.request", "module": "requests.api", "path": "src/requests/api.py",
     "lineno": 14, "end_lineno": 59},
]

ISSUE = '''`Session.send` hangs when `get_encoding_from_headers` returns None.

Calling requests.Session.request with a body triggers it; the json() helper is fine.
I also tried `send` and PreparedRequest.prepare_body.

```
Traceback (most recent call last):
  File "/venv/lib/python3.11/site-packages/requests/api.py", line 59, in request
  File "/venv/lib/python3.11/site-packages/requests/adapters.py", line 501, in send
```
'''


def test_issue_mentions_rules():
    ms = {m["mention"]: m["rule"] for m in lz.issue_mentions(ISSUE)}
    assert ms["Session.send"] == "inline_code" and ms["send"] == "inline_code"
    assert ms["get_encoding_from_headers"] == "inline_code"
    assert ms["requests.Session.request"] == "dotted" and ms["PreparedRequest.prepare_body"] == "dotted"
    assert "json" not in ms and "requests" not in ms and "Calling" not in ms
    assert any(m.startswith("frame:") and m.endswith(":request") for m in ms)
    assert lz.issue_mentions("use self._merge_settings() here")[0]["mention"] == "_merge_settings"
    assert lz.issue_mentions("set self.host = x") == []
    assert [m["mention"] for m in lz.issue_mentions("set `self.host` = x")] == ["host"]


def test_find_anchors_unique_and_degree():
    idx = lz.NodeIndex(NODES)
    deg = {"requests.sessions.Session.request": 60}
    res = lz.find_anchors(ISSUE, idx, lambda n: deg.get(n, 3))
    got = [a["node"] for a in res["anchors"]]
    assert got == ["requests.sessions.Session.send", "requests.utils.get_encoding_from_headers",
                   "requests.models.PreparedRequest.prepare_body", "requests.api.request",
                   "requests.adapters.HTTPAdapter.send"]
    assert "send" in res["ambiguous"]
    assert res["too_connected"] == ["requests.sessions.Session.request"]
    # a frame inside a span breaks a name tie within one module
    two = NODES + [{"id": "requests.adapters.BaseAdapter.send", "module": "requests.adapters",
                    "path": "src/requests/adapters.py", "lineno": 100, "end_lineno": 120}]
    hit = lz.NodeIndex(two).match_frame("/x/requests/adapters.py", 501, "send")
    assert hit == {"requests.adapters.HTTPAdapter.send"}


def test_strata_by_hops():
    edges = [{"source": "a", "target": "b"}, {"source": "c", "target": "b"}, {"source": "c", "target": "d"},
             {"source": "d", "target": "e"}]
    nb = lz.undirected_neighbours(edges)
    f = nb.__getitem__
    assert lz.stratum(["a"], {"a"}, f) == "S0"
    assert lz.stratum(["a"], {"b"}, f) == "S1"
    assert lz.stratum(["a"], {"c"}, f) == "S2"
    assert lz.stratum(["a"], {"d"}, f) == "S3"
    assert lz.stratum(["a", "e"], {"c"}, f) == "S2" and lz.stratum(["e", "a"], {"d"}, f) == "S1"
    assert lz.stratum([], {"a"}, f) == "S3"


def test_function_documents(tmp_path):
    (tmp_path / "m.py").write_text("def f():\n    return 1\n\n\ndef g():\n    return 2\n")
    nodes = [{"id": "m.f", "path": "m.py", "lineno": 1, "end_lineno": 2},
             {"id": "m.g", "path": "m.py", "lineno": 5, "end_lineno": 6}]
    docs = lz.function_documents(nodes, lambda p: (tmp_path / p).read_text())
    assert docs == {"m.f": "m.f\ndef f():\n    return 1", "m.g": "m.g\ndef g():\n    return 2"}
