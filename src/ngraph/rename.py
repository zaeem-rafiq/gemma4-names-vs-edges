"""Opaque renaming for Study B (the "opaque identifiers" condition), with a leak scan.

One consistent, seeded bijection per repository over project-defined names, applied to the
issue text (including tracebacks and paths), candidate code and graph context. Rules (pre-registration,
section 4, made concrete here; each is a pre-registration item):

* Renamed: project-defined names collected with `ast` from every Python file of the repository
  snapshot (tests included, vendored folders excluded): module and package path components,
  classes, functions and methods at any depth, module- and class-level assigned names, and
  attributes assigned on self or cls.
* Never renamed: Python keywords, builtins, dunder names, standard-library module names,
  attributes of builtin types, third-party names (every name the repository imports from a module
  outside itself, its alias, and every attribute it reads from such an import), generic folder
  names (src, lib, tests, docs ...), and names shorter than 3 characters or without a letter.
* Pseudo-words are drawn per sub-token with the generator of ngraph.names (the Study A neutral
  names): sub-token consistent, case pattern, underscores and digits kept; common English words,
  protected names, project names and identity names are rejected; short sub-tokens fall back to
  longer pseudo-words when the short shapes run out. There is no token-count matching: Study B truncates on spans of the original text and maps the
  cut onto the renamed text (map_offset).
* Code (candidate code, graph context, fenced and inline code in the issue, traceback lines):
  every renamable name is renamed. Prose: a renamable name is renamed if it is identifier-shaped
  (underscore, inner capital, leading underscore), part of a dotted path, or not a common English
  word; other prose words are left alone.
* Scrubbed: identity names (repository, organisation and top-level package names, plus any extra
  names given, such as maintainers; a top-level package named by a common English word, by a generic
  word in GENERIC_TOPS or by fewer than 3 characters is not an identity name unless it is the repository
  or organisation name, and stays a renamable module name: pylint's "script", sphinx's "utils",
  pytest's "py" (0.1.3)) as whole words in any case become the renamed package name
  (or "<name>" when they are not project names), and so do identity words that are whole
  sub-tokens of other non-protected names (FLASK_APP, RequestsJSONDecodeError); URLs that contain
  an identity name as a whole word (github.com/encode/httpx; not "urlencode") become "<url>"; GitHub handles in prose become "@user" (not code names, decorators or dotted names). Aliases given to
  project imports (import ... as X) count as project-defined names.
* Leak scan: an independent pass over the renamed text. Hard leaks: a renamable name that is
  identifier-shaped, uncommon or inside a dotted path; an identity name as a whole word or as a
  sub-token of a non-protected name; a URL that contains an identity name as a whole word. The fixed
  words of the tool-output format are blanked before the scan (studyb.leak_text). A renamable name
  inside an interpreter-made file name of a traceback frame ("<ipython-input-37-5b65>", "<stdin>",
  "<string>", "<console>"), which the renamer keeps, is counted under "frame", not hard, if it is one
  of the interpreter's own words there (INTERP_WORDS) (0.1.3). Soft: renamable common words left in prose (expected). Residual
  cues: identity names inside other tokens (for example a third-party package named after the
  project), which are disclosed rather than removed.
"""

from __future__ import annotations

import ast
import builtins
import keyword
import os
import random
import re
import subprocess
import sys
from bisect import bisect_right
from collections import Counter, defaultdict
from dataclasses import dataclass, field

from ngraph.extract import Extractor, module_name_for, strip_prefixes
from ngraph.names import RESERVED, _pseudo_word, _render, _syllable, shape

RENAME_VERSION = "0.1.3"
LONG_AFTER = 8  # rounds in which one sub-token was redrawn before it gets a longer pseudo-word (OpaqueNamer.fit)
MIN_LEN = 3
# generic top-level folder names that never identify a project (sphinx's "utils", sqlfluff's "util") (0.1.3)
GENERIC_TOPS = frozenset("util utils".split())
GENERIC_PATHS = frozenset("src lib tests test testing docs doc examples example scripts tools benchmarks "
                          "bench conftest setup".split())
