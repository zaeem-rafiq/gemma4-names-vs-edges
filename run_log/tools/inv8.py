import sys, re
L = open(sys.argv[1], encoding='utf-8').read().split('\n')
print('total chars 294-537', sum(len(x) + 1 for x in L[293:537]))
for a, b in [(294, 302), (349, 487)]:
    print('-----', a, b)
    for i in range(a - 1, b): print(L[i])
print('----- full lines cut earlier')
for i in (347,): print(i, L[i-1])
for i in (490, 492, 495, 496, 505, 506, 507, 521, 522): print(i, L[i-1])
print('----- order hits')
for i, l in enumerate(L, 1):
    if re.search(r'\b(sort|sorted|order|ordering|deterministic|alphabetical)\b', l, re.I) and not (303 <= i <= 348): print(i, l[:400])
print('----- name hits')
for i, l in enumerate(L, 1):
    if re.search(r'node name|symbol name|dotted|resolve_node_name', l, re.I) and not (488 <= i <= 537): print(i, l[:400])
