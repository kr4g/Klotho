from klotho.topos.graphs import Tree
from .algorithms.ht_algs import *
from typing import List, Union, Tuple
from fractions import Fraction

class HarmonicTree(Tree):
    def __init__(self, root:int, children:Tuple[int, ...]):
        super().__init__(root, children)
        self.__root = root
        self.__children = children
        self.__n_equave = 1
        self.__equave = Fraction(2, 1)
        self.__partials = self._evaluate()
    
    def _evaluate(self):
        return tuple((self.__equave**self.__n_equave) * p for p in measure_partials(self._children))

    @property
    def partials(self):
        return self.__partials
    
    @property
    def equave(self):
        return self.__equave
    
    @property
    def n_equave(self):
        return self.__n_equave
    
    @property
    def root(self):
        return self.__root
    
    @property
    def children(self):
        return self.__children

