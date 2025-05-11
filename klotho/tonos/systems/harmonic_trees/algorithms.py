from typing import Union, Tuple

__all__ = [
    'measure_partials',
]

def measure_partials(partials:Tuple[int], f:Union[int,float]=1):
    result = []
    for s in partials:
        if isinstance(s, tuple):
            F, P = s
            result.extend(measure_partials(P, f * F))
        else:
            s = s if s > 0 else 1 / s
            result.append(f * s)
    return tuple(result)
