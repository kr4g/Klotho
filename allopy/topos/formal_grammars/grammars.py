import random
import sys
import os
# from pathlib import Path

# Calculate the path to the directory two folders up
current_directory = os.path.dirname(__file__)
parent_directory = os.path.dirname(current_directory)
grandparent_directory = os.path.dirname(parent_directory)
sys.path.append(grandparent_directory)

from chronos import rhythm_trees as rt
import skora

def rand_rules(symbols, word_length_min=1, word_length_max=3):
  random_word = lambda length: ''.join(random.choices(symbols, k=length))
  rules = {
      symbol: random_word(random.choice(range(word_length_min,
                                              word_length_max + 1))
      ) for symbol in symbols
  }
  return rules

# this could be better
def constrain_rules(rules, constraints):
  for symbol, constraint in constraints.items():
    if symbol in rules and constraint not in rules[symbol]:
      index_to_mutate = random.randint(0, len(rules[symbol]) - 1)
      value = list(rules[symbol])
      value[index_to_mutate] = constraint
      rules[symbol] = ''.join(value)
  return rules

def apply_rules(rules: dict = {}, axiom: str = ''):
  # context-free grammars only!!!!
  '''
  e.g., context-free grammar:

  Alphabet
  V: A B
  Axiom
  w: B
  Production Rules
  P1: A : AB
  P2: B : A
  '''
  return ''.join(rules[c] for c in axiom if c in rules)

def gen_str(generations=0, axiom='', rules={}, display=False):
  gen_dict = {0: axiom}
  l_str = axiom
  if display:
    max_gen_digits = len(str(generations))
    print(f'Gen {0:>{max_gen_digits}} : {l_str}')
  for i in range(1, generations + 1):
    l_str = apply_rules(rules=rules, axiom=l_str)
    gen_dict[i] = l_str
    if display:
      print(f'Gen {i:>{max_gen_digits}} : {l_str}')
  return gen_dict

# def apply_rules(tree, rules, n):
#     if n == 0:
#         return tree
#     elif isinstance(tree, int):
#         # Apply the rule to standalone integers
#         return apply_rules(rules.get(tree, tree), rules, n-1)
#     elif isinstance(tree, tuple):
#         if len(tree) == 2 and isinstance(tree[1], (tuple, list)):
#             # For a tuple (D, S), apply recursion only to the S part
#             D, S = tree
#             return (D, apply_rules(S, rules, n))
#         else:
#             # Apply rules to each element of the tuple if it's not in the (D, S) format
#             return tuple(apply_rules(elem, rules, n) for elem in tree)
#     elif isinstance(tree, list):
#         # Apply the function recursively to each element of the list
#         return [apply_rules(elem, rules, n) for elem in tree]
#     else:
#         return tree

def apply_rules(tree, rules, n):
    if n == 0:
        return tree
    elif isinstance(tree, int):
        result = rules.get(tree, tree)
        return apply_rules(result() if callable(result) else result, rules, n-1)
    elif isinstance(tree, tuple):
        if len(tree) == 2 and isinstance(tree[1], (tuple, list)):
            D, S = tree
            return (D, apply_rules(S, rules, n))
        else:
            return tuple(apply_rules(elem, rules, n) for elem in tree)
    elif isinstance(tree, list):
        return [apply_rules(elem, rules, n) for elem in tree]
    else:
        return tree

def gen_gr(r_tree, rules, n=1):
  '''
  Expands a rhythm tree according to the given rewrite rules.
  :param r_tree: The RT object representing the rhythm tree.
  :param n: The number of iterations for the transformation.
  :param rules: A dictionary of rewrite rules.
  :return: A new RT object with expanded rhythm tree.
  '''
  new_subdivisions = apply_rules(r_tree.subdivisions, rules, n)
  return rt.RT(r_tree.duration, r_tree.time_signature, new_subdivisions)


