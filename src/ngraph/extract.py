"""Static call-graph extractor for Python repositories (standard library only).

Nodes are module-level functions and class methods (including methods of nested
classes), keyed by qualified name: "pkg.mod.func" or "pkg.mod.Class.method".

A directed edge caller -> callee is kept only when the call resolves to exactly
one in-repository node under these rules (anything else is left unresolved):

  1. f(...)          f is a module-level function of the same module, a simple
                     module-level alias of one, or a name imported from an
                     in-repo module.
  2. C(...)          C is an in-repo class: the edge goes to the __init__ that
                     runs (C's own or an in-repo base's). No edge if C or a
                     base before it in the method order is defined outside the
                     repository.
  3. self.m(...)     inside a method of class K (first positional parameter),
     cls.m(...)      m is looked up in K and its in-repo bases. Not resolved if
                     a foreign base comes first. self.m(...) is also not
                     resolved if any class in that order assigns self.m
                     somewhere (directly or by setattr(self, "m", ...)) or calls
                     setattr(self, <name expression>, ...) outside __setstate__;
                     setattr calls in static methods are ignored (their first
                     parameter is not the instance).
  4. super().m(...)  m is looked up in K's bases, after K.
  5. mod.f(...)      mod is an imported in-repo module (dotted chains allowed).
  6. C.m(...)        C is an in-repo class; m is looked up in C and its bases.

Calls inside nested functions, lambdas and comprehensions count for the
enclosing node. A name that is a parameter, or is assigned anywhere inside the
enclosing node, shadows module-level names and is not resolved (except names
bound only by a local import, which are resolved through that import).
Methods decorated as properties are never call targets. Self-loops (recursion)
are dropped. Tests, docs, examples, benchmarks, scripts and vendored code are
excluded from the node set.

Precision over recall: the goal is a graph whose edges are right, not complete.
"""

from __future__ import annotations

import ast
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field

EXTRACTOR_VERSION = "0.3.1"  # 0.3.0: narrower setattr rule (literal names, __setstate__, static methods)
# 0.3.1: a lib/ folder that holds packages but is not one (matplotlib's lib/matplotlib) is a layout prefix like
# src/ in module names (file selection is unchanged); no graph of a repository without such a folder changes

EXCLUDE_DIRS = {
    "tests", "test", "testing", "docs", "doc", "examples", "example",
    "benchmarks", "benchmark", "bench", "scripts", "tools", ".github",
    "build", "dist", "venv", ".venv", "site-packages", "node_modules",
    "_vendor", "vendor", "vendored", "third_party", "asv_bench", "docs_src",
}
EXCLUDE_FILES = {"setup.py", "conftest.py", "noxfile.py", "fabfile.py"}
PROPERTY_DECORATORS = {"property", "cached_property", "abstractproperty"}


def is_excluded(relpath: str) -> bool:
    parts = relpath.replace(os.sep, "/").split("/")
    if any(p in EXCLUDE_DIRS for p in parts[:-1]):
        return True
    fname = parts[-1]
    if fname in EXCLUDE_FILES:
        return True
    if fname.startswith("test_") or fname.endswith("_test.py"):
        return True
    return False


SRC_IMPORT_RE = re.compile(r"^\s*(?:from|import)\s+src(?:\.|\s|$)", re.M)


def src_is_package(root: str, files) -> bool:
    """True when the code imports `src` itself (e.g. `from src.services import x`), so `src/` is a
    package name rather than the usual src-layout prefix that is stripped from module names."""
    if os.path.isfile(os.path.join(root, "src", "__init__.py")):
        return True
    for rel in files:
        try:
            with open(os.path.join(root, rel), encoding="utf-8", errors="replace") as fh:
                if SRC_IMPORT_RE.search(fh.read()):
                    return True
        except OSError:
            continue
    return False


