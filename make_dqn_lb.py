import os
src = os.path.expanduser('~/sdn_project/rr_lb.py')
s = open(src).read()
old_init = "        self.conn = {}\n"
old_pick = """    def pick_server(self):
        ip = SERVERS[self.rr % len(SERVERS)]
        self.rr += 1
        return ip
"""
assert s.count(old_init) == 1 and s.count(old_pick) == 1, 'rr_lb.py has unexpected content'

s = s.replace(old_init, old_init + """        here = os.path.dirname(os.path.abspath(__file__))
        self.agent = Agent(os.path.join(here, 'dqn_weights.npz'))
""", 1)

s = s.replace(old_pick, """    def read_load(self, ip):
        name = 'srv' + ip.split('.')[-1]
        try:
            with open('/tmp/load_%s' % name) as f:
                return int(f.read().strip() or 0)
        except Exception:
            return 0

    def pick_server(self):
        obs = [min(self.read_load(ip), 20) / 20.0 for ip in SERVERS]
        action = int(self.agent.act(obs))
        self.logger.info('state %s -> server %d', obs, action)
        return SERVERS[action]
""", 1)

header = '''import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dqn_agent import Agent
'''
open(os.path.expanduser('~/sdn_project/dqn_lb.py'), 'w').write(header + s)
print('dqn_lb.py created')
