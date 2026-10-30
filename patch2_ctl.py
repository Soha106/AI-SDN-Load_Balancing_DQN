import os
p = os.path.expanduser('~/sdn_project/dqn_lb.py')
s = open(p).read()
a = "        self.agent = Agent(os.path.join(here, 'dqn_weights.npz'))\n"
b = """    def pick_server(self):
        obs = [min(self.read_load(ip), 20) / 20.0 for ip in SERVERS]
        action = int(self.agent.act(obs))
        self.logger.info('state %s -> server %d', obs, action)
        return SERVERS[action]
"""
assert s.count(a) == 1 and s.count(b) == 1, 'dqn_lb.py has unexpected content'

s = s.replace(a, a + """        self.assigned = {ip: 0 for ip in SERVERS}
        self.last_done = {ip: 0 for ip in SERVERS}
""", 1)

s = s.replace(b, """    def read_done(self, ip):
        name = 'srv' + ip.split('.')[-1]
        try:
            with open('/tmp/done_%s' % name) as f:
                d = int(f.read().strip() or 0)
        except Exception:
            return self.last_done[ip]
        if d < self.last_done[ip]:
            self.assigned[ip] = 0
        self.last_done[ip] = d
        return d

    def pick_server(self):
        out = [max(self.assigned[ip] - self.read_done(ip), 0) for ip in SERVERS]
        obs = [min(n, 20) / 20.0 for n in out]
        action = int(self.agent.act(obs))
        self.assigned[SERVERS[action]] += 1
        self.logger.info('outstanding %s -> server %d', out, action)
        return SERVERS[action]
""", 1)
open(p, 'w').write(s)
print('dqn_lb.py updated')
