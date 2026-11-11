import os, sys, tarfile, zipfile, collections
D = sys.argv[1]; out = sys.argv[2]
with open(out, 'w') as o:
    o.write('archive\tn_entries\tn_files\tuncompressed_bytes\ttop_level\tn_git_entries\tgit_bytes\n')
    for f in sorted(os.listdir(os.path.join(D, 'snapshots'))):
        n = nf = b = gn = gb = 0; top = collections.Counter()
        with tarfile.open(os.path.join(D, 'snapshots', f), 'r:gz') as t:
            for m in t:
                n += 1; nf += m.isfile(); b += m.size if m.isfile() else 0
                name = m.name[2:] if m.name.startswith('./') else m.name
                parts = [p for p in name.split('/') if p]
                if parts: top[parts[0]] += 1
                if parts and parts[0] == '.git': gn += 1; gb += m.size if m.isfile() else 0
        o.write(f'{f}\t{n}\t{nf}\t{b}\t{",".join(sorted(top))}\t{gn}\t{gb}\n'); o.flush()
    tot = 0
    for f in sorted(os.listdir(os.path.join(D, 'wheels'))):
        with zipfile.ZipFile(os.path.join(D, 'wheels', f)) as z: tot += len(z.namelist())
    o.write(f'# wheels: {len(os.listdir(os.path.join(D, "wheels")))} files, {tot} entries in total, none extracted\n')