def strip_prefixes(root: str, files) -> tuple:
    """Leading folders that are layout prefixes, not package names: src/ (unless the code imports `src`
    itself) and lib/ when it holds packages but is not one (matplotlib's lib/matplotlib) (0.3.1)."""
    out = [] if src_is_package(root, files) else ["src"]
    rels = [f.replace(os.sep, "/") for f in files]
    if not os.path.isfile(os.path.join(root, "lib", "__init__.py")) and "lib/__init__.py" not in rels and any(
            r.startswith("lib/") and r.count("/") >= 2 and r.endswith("/__init__.py") for r in rels):
        out.append("lib")
    return tuple(out)


def _prefixes(strip_src) -> tuple:
    if strip_src is True:
        return ("src",)
    return tuple(strip_src) if strip_src else ()


def module_name_for(relpath: str, strip_src=True) -> tuple[str, bool]:
    """strip_src: True strips a leading src/ (the old meaning), or a tuple from strip_prefixes()."""
    parts = relpath.replace(os.sep, "/").split("/")
    if parts and len(parts) > 1 and parts[0] in _prefixes(strip_src):
        parts = parts[1:]
    is_pkg = parts[-1] == "__init__.py"
    if is_pkg:
        parts = parts[:-1]
    else:
        parts[-1] = parts[-1][:-3]
    return ".".join(parts), is_pkg


def list_python_files(root: str) -> list[str]:
    if os.path.isdir(os.path.join(root, ".git")):
        out = subprocess.run(["git", "-C", root, "ls-files", "*.py"],
                             capture_output=True, text=True, check=True).stdout
        files = [line for line in out.splitlines() if line.strip()]
    else:
        files = []
        for d, _, fs in os.walk(root):
            for f in fs:
                if f.endswith(".py"):
                    files.append(os.path.relpath(os.path.join(d, f), root))
    return sorted(f for f in files if not is_excluded(f))


def _top_group(relpath: str, strip_src=True) -> str:
    parts = relpath.replace(os.sep, "/").split("/")
    if len(parts) > 1 and parts[0] in _prefixes(strip_src):
        parts = parts[1:]
    return parts[0] if len(parts) > 1 else "(root)"


DEF_RE = re.compile(r"^\s*(?:async\s+)?def\s", re.M)


def file_lines(root: str, rel: str) -> int:
    try:
        with open(os.path.join(root, rel), encoding="utf-8", errors="replace") as fh:
            return sum(1 for line in fh if line.strip())
    except OSError:
        return 0


def file_defs(root: str, rel: str) -> int:
    try:
        with open(os.path.join(root, rel), encoding="utf-8", errors="replace") as fh:
            return len(DEF_RE.findall(fh.read()))
    except OSError:
        return 0


def select_files(root: str, main_package_only: bool = True, min_share: float = 0.2, skip=()) -> tuple[list, dict]:
    """Non-test Python files used for the graph. With main_package_only, keep the top-level
    package (first path part after an optional src/; loose root files form one group) with the
    most function definitions, plus any other group holding at least `min_share` of them. This
    drops example corpora, demos, benchmark data and side tools outside the main package."""
    skip = set(skip)
    files = [f for f in list_python_files(root) if f not in skip]
    strip = strip_prefixes(root, files)
    # groups keep lib/ whole (matplotlib's lib/ holds matplotlib and mpl_toolkits, one library), so the file
    # selection is the same as before 0.3.1; only module names drop the lib/ prefix
    gstrip = tuple(p for p in strip if p != "lib")
    lines = {f: file_lines(root, f) for f in files}
    defs = {f: file_defs(root, f) for f in files}
    groups: dict[str, list] = {}
    for f in files:
        g = groups.setdefault(_top_group(f, gstrip), [0, 0])
        g[0] += defs[f]
        g[1] += lines[f]
    total_defs = sum(v[0] for v in groups.values())
    info = {"rule": "main package by function definitions" if main_package_only else "all non-test Python files",
            "groups": {g: {"defs": v[0], "lines": v[1]} for g, v in sorted(groups.items(), key=lambda kv: -kv[1][0])},
            "skipped_files": sorted(skip)}
    if main_package_only and groups:
        best = max(groups.items(), key=lambda kv: (kv[1][0], kv[1][1], kv[0]))[0]
        keep = {g for g, v in groups.items() if g == best or (total_defs and v[0] / total_defs >= min_share)}
        files = [f for f in files if _top_group(f, gstrip) in keep]
        info["kept_groups"] = sorted(keep)
    info["src_is_package"] = "src" not in strip
    if "lib" in strip:
        info["lib_is_layout_prefix"] = True
    info["n_files"] = len(files)
    info["n_lines"] = sum(lines[f] for f in files)
    info["n_defs"] = sum(defs[f] for f in files)
    return files, info


