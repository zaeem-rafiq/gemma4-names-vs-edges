import sys, re
L = open(sys.argv[1], encoding='utf-8').read().split('\n')
for a, b in [(1, 66), (71, 103), (127, 157), (303, 348), (488, 537), (540, 567), (596, 632)]:
    print('-----', a, b)
    for i in range(a - 1, min(b, len(L))): print(L[i][:260])
print('----- licence hits')
for i, l in enumerate(L, 1):
    if re.search(r'licen[cs]e|redistribut|terms of|copyright|non-commercial|not.*(share|publish)', l, re.I): print(i, l[:220])