if __name__ == '__main__':
  # Example usage
  import chronos, random, os
  import numpy as np
  
  class randRules(dict):
    def __getitem__(self, key):
      item = super(randRules, self).__getitem__(key)
      return item()
  
  rules = randRules({
    1             : lambda: random.choice([(1, (1, 2)), (1, (2, 1))]),
    2             : lambda: random.choice([(2, (2, 3, 1)), (2, (3, 2)), (2, (1, 3))]),
    3             : lambda: random.choice([(3, (2, 1, 1, 3)), (3, (2, 1, 1)), (3, (2, 3, 1))]),
    4             : lambda: random.choice([(4, (1, 1, 2, 1, 3)), (4, (2, 1, 1, 3))]),
    # (2, (3, 2, 1)): (3, (1, 1, 2)),
    # (3, (1, 1, 2)): (5, (2, 3)),
  })
  # print(rules[1])
  # print(rules[1])
  # print(rules[2])
  # print(rules[2])
  subdivisions = (4, 3, 1, 2)
  bpm = 66
  duration=96
  r_tree = rt.RT(duration=duration, subdivisions=subdivisions)
  print('gen 0')
  # print(f'{r_tree}\n' + 'sum: ' + str(sum(r_tree.ratios)))
  durs = [chronos.beat_duration(r, bpm) for r in r_tree.ratios]
  dur = round(sum(durs), 2)
  min_dur = round(min(durs), 2)
  max_dur = round(max(durs), 2)
  print(f'dur: {dur}\nmin: {min_dur}\nmax: {max_dur}\n\n')
  for i in range(1, 4 + 1):
    print(f'gen {i}')
    r_tree = gen_gr(r_tree, rules)
    print(f'{r_tree}\n' + 'sum: ' + str(sum(r_tree.ratios)))
    durs = [chronos.beat_duration(r, bpm) for r in r_tree.ratios]
    dur = round(sum(durs), 2)
    min_dur = round(min(durs), 2)
    max_dur = round(max(durs), 2)
    print(f'dur: {dur}\nmin: {min_dur}\nmax: {max_dur}\n\n')
  
  FILEPATH = skora.set_score_path()
  notelists = []
  for i in range(7):
    ratios = r_tree.rotate(i).ratios
    f = 666
    root_freq = np.random.uniform(f - 9, f)
    # freqs = [root_freq * 4 * r for r in ratios]
    freqs = [root_freq * 128 * float(r / duration) for r in ratios]
    # freqs = [root_freq * r for r in tonos.scales.CPS().ratios]*len(ratios)
    amps = [a*0.06 + (a * (1/freqs[i])) + (a * (r/duration)) for i, (a, r) in enumerate(zip(list(np.linspace(0.00167, 0.09692, len(ratios))), ratios))]
    np.random.shuffle(amps)
    sustains = [(duration - r) / duration for r in r_tree.rotate(i + 1 % len(r_tree.ratios)).ratios]
    np.random.shuffle(sustains)
    dc = [random.choice([0.125, 0.33, 0.5, 0.67, 0.75, 1.0, 1.0833, 1.167]) for r in ratios]
    durs = [chronos.beat_duration(r, bpm) for r in ratios]
    attks = [d * dcy * random.choice([0.01, 0.167, 0.33, 0.5, 0.667]) for d, dcy in zip(durs, dc)]
    rels = [d * (1 - dcy) * random.choice([0.25, 0.667, 1.167, 1.125]) for d, dcy in zip(durs, dc)]
    pan1 = list(np.random.uniform(-1, 1, size=len(r_tree.ratios)))
    pan2 = [-p1 for p1 in pan1]
    am1 = [float(1 / r) / duration for r in ratios]
    am2 = [float(duration - r) / duration for r in ratios]
    amRatio = [float(r / duration) for r in ratios]
    synthName = ['SineEnv', 'OscAM', 'OscTrm', 'Vib', 'FMWT'][i % 5]
    
    amps = [a*0.0833 for a in amps] if synthName in ['OscTrm', 'Vib', 'AddSyn', 'FMWT'] else amps
    amFunc = [np.random.choice([0,3]) for _ in range(5)]
    amps = [a*0.0001 for a in amps] if synthName in ['OscAM'] and set([1, 2]).issubset(amFunc) else amps
    reverbs = [0.9692] if set([1, 2]).issubset(amFunc) else [a for a in amps]
    carMul = [random.choice([1, 2, 3, 4, 5, 6, 7, 8, 9, 10]) for _ in range(len(ratios))]
    modMul = [random.choice(ratios) * 20.0 for _ in range(len(ratios))]
    vibRise = [d * dcy * random.choice([0.01, 0.167, 0.33, 0.5, 0.667, 0.9692]) for d, dcy in zip(durs, dc)]
    vibDepth = [np.random.uniform(0, 0.023) for _ in range(len(ratios))]
    table = [np.random.randint(8) for _ in range(6)]
    curve = [np.random.uniform(-10, 10) for _ in range(len(ratios))]
    
    notelist = skora.make_notelist(pfields={'synthName': synthName,
                                            'dur': durs,
                                            'dc': dc,
                                            'amplitude': amps,
                                            'frequency': freqs,
                                            'attackTime': attks,
                                            'releaseTime': rels,
                                            'amFunc': amFunc,
                                            'am1': am1,
                                            'am2': am2,
                                            'amRatio': amRatio,
                                            'amRise': [d*dcy for d, dcy in zip(durs, dc)],
                                            'pan': pan1,
                                            'reverberation': reverbs,
                                            'visalMode': [i % 3],
                                            'table': table,
                                            'curve': curve,
                                            'carMul': carMul,
                                            'modMul': modMul,
                                            'vibeRate1': [np.random.uniform(0, 10) for _ in range(len(ratios))],
                                            'vibeRate2': [np.random.uniform(0, 10) for _ in range(len(ratios))],
                                            'vibRise'    : vibRise,
                                            'vibDepth'   : vibDepth,
                                            'trm1': [np.random.uniform(0, 10) for _ in range(len(ratios))],
                                            'trm2': [np.random.uniform(0, 10) for _ in range(len(ratios))],
                                            'trmRise': [d*dcy for d, dcy in zip(durs, dc)],
                                            'trmDepth': [np.random.uniform(0.167, 0.667) for _ in range(len(ratios))],
                                            'Pan1': [pan1],
                                            'Pan2': [pan2],
                                            'PanRise': [d*dcy for d, dcy in zip(durs, dc)],
                                  })
    notelists += notelist
  
  skora.notelist_to_synthSeq(notelists, os.path.join(FILEPATH, 'XX.synthSequence'))
