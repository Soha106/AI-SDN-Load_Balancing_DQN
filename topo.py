import os, sys, time
from mininet.net import Mininet
from mininet.node import RemoteController, OVSSwitch
from mininet.cli import CLI
from mininet.log import setLogLevel

BASE = os.path.dirname(os.path.abspath(__file__))
FACTORS = {1: 1.0, 2: 1.0, 3: 2.0}

def run(mode, label):
    net = Mininet(controller=None, switch=OVSSwitch)
    net.addController('c0', controller=RemoteController, ip='127.0.0.1', port=6653)
    net.addSwitch('s1', protocols='OpenFlow13')
    servers = [net.addHost('srv%d' % i, ip='10.0.0.%d/24' % i,
                           mac='00:00:00:00:00:%02d' % i) for i in (1, 2, 3)]
    clients = [net.addHost('cli%d' % i, ip='10.0.0.%d/24' % (10 + i),
                           mac='00:00:00:00:00:1%d' % i) for i in (1, 2, 3, 4)]
    for h in servers + clients:
        net.addLink(h, net.get('s1'))
    net.start()
    for i, s in enumerate(servers, 1):
        s.cmd('python3 %s/server.py %s %s > /dev/null 2>&1 &' % (BASE, s.name, FACTORS[i]))
    time.sleep(2)
    if mode == 'test':
        out = BASE + '/results'
        os.makedirs(out, exist_ok=True)
        procs = [c.popen('python3 %s/client.py %s 150 7 %s/%s_%s.csv'
                         % (BASE, c.name, out, label, c.name)) for c in clients]
        for p in procs:
            p.communicate()
        print('test finished, results in', out)
    else:
        CLI(net)
    os.system('pkill -f server.py')
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    run(sys.argv[1] if len(sys.argv) > 1 else 'cli',
        sys.argv[2] if len(sys.argv) > 2 else 'rr')
