import random

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

def apply_rules(rules, axiom):
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

def gen_str(generations=0, axiom='p', rules={}, display=False):
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
