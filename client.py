import sys, time, random, threading, urllib.request

name, n, rate, out = sys.argv[1], int(sys.argv[2]), float(sys.argv[3]), sys.argv[4]
random.seed(name)
rows = []
lock = threading.Lock()

def one(i, ms):
    t0 = time.time()
    try:
        url = 'http://10.0.0.100/?ms=%d' % ms
        body = urllib.request.urlopen(url, timeout=20).read().decode().strip()
        srv, ok = body.split()[-1], 1
    except Exception:
        srv, ok = 'none', 0
    lat = (time.time() - t0) * 1000
    with lock:
        rows.append((name, i, ms, srv, round(lat, 1), ok))

threads = []
for i in range(n):
    ms = random.choice([20, 20, 20, 100])
    th = threading.Thread(target=one, args=(i, ms))
    th.start()
    threads.append(th)
    time.sleep(random.expovariate(rate))
for th in threads:
    th.join()

with open(out, 'w') as f:
    f.write('client,req,work_ms,server,latency_ms,ok\n')
    for r in rows:
        f.write(','.join(map(str, r)) + '\n')
