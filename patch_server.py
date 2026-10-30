import os
p = os.path.expanduser('~/sdn_project/server.py')
s = open(p).read()
a = "LOCK = threading.Lock()\n"
b = """        with LOCK:
            time.sleep(ms * FACTOR / 1000.0)
"""
assert s.count(a) == 1 and s.count(b) == 1, 'server.py has unexpected content'

s = s.replace(a, a + '''
import os
CNT = [0]
CLOCK = threading.Lock()
LOADFILE = '/tmp/load_%s' % NAME


def bump(d):
    with CLOCK:
        CNT[0] += d
        tmp = LOADFILE + '.tmp'
        with open(tmp, 'w') as f:
            f.write(str(CNT[0]))
        os.replace(tmp, LOADFILE)


bump(0)
''', 1)

s = s.replace(b, """        bump(1)
        try:
            with LOCK:
                time.sleep(ms * FACTOR / 1000.0)
        finally:
            bump(-1)
""", 1)
open(p, 'w').write(s)
print('server.py patched')
