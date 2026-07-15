import random

import pytest

from klotho.topos.formal_grammars import (
    Alphabet, RuleSet, RewriteSystem, History,
    DerivationTree, derive, Interpreter, markov_walk,
    balance_brackets, bracket_depth, show_generations, word_stats,
    rand_rules, constrain_rules, apply_rules, gen_str,
)
from klotho.topos.graphs import Tree


class TestAlphabet:
    def test_symbols_union(self):
        a = Alphabet(['p', '+'], constants=['.'])
        assert a.symbols == ('p', '+', '.')
        assert a.variables == ('p', '+')
        assert a.constants == ('.',)

    def test_brackets_default_pair(self):
        assert Alphabet('AB', brackets=True).brackets == ('[', ']')
        assert Alphabet('AB').brackets is None
        assert Alphabet('AB', brackets=('<', '>')).brackets == ('<', '>')

    def test_brackets_off_means_ordinary_symbols(self):
        a = Alphabet(['A', '[', ']'])
        assert a.brackets is None
        assert '[' in a

    def test_membership_and_validate(self):
        a = Alphabet('AB', brackets=True)
        assert 'A' in a and '[' in a and 'X' not in a
        assert a.validate('AB[A]')
        assert not a.validate('ABX')

    def test_variable_constant_overlap_rejected(self):
        with pytest.raises(ValueError):
            Alphabet('AB', constants='A')


