import os, glob, csv
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

base = os.path.expanduser('~/sdn_project/results')
FACTOR = {'srv1': 1.0, 'srv2': 1.0, 'srv3': 2.0}


def load(label):
    rows = []
    for f in sorted(glob.glob('%s/%s_cli*.csv' % (base, label))):
        with open(f) as fh:
            rows += list(csv.DictReader(fh))
    return [r for r in rows if r['ok'] == '1']


def stats(label):
    ok = load(label)
    if not ok:
        return None
    lat = sorted(float(r['latency_ms']) for r in ok)
    busy = [sum(float(r['work_ms']) * FACTOR[s] for r in ok if r['server'] == s)
            for s in sorted(FACTOR)]
    jain = sum(busy) ** 2 / (len(busy) * sum(b * b for b in busy))
    n3 = sum(1 for r in ok if r['server'] == 'srv3')
    return [0, sum(lat) / len(lat), lat[len(lat) // 2],
            lat[int(0.95 * (len(lat) - 1))], jain, n3]


def alloc(label):
    c = {'srv1': 0, 'srv2': 0, 'srv3': 0}
    for r in load(label):
        if r['server'] in c:
            c[r['server']] += 1
    return c


names = {'rr': 'Round Robin', 'dqn': 'DQN'}
colors = {'rr': '#888888', 'dqn': '#1f77b4'}
data = {}
for ctl in names:
    data[ctl] = [r for r in (stats('%s%d' % (ctl, k)) for k in (1, 2, 3)) if r]

metrics = [(1, 'Average latency (ms)'), (3, '95th percentile latency (ms)'),
           (4, "Fairness (Jain's index, axis starts at 0.8)"),
           (5, 'Requests sent to slow srv3 (of 600)')]
fig, axes = plt.subplots(2, 2, figsize=(10, 7))
for ax, (idx, title) in zip(axes.flat, metrics):
    for x, ctl in enumerate(names):
        vals = [r[idx] for r in data[ctl]]
        ax.bar(x, sum(vals) / len(vals), color=colors[ctl], alpha=0.6, width=0.55)
        ax.scatter([x] * len(vals), vals, color='black', zorder=3, s=25)
    if idx == 4:
        ax.set_ylim(0.8, 1.0)
    ax.set_xticks([0, 1])
    ax.set_xticklabels([names['rr'], names['dqn']])
    ax.set_title(title, fontsize=10)
fig.suptitle('Real Mininet/Ryu test, 3 runs each (bar = mean, dots = single runs)')
fig.tight_layout()
fig.savefig(base + '/comparison.png', dpi=150)
print('saved', base + '/comparison.png')

fig2, ax2 = plt.subplots(figsize=(7, 4))
servers = ['srv1', 'srv2', 'srv3']
for j, ctl in enumerate(names):
    runs = [alloc('%s%d' % (ctl, k)) for k in (1, 2, 3)]
    means = [sum(r[s] for r in runs) / len(runs) for s in servers]
    ax2.bar([i + j * 0.38 for i in range(3)], means, width=0.38,
            color=colors[ctl], label=names[ctl])
ax2.set_xticks([i + 0.19 for i in range(3)])
ax2.set_xticklabels(['srv1', 'srv2', 'srv3 (slow)'])
ax2.set_ylabel('Requests per run (mean of 3)')
ax2.set_title('How each controller spread the 600 requests')
ax2.legend()
fig2.tight_layout()
fig2.savefig(base + '/request_allocation_real.png', dpi=150)
print('saved', base + '/request_allocation_real.png')
