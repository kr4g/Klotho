import random

__all__ = [
    'rand_rules',
    'constrain_rules',
    'apply_rules',
    'gen_str',
]

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

# def apply_rules(tree, rules, n):
#     if n == 0:
#         return tree
#     elif isinstance(tree, int):
#         result = rules.get(tree, tree)
#         return apply_rules(result() if callable(result) else result, rules, n-1)
#     elif isinstance(tree, tuple):
#         if len(tree) == 2 and isinstance(tree[1], (tuple, list)):
#             D, S = tree
#             return (D, apply_rules(S, rules, n))
#         else:
#             return tuple(apply_rules(elem, rules, n) for elem in tree)
#     elif isinstance(tree, list):
#         return [apply_rules(elem, rules, n) for elem in tree]
#     else:
#         return tree