class TestRuleSet:
    def test_deterministic_string_rules(self):
        rules = RuleSet({'A': 'AB', 'B': 'A'})
        assert rules['A'] == 'AB'
        assert not rules.is_stochastic
        assert not rules.token_mode
        assert rules.rewrite('AB') == 'ABA'

    def test_unknown_tokens_map_to_themselves(self):
        rules = RuleSet({'A': 'AB'})
        assert rules.rewrite('AXA') == 'ABXAB'

    def test_weighted_options_detected(self):
        rules = RuleSet({'t': [(4.0, 't'), (1.0, 'dt')]})
        assert rules.is_stochastic
        options = rules['t']
        assert options == [(4.0, 't'), (1.0, 'dt')]

    def test_single_option_list_equivalent_to_deterministic(self):
        rules = RuleSet({'A': [(2.0, 'AB')]})
        assert rules['A'] == 'AB'
        assert not rules.is_stochastic

    def test_token_mode_multi_char_tokens(self):
        rules = RuleSet({'t': [(1.0, ['V/II', 't'])]})
        assert rules.token_mode
        assert rules.rewrite(('t',)) == ('V/II', 't')

    def test_stochastic_rewrite_respects_weights(self):
        rules = RuleSet({'A': [(1.0, 'B'), (0.0, 'C')]})
        assert rules.rewrite('AAA', rng=1) == 'BBB'

    def test_random_covers_variables_and_constants(self):
        a = Alphabet(['a', 'b'], constants=['.'])
        rules = RuleSet.random(a, word_length=(2, 4), rng=5)
        assert set(rules) == {'a', 'b', '.'}
        assert rules['.'] == '.'
        assert 2 <= len(rules['a']) <= 4

    def test_random_branching_stays_balanced(self):
        a = Alphabet(['p', 'F', '+', '-'], constants=['.'], brackets=True)
        rules = RuleSet.random(a, word_length=(4, 8), branch_probability=1.0,
                               branch_requires='p', rng=11)
        assert rules['['] == '['
        assert rules[']'] == ']'
        for symbol in a.variables:
            word = rules[symbol]
            assert word.count('[') == word.count(']')
            if '[' in word:
                inner = word[word.index('[') + 1:word.index(']')]
                assert 'p' in inner

    def test_random_branch_length_range(self):
        a = Alphabet(['x', '.', '+', '-', 'v'], brackets=True)
        for seed in (3, 17, 88):
            rules = RuleSet.random(a, word_length=(2, 4), branch_probability=1.0,
                                   branch_length=(2, 3), branch_requires='x', rng=seed)
            for symbol in a.variables:
                word = rules[symbol]
                assert word.count('[') == 1 and word.count(']') == 1
                inner = word[word.index('[') + 1:word.index(']')]
                assert 2 <= len(inner) <= 3
                assert 'x' in inner
                stem = word.replace('[' + inner + ']', '')
                assert 2 <= len(stem) <= 4   # word_length governs the stem alone

    def test_random_branch_length_int(self):
        a = Alphabet(['x', '.'], brackets=True)
        rules = RuleSet.random(a, word_length=2, branch_probability=1.0,
                               branch_length=3, rng=5)
        for symbol in a.variables:
            word = rules[symbol]
            inner = word[word.index('[') + 1:word.index(']')]
            assert len(inner) == 3

    def test_random_branch_length_none_keeps_legacy_seed_behavior(self):
        a = Alphabet(['x', '.', '+'], brackets=True)
        for seed in (1, 9, 41):
            default = RuleSet.random(a, word_length=(3, 6), branch_probability=0.7,
                                     branch_requires='x', rng=seed)
            explicit = RuleSet.random(a, word_length=(3, 6), branch_probability=0.7,
                                      branch_requires='x', branch_length=None, rng=seed)
            assert {s: default[s] for s in default} == {s: explicit[s] for s in explicit}

    def test_random_branch_length_min_below_one_raises(self):
        a = Alphabet(['x'], brackets=True)
        with pytest.raises(ValueError):
            RuleSet.random(a, branch_probability=1.0, branch_length=(0, 2), rng=1)

    def test_random_constrain_kwarg_matches_two_step(self):
        a = Alphabet(['x', '.', '+', '-', 'v'], brackets=True)
        constraints = {'x': 'x', '.': 'x'}
        for seed in (7, 23, 42, 71):
            one_call = RuleSet.random(a, word_length=(2, 5), branch_probability=0.5,
                                      branch_requires='x', constrain=constraints,
                                      rng=seed)
            two_step = RuleSet.random(a, word_length=(2, 5), branch_probability=0.5,
                                      branch_requires='x',
                                      rng=seed).constrain(constraints, rng=seed)
            assert {s: one_call[s] for s in one_call} == {s: two_step[s] for s in two_step}
            assert 'x' in one_call['x'] and 'x' in one_call['.']

    def test_random_constrain_kwarg_shares_rng_instance(self):
        constraints = {'a': 'a'}
        one_call = RuleSet.random('ab', word_length=(2, 3), constrain=constraints,
                                  rng=random.Random(5))
        two_step_rng = random.Random(5)
        two_step = RuleSet.random('ab', word_length=(2, 3),
                                  rng=two_step_rng).constrain(constraints, rng=two_step_rng)
        assert {s: one_call[s] for s in one_call} == {s: two_step[s] for s in two_step}

    def test_constrain_places_required_on_stem(self):
        a = Alphabet(['p', 'F'], brackets=True)
        rules = RuleSet({'p': 'F[p]F', 'F': 'FF', '[': '[', ']': ']'}, alphabet=a)
        constrained = rules.constrain({'p': 'p'}, rng=3)
        word = constrained['p']
        stem = [ch for ch, d in _with_depth(word) if d == 0 and ch not in '[]']
        assert 'p' in stem
        # value-like: original unchanged
        assert rules['p'] == 'F[p]F'

    def test_constrain_no_brackets(self):
        rules = RuleSet({'a': 'bb', 'b': 'b'})
        constrained = rules.constrain({'a': 'a'}, rng=0)
        assert 'a' in constrained['a']

    def test_require_min_count_on_stem(self):
        a = Alphabet(['p', 'F'], brackets=True)
        rules = RuleSet({'p': 'F[pp]F', 'F': 'F', '[': '[', ']': ']'}, alphabet=a)
        required = rules.require('p', 'p', min_count=2, rng=4)
        word = required['p']
        stem = [ch for ch, d in _with_depth(word) if d == 0 and ch not in '[]']
        assert stem.count('p') >= 2

    def test_mutate_returns_new_ruleset_and_never_touches_brackets(self):
        a = Alphabet(['p', 'F', '+'], brackets=True)
        rules = RuleSet.random(a, word_length=(4, 6), branch_probability=1.0, rng=9)
        mutated = rules.mutate(1.0, rng=10)
        assert mutated is not rules
        for symbol in a.variables:
            word = mutated[symbol]
            assert word.count('[') == word.count(']')
            assert word.count('[') == rules[symbol].count('[')
        assert mutated['['] == '['

    def test_show_formatter(self, capsys):
        roman = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII']
        rules = RuleSet({'0': '0340'})
        rules.show(formatter=lambda token: roman[int(token)])
        out = capsys.readouterr().out
        assert 'I → I IV V I' in out