VENDORED = frozenset("_vendor vendor vendored third_party site-packages node_modules .venv venv build dist "
                     ".git .tox .nox".split())
_BUILTIN_TYPES = (str, bytes, bytearray, int, float, complex, bool, list, tuple, dict, set, frozenset,
                  object, type, BaseException, memoryview, range, slice, property, staticmethod,
                  classmethod, super)

TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
DOTTED_RE = re.compile(r"(?<![\w.])[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)+")
URL_RE = re.compile(r"https?://[^\s<>()\[\]\"'`]+")
# A GitHub handle in prose (0.1.2): not a dotted name or a call ("@enum.unique", "@admin.register(Thing)"),
# not after "]" or ")" ("]@N.AN" in a string, "(A+B)@v"), not the scheme of a URL ("@https://...").
# OpaqueRenamer._render also leaves "@word" alone when word is a standard decorator ("@property") or a
# project name that the token pass renames, and it skips fenced and inline code (not traceback lines).
HANDLE_RE = re.compile(r"(?<![\w@./\])])@[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})(?![\w-]|\.\w|\(|:/)")
FENCE_RE = re.compile(r"^[ \t]*(`{3,}|~{3,})[^\n]*\n.*?(?:^[ \t]*\1[ \t]*$|\Z)", re.M | re.S)
INLINE_RE = re.compile(r"(?<!`)`([^`\n]+)`(?!`)")
FRAME_LINE_RE = re.compile(r'^[ \t]*File "[^"\n]+", line \d+(?:, in \S+)?[^\n]*$', re.M)
# Python's own words in a traceback frame line, kept as they are ('File "x.py", line 3, in <module>') (0.1.2)
FRAME_WORDS_RE = re.compile(r'\bFile(?= ")|(?<=File ")<[^"<>\n]*>(?=")|\bline(?= \d)|(?<=<)module(?=>)')
# decorators from the standard library and builtins that issue prose names with "@" (not handles) (0.1.2)
DECORATOR_WORDS = frozenset("property staticmethod classmethod abstractmethod abstractproperty dataclass "
                            "cached_property lru_cache cache wraps contextmanager asynccontextmanager overload "
                            "override final total_ordering singledispatch singledispatchmethod unique".split())
# file names that the interpreter itself makes for code typed or run without a file (0.1.3)
INTERP_FILE_RE = re.compile(r"<(?:ipython-input-\d+-[0-9a-f]+|stdin|string|console)>")
INTERP_WORDS = frozenset("ipython input stdin string console".split())
TB_LINE_RE = re.compile(r"^[ \t]*(?:Traceback \(most recent call last\):|[A-Za-z_][\w.]*(?:Error|Exception|Warning|Exit|Interrupt)\b:?)[^\n]*$", re.M)


def is_identifier_shaped(w: str) -> bool:
    core = w.strip("_")
    return bool(core) and (w.startswith("_") or "_" in core or re.search(r"[a-z0-9][A-Z]|[A-Z]{2}[a-z]", w) is not None)


def builtin_protected() -> set:
    s = set(keyword.kwlist) | set(getattr(keyword, "softkwlist", [])) | set(dir(builtins))
    for t in _BUILTIN_TYPES:
        s |= set(dir(t))
    s |= set(getattr(sys, "stdlib_module_names", ()))
    return s


def _case_like(src: str, new: str) -> str:
    if src.isupper() and len(src) > 1:
        return new.upper()
    if src[:1].isupper():
        return new[:1].upper() + new[1:]
    return new


