import numpy as np
from collections import deque

class IsolationTree:
    """Pure NumPy Isolation Tree (Liu, Ting & Zhou 2008). Zero external C-bindings."""
    def __init__(self, height_limit=10):
        self.height_limit = height_limit
        self.left = None
        self.right = None
        self.split_feature = None
        self.split_value = None
        self.size = 0

    def fit(self, X, current_height=0):
        self.size = len(X)
        if current_height >= self.height_limit or self.size <= 1:
            return self
        num_features = X.shape[1]
        self.split_feature = int(np.random.randint(0, num_features))
        col = X[:, self.split_feature]
        f_min, f_max = float(np.min(col)), float(np.max(col))
        if f_min >= f_max:
            return self
        self.split_value = float(np.random.uniform(f_min, f_max))
        left_mask = col < self.split_value
        right_mask = ~left_mask
        if np.sum(left_mask) == 0 or np.sum(right_mask) == 0:
            return self
        self.left = IsolationTree(self.height_limit).fit(X[left_mask], current_height + 1)
        self.right = IsolationTree(self.height_limit).fit(X[right_mask], current_height + 1)
        return self

    def path_length(self, x, current_height=0):
        if self.left is None or self.right is None:
            return float(current_height + self._c(self.size))
        val = x[self.split_feature]
        if val < self.split_value:
            return self.left.path_length(x, current_height + 1)
        else:
            return self.right.path_length(x, current_height + 1)

    @staticmethod
    def _c(n):
        if n <= 1: return 0.0
        if n == 2: return 1.0
        return float(2.0 * (np.log(n - 1) + 0.5772156649) - (2.0 * (n - 1) / n))

class PureNumpyIsolationForest:
    def __init__(self, n_trees=50, max_samples=64, random_state=42):
        self.n_trees = n_trees
        self.max_samples = max_samples
        self.trees = []
        np.random.seed(random_state)

    def fit(self, X):
        self.trees = []
        n_samples = len(X)
        height_limit = int(np.ceil(np.log2(max(self.max_samples, 2))))
        for _ in range(self.n_trees):
            sub_size = min(n_samples, self.max_samples)
            indices = np.random.choice(n_samples, sub_size, replace=False)
            sub_X = X[indices]
            tree = IsolationTree(height_limit=height_limit).fit(sub_X)
            self.trees.append(tree)
        return self

    def anomaly_score(self, x, n_samples):
        paths = [tree.path_length(x) for tree in self.trees]
        avg_path = float(np.mean(paths))
        c_n = IsolationTree._c(n_samples)
        if c_n <= 0: return 0.5
        score = 2.0 ** (- (avg_path / c_n))
        return float(score)

class SentinelAIEngine:
    def __init__(self, window_size=100):
        self.history = deque(maxlen=window_size)
        self.forest = PureNumpyIsolationForest(n_trees=40, max_samples=60, random_state=42)
        self._bootstrap_baseline()

    def _bootstrap_baseline(self):
        np.random.seed(42)
        normal_networks = np.random.normal(loc=18, scale=3, size=(60, 1))
        normal_alerts = np.random.choice([0, 1], size=(60, 1), p=[0.95, 0.05])
        baseline_data = np.hstack([normal_networks, normal_alerts])
        for row in baseline_data:
            self.history.append(row)
        self.forest.fit(np.array(self.history))

    def analyze_telemetry(self, networks_count, alerts_count):
        features = np.array([float(networks_count), float(alerts_count)])
        n_samples = len(self.history)
        
        raw_anomaly_score = self.forest.anomaly_score(features, n_samples)
        risk_score = float(np.clip((raw_anomaly_score - 0.40) * 160.0, 5.0, 99.0))
        if alerts_count > 0:
            risk_score = min(100.0, max(65.0, risk_score + (alerts_count * 15.0)))
        
        is_anomaly = 1 if (risk_score >= 60.0 or alerts_count > 0) else 0
        self.history.append(features)
        
        if len(self.history) >= 50 and np.random.rand() < 0.15:
            self.forest.fit(np.array(self.history))
            
        return is_anomaly, round(risk_score, 2)