def _with_depth(word):
    depth = 0
    result = []
    for ch in word:
        if ch == '[':
            depth += 1
        elif ch == ']':
            depth -= 1
        result.append((ch, depth if ch != '[' else depth - 1))
    return result


class TestRewriteSystem:
    def test_minimal_use(self):
        history = RewriteSystem({'A': 'AB', 'B': 'A'}, axiom='A').generate(5)
        assert isinstance(history, History)
        assert history[0] == 'A'
        assert history[1] == 'AB'
        assert history[3] == 'ABAAB'
        assert history.final == history[5]
        assert len(history) == 6

    def test_step(self):
        system = RewriteSystem({'A': 'AB', 'B': 'A'}, axiom='A')
        assert system.step('AB') == 'ABA'

    def test_token_sequences(self):
        system = RewriteSystem({'t': [(1.0, ['d', 't'])]}, axiom=('t',))
        history = system.generate(2)
        assert history.final == ('d', 'd', 't')

    def test_word_limit_plain(self):
        system = RewriteSystem({'A': 'AA'}, axiom='A')
        history = system.generate(6, word_limit=10)
        assert all(len(word) <= 10 for word in history)

    def test_word_limit_rebalances_brackets(self):
        a = Alphabet(['A'], brackets=True)
        system = RewriteSystem({'A': 'A[A]A', '[': '[', ']': ']'},
                               axiom='A', alphabet=a)
        history = system.generate(5, word_limit=40)
        for word in history:
            assert len(word) <= 40
            assert word.count('[') == word.count(']')

    def test_mutation_records_rule_snapshots(self):
        a = Alphabet(['a', 'b', 'c'])
        rules = RuleSet.random(a, word_length=(2, 3), rng=6)
        system = RewriteSystem(rules, axiom='a', rng=6)
        history = system.generate(10, mutation=0.9)
        assert len(history.rules) == len(history.words)
        assert any(dict(history.rules[i]._rules) != dict(history.rules[0]._rules)
                   for i in range(len(history.rules)))
        # system's own rules stay unchanged (generate is pure)
        assert dict(system.rules._rules) == dict(rules._rules)

    def test_generate_without_mutation_keeps_same_rules(self):
        system = RewriteSystem({'A': 'AB', 'B': 'A'}, axiom='A')
        history = system.generate(3)
        assert all(snapshot is history.rules[0] for snapshot in history.rules)

    def test_grow_returns_final_word(self):
        assert RewriteSystem({'A': 'AB', 'B': 'A'}, axiom='A').grow(3) == 'ABAAB'

    def test_grow_matches_generate_final_with_word_limit(self):
        a = Alphabet(['A'], brackets=True)
        rules = {'A': 'A[A]A', '[': '[', ']': ']'}
        grown = RewriteSystem(rules, axiom='A', alphabet=a).grow(5, word_limit=40)
        history = RewriteSystem(rules, axiom='A', alphabet=a).generate(5, word_limit=40)
        assert grown == history.final


class TestBracketUtilities:
    def test_balance_brackets_drops_orphans_and_closes(self):
        assert balance_brackets(']AB[C') == 'AB[C]'
        assert balance_brackets('A[B[C') == 'A[B[C]]'
        assert balance_brackets('ABC') == 'ABC'

    def test_balance_brackets_custom_pair(self):
        assert balance_brackets('<A<B', brackets=('<', '>')) == '<A<B>>'

    def test_balance_brackets_tokens(self):
        assert balance_brackets(('[', 'A')) == ('[', 'A', ']')

    def test_bracket_depth(self):
        assert bracket_depth('A[B[C]]D') == 2
        assert bracket_depth('ABC') == 0
        assert bracket_depth('<A<B>>', brackets=('<', '>')) == 2