def repo_python_files(root: str) -> list[str]:
    if os.path.isdir(os.path.join(root, ".git")):
        out = subprocess.run(["git", "-C", root, "ls-files", "*.py"], capture_output=True, text=True,
                             check=True).stdout.splitlines()
    else:
        out = [os.path.relpath(os.path.join(d, f), root) for d, _, fs in os.walk(root) for f in fs if f.endswith(".py")]
    return sorted(f for f in out if f.strip() and not set(f.replace(os.sep, "/").split("/")[:-1]) & VENDORED)


# ----------------------------------------------------------------------------- names
@dataclass
class ProjectNames:
    defined: dict = field(default_factory=dict)        # name -> sorted kinds
    third_party: set = field(default_factory=set)
    packages: list = field(default_factory=list)       # top-level project packages
    identity: list = field(default_factory=list)       # lower-case identity words
    extra_identity: list = field(default_factory=list)  # free-form strings (e.g. maintainer names)
    parse_errors: list = field(default_factory=list)

    @property
    def protected(self) -> set:
        return builtin_protected() | self.third_party

    def renamable(self) -> list[str]:
        prot = self.protected
        out = []
        for n in self.defined:
            if (len(n) < MIN_LEN or not re.search(r"[A-Za-z]", n) or n in prot or n in GENERIC_PATHS
                    or (n.startswith("__") and n.endswith("__"))):
                continue
            out.append(n)
        return sorted(out)


