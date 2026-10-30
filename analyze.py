import sys, os, glob, csv

label = sys.argv[1]
base = os.path.dirname(os.path.abspath(__file__))
FACTOR = {'srv1': 1.0, 'srv2': 1.0, 'srv3': 2.0}

rows = []
for f in sorted(glob.glob('%s/results/%s_cli*.csv' % (base, label))):
    with open(f) as fh:
        rows += list(csv.DictReader(fh))

ok = [r for r in rows if r['ok'] == '1']
lat = sorted(float(r['latency_ms']) for r in ok)
p95 = lat[int(0.95 * (len(lat) - 1))]

lines = []
lines.append('Run label            : %s' % label)
lines.append('Total requests       : %d' % len(rows))
lines.append('Failed requests      : %d' % (len(rows) - len(ok)))
lines.append('Average latency (ms) : %.1f' % (sum(lat) / len(lat)))
lines.append('Median latency (ms)  : %.1f' % lat[len(lat) // 2])
lines.append('95th pct latency (ms): %.1f' % p95)
lines.append('Max latency (ms)     : %.1f' % lat[-1])
lines.append('')

busy = {}
for s in sorted(FACTOR):
    sr = [r for r in ok if r['server'] == s]
    b = sum(float(r['work_ms']) * FACTOR[s] for r in sr)
    busy[s] = b
    avg = sum(float(r['latency_ms']) for r in sr) / max(len(sr), 1)
    lines.append('%s: %3d requests, busy time %6.0f ms, avg latency %.1f ms'
                 % (s, len(sr), b, avg))

x = list(busy.values())
jain = sum(x) ** 2 / (len(x) * sum(v * v for v in x))
lines.append('')
lines.append("Jain's fairness index (busy time): %.3f  (1.0 = perfectly balanced)" % jain)

text = '\n'.join(lines)
print(text)
open('%s/results/summary_%s.txt' % (base, label), 'w').write(text + '\n')
