import numpy as np
from collections import deque

class TemporalSequenceEngine:
    def __init__(self, sequence_length=10):
        self.seq_len = sequence_length
        self.history = deque(maxlen=sequence_length)
        # Weights for temporal metrics: [networks_delta, threats_burst, signal_jitter]
        self.weights = np.array([0.35, 0.45, 0.20])

    def push_sample(self, networks: float, threats: float, rssi_mean: float = -65.0) -> dict:
        self.history.append([networks, threats, rssi_mean])
        
        # Buffer fill hone tak baseline return karein
        if len(self.history) < 3:
            return {
                "temporal_anomaly_score": 0.0,
                "burst_flag": False,
                "history_points": list(self.history)
            }

        arr = np.array(self.history)
        
        # Temporal velocity / gradients (rate of change over time)
        diffs = np.diff(arr, axis=0)
        recent_burst = np.abs(diffs[-1])
        
        # Variance / temporal jitter across the sliding window
        window_variance = np.var(arr, axis=0)
        
        # Sequence reconstruction error approximation
        error_vector = (recent_burst * 0.7) + (np.sqrt(window_variance) * 0.3)
        raw_score = float(np.dot(error_vector, self.weights))
        
        # Normalize score between 0.0 and 100.0
        normalized_score = float(np.clip(raw_score * 18.5, 0.0, 100.0))
        burst_detected = bool(normalized_score >= 55.0 or recent_burst[1] > 0)

        return {
            "temporal_anomaly_score": round(normalized_score, 2),
            "burst_flag": burst_detected,
            "history_points": [float(p[0]) for p in self.history]
        }
