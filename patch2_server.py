import os
p = os.path.expanduser('~/sdn_project/server.py')
s = open(p).read()
a = "CNT = [0]\n"
b = "        CNT[0] += d\n"
c = "bump(0)\n"
assert s.count(a) == 1 and s.count(b) == 1 and s.count(c) == 1, 'server.py has unexpected content'
assert 'DONE' not in s, 'already patched'

s = s.replace(a, a + '''DONE = [0]


def wr(path, v):
    with open(path + '.tmp', 'w') as f:
        f.write(str(v))
    os.replace(path + '.tmp', path)

''', 1)

s = s.replace(b, b + """        if d < 0:
            DONE[0] += 1
            wr('/tmp/done_%s' % NAME, DONE[0])
""", 1)
s = s.replace(c, c + "wr('/tmp/done_%s' % NAME, 0)\n", 1)
open(p, 'w').write(s)
print('server.py updated')