def collect_names(root: str, files: list[str] | None = None, repo: str | None = None,
                  org: str | None = None, extra_identity=()) -> ProjectNames:
    files = repo_python_files(root) if files is None else files
    strip = strip_prefixes(root, files)
    mods = {}
    for rel in files:
        mod, _ = module_name_for(rel, strip)
        # files under hidden folders (.circleci, .github, ...) are tooling, not project code, and give a
        # module name with an empty component that no renaming can map (0.1.2)
        if mod and all(mod.split(".")) and not any(c.startswith(".") for c in rel.replace(os.sep, "/").split("/")):
            mods[rel] = mod
    project_tops = {m.split(".")[0] for m in mods.values()}
    # identity words (0.1.2): a top-level name that is itself a module or package (top/__init__.py or
    # top.py at the top of the import path) or that project code imports absolutely (namespace packages,
    # packages whose __init__.py sits deeper). A folder of scripts that nothing imports (bin, ci, release)
    # is not one.
    imported_tops = set()
    self_tops = set(mods.values()) & project_tops
    # local import roots (0.1.2): a module or package X directly inside a folder P that is not a package
    # (examples/tutorial/flaskr) is importable as "X" by scripts and tests that run from P (see is_local),
    # so "from flaskr import create_app" in examples/tutorial/tests is a project import, not a third-party one
    local_roots = set()
    for rel in mods:
        parts = rel.replace(os.sep, "/").split("/")
        for i in range(1, len(parts)):
            if not os.path.isfile(os.path.join(root, *parts[:i], "__init__.py")):
                x = parts[i][:-3] if i == len(parts) - 1 else parts[i]
                if x and x != "__init__":
                    local_roots.add(("/".join(parts[:i]), x))

    def is_local(rel_imp: str, top: str) -> bool:
        # P is the importing file's nearest folder that is not a package (where a script or test runs from),
        # or that folder's parent (a test folder next to its package, as in examples/tutorial/tests)
        d = rel_imp.replace(os.sep, "/").split("/")[:-1]
        while d and os.path.isfile(os.path.join(root, *d, "__init__.py")):
            d = d[:-1]
        return any(("/".join(q), top) in local_roots for q in (d, d[:-1]) if q)
    defined = defaultdict(set)
    third = set()
    errors = []

    def add(name, kind):
        if name:
            defined[name].add(kind)

    for rel, mod in mods.items():
        for comp in mod.split("."):
            add(comp, "module")
        try:
            with open(os.path.join(root, rel), "rb") as fh:
                tree = ast.parse(fh.read(), filename=rel)
        except (SyntaxError, ValueError, OSError) as exc:
            errors.append(f"{rel}: {type(exc).__name__}")
            continue
        foreign_roots = set()
        for n in ast.walk(tree):
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                add(n.name, "function")
            elif isinstance(n, ast.ClassDef):
                add(n.name, "class")
                for st in Extractor._toplevel_stmts(n.body):
                    for t in _assign_targets(st):
                        add(t, "class_attribute")
            elif isinstance(n, ast.Attribute) and isinstance(n.ctx, ast.Store) and \
                    isinstance(n.value, ast.Name) and n.value.id in ("self", "cls"):
                add(n.attr, "attribute")
            elif isinstance(n, ast.Import):
                for a in n.names:
                    if a.name.split(".")[0] in project_tops or is_local(rel, a.name.split(".")[0]):
                        if a.name.split(".")[0] in project_tops:
                            imported_tops.add(a.name.split(".")[0])
                        if a.asname:
                            add(a.asname, "alias")
                    else:
                        third.update(a.name.split("."))
                        bound = a.asname or a.name.split(".")[0]
                        third.add(bound)
                        foreign_roots.add(bound)
            elif isinstance(n, ast.ImportFrom):
                if n.level > 0 or (n.module and (n.module.split(".")[0] in project_tops
                                                 or is_local(rel, n.module.split(".")[0]))):
                    if n.level == 0 and n.module.split(".")[0] in project_tops:
                        imported_tops.add(n.module.split(".")[0])
                    for a in n.names:
                        if a.asname:
                            add(a.asname, "alias")
                elif n.module:
                    third.update(n.module.split("."))
                    for a in n.names:
                        if a.name != "*":
                            third.add(a.name)
                            third.add(a.asname or a.name)
                            foreign_roots.add(a.asname or a.name)
        for st in Extractor._toplevel_stmts(tree.body):
            for t in _assign_targets(st):
                add(t, "module_variable")
        # attribute chains read from third-party or standard-library imports
        for n in ast.walk(tree):
            if isinstance(n, ast.Attribute):
                chain, cur = [], n
                while isinstance(cur, ast.Attribute):
                    chain.append(cur.attr)
                    cur = cur.value
                if isinstance(cur, ast.Name) and cur.id in foreign_roots:
                    third.update(chain)
    tops = sorted(t for t in self_tops | imported_tops if t not in GENERIC_PATHS)
    # the project's own top-level names are never third-party, even when a foreign module path contains one
    # (sympy: "from sage.interfaces.sympy import ...") (0.1.2)
    third -= project_tops | set(tops)
    # a top-level package named by a common English word (pylint's maintenance package "script") is not an
    # identity word unless it is the repository or organisation name: scrubbing it would rewrite ordinary
    # prose, and it stays a renamable module name in code and dotted paths; nor is a generic folder name
    # (GENERIC_TOPS: sphinx's "utils" would be scrubbed in any case and inside names such as get_utils),
    # nor a name shorter than MIN_LEN (pytest's "py" shim), which is never renamed and would otherwise
    # rewrite every ".py" (0.1.3)
    from ngraph.items import common_word_filter
    common = common_word_filter()
    own = {x.lower() for x in (repo, org) if x}
    ident = {t.lower() for t in tops if t.lower() in own or (
        len(t) >= MIN_LEN and t.lower() not in GENERIC_TOPS and not common(t.lower()))}
    for x in (repo, org):
        if x:
            ident.add(x.lower())
    return ProjectNames({k: sorted(v) for k, v in sorted(defined.items())}, third, tops, sorted(ident),
                        list(extra_identity), errors)


def _assign_targets(st) -> list[str]:
    out = []
    if isinstance(st, ast.Assign):
        targets = st.targets
    elif isinstance(st, (ast.AnnAssign, ast.AugAssign)):
        targets = [st.target]
    else:
        return out
    for t in targets:
        for n in ast.walk(t):
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store):
                out.append(n.id)
    return out


