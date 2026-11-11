import json, hashlib, os, sys, csv, collections
R = sys.argv[1]; times = {r['tag']: r for r in csv.DictReader(open(sys.argv[2]), delimiter='\t')}
out = []
def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''): h.update(b)
    return h.hexdigest()
for tag in ('E2B', 'E4B', '12B', '31B'):
    p = os.path.join(R, 'studyA_%s.jsonl' % tag)
    L = [json.loads(l) for l in open(p)]
    h = L[0]['_header']; pk = h['package']
    body = L[1:]
    resumes = sum('_resume' in x for x in body)
    keys = collections.Counter(k for x in body for k in x if 'err' in k.lower() or 'retr' in k.lower())
    nonempty = sum(1 for x in body if any(x.get(k) for k in x if 'err' in k.lower()))
    t = times[tag]
    out.append(f"### {tag}\n- File: runs/studyA_{tag}.jsonl\n- Size: {os.path.getsize(p)} bytes\n- Lines: {len(L)} (1 header + {len(body)} rows)\n- SHA-256: {sha(p)}\n- Start: {t['start_utc']}\n- End: {t['end_utc']}\n- Exit: {t['exit']}\n- _resume lines: {resumes}\n- Rows with a non-empty error field: {nonempty} (error/retry keys seen: {dict(keys)})\n- code_hash: {pk['code_hash']}\n- code_sha256_current: {pk['code_sha256_current']}\n- items_digest: {pk['items_digest']}\n- items_folder: {pk['items_folder']}\n- manifests: {json.dumps(pk['manifests'])}\n- model sha256: {h['model_gguf']['sha256']}\n- answer_prefix: {h['settings']['answer_prefix']!r}; thought_block: {h['settings']['thought_block']}; answer_prefix_source: {json.dumps(h['answer_prefix_source'])[:200]}\n")
p = os.path.join(R, 'studyA_report.json'); t = times['analysis']
L = open(p).read().count('\n')
j = json.load(open(p))
out.append(f"### Report\n- File: runs/studyA_report.json\n- Size: {os.path.getsize(p)} bytes\n- Lines: {L}\n- SHA-256: {sha(p)}\n- Start: {t['start_utc']}\n- End: {t['end_utc']}\n- Exit: {t['exit']}\n- Top-level keys: {list(j)}\n")
print('\n'.join(out))
