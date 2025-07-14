__all__ = [
    'factor_children',
    'refactor_children',
    'get_signs',
    'get_abs',
    'rotate_children',
    'print_subdivisions',
]

def factor_children(subdivs:tuple) -> tuple:
    def _factor(subdivs, acc):
        for element in subdivs:
            if isinstance(element, tuple):
                _factor(element, acc)
            else:
                acc.append(element)
        return acc
    return tuple(_factor(subdivs, []))

def refactor_children(subdivs:tuple, factors:tuple) -> tuple:
    def _refactor(subdivs, index):
        result = []
        for element in subdivs:
            if isinstance(element, tuple):
                nested_result, index = _refactor(element, index)
                result.append(nested_result)
            else:
                result.append(factors[index])
                index += 1
        return tuple(result), index
    return _refactor(subdivs, 0)[0]

def get_signs(subdivs):
        signs = []
        for element in subdivs:
            if isinstance(element, tuple):
                signs.extend(get_signs(element))
            else:
                signs.append(1 if element >= 0 else -1)
        return signs
    
def get_abs(subdivs):
        result = []
        for element in subdivs:
            if isinstance(element, tuple):
                result.extend(get_abs(element))
            else:
                result.append(abs(element))
        return result

def rotate_children(subdivs: tuple, n: int = 1, preserve_signs: bool = False) -> tuple:
    """Rotates the children of a nested tuple structure.
    
    Args:
        subdivs: Nested tuple structure to rotate
        n: Number of positions to rotate
        preserve_signs: If True, preserves the signs of numbers while rotating their absolute values
    """
    if not preserve_signs:
        factors = factor_children(subdivs)
        n = n % len(factors)
        factors = factors[n:] + factors[:n]
        return refactor_children(subdivs, factors)
    
    signs = get_signs(subdivs)
    abs_values = get_abs(subdivs)
    
    n = n % len(abs_values)
    rotated_values = abs_values[n:] + abs_values[:n]
    
    signed_values = [val * sign for val, sign in zip(rotated_values, signs)]
    
    return refactor_children(subdivs, tuple(signed_values))

def print_subdivisions(subdivs):
    """Format nested tuple structure removing commas."""
    if isinstance(subdivs, (tuple, list)):
        inner = ' '.join(str(print_subdivisions(x)) for x in subdivs)
        return f"({inner})"
    return str(subdivs) 