import os, sys, json, collections
D = sys.argv[1]
exts = collections.Counter(); per = collections.Counter(); size = collections.Counter(); total = 0
for r, ds, fs in os.walk(D):
    rel = os.path.relpath(r, D)
    for f in fs:
        p = os.path.join(r, f); s = os.path.getsize(p); total += s
        n = f.lower()
        e = '.tar.gz' if n.endswith('.tar.gz') else (os.path.splitext(n)[1] or '(none)')
        exts[e] += 1; per[rel] += 1; size[rel] += s
print('total_files', sum(exts.values()), 'total_bytes', total)
print('EXT', exts.most_common())
print('PER FOLDER (non-repeating view)')
tops = collections.defaultdict(lambda: [0, 0, 0])
for k in per:
    parts = k.split(os.sep)
    t = parts[0]
    tops[t][0] += per[k]; tops[t][1] += size[k]; tops[t][2] += 1
for t, v in sorted(tops.items()): print(' ', t, 'files', v[0], 'bytes', v[1], 'dirs_with_files', v[2])
for k in sorted(per):
    d = k.count(os.sep)
    if k.split(os.sep)[0] in ('docker', 'sandbox', 'sample_submission', '.'):
        print('  F', k, per[k], size[k])
def typ(v):
    if isinstance(v, list): return 'list[%s]' % (typ(v[0]) if v else '?')
    if isinstance(v, dict): return 'dict{%s}' % ','.join(list(v)[:8])
    return type(v).__name__
rows = [json.loads(l) for l in open(os.path.join(D, 'tasks.jsonl'))]
print('TASKS', len(rows))
keys = collections.defaultdict(collections.Counter)
for r in rows:
    for k, v in r.items(): keys[k][typ(v)] += 1
for k, c in keys.items():
    ex = str(rows[0].get(k))[:70].replace('\n', ' ')
    print(' ', k, dict(c.most_common(4)), 'n_present', sum(c.values()), 'empty', sum(1 for r in rows if r.get(k) in (None, '', [], {})), 'ex:', ex)
