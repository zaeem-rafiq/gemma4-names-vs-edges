import sys, csv, re, json, os, tarfile, collections
D = sys.argv[1]; T = sys.argv[2]
rows = [r for r in csv.DictReader((l for l in open(T) if not l.startswith('#')), delimiter='\t')]
print('archives', len(rows), 'entries', sum(int(r['n_entries']) for r in rows), 'files', sum(int(r['n_files']) for r in rows), 'uncompressed', sum(int(r['uncompressed_bytes']) for r in rows))
print('has_git', collections.Counter(r['has_git'] for r in rows)); print('top_level patterns', collections.Counter(r['top_level'][:60] for r in rows).most_common(5))
print([l.strip() for l in open(T) if l.startswith('#')])
print('first', rows[0]['archive'], rows[0]['n_files'], rows[0]['uncompressed_bytes'])
L = open(os.path.join(D, 'HARNESS_README.md'), encoding='utf-8').read().split('\n')
for i, l in enumerate(L, 1):
    if re.search(r'\b(split|hidden|private|public (test|lb|leader)|leaderboard|FAIL_TO_PASS|Stage 1|Stage 2)\b', l, re.I): print(i, l[:190])
tasks = [json.loads(l) for l in open(os.path.join(D, 'tasks.jsonl'))]
for k in ('patch', 'test_patch', 'problem_statement'):
    v = sorted(len(t[k]) for t in tasks); print(k, 'chars min/median/max', v[0], v[len(v)//2], v[-1])
t = next(r for r in tasks if r['base_commit'].startswith('016ab760'))
print('task', t['instance_id'])
with tarfile.open(os.path.join(D, 'snapshots', t['instance_id'] + '.tgz'), 'r:gz') as a:
    names = [m.name for m in a]
print(len(names), [n for n in names if n.endswith('settings/app02_py310/main.py')][:3], 'graph tests.* under tests/', any(n.lstrip('./').startswith('tests/') for n in names))
