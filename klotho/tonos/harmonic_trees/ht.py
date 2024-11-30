from klotho.topos.graphs import Tree
from .algorithms.ht_algs import *
from klotho.tonos import fold_interval
from fractions import Fraction

class HarmonicTree(Tree):
    '''
    '''
    def __init__(self,
                 root:int                             = 1,
                 children:Tuple[int, ...]             = (1,),
                 equave:Union[Fraction,int,float,str] = 2,
                 span:int                             = 1,
                 inverse:bool                         = False):
        
        super().__init__(root, children)
        self._equave    = Fraction(equave)
        self._span      = span
        self._inverse   = inverse
        self._harmonics = None
        self._ratios    = None
        self._evaluate()

    # def _evaluate(self, inverse:bool=False):
    #     return tuple(fold_interval(
    #         interval  = p if not inverse else 1 / p,
    #         equave    = self.__equave,
    #         spans = self.__span) for p in measure_partials(self._children))
    def _evaluate(self):
        self.graph.nodes[0]['span'] = self._span
        def process_subtree(node=0, factor=1):
            value = self.graph.nodes[node]['label']
            self.graph.nodes[node]['multiple'] = value
            children = list(self.graph.successors(node))
            
            if not children:
                harmonic = value * factor
                self.graph.nodes[node]['harmonic'] = harmonic
                self.graph.nodes[node]['ratio'] = fold_interval(Fraction(harmonic), self._equave, self._span)
                return
            else:
                for child in children:
                    harmonic = self.graph.nodes[child]['label'] * factor
                    self.graph.nodes[child]['harmonic'] = harmonic
                    self.graph.nodes[child]['ratio'] = fold_interval(Fraction(harmonic), self._equave, self._span)
                    if self.graph.out_degree(child) > 0:
                        process_subtree(child, harmonic)
        
        process_subtree()
    
    @property
    def harmonics(self):
        if self._harmonics is None:
            self._harmonics = tuple(self.graph.nodes[n]['harmonic'] for n in self.leaf_nodes)
        return self._harmonics
    
    @property
    def ratios(self):
        if self._ratios is None:
            self._ratios = tuple(self.graph.nodes[n]['ratio'] for n in self.leaf_nodes)
        return self._ratios
    
    @property
    def equave(self):
        return self._equave
    
    @property
    def span(self):
        return self._span
    
    # @property
    # def inverse(self):
    #     return HarmonicTree(
    #         root     = self.__root,
    #         children = self.__children,
    #         equave   = self.__equave,
    #         span = self.__span,
    #         inverse  = not self.__inverse
    #     )
    