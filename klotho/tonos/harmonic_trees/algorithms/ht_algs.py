from typing import Union, Tuple

def measure_partials(partials:Tuple[int], f:Union[int,float]=1):
    result = []
    for s in partials:
        if isinstance(s, tuple):
            F, P = s
            result.extend(measure_partials(P, f * F))
        else:
            result.append(f * s)
    return tuple(result)
