"""Portable inference: this module needs NumPy only, including in Ryu."""
import numpy as np


class Agent:
    def __init__(self, weights_path):
        with np.load(weights_path, allow_pickle=False) as data:
            if int(data['format_version']) != 1:
                raise ValueError('Unsupported weights format')
            self.layers = [(data[f'w{i}'].astype(np.float32),
                            data[f'b{i}'].astype(np.float32)) for i in range(3)]
        sizes = (3, 64, 64, 3)
        for i, (w, b) in enumerate(self.layers):
            if w.shape != (sizes[i + 1], sizes[i]) or b.shape != (sizes[i + 1],):
                raise ValueError('Expected network dimensions 3 -> 64 -> 64 -> 3')
            if not np.isfinite(w).all() or not np.isfinite(b).all():
                raise ValueError('Weights must be finite')

    def q_values(self, obs):
        """Same float32 linear/ReLU forward pass as the training network."""
        x = np.asarray(obs, dtype=np.float32)
        if x.shape != (3,) or not np.isfinite(x).all() or np.any((x < 0) | (x > 1)):
            raise ValueError('obs must contain 3 finite queue counts / 20 in [0, 1]')
        for i, (w, b) in enumerate(self.layers):
            x = w @ x + b
            if i < 2:
                x = np.maximum(x, 0)
        return x

    def act(self, obs):
        # Greedy inference has no exploration. Ties use the lowest server ID.
        return int(np.argmax(self.q_values(obs)))
