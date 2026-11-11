"""Minimal reader for the metadata section of a GGUF file (no tensors are read).

Used to record the chat template, special-token ids and tokenizer settings of each model
file next to its SHA-256, and to inspect vocab-only GGUFs. Follows the GGUF layout:
magic "GGUF", uint32 version, uint64 tensor count, uint64 key/value count, then typed
key/value pairs (little-endian). Large arrays (the vocabulary itself) are summarised by
length unless `keep_arrays` is set.
"""

from __future__ import annotations

import hashlib
import json
import struct
import sys

_SCALARS = {0: "<B", 1: "<b", 2: "<H", 3: "<h", 4: "<I", 5: "<i", 6: "<f", 7: "<?", 10: "<Q", 11: "<q", 12: "<d"}
_STRING, _ARRAY = 8, 9


class _Buf:
    def __init__(self, fh):
        self.fh = fh

    def read(self, fmt):
        size = struct.calcsize(fmt)
        data = self.fh.read(size)
        if len(data) != size:
            raise EOFError("truncated GGUF header")
        return struct.unpack(fmt, data)[0]

    def string(self):
        n = self.read("<Q")
        return self.fh.read(n).decode("utf-8", errors="replace")


def _value(buf: _Buf, vtype: int, keep_arrays: bool, max_keep: int):
    if vtype in _SCALARS:
        return buf.read(_SCALARS[vtype])
    if vtype == _STRING:
        return buf.string()
    if vtype == _ARRAY:
        etype = buf.read("<I")
        n = buf.read("<Q")
        out = []
        for i in range(n):
            v = _value(buf, etype, keep_arrays, max_keep)
            if keep_arrays or i < max_keep:
                out.append(v)
        return out if (keep_arrays or n <= max_keep) else {"length": n, "head": out}
    raise ValueError(f"unknown GGUF value type {vtype}")


def read_metadata(path: str, keep_arrays: bool = False, max_keep: int = 8) -> dict:
    with open(path, "rb") as fh:
        buf = _Buf(fh)
        if fh.read(4) != b"GGUF":
            raise ValueError("not a GGUF file")
        version = buf.read("<I")
        n_tensors = buf.read("<Q")
        n_kv = buf.read("<Q")
        meta = {"gguf.version": version, "gguf.tensor_count": n_tensors}
        for _ in range(n_kv):
            key = buf.string()
            vtype = buf.read("<I")
            meta[key] = _value(buf, vtype, keep_arrays, max_keep)
    return meta


def sha256(path: str, chunk: int = 1 << 24) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            b = fh.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Print GGUF metadata (chat template, special tokens, tokenizer)")
    ap.add_argument("gguf")
    ap.add_argument("--sha256", action="store_true", help="also hash the whole file (slow for big models)")
    ap.add_argument("--out")
    a = ap.parse_args()
    m = read_metadata(a.gguf)
    if a.sha256:
        m["file.sha256"] = sha256(a.gguf)
    txt = json.dumps(m, indent=1, ensure_ascii=False)
    if a.out:
        with open(a.out, "w") as fh:
            fh.write(txt)
    sys.stdout.write(txt[:20000] + "\n")