@dataclass
class ClassInfo:
    qname: str
    module: str
    node: ast.ClassDef
    methods: dict = field(default_factory=dict)        # name -> method qname
    property_methods: set = field(default_factory=set)  # names that are properties
    ambiguous_methods: set = field(default_factory=set)
    base_refs: list = field(default_factory=list)       # resolved: ("class", qn) | ("foreign", text)
    self_attrs: set = field(default_factory=set)        # names assigned as self.<name>


@dataclass
class ModuleInfo:
    name: str
    is_pkg: bool
    path: str
    tree: ast.Module
    bindings: dict = field(default_factory=dict)  # name -> list of binding tuples


@dataclass
class FuncInfo:
    qname: str
    module: str
    cls: str | None          # enclosing class qname, if a method
    node: ast.AST
    kind: str                # "function" | "method"
    first_param: str | None
    is_static: bool
    is_classmethod: bool


class Extractor:
    def __init__(self, root: str, files: list | None = None):
        self.root = root
        self.files = files
        self.modules: dict[str, ModuleInfo] = {}
        self.classes: dict[str, ClassInfo] = {}
        self.funcs: dict[str, FuncInfo] = {}
        self.parse_errors: list[str] = []
        self.stats = {"calls_seen": 0, "calls_resolved": 0}

    # ------------------------------------------------------------------ load
    def load(self) -> None:
        files = self.files if self.files is not None else list_python_files(self.root)
        strip = strip_prefixes(self.root, files)
        for rel in files:
            modname, is_pkg = module_name_for(rel, strip)
            if not modname:
                continue
            try:
                with open(os.path.join(self.root, rel), "rb") as fh:
                    src = fh.read()
                tree = ast.parse(src, filename=rel)
            except (SyntaxError, ValueError, UnicodeDecodeError) as exc:
                self.parse_errors.append(f"{rel}: {exc.__class__.__name__}")
                continue
            if modname in self.modules:  # duplicate module path (e.g. two layouts)
                self.parse_errors.append(f"{rel}: duplicate module {modname}")
                continue
            self.modules[modname] = ModuleInfo(modname, is_pkg, rel, tree)
        for mod in self.modules.values():
            self._collect_module(mod)
        for cinfo in self.classes.values():
            cinfo.base_refs = [self._resolve_base(cinfo, b) for b in cinfo.node.bases]

    @staticmethod
    def _toplevel_stmts(body):
        """Yield statements at this block level, descending into if/try/with blocks."""
        for st in body:
            if isinstance(st, (ast.If, ast.With, ast.AsyncWith)):
                yield from Extractor._toplevel_stmts(st.body)
                yield from Extractor._toplevel_stmts(getattr(st, "orelse", []))
            elif isinstance(st, ast.Try) or (hasattr(ast, "TryStar") and isinstance(st, getattr(ast, "TryStar"))):
                yield from Extractor._toplevel_stmts(st.body)
                for h in st.handlers:
                    yield from Extractor._toplevel_stmts(h.body)
                yield from Extractor._toplevel_stmts(st.orelse)
                yield from Extractor._toplevel_stmts(st.finalbody)
            else:
                yield st

    def _bind(self, table: dict, name: str, binding: tuple) -> None:
        table.setdefault(name, []).append(binding)

    def _collect_module(self, mod: ModuleInfo) -> None:
        for st in self._toplevel_stmts(mod.tree.body):
            if isinstance(st, (ast.FunctionDef, ast.AsyncFunctionDef)):
                qn = f"{mod.name}.{st.name}"
                self._bind(mod.bindings, st.name, ("func", qn, self._is_overload(st)))
                if qn not in self.funcs:
                    self.funcs[qn] = FuncInfo(qn, mod.name, None, st, "function", None, False, False)
            elif isinstance(st, ast.ClassDef):
                qn = f"{mod.name}.{st.name}"
                self._bind(mod.bindings, st.name, ("class", qn))
                self._collect_class(mod, st, qn)
            elif isinstance(st, ast.Import):
                for a in st.names:
                    if a.asname:
                        self._bind(mod.bindings, a.asname, ("import_module", a.name))
                    else:
                        head = a.name.split(".")[0]
                        self._bind(mod.bindings, head, ("import_module", head))
            elif isinstance(st, ast.ImportFrom):
                base = self._resolve_relative(mod, st.module, st.level)
                if base is None:
                    continue
                for a in st.names:
                    if a.name == "*":
                        self._bind(mod.bindings, "*", ("star", base))
                        continue
                    self._bind(mod.bindings, a.asname or a.name, ("import_from", base, a.name))
            elif isinstance(st, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
                targets = st.targets if isinstance(st, ast.Assign) else [st.target]
                value = st.value
                for t in targets:
                    for nm in self._store_names(t):
                        if (isinstance(st, ast.Assign) and len(st.targets) == 1
                                and isinstance(t, ast.Name) and isinstance(value, ast.Name)):
                            self._bind(mod.bindings, nm, ("alias", value.id))
                        else:
                            self._bind(mod.bindings, nm, ("other",))
            elif isinstance(st, (ast.For, ast.AsyncFor)):
                for nm in self._store_names(st.target):
                    self._bind(mod.bindings, nm, ("other",))

    @staticmethod
    def _store_names(target) -> list[str]:
        out = []
        for n in ast.walk(target):
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store):
                out.append(n.id)
            elif isinstance(n, ast.Starred) and isinstance(n.value, ast.Name):
                out.append(n.value.id)
        return out

    @staticmethod
    def _decorator_names(fn) -> list[str]:
        names = []
        for d in fn.decorator_list:
            node = d.func if isinstance(d, ast.Call) else d
            if isinstance(node, ast.Name):
                names.append(node.id)
            elif isinstance(node, ast.Attribute):
                names.append(node.attr)
        return names

    def _is_overload(self, fn) -> bool:
        return "overload" in self._decorator_names(fn)

    def _collect_class(self, mod: ModuleInfo, cnode: ast.ClassDef, cqn: str) -> None:
        if cqn in self.classes:
            return
        cinfo = ClassInfo(cqn, mod.name, cnode)
        self.classes[cqn] = cinfo
        defs: dict[str, list] = {}
        for st in self._toplevel_stmts(cnode.body):
            if isinstance(st, (ast.FunctionDef, ast.AsyncFunctionDef)):
                defs.setdefault(st.name, []).append(st)
            elif isinstance(st, ast.ClassDef):
                self._collect_class(mod, st, f"{cqn}.{st.name}")
            elif isinstance(st, (ast.Assign, ast.AnnAssign)):
                targets = st.targets if isinstance(st, ast.Assign) else [st.target]
                for t in targets:
                    for nm in self._store_names(t):
                        # class attribute with the same name as a method makes it ambiguous
                        cinfo.ambiguous_methods.add(nm)
        for name, fns in defs.items():
            decos = [set(self._decorator_names(f)) for f in fns]
            if any(d & PROPERTY_DECORATORS or any(x in ("setter", "getter", "deleter") for x in d) for d in decos):
                cinfo.property_methods.add(name)
            impl = [f for f in fns if "overload" not in self._decorator_names(f)]
            if len(impl) != 1:
                cinfo.ambiguous_methods.add(name)
                chosen = impl[-1] if impl else fns[-1]
            else:
                chosen = impl[0]
            mqn = f"{cqn}.{name}"
            d = set(self._decorator_names(chosen))
            args = chosen.args
            params = [a.arg for a in (args.posonlyargs + args.args)]
            fi = FuncInfo(mqn, mod.name, cqn, chosen, "method",
                          params[0] if params else None,
                          "staticmethod" in d, "classmethod" in d)
            self.funcs[mqn] = fi
            cinfo.methods[name] = mqn
        # instance attributes assigned via self.<name> = ... in any method
        for fns in defs.values():
            for f in fns:
                params = [a.arg for a in (f.args.posonlyargs + f.args.args)]
                if not params:
                    continue
                selfname = params[0]
                static = "staticmethod" in self._decorator_names(f)
                for n in ast.walk(f):
                    if (isinstance(n, ast.Attribute) and isinstance(n.ctx, ast.Store)
                            and isinstance(n.value, ast.Name) and n.value.id == selfname):
                        cinfo.self_attrs.add(n.attr)
                    elif (isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "setattr"
                          and not static and n.args and isinstance(n.args[0], ast.Name)
                          and n.args[0].id == selfname):
                        # setattr(self, "name", ...) sets that one attribute. setattr(self, <expression>,
                        # ...) could replace any method, so it makes every attribute uncertain, except
                        # in __setstate__, which restores pickled instance state. A static method's
                        # first parameter is not the instance, so its setattr calls are ignored.
                        name = n.args[1] if len(n.args) >= 2 else None
                        if isinstance(name, ast.Constant) and isinstance(name.value, str):
                            cinfo.self_attrs.add(name.value)
                        elif f.name != "__setstate__":
                            cinfo.self_attrs.add("*")

    def _resolve_relative(self, mod: ModuleInfo, module: str | None, level: int) -> str | None:
        if level == 0:
            return module
        pkg_parts = mod.name.split(".") if mod.is_pkg else mod.name.split(".")[:-1]
        up = level - 1
        if up > len(pkg_parts):
            return None
        base_parts = pkg_parts[: len(pkg_parts) - up] if up else pkg_parts
        base = ".".join(base_parts)
        if module:
            return f"{base}.{module}" if base else module
        return base or None

    # ------------------------------------------------------------ resolution
    def resolve_name_in_module(self, modname: str, name: str, seen=None):
        """Resolve a module-level name. Returns ("func", qn) | ("class", qn) | ("module", m) | None."""
        if seen is None:
            seen = set()
        key = (modname, name)
        if key in seen:
            return None
        seen.add(key)
        mod = self.modules.get(modname)
        if mod is None:
            return None
        bs = mod.bindings.get(name)
        if bs:
            real = [b for b in bs if not (b[0] == "func" and b[2])]  # drop @overload stubs
            if not real:
                real = bs[-1:]
            if len(real) != 1:
                return None  # bound more than once at module level: ambiguous
            return self._resolve_binding(modname, real[0], seen)
        sub = f"{modname}.{name}"
        if sub in self.modules:
            return ("module", sub)
        stars = mod.bindings.get("*", [])
        hits = []
        for st in stars:
            r = self.resolve_name_in_module(st[1], name, seen)
            if r is not None:
                hits.append(r)
        if len(hits) == 1:
            return hits[0]
        return None

    def _resolve_binding(self, modname: str, b: tuple, seen):
        kind = b[0]
        if kind == "func":
            return ("func", b[1])
        if kind == "class":
            return ("class", b[1])
        if kind == "import_module":
            return ("module", b[1]) if b[1] in self.modules else None
        if kind == "import_from":
            base, attr = b[1], b[2]
            sub = f"{base}.{attr}"
            if sub in self.modules:
                return ("module", sub)
            if base in self.modules:
                return self.resolve_name_in_module(base, attr, seen)
            return None
        if kind == "alias":
            return self.resolve_name_in_module(modname, b[1], seen)
        return None

    def resolve_attr_chain(self, start, attrs: list[str]):
        """Walk attributes from a resolved start ('module' or 'class')."""
        cur = start
        for i, a in enumerate(attrs):
            if cur is None:
                return None
            if cur[0] == "module":
                cur = self.resolve_name_in_module(cur[1], a)
            elif cur[0] == "class":
                if i != len(attrs) - 1:
                    nested = f"{cur[1]}.{a}"
                    if nested in self.classes:
                        cur = ("class", nested)
                        continue
                    return None
                m = self.lookup_method(cur[1], a, skip_self=False, check_self_attrs=False)
                return ("func", m) if m else None
            else:
                return None
        return cur

    def mro(self, cqn: str) -> list:
        """Depth-first, left-to-right order with duplicates removed (keeps last occurrence,
        which approximates C3 for simple hierarchies). Foreign bases appear as ('foreign', text)."""
        order: list = []

        def visit(ref, depth=0):
            if depth > 50:
                return
            order.append(ref)
            if ref[0] == "class" and ref[1] in self.classes:
                for b in self.classes[ref[1]].base_refs:
                    visit(b, depth + 1)

        visit(("class", cqn))
        seen_last = {}
        for i, r in enumerate(order):
            seen_last[r] = i
        return [r for i, r in enumerate(order) if seen_last[r] == i]

    def lookup_method(self, cqn: str, name: str, skip_self: bool, check_self_attrs: bool):
        order = self.mro(cqn)
        if skip_self:
            order = order[1:]
        if check_self_attrs:
            for ref in self.mro(cqn):
                if ref[0] == "class" and ref[1] in self.classes:
                    sa = self.classes[ref[1]].self_attrs
                    if name in sa or "*" in sa:
                        return None
        for ref in order:
            if ref[0] != "class" or ref[1] not in self.classes:
                return None  # a foreign base comes first: it might define the name
            ci = self.classes[ref[1]]
            if name in ci.methods:
                if name in ci.property_methods or name in ci.ambiguous_methods:
                    return None
                return ci.methods[name]
            if name in ci.ambiguous_methods:
                return None
        return None

    def _resolve_base(self, cinfo: ClassInfo, expr):
        dotted = self._dotted(expr)
        if dotted is None:
            return ("foreign", ast.dump(expr)[:60])
        parts = dotted.split(".")
        mod = cinfo.module
        # a base may refer to an enclosing class's sibling; only module-level lookup here
        r = self.resolve_name_in_module(mod, parts[0])
        if r is not None and len(parts) > 1:
            r = self.resolve_attr_chain(r, parts[1:]) if r[0] in ("module", "class") else None
        if r is not None and r[0] == "class":
            return ("class", r[1])
        return ("foreign", dotted)

    @staticmethod
    def _dotted(expr) -> str | None:
        parts = []
        while isinstance(expr, ast.Attribute):
            parts.append(expr.attr)
            expr = expr.value
        if isinstance(expr, ast.Name):
            parts.append(expr.id)
            return ".".join(reversed(parts))
        return None

    def constructor_target(self, cqn: str):
        return self.lookup_method(cqn, "__init__", skip_self=False, check_self_attrs=False)

    # -------------------------------------------------------------- edges
    def _local_names(self, fnode) -> tuple[set, dict, set]:
        """Names bound inside the function subtree, and names bound only by a local import."""
        bound: dict[str, list] = {}

        def add(name, b):
            bound.setdefault(name, []).append(b)

        args = fnode.args
        for a in args.posonlyargs + args.args + args.kwonlyargs:
            add(a.arg, ("param",))
        if args.vararg:
            add(args.vararg.arg, ("param",))
        if args.kwarg:
            add(args.kwarg.arg, ("param",))
        for n in ast.walk(fnode):
            if n is fnode:
                continue
            if isinstance(n, ast.Name) and isinstance(n.ctx, (ast.Store, ast.Del)):
                add(n.id, ("store",))
            elif isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                add(n.name, ("store",))
                if not isinstance(n, ast.ClassDef):
                    a2 = n.args
                    for a in a2.posonlyargs + a2.args + a2.kwonlyargs:
                        add(a.arg, ("param",))
                    if a2.vararg:
                        add(a2.vararg.arg, ("param",))
                    if a2.kwarg:
                        add(a2.kwarg.arg, ("param",))
            elif isinstance(n, ast.Lambda):
                for a in n.args.posonlyargs + n.args.args + n.args.kwonlyargs:
                    add(a.arg, ("param",))
            elif isinstance(n, (ast.Global, ast.Nonlocal)):
                for nm in n.names:
                    add(nm, ("store",))
            elif isinstance(n, ast.ExceptHandler) and n.name:
                add(n.name, ("store",))
            elif isinstance(n, ast.alias):
                pass
            elif isinstance(n, ast.Import):
                for a in n.names:
                    nm = a.asname or a.name.split(".")[0]
                    add(nm, ("import_module", a.name if a.asname else a.name.split(".")[0]))
            elif isinstance(n, ast.ImportFrom):
                for a in n.names:
                    if a.name == "*":
                        continue
                    add(a.asname or a.name, ("import_from", n.module, n.level, a.name))
            elif hasattr(ast, "MatchAs") and isinstance(n, getattr(ast, "MatchAs")) and n.name:
                add(n.name, ("store",))
        shadow = set()
        local_imports = {}
        reassigned = set()
        for nm, bs in bound.items():
            if len(bs) == 1 and bs[0][0] in ("import_module", "import_from"):
                local_imports[nm] = bs[0]
            else:
                shadow.add(nm)
            if any(b[0] != "param" for b in bs) or len(bs) > 1:
                reassigned.add(nm)
        return shadow, local_imports, reassigned

    def _resolve_local_import(self, fi: FuncInfo, b: tuple):
        mod = self.modules[fi.module]
        if b[0] == "import_module":
            return ("module", b[1]) if b[1] in self.modules else None
        base = self._resolve_relative(mod, b[1], b[2])
        if base is None:
            return None
        return self._resolve_binding(fi.module, ("import_from", base, b[3]), set())

    def _resolve_head(self, fi: FuncInfo, name: str, shadow: set, local_imports: dict):
        if name in local_imports:
            return self._resolve_local_import(fi, local_imports[name])
        if name in shadow:
            return None
        return self.resolve_name_in_module(fi.module, name)

    def resolve_call(self, fi: FuncInfo, call: ast.Call, shadow: set, local_imports: dict,
                     reassigned: set = frozenset()):
        f = call.func
        # super().m(...)
        if (isinstance(f, ast.Attribute) and isinstance(f.value, ast.Call)
                and isinstance(f.value.func, ast.Name) and f.value.func.id == "super"
                and fi.cls is not None and "super" not in shadow):
            return self.lookup_method(fi.cls, f.attr, skip_self=True, check_self_attrs=False)
        if isinstance(f, ast.Name):
            r = self._resolve_head(fi, f.id, shadow, local_imports)
            return self._callable_target(r)
        dotted = self._dotted(f)
        if dotted is None:
            return None
        parts = dotted.split(".")
        head, attrs = parts[0], parts[1:]
        # self.m(...) / cls.m(...): first positional parameter of a non-static method, never reassigned
        if fi.cls is not None and not fi.is_static and fi.first_param and head == fi.first_param:
            if len(attrs) != 1 or head in reassigned:
                return None
            return self.lookup_method(fi.cls, attrs[0], skip_self=False,
                                      check_self_attrs=not fi.is_classmethod)
        r = self._resolve_head(fi, head, shadow, local_imports)
        if r is None or r[0] not in ("module", "class"):
            return None
        r = self.resolve_attr_chain(r, attrs)
        return self._callable_target(r)

    def _callable_target(self, r):
        if r is None:
            return None
        if r[0] == "func":
            return r[1] if r[1] in self.funcs else None
        if r[0] == "class":
            return self.constructor_target(r[1])
        return None

    def edges(self) -> list[tuple[str, str]]:
        out = set()
        for fi in self.funcs.values():
            shadow, local_imports, reassigned = self._local_names(fi.node)
            # walk the body only: decorators and default values run at definition time
            for n in (x for st in fi.node.body for x in ast.walk(st)):
                if isinstance(n, ast.Call):
                    self.stats["calls_seen"] += 1
                    tgt = self.resolve_call(fi, n, shadow, local_imports, reassigned)
                    if tgt and tgt in self.funcs and tgt != fi.qname:
                        self.stats["calls_resolved"] += 1
                        out.add((fi.qname, tgt))
        return sorted(out)

    # ------------------------------------------------------------- output
    def node_records(self) -> list[dict]:
        recs = []
        for qn, fi in sorted(self.funcs.items()):
            recs.append({
                "id": qn,
                "kind": fi.kind,
                "module": fi.module,
                "class": fi.cls,
                "name": qn.rsplit(".", 1)[-1],
                "path": self.modules[fi.module].path,
                "lineno": getattr(fi.node, "lineno", None),
                "end_lineno": getattr(fi.node, "end_lineno", None),
            })
        return recs


