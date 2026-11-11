import os, sys, json, collections, re
D = sys.argv[1]
G = os.path.join(D, 'graphs')
def load(n): return json.load(open(os.path.join(G, n + '.json')))
names = sorted(f[:-5] for f in os.listdir(G))
pick = [names[0], [g for g in names if g.startswith('rich')][0]]
for n in pick:
    j = load(n); N = j['nodes']; E = j['edges']
    print('==', n, len(N), len(E), collections.Counter(e['type'] for e in E))
    print(' node id==name', sum(x['id'] == x['name'] for x in N), 'top-level segment', collections.Counter(x['name'].split('.')[0] for x in N).most_common(8))
    print(' depth', sorted(collections.Counter(x['name'].count('.') for x in N).items()))
    kind = collections.Counter()
    for x in N:
        s = x['text'].lstrip()
        kind['class' if s.startswith('class ') else 'async def' if s.startswith('async def ') else 'def' if s.startswith('def ') else 'decorated' if s.startswith('@') else 'other'] += 1
    print(' kinds by text', kind.most_common())
    L = sorted(len(x['text']) for x in N); print(' text chars median', L[len(L)//2], 'max', L[-1], 'empty', sum(not x['text'].strip() for x in N))
    print(' text stub share', sum(bool(re.search(r':\s*\n\s*None\s*$', x['text'])) for x in N))
    ids = {x['id'] for x in N}
    print(' edge endpoints outside nodes', sum(e['source'] not in ids or e['target'] not in ids for e in E))
    p = {(e['source'], e['target']) for e in E}; nl = [(a, b) for a, b in p if a != b]
    print(' non-self pairs', len(nl), 'with reverse', sum((b, a) in p for a, b in nl), 'keys', collections.Counter(e['key'] for e in E).most_common(3))
    print(' multi edge ex', [(e['source'][:40], e['target'][:40]) for e in E if e['key'] == 1][:2])
    print(' name ex', [x['name'][:60] for x in N[:3]], 'with path sep', sum('/' in x['name'] or ';' in x['name'] for x in N))
# all graphs
tot = collections.Counter(); t2 = collections.Counter(); bad = 0
for n in names:
    j = load(n)
    t2.update(e['type'] for e in j['edges'])
    p = {(e['source'], e['target']) for e in j['edges']}; nl = [(a, b) for a, b in p if a != b]
    tot['graphs'] += 1; tot['nonself'] += len(nl); tot['rev'] += sum((b, a) in p for a, b in nl); tot['nodes'] += len(j['nodes']); tot['edges'] += len(j['edges'])
print('ALL', dict(tot), 'edge types', t2.most_common())
