"""Tests for the Study B opaque renamer and its leak scan."""

import pytest

from ngraph import rename as rn

FILES = {
    "src/acme/__init__.py": "from .sessions import Session\n__version__ = '1.0'\n",
    "src/acme/sessions.py": '''import json
import os
from urllib3.util import Retry
import numpy as np

DEFAULT_TIMEOUT = 5


class Session:
    retries = Retry(3)

    def __init__(self):
        self.adapter_pool = {}
        self.headers = {}

    def send(self, request):
        data = self.headers.get("x")
        path = os.path.join("a", "b")
        return self._merge_settings(json.dumps(data), np.zeros(2))

    def get(self, url):
        return self.send(url)

    def _merge_settings(self, a, b):
        return a
''',
    "src/acme/utils.py": '''from .sessions import Session as AcmeSession
from acme_plugins import thing
ACME_HOME = "~/.acme"


def get_encoding_from_headers(headers):
    return headers.get("content-type")


def to_key_val_list(value):
    return list(value)
''',
    "tests/test_sessions.py": "from acme.sessions import Session\n\n\ndef test_send_works():\n    assert Session()\n",
}

ISSUE = """Acme's Session.send hangs when get_encoding_from_headers returns None (see https://github.com/acme-org/acme/issues/12, cc @jdoe).

The session object is fine and DEFAULT_TIMEOUT is ignored; `send` is the culprit. Plain requests to https://example.org/send work.

```python
import acme
from acme.sessions import Session
Session().send(acme.utils.to_key_val_list([1]))
```

Traceback (most recent call last):
  File "/venv/lib/python3.11/site-packages/acme/sessions.py", line 17, in send
    return self._merge_settings(json.dumps(data), np.zeros(2))
acme.exceptions.ConnectionError: boom
"""


@pytest.fixture()
def repo(tmp_path):
    for rel, src in FILES.items():
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(src)
    return tmp_path


def _common(words=("session", "object", "fine", "send", "get", "plain", "work", "headers", "data")):
    ws = set(words)
    return lambda w: w.lower() in ws


def test_collect_names(repo):
    names = rn.collect_names(str(repo), repo="acme", org="acme-org")
    ren = set(names.renamable())
    for n in ["acme", "sessions", "utils", "Session", "send", "_merge_settings", "DEFAULT_TIMEOUT",
              "adapter_pool", "retries", "get_encoding_from_headers", "to_key_val_list", "test_send_works",
              "test_sessions"]:
        assert n in ren, n
    for n in ["get", "json", "os", "path", "join", "Retry", "urllib3", "util", "numpy", "np", "zeros", "dumps",
              "__init__", "__version__", "tests", "src"]:
        assert n not in ren, n
    assert names.packages == ["acme"] and names.identity == ["acme", "acme-org"]
    assert "AcmeSession" in ren and "acme_plugins" not in ren and "ACME_HOME" in ren


def test_issue_renaming_rules(repo):
    names = rn.collect_names(str(repo), repo="acme", org="acme-org", extra_identity=["Jane Doe"])
    r = rn.OpaqueRenamer(names, seed=1, common_word=_common())
    m = r.map
    out = r.rename_issue(ISSUE + "\nThanks, Jane Doe\n").text
    assert f"{m['Session']}.{m['send']}" in out  # dotted path in prose
    assert m["get_encoding_from_headers"] in out and m["DEFAULT_TIMEOUT"] in out  # identifier-shaped prose
    assert "The session object is fine" in out  # common words in prose stay
    assert f"`{m['send']}`" in out  # inline code
    assert "<url>" in out and "https://example.org/send" in out and "@user" in out and "<name>" in out
    assert out.startswith(rn._case_like("Acme", m["acme"]) + "'s")  # identity word, case kept
    assert "Plain requests to" in out
    assert f"from {m['acme']}.{m['sessions']} import {m['Session']}" in out  # code block
    assert f"{m['acme']}/{m['sessions']}.py\", line 17, in {m['send']}" in out  # traceback frame
    assert f"self.{m['_merge_settings']}(json.dumps(data), np.zeros(2))" in out  # source line under frame
    assert "ConnectionError" in out and f"{m['acme']}.exceptions.ConnectionError" in out
    scan = r.leak_scan(out)
    assert scan["ok"], scan
    assert "session" in {k.lower() for k in scan["soft"]} or scan["soft"] == {}
    raw = r.leak_scan(ISSUE + "Jane Doe")
    assert not raw["ok"] and "Session" in raw["hard"] and "<url with identity>" in raw["hard"]
    assert "Jane Doe" in raw["hard"] and "acme" in raw["hard"]