class TestDiagnostics:
    def test_show_generations_accepts_history_and_dict(self, capsys):
        history = RewriteSystem({'A': 'AB', 'B': 'A'}, axiom='A').generate(2)
        show_generations(history)
        show_generations({0: 'A', 1: 'AB'})
        out = capsys.readouterr().out
        assert 'Gen 0 : A' in out

    def test_show_generations_truncates(self, capsys):
        show_generations({0: 'X' * 300}, max_chars=50)
        out = capsys.readouterr().out
        assert '…' in out

    def test_word_stats(self):
        stats = word_stats('AAB', alphabet=Alphabet('ABC'))
        assert stats['length'] == 3
        assert stats['counts'] == {'A': 2, 'B': 1}
        assert stats['distribution']['A'] == pytest.approx(2 / 3)
        assert stats['missing'] == ['C']


class TestDerivation:
    RULES = {
        't': [(4.0, ['t']), (2.5, ['d', 't']), (1.5, ['t', 't'])],
        'd': [(4.0, ['d']), (2.5, ['s', 'd'])],
        's': [(5.0, ['s'])],
    }

    def test_identity_expansion_terminates_branch(self):
        tree = derive('s', self.RULES, max_depth=10, rng=0)
        assert tree.is_leaf
        assert tree.symbol == 's'

    def test_leaves_and_tokens_left_to_right(self):
        tree = DerivationTree('t', [
            DerivationTree('d', [DerivationTree('s'), DerivationTree('d')]),
            DerivationTree('t'),
        ])
        assert tree.tokens() == ['s', 'd', 't']
        assert [n.symbol for n in tree.leaves()] == ['s', 'd', 't']

    def test_derive_respects_max_depth(self):
        tree = derive('t', {'t': [(1.0, ['t', 't'])]}, max_depth=3, rng=1)
        def depth(node):
            return 0 if node.is_leaf else 1 + max(depth(c) for c in node.children)
        assert depth(tree) <= 3

    def test_prolatio_head_weight(self):
        tree = DerivationTree('t', [
            DerivationTree('d', [DerivationTree('s'), DerivationTree('d')]),
            DerivationTree('t'),
        ])
        assert tree.prolatio() == ((1, (1, 1)), 1)
        assert tree.prolatio(head_weight=2) == ((1, (1, 2)), 2)
        assert DerivationTree('t').prolatio() == ()

    def test_show_prints_ascii(self, capsys):
        tree = DerivationTree('t', [DerivationTree('d'), DerivationTree('t')])
        tree.show()
        out = capsys.readouterr().out
        assert '└─ t' in out
        assert '├─ d' in out

    def test_data_dict_open(self):
        node = DerivationTree('x', weight=3)
        node.data['chord'] = ('C4', 'E4')
        assert node.data == {'weight': 3, 'chord': ('C4', 'E4')}

    def test_to_tree_symbols_and_attrs(self):
        dtree = DerivationTree('t', [
            DerivationTree('d', [DerivationTree('s'), DerivationTree('d')]),
            DerivationTree('t'),
        ])
        for leaf, chord in zip(dtree.leaves(), ['S', 'D', 'T']):
            leaf.data['chord'] = chord
        tree = dtree.to_tree(chord='chord')
        assert isinstance(tree, Tree)
        assert tree[tree.root]['label'] == 't'
        leaf_chords = [tree[n].get('chord') for n in tree.leaf_nodes]
        assert leaf_chords == ['S', 'D', 'T']

    def test_to_tree_callable_specs(self):
        dtree = DerivationTree('t', [DerivationTree('d'), DerivationTree('t')])
        tree = dtree.to_tree(value=lambda n: n.symbol.upper(),
                             mark=lambda n: 1 if n.is_leaf else None)
        assert tree[tree.root]['label'] == 'T'
        assert 'mark' not in tree[tree.root]
        assert all(tree[n]['mark'] == 1 for n in tree.leaf_nodes)

    def test_to_tree_single_node(self):
        tree = DerivationTree('t').to_tree()
        assert isinstance(tree, Tree)
        assert tree[tree.root]['label'] == 't'