# ----------------------------------------------------------------------------- pseudo-words
class OpaqueNamer:
    """Sub-token-consistent pseudo-word renaming that scales to whole repositories (O(names))."""

    def __init__(self, seed: int, reject, forbidden=(), taken_names=()):
        self.rng = random.Random(seed)
        self.reject = reject
        self.forbidden = sorted({f for f in forbidden if len(f) >= 3})
        self.taken_names = set(taken_names)
        self.sub_map: dict[str, str] = {}
        self.map: dict[str, str] = {}
        self.used: set[str] = set()
        self.fallback: set[str] = set()
        self._by_sub = defaultdict(set)
        self._redraws = defaultdict(int)

    def _free(self, w: str, sub: str) -> bool:
        return (w != sub and w not in self.used and w not in RESERVED and not any(f in w for f in self.forbidden)
                and not (len(w) > 1 and self.reject(w)))

    def _draw(self, sub: str, long: bool = False) -> str:
        for widen in range(0 if long else 3 if len(sub) <= 2 else 1):
            for _ in range(400):
                w = _pseudo_word(self.rng, sub, None, widen)
                if self._free(w, sub):
                    return w
        for _ in range(20000):  # short shapes used up: a longer pseudo-word
            w = "".join(_syllable(self.rng) for _ in range(self.rng.randint(2, 3)))
            if self._free(w, sub):
                self.fallback.add(sub)
                return w
        raise RuntimeError(f"could not draw a pseudo-word for sub-token {sub!r}")

    @staticmethod
    def _subs(comp: str) -> list[str]:
        _, parts, _, _ = shape(comp)
        return [t.lower() for humps in parts for k, t in humps if k != "digit"]

    def compose(self, comp: str) -> str:
        prefix, parts, suffix, seps = shape(comp)
        pieces = ["".join(t if k == "digit" else _render(k, self.sub_map[t.lower()]) for k, t in humps)
                  for humps in parts]
        return prefix + pieces[0] + "".join(sep + p for sep, p in zip(seps, pieces[1:])) + suffix

    def _valid(self, comp: str, new: str, owner: dict) -> bool:
        low = new.lower()
        if new == comp or low in RESERVED or new in self.taken_names or any(f in low for f in self.forbidden):
            return False
        if any(self.reject(p.lower()) for p in re.split(r"[_-]", new) if len(p) > 1 and p.isalpha()):
            return False
        return owner.get(new, comp) == comp

    def fit(self, comps) -> None:
        comps = [c for c in dict.fromkeys(comps) if c not in self.map]
        for c in comps:
            for t in self._subs(c):
                self._by_sub[t].add(c)
                if t not in self.sub_map:
                    w = self._draw(t)
                    self.sub_map[t] = w
                    self.used.add(w)
        owner = {v: k for k, v in self.map.items()}
        todo = list(comps)
        for _ in range(100):
            bad = []
            for c in todo:
                new = self.compose(c)
                if self._valid(c, new, owner):
                    owner[new] = c
                    self.map[c] = new
                else:
                    bad.append(c)
            if not bad:
                return
            redo = set()
            counted = set()
            for c in bad:
                subs = [t for t in self._subs(c)]
                if not subs:
                    raise RuntimeError(f"name {c!r} has no letters to rename")
                t = subs[self.rng.randrange(len(subs))]
                self.used.discard(self.sub_map[t])
                # a sub-token redrawn in LONG_AFTER rounds without success (a one-letter sub-token whose every
                # one-letter stand-in collides with a kept name: sympy's a11 -> f11) gets a longer
                # pseudo-word, which practically never collides (0.1.2)
                if t not in counted:  # one count per round, however many bad names share t
                    counted.add(t)
                    self._redraws[t] += 1
                self.sub_map[t] = self._draw(t, long=self._redraws[t] >= LONG_AFTER)
                self.used.add(self.sub_map[t])
                redo |= self._by_sub[t]
            for c in redo:  # names that share a redrawn sub-token are composed again
                if c in self.map:
                    owner.pop(self.map.pop(c), None)
            todo = sorted(redo | set(bad))
        raise RuntimeError("could not find a valid opaque renaming")


