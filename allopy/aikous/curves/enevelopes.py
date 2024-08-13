import numpy as np

def line(n, min_val=0.0, max_val=1.0):
    return np.linspace(min_val, max_val, n)

def swell(n, min_val=0.0, max_val=1.0):
    up = np.linspace(min_val, max_val, n//2, endpoint=False)
    down = np.linspace(max_val, min_val, n//2 + n % 2, endpoint=True)
    result = np.concatenate([up, down])
    return result
