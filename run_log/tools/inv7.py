import os, sys, json, re, tarfile, collections
D = sys.argv[1]
t = next(json.loads(l) for l in open(os.path.join(D, 'tasks.jsonl')) if json.loads(l)['instance_id'] == 'fastapi_15661')
print('TASK', {k: (v if len(v) < 60 else 'len=%d' % len(v)) for k, v in t.items()})
print('problem first words:', ' '.join(t['problem_statement'].split()[:8]))
print('patch files:', re.findall(r'^\+\+\+ b/(\S+)', t['patch'], re.M), 'minus:', re.findall(r'^--- (\S+)', t['patch'], re.M))
print('patch hunks', len(re.findall(r'^@@', t['patch'], re.M)), 'new file', 'new file mode' in t['patch'], 'starts with', t['patch'][:12].split('\n')[0])
print('test files:', re.findall(r'^\+\+\+ b/(\S+)', t['test_patch'], re.M))
g = 'fastapi_%s' % t['base_commit']
j = json.load(open(os.path.join(D, 'graphs', g + '.json')))
print('GRAPH', g, {k: type(v).__name__ for k, v in j.items()}, j['graph'], j['directed'], j['multigraph'])
N, E = j['nodes'], j['edges']
print('counts', len(N), len(E))
for x in N[:3]:
    print('NODE', json.dumps({'id': x['id'], 'name': x['name'], 'key_order': list(x), 'text_len': len(x['text']), 'text_first_line_len': len(x['text'].split('\n')[0]), 'text_lines': x['text'].count('\n') + 1, 'starts': x['text'].split(' ')[0]}))
for e in E[:5]: print('EDGE', json.dumps(e))
ids = [x['id'] for x in N]
print('ids unique', len(ids) == len(set(ids)), 'unique', len(set(ids)))
bad = [x['name'] for x in N if not re.fullmatch(r'[A-Za-z0-9_.]+', x['name'])]
print('names with other chars', len(bad), collections.Counter(c for b in bad for c in set(re.sub(r'[A-Za-z0-9_.]', '', b))).most_common(10), [b[:60] for b in bad[:5]])
for p in ('tests.', 'docs_src.', 'scripts.'): print('startswith', p, sum(x['name'].startswith(p) for x in N))
print('self loops', sum(e['source'] == e['target'] for e in E))
c = collections.Counter((e['source'], e['target']) for e in E)
print('dup (source,target) pairs', sum(1 for v in c.values() if v > 1), 'extra edges', sum(v - 1 for v in c.values() if v > 1), 'of which self', sum(1 for (a, b), v in c.items() if v > 1 and a == b))
with tarfile.open(os.path.join(D, 'snapshots', 'fastapi_15661.tgz'), 'r:gz') as a:
    names = [m.name for m in a]
print('tar first', names[:4], 'n', len(names))
print('top', sorted({n[2:].split('/')[0] if n.startswith('./') else n.split('/')[0] for n in names if n not in ('.', './')})[:30])
print('routing', [n for n in names if n.rstrip('/').endswith('fastapi/routing.py')])