def git_head(root: str) -> str | None:
    try:
        return subprocess.run(["git", "-C", root, "rev-parse", "HEAD"], capture_output=True,
                              text=True, check=True).stdout.strip()
    except Exception:
        return None


def extract(root: str, repo_label: str | None = None, links_key: str = "links", files: list | None = None,
            file_info: dict | None = None) -> dict:
    ex = Extractor(root, files)
    ex.load()
    edges = ex.edges()
    nodes = ex.node_records()
    return {
        "directed": True,
        "multigraph": False,
        "graph": {
            "repo": repo_label or os.path.basename(os.path.abspath(root)),
            "commit": git_head(root),
            "extractor": "ngraph.extract",
            "extractor_version": EXTRACTOR_VERSION,
            "python": sys.version.split()[0],
            "n_modules": len(ex.modules),
            "parse_errors": ex.parse_errors,
            "calls_seen": ex.stats["calls_seen"],
            "calls_resolved": ex.stats["calls_resolved"],
            "file_selection": file_info or {"rule": "all non-test Python files"},
        },
        "nodes": nodes,
        links_key: [{"source": s, "target": t, "type": "calls"} for s, t in edges],
    }


def mirrored(graph: dict, links_key: str = "links") -> dict:
    """Official-like view: every edge mirrored, single 'calls' type (as other participants' public notebooks
    describe the official graphs; to be checked against the competition data at MC3)."""
    g = json.loads(json.dumps(graph))
    pairs = {(e["source"], e["target"]) for e in graph[links_key]}
    pairs |= {(t, s) for s, t in pairs}
    g[links_key] = [{"source": s, "target": t, "type": "calls"} for s, t in sorted(pairs)]
    g["graph"]["view"] = "mirrored"
    return g


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("root")
    ap.add_argument("--label")
    ap.add_argument("--out", required=True)
    ap.add_argument("--mirrored-out")
    ap.add_argument("--all-files", action="store_true", help="do not restrict to the main package")
    args = ap.parse_args()
    fs, finfo = select_files(args.root, main_package_only=not args.all_files)
    g = extract(args.root, args.label, files=fs, file_info=finfo)
    with open(args.out, "w") as fh:
        json.dump(g, fh, indent=1)
    if args.mirrored_out:
        with open(args.mirrored_out, "w") as fh:
            json.dump(mirrored(g), fh, indent=1)
    gs = g["graph"]
    print(f"{gs['repo']}: {len(g['nodes'])} nodes, {len(g['links'])} edges, "
          f"{gs['calls_resolved']}/{gs['calls_seen']} calls resolved, {len(gs['parse_errors'])} parse errors")
