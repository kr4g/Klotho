# examples/l_system.py
import sys
import os
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

# from allopy import chronos
from allopy.chronos import rhythm_trees as rt
# from allopy import tonos
# from allopy.topos import topos
from allopy.topos import formal_grammars as fg
from allopy.topos.random import rando
# from allopy.aikous import aikous
from allopy.skora import skora

FILEPATH = skora.set_score_path()

def materials():
    
    S = ('F', 'G', 'f', '+', '-', '&')
    C = {'F': 'F', 'f': 'F'}
    G = fg.grammars.constrain_rules(fg.grammars.rand_rules(S, word_length_min=2, word_length_max=7), C)
    
    print(S)
    print(G)
    
    l_str_gens = fg.grammars.gen_str(generations=5, axiom='F', rules=G, display=False)
    
    for i in range(5):
        print(f'Gen: {i}\n{l_str_gens[i]}')
        
    W = [l_str for l_str in l_str_gens.values()]
    
    G_ = rando.rand_encode(W, ['A', 'B', 'C', 'D'])
    
    print(G_)
    
    return None

def composition(l_str: str):
    # for ch in l_str:
    #     if ch == 'F':
    return None

def examples():
    return None

if __name__ == '__main__':
    materials()
    examples()