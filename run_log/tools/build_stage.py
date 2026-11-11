import os, sys, io, gzip, tarfile, hashlib, collections, json
D, OUT = sys.argv[1], sys.argv[2]
LIMIT, MARGIN, MAXM = 350 * 10**6, 10 * 10**6, 2 * 2**20
os.makedirs(OUT)  # fails if the folder already exists
REPOS = ['fastapi', 'rich', 'requests', 'httpx']
KEEP = {'pyproject.toml', 'setup.cfg', 'setup.py'}
REASONS = ['unsafe_path', 'symlink', 'hardlink', 'device', 'too_large_2MB']
class Writer:
    def __init__(self, base): self.base, self.n, self.done, self.raw = base, 0, [], None; self.open()
    def open(self):
        self.n += 1; self.path = os.path.join(OUT, '%s._part%d.tmp' % (self.base, self.n))
        self.raw = open(self.path, 'wb'); self.gz = gzip.GzipFile(filename='', mode='wb', fileobj=self.raw, mtime=0)
        self.tar = tarfile.open(fileobj=self.gz, mode='w', format=tarfile.GNU_FORMAT); self.members = 0; self.skip = collections.Counter()
    def close(self):
        self.tar.close(); self.gz.close(); self.raw.close(); self.done.append((self.path, self.members, dict(self.skip)))
    def add(self, name, data):
        if self.members and self.raw.tell() + len(data) // 2 + MARGIN > LIMIT: self.close(); self.open()
        ti = tarfile.TarInfo(name); ti.size = len(data); ti.mode = 0o644; ti.mtime = 0
        self.tar.addfile(ti, io.BytesIO(data)); self.members += 1
    def finish(self):
        self.close(); out = []
        for i, (p, m, s) in enumerate(self.done, 1):
            final = '%s_%d.tar.gz' % (self.base, i) if len(self.done) > 1 else '%s.tar.gz' % self.base
            os.rename(p, os.path.join(OUT, final)); out.append((final, m, s))
        return out
rows = []
for repo in REPOS:
    w = Writer('graphs_' + repo)
    for f in sorted(os.listdir(os.path.join(D, 'graphs'))):
        if f.endswith('.json') and f.rsplit('_', 1)[0] == repo:
            p = os.path.join(D, 'graphs', f)
            if os.path.islink(p) or not os.path.isfile(p): w.skip['symlink'] += 1; continue
            w.add('graphs/' + f, open(p, 'rb').read())
    rows += w.finish()
for repo in REPOS:
    w = Writer('py_' + repo)
    for f in sorted(os.listdir(os.path.join(D, 'snapshots'))):
        if not f.endswith('.tgz'): continue
        iid = f[:-4]
        if iid.rsplit('_', 1)[0] != repo: continue
        p = os.path.join(D, 'snapshots', f)
        if os.path.islink(p): w.skip['symlink'] += 1; continue
        with tarfile.open(p, 'r|gz') as t:
            for m in t:
                name = m.name[2:] if m.name.startswith('./') else m.name
                parts = [x for x in name.split('/') if x not in ('', '.')]
                if m.name.startswith('/') or '..' in name.split('/'): w.skip['unsafe_path'] += 1; continue
                if m.isdir() or not parts: continue
                if parts[0] == '.git' or '.git' in parts: continue
                if m.issym(): w.skip['symlink'] += 1; continue
                if m.islnk(): w.skip['hardlink'] += 1; continue
                if not m.isreg(): w.skip['device'] += 1; continue
                base = parts[-1]
                if not (base.endswith('.py') or base in KEEP): continue
                if m.size > MAXM: w.skip['too_large_2MB'] += 1; continue
                data = t.extractfile(m).read()
                if len(data) != m.size: raise SystemExit('short read %s %s' % (f, m.name))
                w.add(iid + '/' + '/'.join(parts), data)
    rows += w.finish()
with open(os.path.join(OUT, 'MANIFEST.tsv'), 'w') as o:
    o.write('bundle\tbytes\tsha256\tmembers\t' + '\t'.join('skipped_' + r for r in REASONS) + '\n')
    for name, mem, skip in rows:
        p = os.path.join(OUT, name); h = hashlib.sha256()
        with open(p, 'rb') as f:
            for b in iter(lambda: f.read(1 << 20), b''): h.update(b)
        n = 0
        with tarfile.open(p, 'r|gz') as t:
            for m in t:
                n += 1
                if not m.isreg() or m.name.startswith('/') or '..' in m.name.split('/') or (name.startswith('py_') and '/.git/' in m.name): raise SystemExit('bad member ' + m.name)
        if n != mem: raise SystemExit('member mismatch ' + name)
        if os.path.getsize(p) >= LIMIT: raise SystemExit('too big ' + name)
        o.write('\t'.join([name, str(os.path.getsize(p)), h.hexdigest(), str(mem)] + [str(skip.get(r, 0)) for r in REASONS]) + '\n')
print('OK')