class TestInterpreter:
    def test_actions_and_emissions(self):
        interp = Interpreter(state={'level': 0.0})

        @interp.on('p')
        def emit_event(state, emit):
            emit(round(state['level'], 2))

        @interp.on('+')
        def up(state, emit):
            state['level'] += 0.1

        assert interp.run('p+p++p') == [0.0, 0.1, 0.3]

    def test_unknown_symbols_are_noops(self):
        interp = Interpreter(actions={'p': lambda s, emit: emit(1)})
        assert interp.run('pXYZp') == [1, 1]

    def test_brackets_scope_state(self):
        interp = Interpreter(state={'level': 0}, brackets=True)

        @interp.on('p')
        def emit_event(state, emit):
            emit((state['level'], state.depth))

        @interp.on('+')
        def up(state, emit):
            state['level'] += 1

        assert interp.run('p[+p[+p]]p') == [(0, 0), (1, 1), (2, 2), (0, 0)]

    def test_on_push_override(self):
        interp = Interpreter(state={'gain': 1.0}, brackets=True,
                             on_push=lambda s: {'gain': s['gain'] * 0.5})

        @interp.on('p')
        def emit_event(state, emit):
            emit(state['gain'])

        assert interp.run('p[p[p]]') == [1.0, 0.5, 0.25]

    def test_run_is_reentrant(self):
        interp = Interpreter(state={'n': 0},
                             actions={'x': lambda s, emit: (s.__setitem__('n', s['n'] + 1),
                                                            emit(s['n']))[1]})
        assert interp.run('xx') == [1, 2]
        assert interp.run('xx') == [1, 2]

    def test_emissions_can_be_any_object(self):
        payload = {'freq': 440}
        interp = Interpreter(actions={'e': lambda s, emit: emit(payload)})
        assert interp.run('e')[0] is payload


class TestMarkovWalk:
    def test_walk_follows_table(self):
        path = markov_walk({0: {1: 1}, 1: {0: 1}}, start=0, length=6)
        assert path == [0, 1, 0, 1, 0, 1]

    def test_walk_length_and_start(self):
        table = {0: {3: 6, 4: 6}, 3: {4: 6, 0: 3}, 4: {0: 6, 3: 3}}
        path = markov_walk(table, start=0, length=16, rng=8)
        assert len(path) == 16
        assert path[0] == 0
        for a, b in zip(path, path[1:]):
            assert b in table[a]

    def test_seeded_walk_is_reproducible(self):
        table = {0: {0: 1, 1: 1}, 1: {0: 1, 1: 1}}
        assert markov_walk(table, start=0, length=12, rng=42) == \
               markov_walk(table, start=0, length=12, rng=42)


class TestLegacyWrappers:
    def test_rand_rules_plain_dict(self):
        rules = rand_rules(['a', 'b', 'c'], 2, 3)
        assert set(rules) == {'a', 'b', 'c'}
        assert all(isinstance(word, str) and 2 <= len(word) <= 3
                   for word in rules.values())

    def test_constrain_rules_in_place(self):
        rules = {'a': 'bb', 'b': 'b'}
        result = constrain_rules(rules, {'a': 'a'})
        assert result is rules
        assert 'a' in rules['a']

    def test_apply_rules(self):
        assert apply_rules({'A': 'AB', 'B': 'A'}, 'AB') == 'ABA'
        assert apply_rules({'A': 'AB'}, 'AXA') == 'ABXAB'

    def test_gen_str_dict_shape(self):
        gen_dict = gen_str(3, 'A', {'A': 'AB', 'B': 'A'})
        assert gen_dict == {0: 'A', 1: 'AB', 2: 'ABA', 3: 'ABAAB'}
