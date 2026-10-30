import random

N_SERVERS = 3
SPEED = [1.0, 1.0, 2.0]
WORK_CHOICES = [20, 20, 20, 100]
ARRIVAL_RATE = 35.0
OVERHEAD_MS = 40.0
EPISODE_LEN = 600
MAX_Q = 20


class LoadBalancerEnv:
    n_actions = N_SERVERS
    obs_dim = N_SERVERS

    def __init__(self, seed=None):
        self.rng = random.Random(seed)
        self.reset()

    def reset(self):
        self.t = 0.0
        self.free_at = [0.0] * N_SERVERS
        self.pending = [[] for _ in range(N_SERVERS)]
        self.count = 0
        self.t += self.rng.expovariate(ARRIVAL_RATE / 1000.0)
        return self._obs()

    def _obs(self):
        obs = []
        for i in range(N_SERVERS):
            self.pending[i] = [f for f in self.pending[i] if f > self.t]
            obs.append(min(len(self.pending[i]), MAX_Q) / MAX_Q)
        return obs

    def step(self, action):
        work = self.rng.choice(WORK_CHOICES)
        start = max(self.t, self.free_at[action])
        finish = start + work * SPEED[action]
        self.free_at[action] = finish
        self.pending[action].append(finish)
        latency = finish - self.t + OVERHEAD_MS
        reward = -latency / 100.0
        self.count += 1
        done = self.count >= EPISODE_LEN
        self.t += self.rng.expovariate(ARRIVAL_RATE / 1000.0)
        info = {'latency': latency, 'server': action, 'work': work}
        return self._obs(), reward, done, info


def evaluate(policy, episodes=50, seed=0):
    env = LoadBalancerEnv(seed)
    lats, busy, counts = [], [0.0] * N_SERVERS, [0] * N_SERVERS
    for _ in range(episodes):
        obs = env.reset()
        done, k = False, 0
        while not done:
            a = policy(obs, k)
            obs, r, done, info = env.step(a)
            k += 1
            lats.append(info['latency'])
            busy[a] += info['work'] * SPEED[a]
            counts[a] += 1
    lats.sort()
    avg = sum(lats) / len(lats)
    p95 = lats[int(0.95 * (len(lats) - 1))]
    jain = sum(busy) ** 2 / (N_SERVERS * sum(b * b for b in busy))
    return avg, p95, jain, counts


if __name__ == '__main__':
    rng = random.Random(1)
    policies = {
        'round_robin': lambda o, k: k % N_SERVERS,
        'random': lambda o, k: rng.randrange(N_SERVERS),
        'least_connections': lambda o, k: o.index(min(o)),
    }
    print('%-18s %8s %8s %8s  %s' % ('policy', 'avg_ms', 'p95_ms', 'fair', 'requests per server'))
    for name, pol in policies.items():
        avg, p95, jain, counts = evaluate(pol)
        print('%-18s %8.1f %8.1f %8.3f  %s' % (name, avg, p95, jain, counts))
