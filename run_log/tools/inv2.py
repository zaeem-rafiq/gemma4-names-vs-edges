import os, sys, json, collections, re, zipfile, struct, ast, hashlib
D = sys.argv[1]
rows = [json.loads(l) for l in open(os.path.join(D, 'tasks.jsonl'))]
print('REPOS', collections.Counter(r['repo'] for r in rows).most_common())
print('ID PREFIX', collections.Counter(r['instance_id'].rsplit('_', 1)[0] for r in rows).most_common())
print('ID regex ok', all(re.fullmatch(r'[a-z0-9_-]+_\d+', r['instance_id']) for r in rows), 'unique', len({r['instance_id'] for r in rows}))
print('EX IDS', [r['instance_id'] for r in rows[:2]])
print('created_at', min(r['created_at'] for r in rows), max(r['created_at'] for r in rows))
print('base_commit unique', len({r['base_commit'] for r in rows}), 'dups', [c for c, n in collections.Counter(r['base_commit'] for r in rows).items() if n > 1])
gs = {f[:-5] for f in os.listdir(os.path.join(D, 'graphs'))}
es = {f[:-4] for f in os.listdir(os.path.join(D, 'embeddings'))}
ss = {f[:-4] for f in os.listdir(os.path.join(D, 'snapshots'))}
def gname(r): return r['repo'].split('/')[-1] + '_' + r['base_commit']
print('graphs', len(gs), 'embeddings', len(es), 'graph==embedding names', gs == es, 'snapshots', len(ss))
print('tasks with graph by repo-short_commit', sum(gname(r) in gs for r in rows), 'tasks with graph by commit only', sum(any(g.endswith(r['base_commit']) for g in gs) for r in rows))
print('tasks without graph', [r['instance_id'] for r in rows if gname(r) not in gs][:10], 'graphs unused', [g for g in gs if g not in {gname(r) for r in rows}][:10])
print('snapshot==instance_id', ss == {r['instance_id'] for r in rows})
print('GRAPH PREFIX', collections.Counter(g.rsplit('_', 1)[0] for g in gs).most_common())
names = sorted(gs); pick = [names[0], [g for g in names if not g.startswith('fastapi')][0]]
sizes = sorted((os.path.getsize(os.path.join(D, 'graphs', g + '.json')), g) for g in names)
print('graph bytes min/max', sizes[0], sizes[-1])
def typ(v):
    if isinstance(v, list): return 'list[%s]' % (typ(v[0]) if v else '?')
    if isinstance(v, dict): return 'dict'
    return type(v).__name__
def short(v, n=90): return str(v)[:n].replace('\n', ' ')
def analyse(g):
    j = json.load(open(os.path.join(D, 'graphs', g + '.json')))
    print('\n==', g, 'top keys', {k: typ(v) for k, v in j.items()} if isinstance(j, dict) else type(j))
    for k, v in j.items():
        if not isinstance(v, (list, dict)): print('  meta', k, short(v))
        elif isinstance(v, dict) and len(v) < 15: print('  meta', k, short(v, 300))
    nk = next((k for k in j if 'node' in k.lower()), None); ek = next((k for k in j if 'edge' in k.lower() or 'link' in k.lower()), None)
    N, E = j[nk], j[ek]
    print('  nodes key', nk, type(N).__name__, len(N), '| edges key', ek, type(E).__name__, len(E))
    nl = list(N.values()) if isinstance(N, dict) else N; el = list(E.values()) if isinstance(E, dict) else E
    if isinstance(N, dict): print('  node dict key ex', short(list(N)[:3], 200))
    for name, L in (('node', nl), ('edge', el)):
        if not L: continue
        keys = collections.defaultdict(collections.Counter)
        for x in L:
            if isinstance(x, dict):
                for k, v in x.items(): keys[k][typ(v)] += 1
        print('  %s fields' % name, {k: dict(c) for k, c in keys.items()})
        print('  %s ex' % name, short(L[0], 400))
        for k, c in keys.items():
            vals = collections.Counter(str(x.get(k)) for x in L if isinstance(x, dict))
            if len(vals) <= 25: print('    values', k, vals.most_common())
    if isinstance(E, list) and E and isinstance(E[0], dict):
        s = next(k for k in E[0] if k in ('source', 'src', 'from', 'u', 'head', 'caller'))
        t = next(k for k in E[0] if k in ('target', 'dst', 'to', 'v', 'tail', 'callee'))
        ty = next((k for k in E[0] if k in ('type', 'kind', 'edge_type', 'relation', 'label')), None)
        pairs = {(e[s], e[t]) for e in E}
        rev = sum((b, a) in pairs for a, b in pairs if a != b)
        print('  direct pairs', len(pairs), 'with reverse pair present', rev, 'self loops', sum(a == b for a, b in pairs))
        if ty:
            by = collections.defaultdict(set)
            for e in E: by[e[ty]].add((e[s], e[t]))
            for k, v in by.items():
                print('   type', k, 'pairs', len(v), 'reversed in same type', sum((b, a) in v for a, b in v if a != b))
            types = list(by)
            for i, a in enumerate(types):
                for b in types[i + 1:]:
                    m = sum((y, x) in by[b] for x, y in by[a])
                    if m: print('   mirror', a, '<->', b, m, 'of', len(by[a]), len(by[b]))
for g in pick: analyse(g)
# npz header (no numpy, no pickle)
p = os.path.join(D, 'embeddings', names[0] + '.npz')
with zipfile.ZipFile(p) as z:
    for i in z.infolist():
        with z.open(i) as f:
            f.read(6); maj = f.read(2)[0]
            hl = struct.unpack('<H', f.read(2))[0] if maj == 1 else struct.unpack('<I', f.read(4))[0]
            print('NPZ', i.filename, i.file_size, f.read(hl).decode().strip())
for f in ('tasks.jsonl', 'HARNESS_README.md'):
    print('SHA', hashlib.sha256(open(os.path.join(D, f), 'rb').read()).hexdigest(), f)
for sub in ('docker', 'sandbox', 'sample_submission'):
    for r, _, fs in os.walk(os.path.join(D, sub)):
        for f in sorted(fs):
            q = os.path.join(r, f); print('SHA', hashlib.sha256(open(q, 'rb').read()).hexdigest(), os.path.relpath(q, D), os.path.getsize(q))
