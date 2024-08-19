from ..trees import *

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

def rotate_children(subdivs:tuple, n:int=1) -> tuple:
    factors = factor_children(subdivs)
    n = n % len(factors)
    factors = factors[n:] + factors[:n]
    return refactor_children(subdivs, factors)

def rotate_tree(tree:Tree, n:int=1) -> Tree:
    return Tree(tree._root, rotate_children(tree._children, n))
