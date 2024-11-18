from klotho.topos.graphs import Tree
from .algorithms.ht_algs import *
from klotho.tonos import fold_interval
from fractions import Fraction

class HarmonicTree(Tree):
    '''
    '''
    def __init__(self,
                 root:int                           = 1,
                 children:Tuple[int, ...]           = (1,),
                 equave:Union[Fraction, float, str] = Fraction(2, 1),
                 n_equave:int                       = 1,
                 inverse:bool                       = False):
        
        super().__init__(root, children)
        self.__root     = root
        self.__children = children
        self.__tree     = Tree(root, children)
        self.__equave   = Fraction(equave)
        self.__n_equave = n_equave
        self.__inverse  = inverse
        self.__partials = self._evaluate()

    def _evaluate(self, inverse:bool=False):
        return tuple(fold_interval(
            interval  = p if not inverse else 1 / p,
            equave    = self.__equave,
            n_equaves = self.__n_equave) for p in measure_partials(self._children))
    
    @property
    def root(self):
        return self.__root
    
    @property
    def children(self):
        return self.__children
    
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
    def tree(self):
        return self.__tree
    
    @property
    def inverse(self):
        return HarmonicTree(
            root     = self.__root,
            children = self.__children,
            equave   = self.__equave,
            n_equave = self.__n_equave,
            inverse  = not self.__inverse
        )
    