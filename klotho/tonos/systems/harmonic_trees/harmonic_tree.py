from klotho.topos.graphs import Tree
from .algorithms import *
from klotho.tonos.utils.interval_normalization import reduce_interval
from typing import Tuple, Union
from fractions import Fraction


def _odd_prime_generator():
    yield 3
    primes = [3]
    n = 5
    while True:
        if all(n % p != 0 for p in primes if p * p <= n):
            primes.append(n)
            yield n
        n += 2


class HarmonicTree(Tree):
    """
    A tree structure that models multiplicative harmonic relationships.

    Each leaf node's *harmonic* value is the product of node labels along
    the path from the root. When an equave is specified, leaf ratios are
    reduced into the equave window controlled by *span*.

    This is useful for building spectra, combination tones, and other
    structures derived from a chain of harmonic multiplications.

    Parameters
    ----------
    root : int, optional
        The label of the root node (typically the fundamental partial
        number). Default is 1.
    children : tuple of int, optional
        Child labels that define the branching structure. Default is ``(1,)``.
    equave : Fraction, int, float, str, or None, optional
        Interval of equivalence for ratio reduction. ``None`` disables
        reduction.
    span : int, optional
        Number of equaves for the reduction window. Default is 1.
    """

    def __init__(self,
                 root:int                                  = 1,
                 children:Tuple[int, ...]                  = (1,),
                 equave:Union[Fraction,int,float,str,None] = None,
                 span:int                                  = 1):
        
        super().__init__(root, children)
        
        self._meta['equave'] = Fraction(equave) if equave is not None else None
        self._meta['span']   = span
        
        self._evaluate()

    def _post_structure_clone(self):
        self._meta['equave'] = None
        self._meta['span'] = 1
        non_root = [n for n in self._graph.node_indices() if n != self._root]
        nodes_by_depth = sorted(non_root, key=lambda n: self.depth_of(n), reverse=True)
        odd_primes = _odd_prime_generator()
        label_map = {n: next(odd_primes) for n in nodes_by_depth}
        self._graph[self._root] = {'label': 1}
        for node in non_root:
            self._graph[node] = {'label': label_map[node]}
        self._evaluate()

    def _evaluate(self):
        self[0]['multiple'] = self[self.root]['label']
        self[0]['harmonic'] = self[self.root]['label']
        def process_subtree(node=0, factor=1):
            value = self[node]['label']
            self[node]['multiple'] = value if value > 0 else Fraction(1, abs(value))
            children = list(self.successors(node))
            
            if not children:
                harmonic = value * factor
                self[node]['harmonic'] = harmonic
                
                if self.equave is not None:
                    self[node]['ratio'] = reduce_interval(Fraction(harmonic), self.equave, self.span)
                else:
                    self[node]['ratio'] = harmonic
                
                return
            else:
                for child in children:
                    value = self[child]['label']
                    self[child]['multiple'] = value
                    harmonic = value * factor
                    self[child]['harmonic'] = harmonic
                    
                    if self.equave is not None:
                        self[child]['ratio'] = reduce_interval(Fraction(harmonic), self.equave, self.span)
                    else:
                        self[child]['ratio'] = harmonic
                    
                    if self.out_degree(child) > 0:
                        process_subtree(child, harmonic)
        
        process_subtree()

    @property
    def harmonics(self):
        """tuple : Raw harmonic values at each leaf node (product along path from root)."""
        return tuple(self[n]['harmonic'] for n in self.leaf_nodes)

    @property
    def ratios(self):
        """tuple : Equave-reduced ratios at each leaf node (or raw harmonics if no equave)."""
        return tuple(self[n]['ratio'] for n in self.leaf_nodes)
    
    @property
    def equave(self):
        """Fraction or None : The interval of equivalence, or None if reduction is disabled."""
        return self._meta['equave']
    
    @property
    def span(self):
        """int : Number of equaves used for the reduction window."""
        return self._meta['span']
    
    # @property
    # def inverse(self):
    #     return HarmonicTree(
    #         root     = self.__root,
    #         children = self.__children,
    #         equave   = self.__equave,
    #         span = self.__span,
    #         inverse  = not self.__inverse
    #     )
    