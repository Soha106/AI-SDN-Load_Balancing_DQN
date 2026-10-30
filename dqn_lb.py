import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dqn_agent import Agent
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, ethernet, arp, ipv4, tcp, ether_types

VIP = '10.0.0.100'
VMAC = '00:00:00:00:01:00'

HOSTS = {
    '10.0.0.1':  ('00:00:00:00:00:01', 1),
    '10.0.0.2':  ('00:00:00:00:00:02', 2),
    '10.0.0.3':  ('00:00:00:00:00:03', 3),
    '10.0.0.11': ('00:00:00:00:00:11', 4),
    '10.0.0.12': ('00:00:00:00:00:12', 5),
    '10.0.0.13': ('00:00:00:00:00:13', 6),
    '10.0.0.14': ('00:00:00:00:00:14', 7),
}
SERVERS = ['10.0.0.1', '10.0.0.2', '10.0.0.3']


class RRLoadBalancer(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.rr = 0
        self.conn = {}
        here = os.path.dirname(os.path.abspath(__file__))
        self.agent = Agent(os.path.join(here, 'dqn_weights.npz'))
        self.assigned = {ip: 0 for ip in SERVERS}
        self.last_done = {ip: 0 for ip in SERVERS}

    def read_load(self, ip):
        name = 'srv' + ip.split('.')[-1]
        try:
            with open('/tmp/load_%s' % name) as f:
                return int(f.read().strip() or 0)
        except Exception:
            return 0

    def read_done(self, ip):
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

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def features_handler(self, ev):
        dp = ev.msg.datapath
        ofp, p = dp.ofproto, dp.ofproto_parser
        actions = [p.OFPActionOutput(ofp.OFPP_CONTROLLER, ofp.OFPCML_NO_BUFFER)]
        self.add_flow(dp, 0, p.OFPMatch(), actions)

    def add_flow(self, dp, prio, match, actions, idle=0):
        ofp, p = dp.ofproto, dp.ofproto_parser
        inst = [p.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, actions)]
        dp.send_msg(p.OFPFlowMod(datapath=dp, priority=prio, match=match,
                                 instructions=inst, idle_timeout=idle))

    def send_out(self, dp, msg, actions):
        p = dp.ofproto_parser
        dp.send_msg(p.OFPPacketOut(datapath=dp, buffer_id=msg.buffer_id,
                                   in_port=msg.match['in_port'],
                                   actions=actions, data=msg.data))

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        msg = ev.msg
        dp = msg.datapath
        p = dp.ofproto_parser
        in_port = msg.match['in_port']
        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)

        if eth.ethertype == ether_types.ETH_TYPE_ARP:
            self.handle_arp(dp, in_port, pkt.get_protocol(arp.arp))
            return

        ip = pkt.get_protocol(ipv4.ipv4)
        if ip is None:
            return

        if ip.dst == VIP:
            t = pkt.get_protocol(tcp.tcp)
            if t:
                self.handle_lb(dp, msg, in_port, ip, t)
            return

        if ip.dst in HOSTS:
            port = HOSTS[ip.dst][1]
            actions = [p.OFPActionOutput(port)]
            self.add_flow(dp, 1, p.OFPMatch(eth_type=0x0800, ipv4_dst=ip.dst),
                          actions, idle=30)
            self.send_out(dp, msg, actions)

    def handle_arp(self, dp, in_port, a):
        if a.opcode != arp.ARP_REQUEST:
            return
        if a.dst_ip == VIP:
            mac = VMAC
        elif a.dst_ip in HOSTS:
            mac = HOSTS[a.dst_ip][0]
        else:
            return
        ofp, p = dp.ofproto, dp.ofproto_parser
        pk = packet.Packet()
        pk.add_protocol(ethernet.ethernet(dst=a.src_mac, src=mac,
                                          ethertype=ether_types.ETH_TYPE_ARP))
        pk.add_protocol(arp.arp(opcode=arp.ARP_REPLY, src_mac=mac, src_ip=a.dst_ip,
                                dst_mac=a.src_mac, dst_ip=a.src_ip))
        pk.serialize()
        dp.send_msg(p.OFPPacketOut(datapath=dp, buffer_id=ofp.OFP_NO_BUFFER,
                                   in_port=ofp.OFPP_CONTROLLER,
                                   actions=[p.OFPActionOutput(in_port)], data=pk.data))

    def handle_lb(self, dp, msg, in_port, ip, t):
        p = dp.ofproto_parser
        key = (ip.src, t.src_port)
        if (t.bits & 0x12) == 0x02 or key not in self.conn:
            self.conn[key] = self.pick_server()
        s_ip = self.conn[key]
        s_mac, s_port = HOSTS[s_ip]
        self.logger.info('request from %s:%s -> %s', ip.src, t.src_port, s_ip)

        fwd_match = p.OFPMatch(eth_type=0x0800, ip_proto=6, ipv4_src=ip.src,
                               ipv4_dst=VIP, tcp_src=t.src_port, tcp_dst=t.dst_port)
        fwd_actions = [p.OFPActionSetField(eth_dst=s_mac),
                       p.OFPActionSetField(ipv4_dst=s_ip),
                       p.OFPActionOutput(s_port)]
        rev_match = p.OFPMatch(eth_type=0x0800, ip_proto=6, ipv4_src=s_ip,
                               ipv4_dst=ip.src, tcp_src=t.dst_port, tcp_dst=t.src_port)
        rev_actions = [p.OFPActionSetField(eth_src=VMAC),
                       p.OFPActionSetField(ipv4_src=VIP),
                       p.OFPActionOutput(in_port)]
        self.add_flow(dp, 10, fwd_match, fwd_actions, idle=5)
        self.add_flow(dp, 10, rev_match, rev_actions, idle=5)
        self.send_out(dp, msg, fwd_actions)
