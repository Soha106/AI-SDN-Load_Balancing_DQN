import os, glob, csv

base = os.path.expanduser('~/sdn_project/results')
FACTOR = {'srv1': 1.0, 'srv2': 1.0, 'srv3': 2.0}


def stats(label):
    rows = []
    for f in sorted(glob.glob('%s/%s_cli*.csv' % (base, label))):
        with open(f) as fh:
            rows += list(csv.DictReader(fh))
    ok = [r for r in rows if r['ok'] == '1']
    if not ok:
        return None
    lat = sorted(float(r['latency_ms']) for r in ok)
    busy = [sum(float(r['work_ms']) * FACTOR[s] for r in ok if r['server'] == s)
            for s in sorted(FACTOR)]
    jain = sum(busy) ** 2 / (len(busy) * sum(b * b for b in busy))
    n3 = sum(1 for r in ok if r['server'] == 'srv3')
    return [len(rows) - len(ok), sum(lat) / len(lat), lat[len(lat) // 2],
            lat[int(0.95 * (len(lat) - 1))], jain, n3]


HEAD = '%-10s %6s %8s %8s %8s %7s %6s'
ROW = '%-10s %6d %8.1f %8.1f %8.1f %7.3f %6d'
print(HEAD % ('run', 'failed', 'avg_ms', 'med_ms', 'p95_ms', 'fair', 'srv3'))
means = {}
for ctl in ('rr', 'dqn'):
    got = []
    for k in (1, 2, 3):
        r = stats('%s%d' % (ctl, k))
        if r is None:
            print('%s%d: no data' % (ctl, k))
            continue
        got.append(r)
        print(ROW % tuple(['%s%d' % (ctl, k)] + r))
    if got:
        m = [sum(x[i] for x in got) / len(got) for i in range(6)]
        means[ctl] = m
        print(ROW % tuple([ctl + '_mean'] + m))
    print()

if 'rr' in means and 'dqn' in means:
    a, b = means['rr'], means['dqn']
    names = ['failed', 'avg latency', 'median latency', 'p95 latency', 'fairness', 'srv3 requests']
    print('DQN vs Round Robin (mean of the runs):')
    for i in range(1, 6):
        ch = (b[i] - a[i]) / a[i] * 100
        f = '%.3f' if i == 4 else '%.1f'
        print(('  %-15s ' + f + ' -> ' + f + '  (%+.1f%%)') % (names[i], a[i], b[i], ch))
