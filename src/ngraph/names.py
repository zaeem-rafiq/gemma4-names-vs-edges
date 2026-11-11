"""Neutral (pseudo-word) names for Study A versions G2 and G4.

Renaming works on sub-tokens. Each name component (a dotted path part such as
`_client`, `AsyncClient` or `build_request`) is split into underscore-separated
parts and camel-case humps; every alphabetic hump is a sub-token (`async`,
`client`, `build`, `request`, `http` ...). Within one item every sub-token is mapped
to one pronounceable pseudo-word, used everywhere that sub-token occurs, with the
original's case pattern (lower / Capitalised / UPPER). So `request`, `build_request`
and `_api.request` keep sharing a piece in the neutral version, just as they share
a word in the real version: the neutral names remove meaning and memory of the
repository, not the lexical structure inside the prompt. Leading and trailing
underscores, underscore positions and digits are kept.

Python's own protocol names (__init__, __call__, __enter__ ..., listed in STD_DUNDERS)
are kept unchanged, because they are language vocabulary, not project vocabulary.
Any other double-underscore name (for example rich's __rich_console__) is renamed
like an ordinary name and keeps its underscores.

STD_DUNDERS and RESERVED are frozen literals (built once from Python 3.13's builtin
types, collections.abc, contextlib, os.PathLike, keyword and builtins, plus a few
Python 2 protocol names) so that generated items do not depend on the Python version.

Token-count matching: each sub-token's pseudo-word is drawn so that its token count
under `count_tokens` equals the sub-token's; then a repair pass re-draws sub-tokens
while that lowers the total gap between renamed and original components. Remaining
gaps are recorded per component. `count_tokens` is pluggable. The default
(`approx_token_count`) is only a stand-in for development in the cloud sandbox; the
frozen items must be regenerated with the Gemma tokenizer (for example from the GGUF
vocabulary on the Mac) before pre-registration.
"""

from __future__ import annotations

import random
import re
from typing import Callable

CONSONANTS = "bdfgklmnprstvz"
VOWELS = "aeiou"
CODAS = ["", "", "", "n", "r", "l", "s", "k"]
STD_DUNDERS = frozenset("""
    __abs__ __add__ __aenter__ __aexit__ __aiter__ __alloc__ __and__ __anext__ __await__
    __bool__ __buffer__ __bytes__ __call__ __cause__ __ceil__ __class__ __class_getitem__
    __cmp__ __coerce__ __complex__ __contains__ __context__ __copy__ __deepcopy__ __del__
    __delattr__ __delete__ __delitem__ __delslice__ __dir__ __div__ __divmod__ __enter__ __eq__
    __exit__ __float__ __floor__ __floordiv__ __format__ __fspath__ __ge__ __get__ __getattr__
    __getattribute__ __getformat__ __getinitargs__ __getitem__ __getnewargs__ __getnewargs_ex__
    __getslice__ __getstate__ __gt__ __hash__ __hex__ __iadd__ __iand__ __idiv__ __ifloordiv__
    __ilshift__ __imatmul__ __imod__ __imul__ __index__ __init__ __init_subclass__
    __instancecheck__ __int__ __invert__ __ior__ __ipow__ __irshift__ __isub__ __iter__
    __itruediv__ __ixor__ __le__ __len__ __length_hint__ __long__ __lshift__ __lt__ __main__
    __matmul__ __missing__ __mod__ __mro_entries__ __mul__ __ne__ __neg__ __new__ __next__
    __nonzero__ __oct__ __or__ __pos__ __post_init__ __pow__ __prepare__ __radd__ __rand__
    __rdiv__ __rdivmod__ __reduce__ __reduce_ex__ __release_buffer__ __repr__ __reversed__
    __rfloordiv__ __rlshift__ __rmatmul__ __rmod__ __rmul__ __ror__ __round__ __rpow__
    __rrshift__ __rshift__ __rsub__ __rtruediv__ __rxor__ __set__ __set_name__ __setattr__
    __setitem__ __setslice__ __setstate__ __sizeof__ __str__ __sub__ __subclasscheck__
    __subclasses__ __subclasshook__ __suppress_context__ __traceback__ __truediv__ __trunc__
    __unicode__ __xor__
""".split())