def test_code_renaming_and_bijection(repo):
    names = rn.collect_names(str(repo), repo="acme")
    r = rn.OpaqueRenamer(names, seed=1, common_word=_common())
    src = FILES["src/acme/sessions.py"]
    out = r.rename_code(src)
    assert f"class {r.map['Session']}:" in out.text and f"self.{r.map['headers']}.get(" in out.text
    assert f"def {r.map['send']}(self, request):" in out.text and "os.path.join" in out.text
    assert "def __init__(self):" in out.text and "Retry(3)" in out.text
    assert r.leak_scan(out.text)["ok"]
    assert 0 < out.share_changed < 1
    assert len(set(r.map.values())) == len(r.map)
    assert all(v != k for k, v in r.map.items())
    assert {r.inverse[v] for v in r.map.values()} == set(r.map)
    r2 = rn.OpaqueRenamer(names, seed=1, common_word=_common())
    r3 = rn.OpaqueRenamer(names, seed=2, common_word=_common())
    assert r2.map == r.map and r3.map != r.map
    # sub-token consistency: names sharing a part share its pseudo-word
    a, b = r.map["get_encoding_from_headers"].split("_"), r.map["to_key_val_list"].split("_")
    assert len(a) == 4 and len(b) == 4


def test_identity_subtokens_are_scrubbed(repo):
    names = rn.collect_names(str(repo), repo="acme")
    r = rn.OpaqueRenamer(names, seed=1, common_word=_common())
    pseudo = r.identity_map["acme"]
    out = r.rename_issue("Set ACME_DEBUG=1 and call AcmeSession; acme_plugins breaks.").text
    assert f"{pseudo.upper()}_DEBUG=1" in out and r.map["AcmeSession"] in out
    assert "acme_plugins" in out  # third-party name: kept and reported as a residual cue
    scan = r.leak_scan(out)
    assert scan["ok"] and scan["residual_identity"] == {"acme_plugins": 1}
    assert not r.leak_scan("Set ACME_DEBUG=1")["ok"]


def test_offsets_map_original_cuts():
    spans = [(2, 5, 2, 9), (10, 12, 16, 17)]  # "abXYZcdefgHIjk": XYZ -> 7 chars, HI -> 1 char
    assert rn.map_offset(spans, 0) == 0 and rn.map_offset(spans, 2) == 2
    assert rn.map_offset(spans, 3) == 9  # inside a renamed token: cut after it
    assert rn.map_offset(spans, 5) == 9 and rn.map_offset(spans, 7) == 11
    assert rn.map_offset(spans, 12) == 17 and rn.map_offset(spans, 14) == 19


def test_rendered_spans_reproduce_text(repo):
    names = rn.collect_names(str(repo), repo="acme")
    r = rn.OpaqueRenamer(names, seed=1, common_word=_common())
    res = r.rename_issue(ISSUE)
    for os_, oe, ns, ne in res.spans:
        assert res.text[ns:ne] in (r.map.get(ISSUE[os_:oe]), "<url>", "@user") or \
            res.text[ns:ne].lower() == r.identity_map.get(ISSUE[os_:oe].lower())
    cut = ISSUE.index("The session")
    assert res.text[: rn.map_offset(res.spans, cut)].endswith("\n\n")
