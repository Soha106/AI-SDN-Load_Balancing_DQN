#!/bin/bash
sudo -v
for round in 1 2 3; do
  for ctl in rr dqn; do
    echo "=== round $round : $ctl ==="
    sudo mn -c > /dev/null 2>&1
    ryu-manager ~/sdn_project/${ctl}_lb.py > /tmp/ryu_${ctl}.log 2>&1 &
    RPID=$!
    sleep 8
    sudo python3 ~/sdn_project/topo.py test ${ctl}${round} > /tmp/topo_${ctl}${round}.log 2>&1
    tail -n 3 /tmp/topo_${ctl}${round}.log | head -n 1
    kill $RPID 2>/dev/null
    sleep 2
  done
done
sudo mn -c > /dev/null 2>&1
sudo chown -R $USER:$USER ~/sdn_project
echo "all runs finished"