RESERVED = frozenset("""
    _ abs aiter all and anext any as ascii assert async await bin bool break breakpoint
    bytearray bytes callable case chr class classmethod cls compile complex continue copyright
    credits def del delattr dict dir divmod elif else enumerate eval except exec exit false
    filter finally float for format from frozenset getattr global globals hasattr hash help hex
    id if import in input int is isinstance issubclass iter lambda len license list locals map
    match max memoryview min next none nonlocal not object oct open or ord pass pow print
    property quit raise range repr return reversed round self set setattr slice sorted
    staticmethod str sum super true try tuple type vars while with yield zip
""".split())


def split_subtokens(name: str) -> list[str]:
    """Split an identifier into lower-case sub-tokens on underscores, digits and case changes."""
    out = []
    for part in re.split(r"[_\W\d]+", name):
        if not part:
            continue
        out.extend(p.lower() for p in re.findall(r"[A-Z]+(?=[A-Z][a-z]|$)|[A-Z]?[a-z]+|[A-Z]+", part))
    return [t for t in out if t]


def approx_token_count(s: str) -> int:
    """Rough stand-in for a subword tokenizer: about one token per 4 letters of each sub-token,
    plus one per underscore/dot. NOT the Gemma tokenizer."""
    n = 0
    for piece in re.split(r"([_.])", s):
        if piece in ("_", "."):
            n += 1
        elif piece:
            for sub in re.findall(r"[A-Z]+(?=[A-Z][a-z]|$)|[A-Z]?[a-z]+|[A-Z]+|\d+", piece):
                n += max(1, -(-len(sub) // 4))
    return max(n, 1)


HUMP_RE = re.compile(r"[A-Z]+(?=[A-Z][a-z]|\d|$)|[A-Z]?[a-z]+|[A-Z]+|\d+")


# Substrings that make a generated name read as an offensive word. A question whose neutral names contain one
# is named again (items.build_versions). Added on 8 Nov 2026 after scans found such names in 10 questions (for
# example "raper", "nazizes", "pedo" and "pisso", and, for the short stems "nig", "milf" and "sperm", "nigu",
# "posmilfas" and "disperme"). Widened the same day (the wider check): each name is now also read with "_" and
# "-" removed (the first version had missed "kil_ra_pe" and "kir_na_zi"), and the second group below adds
# words the first list lacked that the generator can write ("fuk", "paki", "puto", "figa" and others). A
# further scan found "puki" (Malay), added at the end, and "fok" (Afrikaans) and "pula" (Romanian), which are
# blocked only when a whole pseudo-word equals one of them (WHOLE_WORD_BLOCKED, checked in
# items.offensive_naming), the narrowest rule that renames the questions in which they were found.
# Pseudo-words use only the letters in CONSONANTS and VOWELS, so the entries that need c, h, j or w
# (UNWRITABLE_BLOCKED) can never match; they are kept so that the list reads as intended. Dots between the
# parts of a qualified name, and digits, are not removed.
OFFENSIVE_SUBSTRINGS = ("rape", "nazi", "hitler", "pedo", "piss", "fuck", "shit", "cunt", "nig", "fagg", "slut",
                        "whore", "dick", "cock", "porn", "penis", "vagin", "bitch", "kike", "chink", "retard",
                        "molest", "dildo", "jizz", "wank", "twat", "milf", "sperm",
                        "fuk", "paki", "puta", "puto", "pute", "figa", "boner", "rapist", "kafir", "neger", "spaz",
                        "tard", "semen", "vulva", "orgasm", "masturb", "fagot", "lesbo", "sodomi", "gestapo",
                        "taliban", "merde", "merda", "salope", "verga", "foda", "puki")
UNWRITABLE_BLOCKED = ("hitler", "fuck", "shit", "cunt", "whore", "dick", "cock", "bitch", "chink", "jizz", "wank",
                      "twat")
# Pseudo-words blocked only as a whole (compared in lower case; see the comment above).
WHOLE_WORD_BLOCKED = ("fok", "pula")


def offensive(s: str) -> bool:
    """True if `s`, in lower case, contains one of OFFENSIVE_SUBSTRINGS as written or with "_" and "-"
    removed (so a word split across name parts, as in "kil_ra_pe", is found)."""
    low = s.lower()
    joined = low.replace("_", "").replace("-", "")
    return any(b in low or b in joined for b in OFFENSIVE_SUBSTRINGS)


def _syllable(rng: random.Random) -> str:
    return rng.choice(CONSONANTS) + rng.choice(VOWELS) + rng.choice(CODAS)


def _pseudo_word(rng: random.Random, sub: str, n_tokens: int | None = None, widen: int = 0) -> str:
    """A lower-case pseudo-word for one sub-token: a consonant for a 1-letter sub-token,
    consonant+vowel for a 2-letter one, otherwise 1-4 syllables. With `n_tokens` (the
    sub-token's own token count) the syllable count is centred on it, since one syllable is
    often one token; without it, about one syllable per 3 letters. Both get a +-1 jitter.
    `widen` moves a 1- or 2-letter sub-token to the next longer shape (consonant -> CV ->
    CV + coda); it is used only when the shorter shape has no free pseudo-word left in the item."""
    short = len(sub) + widen
    if len(sub) <= 2 and short == 1:
        return rng.choice(CONSONANTS)
    if len(sub) <= 2 and short == 2:
        return rng.choice(CONSONANTS) + rng.choice(VOWELS)
    if len(sub) <= 2:
        return rng.choice(CONSONANTS) + rng.choice(VOWELS) + rng.choice([c for c in CODAS if c])
    centre = n_tokens if n_tokens is not None else len(sub) // 3
    n_syll = max(1, min(4, centre + rng.choice([-1, 0, 0, 1])))
    return "".join(_syllable(rng) for _ in range(n_syll))


def _humps(part: str) -> list:
    """Camel-case humps of one underscore-free part as (kind, text); kind is
    lower / cap / upper / digit."""
    out = []
    for h in HUMP_RE.findall(part):
        if h.isdigit():
            out.append(("digit", h))
        elif h.isupper() and (len(h) > 1 or not out or out[-1][0] == "upper"):
            out.append(("upper", h))
        elif h[:1].isupper():
            out.append(("cap", h))
        else:
            out.append(("lower", h))
    if not out:  # e.g. only non-ASCII letters
        out.append(("lower", part or "x"))
    return out


def shape(comp: str):
    """(prefix underscores, list of parts, suffix underscores, separators between parts); each
    part is a list of humps, and the empty part inside "a__b" is an empty list. Parts are split
    on "_" and on "-" (module paths taken from folder names such as "options-strategy"), and the
    neutral name keeps the same separators."""
    m = re.match(r"^(_*)(.*?)(_*)$", comp)
    prefix, core, suffix = m.group(1), m.group(2), m.group(3)
    if not core:
        return prefix, [_humps("x")], suffix, []  # an all-underscore name gets one pseudo-word
    pieces = re.split(r"([_-])", core)
    parts, seps = pieces[0::2], pieces[1::2]
    return prefix, [(_humps(p) if p else []) for p in parts], suffix, seps


def _render(kind: str, word: str) -> str:
    if kind == "cap":
        return word.capitalize()
    if kind == "upper":
        return word.upper()
    return word


class NeutralNamer:
    """Consistent sub-token renaming for one item. Call `fit` with every component that
    will be shown (and the repository handle), then use `neutral_qname`."""

    def __init__(self, seed: int, count_tokens: Callable[[str], int] = approx_token_count,
                 forbidden_subtokens: set | None = None, max_tries: int = 400, repair_tries: int = 40,
                 syllables_by_tokens: bool | None = None, reject: Callable[[str], bool] | None = None):
        self.rng = random.Random(seed)
        self.reject = reject  # e.g. "is a common English word"; applied to pseudo-words and to name parts
        self.count_tokens = count_tokens
        # centre syllable counts on token counts for a real tokenizer; letter-based for the stand-in
        self.syllables_by_tokens = (count_tokens is not approx_token_count) if syllables_by_tokens is None \
            else syllables_by_tokens
        self.forbidden = {t for t in (forbidden_subtokens or set()) if len(t) >= 3}
        self.max_tries = max_tries
        self.repair_tries = repair_tries
        self.sub_map: dict[str, str] = {}
        self.map: dict[str, str] = {}
        self.mismatch: dict[str, tuple[int, int]] = {}
        self.widened: dict[str, int] = {}  # sub-tokens that needed a longer pseudo-word shape
        self._shapes: dict[str, tuple] = {}

    # ----------------------------------------------------------- helpers
    def _leaks(self, s: str) -> bool:
        low = s.lower()
        return any(t in low for t in self.forbidden)

    def _subs(self, comp: str) -> list:
        prefix, parts, suffix, seps = self._shapes[comp]
        return [t.lower() for humps in parts for k, t in humps if k != "digit"]

    def _compose(self, comp: str, sub_map: dict) -> str:
        prefix, parts, suffix, seps = self._shapes[comp]
        pieces = ["".join(t if k == "digit" else _render(k, sub_map[t.lower()]) for k, t in humps)
                  for humps in parts]
        core = pieces[0] + "".join(sep + piece for sep, piece in zip(seps, pieces[1:]))
        return prefix + core + suffix

    def _draw(self, sub: str, taken: set) -> str:
        target = self.count_tokens(sub)
        for widen in range(3 if len(sub) <= 2 else 1):
            best, best_gap = None, None
            for _ in range(self.max_tries):
                w = _pseudo_word(self.rng, sub, target if self.syllables_by_tokens else None, widen)
                if w == sub or w in taken or w in RESERVED or self._leaks(w) or (self.reject and len(w) > 1 and self.reject(w)):
                    continue
                gap = abs(self.count_tokens(w) - target)
                if best is None or gap < best_gap:
                    best, best_gap = w, gap
                if gap == 0:
                    break
            if best is not None:
                if widen:
                    self.widened[sub] = widen
                return best
        raise RuntimeError(f"could not draw a pseudo-word for sub-token {sub!r}")

    def _valid(self, comps: list, sub_map: dict) -> bool:
        seen = set()
        for c in comps:
            new = self._compose(c, sub_map)
            if new == c or new.lower() in RESERVED or self._leaks(new) or new in seen:
                return False
            # letter-only parts (digits are kept as they are, and "401" is a frequent "word" in wordfreq)
            if self.reject and any(self.reject(p.lower()) for p in re.split(r"[_-]", new) if len(p) > 1 and p.isalpha()):
                return False
            seen.add(new)
        return True

    def _gap(self, comps: list, sub_map: dict) -> int:
        return sum(abs(self.count_tokens(self._compose(c, sub_map)) - self.count_tokens(c)) for c in comps)

    # -------------------------------------------------------------- main
    def fit(self, components) -> None:
        comps = []
        for c in components:
            if c in STD_DUNDERS or c in self.map or c in comps:
                continue
            comps.append(c)
        if not comps:
            return
        for c in comps:
            self._shapes[c] = shape(c)
        sub_map = dict(self.sub_map)
        for c in comps:
            for t in self._subs(c):
                if t not in sub_map:
                    sub_map[t] = self._draw(t, set(sub_map.values()))
        allc = [c for c in self.map] + comps  # earlier components must stay valid too
        new_subs = [t for t in dict.fromkeys(t for c in comps for t in self._subs(c)) if t not in self.sub_map]
        # validity: no leak across hump boundaries, no reserved word, no two components alike
        for _ in range(50):
            if self._valid(allc, sub_map):
                break
            bad = next(c for c in comps if not self._valid([c], sub_map)) if any(
                not self._valid([c], sub_map) for c in comps) else comps[0]
            redraw = [t for t in self._subs(bad) if t in new_subs] or new_subs
            t = redraw[self.rng.randrange(len(redraw))]
            sub_map[t] = self._draw(t, set(v for k, v in sub_map.items() if k != t))
        else:
            raise RuntimeError("could not find a valid neutral renaming")
        # repair token-count gaps by re-drawing new sub-tokens while the total gap falls
        total = self._gap(comps, sub_map)
        for c in comps:
            if total == 0:
                break
            if self.count_tokens(self._compose(c, sub_map)) == self.count_tokens(c):
                continue
            for t in [t for t in self._subs(c) if t in new_subs]:
                for _ in range(self.repair_tries):
                    trial = dict(sub_map)
                    w = _pseudo_word(self.rng, t, self.count_tokens(t) if self.syllables_by_tokens else None)
                    if (w == t or w in RESERVED or self._leaks(w) or (self.reject and len(w) > 1 and self.reject(w))
                            or w in set(v for k, v in sub_map.items() if k != t)):
                        continue
                    trial[t] = w
                    g = self._gap(comps, trial)
                    if g < total and self._valid(allc, trial):
                        sub_map, total = trial, g
                        break
                if self.count_tokens(self._compose(c, sub_map)) == self.count_tokens(c):
                    break
        self.sub_map = sub_map
        for c in comps:
            new = self._compose(c, sub_map)
            self.map[c] = new
            a, b = self.count_tokens(c), self.count_tokens(new)
            if a != b:
                self.mismatch[c] = (a, b)

    # ------------------------------------------------- later adjustments
    def propose(self, t: str, wide: bool = False) -> str | None:
        """A fresh pseudo-word for sub-token `t` under the same constraints as the first draw
        (not yet checked against whole names; `set_sub` does that). With `wide`, the length is
        drawn more freely (1-4 syllables; consonant, CV or CV+coda for 1-2 letter sub-tokens),
        so that a name can also become shorter than its original to offset a longer one."""
        taken = {v for k, v in self.sub_map.items() if k != t}
        target = self.count_tokens(t) if self.syllables_by_tokens else None
        for _ in range(50):
            if wide and len(t) > 2:
                w = _pseudo_word(self.rng, t, self.rng.randint(1, 4))
            elif wide:
                w = _pseudo_word(self.rng, t, None, self.rng.randint(0, 2))
            else:
                w = _pseudo_word(self.rng, t, target, self.widened.get(t, 0))
            if w == t or w in taken or w in RESERVED or self._leaks(w) or (self.reject and len(w) > 1 and self.reject(w)):
                continue
            return w
        return None

    def set_sub(self, t: str, w: str) -> bool:
        """Use `w` for sub-token `t` if every fitted name stays valid; updates the name map."""
        comps = [c for c in self.map if c in self._shapes]
        if w in {v for k, v in self.sub_map.items() if k != t}:
            return False
        trial = dict(self.sub_map)
        trial[t] = w
        if not self._valid(comps, trial):
            return False
        self.sub_map = trial
        self.mismatch = {}
        for c in comps:
            new = self._compose(c, trial)
            self.map[c] = new
            a, b = self.count_tokens(c), self.count_tokens(new)
            if a != b:
                self.mismatch[c] = (a, b)
        return True

    def neutral_component(self, comp: str) -> str:
        if comp in STD_DUNDERS:
            self.map.setdefault(comp, comp)
            return comp
        if comp not in self.map:
            self.fit([comp])
        return self.map[comp]

    def neutral_qname(self, qname: str) -> str:
        return ".".join(self.neutral_component(c) for c in qname.split("."))

    @staticmethod
    def handle_component(repo: str) -> str:
        return re.sub(r"\W", "_", repo).strip("_") or "repo"

    def neutral_handle(self, repo: str) -> str:
        return self.neutral_component(self.handle_component(repo))
