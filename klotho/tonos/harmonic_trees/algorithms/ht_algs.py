
def measure_partials(T, p=1):
    result = []
    for s in T:
        if isinstance(s, tuple):
            D, S = s
            result.extend(measure_partials(S, p * D))
        else:
            result.append(p * s)
    return tuple(result)