# ----------------------------------------------------------------------------- renamer
@dataclass
class Rendered:
    text: str
    spans: list            # (orig_start, orig_end, new_start, new_end) for every replacement
    n_tokens: int          # identifier tokens in the original text
    n_renamed: int         # identifier tokens renamed

    @property
    def share_changed(self) -> float:
        return self.n_renamed / self.n_tokens if self.n_tokens else 0.0


def map_offset(spans, k: int) -> int:
    """Original offset -> renamed offset. Inside a replaced span, the cut moves to its end."""
    starts = [s[0] for s in spans]
    i = bisect_right(starts, k) - 1
    if i >= 0:
        os_, oe, ns, ne = spans[i]
        if os_ < k < oe:
            return ne
        if k >= oe:
            return ne + (k - oe)
    return k


class OpaqueRenamer:
    def __init__(self, names: ProjectNames, seed: int = 1, common_word=None):
        if common_word is None:
            from ngraph.items import common_word_filter
            common_word = common_word_filter()
        self.names = names
        self.seed = seed
        self.common = common_word
        self.protected = names.protected
        renamable = names.renamable()
        self.renamable = set(renamable)
        prot_low = {p.lower() for p in self.protected}
        ren_low = {r.lower() for r in renamable}

        def reject(w):
            lw = w.lower()
            return common_word(lw) or lw in prot_low or lw in ren_low

        self.namer = OpaqueNamer(seed, reject, forbidden=names.identity,
                                 taken_names=set(self.protected) | set(renamable))
        for i in range(0, len(renamable), 500):
            self.namer.fit(renamable[i:i + 500])
        self.map = {n: self.namer.map[n] for n in renamable}
        ident = [i for i in names.identity if i not in prot_low]
        self.namer.fit([i for i in ident if i not in self.map])  # identity words that are not module names
        self.identity_map = {i: self.namer.map[i] for i in ident}
        self.identity_re = _words_re(ident)
        # whole words (github.com/encode/httpx, httpx.readthedocs.io), not substrings: "urlencode" or
        # "percent-encoded" must not turn an unrelated URL into <url> (0.1.1)
        self.url_identity_re = _words_re(names.identity)
        self.extra_re = re.compile("|".join(re.escape(x) for x in names.extra_identity), re.I) \
            if names.extra_identity else None
        inv = {}
        for k, v in self.map.items():
            if v in inv:
                raise RuntimeError(f"not a bijection: {k} and {inv[v]} -> {v}")
            inv[v] = k
        self.inverse = inv

    # ------------------------------------------------------------------ segmentation
    @staticmethod
    def code_spans(text: str, blocks_only: bool = False) -> list[tuple[int, int]]:
        spans = [(m.start(), m.end()) for m in FENCE_RE.finditer(text)]
        spans += [(m.start(1), m.end(1)) for m in INLINE_RE.finditer(text)]
        if blocks_only:  # fenced and inline code only, without traceback lines
            return _merge(spans)
        for m in FRAME_LINE_RE.finditer(text):
            spans.append((m.start(), m.end()))
            nxt = text.find("\n", m.end() + 1)
            line = text[m.end() + 1: nxt if nxt != -1 else len(text)]
            if m.end() < len(text) and line.startswith((" ", "\t")):
                spans.append((m.end() + 1, m.end() + 1 + len(line)))
        spans += [(m.start(), m.end()) for m in TB_LINE_RE.finditer(text)]
        return _merge(spans)

    # ------------------------------------------------------------------ renaming
    def _identity_new(self, word: str) -> str:
        new = self.identity_map.get(word.lower())
        return _case_like(word, new) if new else "<name>"

    def _render(self, text: str, all_code: bool) -> Rendered:
        code = [(0, len(text))] if all_code else self.code_spans(text)
        repl = []
        blocked = []
        for m in URL_RE.finditer(text):
            u = m.group(0)
            if (self.url_identity_re and self.url_identity_re.search(u)) or (self.extra_re and self.extra_re.search(u)):
                repl.append((m.start(), m.end(), "<url>"))
            blocked.append((m.start(), m.end()))
        if self.extra_re:
            for m in self.extra_re.finditer(text):
                if not _inside(_merge(blocked), m.start()):
                    repl.append((m.start(), m.end(), "<name>"))
                    blocked.append((m.start(), m.end()))
        for m in FRAME_LINE_RE.finditer(text):
            for w in FRAME_WORDS_RE.finditer(m.group(0)):
                blocked.append((m.start() + w.start(), m.start() + w.end()))
        if not all_code:
            blocks = self.code_spans(text, blocks_only=True)
            ident = set(self.names.identity)
            for m in HANDLE_RE.finditer(text):
                word = m.group(0)[1:]
                # a decorator written in prose is not a handle: a standard one, or a project name that the
                # token pass renames (identifier-shaped or uncommon); an identity word is always a handle (0.1.2)
                if word.lower() not in ident and (word in DECORATOR_WORDS or (
                        word in self.renamable and (is_identifier_shaped(word) or not self.common(word.lower())))):
                    continue
                if _overlaps(_merge(blocked), m.start(), m.end()) or _inside(blocks, m.start()):
                    continue
                repl.append((m.start(), m.end(), "@user"))
                blocked.append((m.start(), m.end()))
        blocked = _merge(blocked)
        dotted = _merge([(m.start(), m.end()) for m in DOTTED_RE.finditer(text)])
        n_tok = n_ren = 0
        for m in TOKEN_RE.finditer(text):
            if _inside(blocked, m.start()):
                continue
            tok = m.group(0)
            n_tok += 1
            new = self._rename_token(tok, _inside(code, m.start()), _inside(dotted, m.start()))
            if new != tok:
                repl.append((m.start(), m.end(), new))
                n_ren += 1
        repl.sort()
        out, spans, pos, shift = [], [], 0, 0
        for s, e, new in repl:
            if s < pos:
                continue  # overlaps an earlier replacement (URL or name already scrubbed)
            out.append(text[pos:s])
            ns = s + shift
            out.append(new)
            spans.append((s, e, ns, ns + len(new)))
            shift += len(new) - (e - s)
            pos = e
        out.append(text[pos:])
        return Rendered("".join(out), spans, n_tok, n_ren)

    def _rename_token(self, tok: str, in_code: bool, in_dotted: bool) -> str:
        if tok in self.map:
            if in_code or in_dotted or is_identifier_shaped(tok) or not self.common(tok.lower()):
                return self.map[tok]
            # a common English word in prose; identity words are still scrubbed below
        if self.identity_re and tok.lower() in self.identity_map and self.identity_re.fullmatch(tok):
            return self._identity_new(tok)
        if tok not in self.protected and self.identity_map:
            return self._scrub_subtokens(tok)
        return tok

    def _identity_humps(self, tok: str) -> bool:
        _, parts, _, _ = shape(tok)
        return any(k != "digit" and t.lower() in self.identity_map for humps in parts for k, t in humps)

    def _scrub_subtokens(self, tok: str) -> str:
        """FLASK_APP -> ZORKA_APP: identity words that are whole sub-tokens of another name."""
        if not self._identity_humps(tok):
            return tok
        prefix, parts, suffix, seps = shape(tok)
        pieces = ["".join(_render(k, self.identity_map[t.lower()]) if k != "digit" and t.lower() in self.identity_map
                          else t for k, t in humps) for humps in parts]
        return prefix + pieces[0] + "".join(sep + p for sep, p in zip(seps, pieces[1:])) + suffix

    def rename_code(self, text: str) -> Rendered:
        return self._render(text, all_code=True)

    def rename_issue(self, text: str) -> Rendered:
        return self._render(text, all_code=False)

    # ------------------------------------------------------------------ leak scan
    def leak_scan(self, renamed: str) -> dict:
        hard, soft, residual = Counter(), Counter(), Counter()
        dotted = _merge([(m.start(), m.end()) for m in DOTTED_RE.finditer(renamed)])
        urls = [(m.start(), m.end()) for m in URL_RE.finditer(renamed)]
        for m in URL_RE.finditer(renamed):
            if self.url_identity_re and self.url_identity_re.search(m.group(0)):
                hard["<url with identity>"] += 1
        # an interpreter-made file name in a traceback frame line, which the renamer leaves alone
        # ("<ipython-input-3-ab12>", INTERP_FILE_RE): the interpreter's own words there (INTERP_WORDS) are
        # not hard leaks even when the project defines them; the hash tail, identity words and other
        # "<...>" file names (doctest) are scanned as usual (0.1.3)
        frames = _merge([(m.start() + w.start(), m.start() + w.end()) for m in FRAME_LINE_RE.finditer(renamed)
                         for w in FRAME_WORDS_RE.finditer(m.group(0)) if INTERP_FILE_RE.fullmatch(w.group(0))])
        frame = Counter()
        for m in TOKEN_RE.finditer(renamed):
            if _inside(urls, m.start()):
                continue
            t = m.group(0)
            low = t.lower()
            if low in self.identity_map and t not in self.inverse:
                hard[t] += 1
            elif low in INTERP_WORDS and t in self.renamable and _inside(frames, m.start()):
                frame[t] += 1
            elif t in self.renamable:
                if _inside(dotted, m.start()) or is_identifier_shaped(t) or not self.common(low):
                    hard[t] += 1
                else:
                    soft[t] += 1
            elif t not in self.inverse and t not in self.protected and self._identity_humps(t):
                hard[t] += 1
            elif any(i in low for i in self.identity_map if len(i) >= 4):
                residual[t] += 1  # identity word inside another token (e.g. a third-party package)
        if self.extra_re:
            for m in self.extra_re.finditer(renamed):
                hard[m.group(0)] += 1
        return {"ok": not hard, "hard": dict(hard), "soft": dict(soft), "residual_identity": dict(residual),
                "frame": dict(frame)}

    def export(self) -> dict:
        return {"rename_version": RENAME_VERSION, "seed": self.seed, "map": dict(sorted(self.map.items())),
                "identity_map": self.identity_map, "sub_map": dict(sorted(self.namer.sub_map.items())),
                "fallback_subtokens": sorted(self.namer.fallback),
                "n_protected_defined": sum(1 for n in self.names.defined if n in self.protected),
                "packages": self.names.packages}


def _words_re(words, substring: bool = False):
    words = sorted({w for w in words if w}, key=len, reverse=True)
    if not words:
        return None
    alt = "|".join(map(re.escape, words))
    return re.compile(alt if substring else r"(?<![A-Za-z0-9])(" + alt + r")(?![A-Za-z0-9])", re.I)


def _merge(spans):
    out = []
    for s, e in sorted(spans):
        if out and s <= out[-1][1]:
            out[-1] = (out[-1][0], max(out[-1][1], e))
        else:
            out.append((s, e))
    return out


def _inside(spans, k: int) -> bool:
    lo, hi = 0, len(spans)
    while lo < hi:
        mid = (lo + hi) // 2
        if spans[mid][1] <= k:
            lo = mid + 1
        else:
            hi = mid
    return lo < len(spans) and spans[lo][0] <= k < spans[lo][1]


def _overlaps(spans, s: int, e: int) -> bool:
    """True if [s, e) meets any merged span."""
    return any(a < e and s < b for a, b in spans)
