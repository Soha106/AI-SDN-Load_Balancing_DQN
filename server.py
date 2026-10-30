import sys, time, threading
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

NAME = sys.argv[1]
FACTOR = float(sys.argv[2])
LOCK = threading.Lock()

import os
CNT = [0]
DONE = [0]


def wr(path, v):
    with open(path + '.tmp', 'w') as f:
        f.write(str(v))
    os.replace(path + '.tmp', path)

CLOCK = threading.Lock()
LOADFILE = '/tmp/load_%s' % NAME


def bump(d):
    with CLOCK:
        CNT[0] += d
        if d < 0:
            DONE[0] += 1
            wr('/tmp/done_%s' % NAME, DONE[0])
        tmp = LOADFILE + '.tmp'
        with open(tmp, 'w') as f:
            f.write(str(CNT[0]))
        os.replace(tmp, LOADFILE)


bump(0)
wr('/tmp/done_%s' % NAME, 0)

class H(BaseHTTPRequestHandler):
    def do_GET(self):
        q = parse_qs(urlparse(self.path).query)
        ms = float(q.get('ms', ['0'])[0])
        bump(1)
        try:
            with LOCK:
                time.sleep(ms * FACTOR / 1000.0)
        finally:
            bump(-1)
        body = ('Response from %s\n' % NAME).encode()
        self.send_response(200)
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass

class S(ThreadingHTTPServer):
    request_queue_size = 128

S(('0.0.0.0', 80), H).serve_forever()
