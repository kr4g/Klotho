'''
--------------------------------------------------------------------------------------
General functions for generating and transforming sequences in a topological manner.
--------------------------------------------------------------------------------------
'''
from math import prod

__all__ = [
    'permute_list',
    'autoref',
    'autoref_rotmat',
    'iso_pairs',
    'pair_adjacent',
    'substitute',
    'nested_chain',
    'alternate_sequence',
]


def _parse_autoref_args(args, mode_hint:bool):
    '''
    Shared argument handling for :func:`autoref` and :func:`autoref_rotmat`.

    Returns ``(lst1, lst2)``. A single argument is used for both, which is
    the ``lst1 is lst2`` case Haddad always works in; two arguments are the
    Klotho extension documented on both public functions.

    A second positional argument whose elements are not numbers is rejected
    loudly. It used to be taken as ``lst2`` in silence: because ``mode`` is
    keyword-only, ``autoref_rotmat(lst, 'GSDC')`` made ``('G','S','D','C')``
    the tail list and returned a matrix of letters.
    '''
    if len(args) == 1:
        lst1 = lst2 = tuple(args[0])
    elif len(args) == 2:
        lst1, lst2 = map(tuple, args)
        for i, x in enumerate(lst2):
            if not isinstance(x, (int, float)):
                hint = (" If you meant to choose a rotation mode, note that "
                        "'mode' is keyword-only: write "
                        f"mode={args[1]!r}, not a bare second argument."
                        ) if mode_hint else ''
                raise ValueError(
                    'The second positional argument is the tail list and must '
                    f'contain only numbers, but element {i} is {x!r} '
                    f'({type(x).__name__}).' + hint
                )
    else:
        raise ValueError('Function expects either one or two iterable arguments.')

    if len(lst1) != len(lst2):
        raise ValueError('The tuples must be of equal length.')

    return lst1, lst2

# Algorithm 4: PermutList
def permute_list(lst:tuple, pt:int, preserve_signs:bool=False) -> tuple:
    '''
    Algorithm 4: PermutList with optional sign preservation.

    Parameters
    ----------
    lst : tuple
        List of elements to be permuted.
    pt : int
        Starting position for the permutation.
    preserve_signs : bool, optional
        If True, preserves signs while rotating absolute values (default is False).

    Returns
    -------
    tuple
        Circularly permuted list.
    '''
    if not preserve_signs:
        pt = pt % len(lst)
        return lst[pt:] + lst[:pt]
    
    signs = tuple(1 if x >= 0 else -1 for x in lst)
    abs_values = tuple(abs(x) for x in lst)
    
    pt = pt % len(abs_values)
    rotated = abs_values[pt:] + abs_values[:pt]
    
    return tuple(val * sign for val, sign in zip(rotated, signs))

# Algorithm 5: AutoRef
def autoref(*args, preserve_signs:bool=False, depth:int=1):
    '''
    Algorithm 5: AutoRef with optional sign preservation and iteration.

    Each element of ``lst1`` becomes the D (head) of a ``(D, S)`` pair whose
    S (tail) is ``lst2`` rotated one step further than the last. The result
    is a rhythm-tree subdivision spec.

    Parameters
    ----------
    *args
        One list, or two lists of equal length.

        The one-list form is Haddad's; his section 2.3.8 is single-list
        throughout. The ``(lst1, lst2)`` form is a deliberate **Klotho
        extension with no basis in the thesis**. Its invariant is that
        **heads come from ``lst1``, tails from ``lst2``, and the two never
        mix**; the one-list form is exactly the ``lst1 is lst2`` case.
    preserve_signs : bool, optional
        If True, preserves signs while rotating absolute values (default is
        False). Not available with ``depth`` above 1 -- see below.
    depth : int, optional
        Number of iterations (default 1, which is Haddad's plain AutoRef).
        Each further iteration replaces every tail with the AutoRef of that
        tail, so the proportions are preserved all the way down; a list of
        length n yields ``n ** (depth + 1)`` leaves.

        This is *not* the same as calling ``autoref`` on its own output,
        which puts the whole ``(D, S)`` pair in the head slot and does not
        produce a rhythm-tree spec at all.

    Returns
    -------
    tuple
        Tuple containing each original element paired with a permutation.

    Raises
    ------
    ValueError
        If ``depth`` is not an integer of at least 1, or if
        ``preserve_signs`` is combined with a ``depth`` above 1.

    Notes
    -----
    Iteration is Haddad's section 2.3.7, "De l'autoreference" ("On
    self-reference"): "Il s'agit de substituer en subdivisant tout le rythme
    par lui-meme en operant une rotation circulaire a chaque iteration" --
    "It consists of substituting by subdividing the whole rhythm by itself,
    performing a circular rotation at each iteration." Verified against his
    figures 2.18-2.20 (evidence and transcriptions in
    ``projects/klotho-evolution/evidence/haddad-fig-2.19-2.20/``).

    Examples
    --------
    >>> autoref((2, 3))
    ((2, (3, 2)), (3, (2, 3)))
    >>> autoref((2, 3), depth=2)
    ((2, ((3, (2, 3)), (2, (3, 2)))), (3, ((2, (3, 2)), (3, (2, 3)))))
    '''
    if isinstance(depth, bool) or not isinstance(depth, int):
        raise ValueError(f'depth must be an integer of at least 1; got {depth!r}.')
    if depth < 1:
        raise ValueError(f'depth must be an integer of at least 1; got {depth}.')

    if depth > 1 and preserve_signs:
        # permute_list tests ``x >= 0`` on every element, and from depth 2
        # the elements are nested tuples. Haddad publishes no signed
        # iterated example, so rather than invent sign semantics for a
        # nested structure the combination is refused.
        raise ValueError(
            'preserve_signs=True is not defined for depth > 1: from the second '
            'iteration the tails hold nested (D, S) pairs rather than numbers, '
            'and a sign has no meaning on a subtree. Use depth=1, or apply '
            'signs to the result yourself.'
        )

    lst1, lst2 = _parse_autoref_args(args, mode_hint=False)

    rows = tuple((elt, permute_list(lst2, n + 1, preserve_signs))
                 for n, elt in enumerate(lst1))

    if depth == 1:
        return rows

    # Recur on the TAIL only; the head keeps its integer D so the result
    # stays a legal rhythm-tree spec at every level.
    return tuple((head, autoref(tail, depth=depth - 1)) for head, tail in rows)

# AutoRef Matrices
def autoref_rotmat(*args, mode='G', preserve_signs:bool=False):
    '''
    AutoRef rotation matrices with optional sign preservation.

    Parameters
    ----------
    *args
        One list, or two lists of equal length, to generate rotation
        matrices from.

        As with :func:`autoref`, the two-list form is a **Klotho extension
        with no basis in the thesis** -- Haddad's section 2.3.8 works from a
        single list of proportions throughout. ``lst1`` supplies the head
        (D) column, ``lst2`` supplies the tail (S) table, and the two never
        mix; one list is the ``lst1 is lst2`` case. Per mode: every mode's
        row 0 attaches ``autoref(lst2)``'s tails to ``lst1`` in order. Mode
        ``'D'`` then freezes that tail table and rotates only the heads,
        which is where ``lst2``'s role is most visible; mode ``'S'`` freezes
        ``lst1`` and shears only the tails.
    mode : str, optional
        Rotation mode. Default is ``'G'``.

        - ``'G'`` (group): both lists rotate together by the row index --
          heads and tails stay locked.
        - ``'S'``: heads stay fixed; each row shears the tails one extra
          step (``i + j + 1``).
        - ``'D'``: tails are frozen to ``autoref(lst2)`` column-wise; only
          the heads rotate.
        - ``'C'`` (circular): heads rotate by the row index and tails by
          twice it, so both permute circularly but at different rates.
    preserve_signs : bool, optional
        If True, preserves signs while rotating absolute values (default is False).

    The four modes are Haddad's, from section 2.3.8, "Les modes de rotation
    sur un rythme autoreferentiel" ("Rotation modes on a self-referential
    rhythm"), of *L'Unite Temporelle : Une approche pour l'ecriture de la
    duree et de sa quantification* ("The Temporal Unit: An approach to the
    writing of duration and its quantification"), doctoral thesis, Sorbonne
    Universite, 2020, HAL tel-03258984. Mode names follow the thesis: Group,
    S, D, and circulaire (circular).

    Returns
    -------
    tuple
        Tuple of rotation matrices based on the specified mode.

    Examples
    --------
    >>> autoref_rotmat((3, 4, 5, 7), mode='C')[1]
    ((4, (7, 3, 4, 5)), (5, (3, 4, 5, 7)), (7, (4, 5, 7, 3)), (3, (5, 7, 3, 4)))
    '''
    lst1, lst2 = _parse_autoref_args(args, mode_hint=True)

    match mode.upper():
        case 'G':
            return tuple(autoref(permute_list(lst1, i, preserve_signs), 
                               permute_list(lst2, i, preserve_signs), 
                               preserve_signs=preserve_signs) 
                        for i in range(len(lst1)))
        case 'S':
            return tuple(tuple((lst1[j], permute_list(lst2, i + j + 1, preserve_signs)) 
                             for j in range(len(lst1))) 
                        for i in range(len(lst1)))
        case 'D':
            return tuple(tuple((elem, autoref(lst2, preserve_signs=preserve_signs)[j][1]) 
                             for j, elem in enumerate(permute_list(lst1, i, preserve_signs))) 
                        for i in range(len(lst1)))
        case 'C':
            # Haddad 2020, sec 2.3.8.4, "La rotation en mode circulaire"
            # ("Rotation in circular mode"): "une rotation circulaire pour
            # les elements D, et une permutation circulaire pour les
            # elements S" -- "a circular rotation for the D elements, and a
            # circular permutation for the S elements". So the heads advance
            # one step per row and the tails two. Verified against the
            # thesis matrix for (3 4 5 7).
            #
            # The thesis gives only that n=4 example, where 2i mod 4 is
            # indistinguishable from alternating 0/2 by row parity (which is
            # what the 2024 implementation did, and what was first restored
            # here). They diverge from n=5: parity oscillates between two
            # tail tables, while 2i keeps permuting circularly through all
            # of them -- which is what the text actually describes, and what
            # modes G and S already do at rate 1. n=4 output is unchanged.
            return tuple(tuple((elem, autoref(permute_list(lst2, 2 * i, preserve_signs),
                                              preserve_signs=preserve_signs)[j][1])
                             for j, elem in enumerate(permute_list(lst1, i, preserve_signs)))
                        for i in range(len(lst1)))
        case _:
            raise ValueError('Invalid mode. Choose from G, S, D, or C.')

# ------------------------------------------------------------------------------------

def iso_pairs(*lists):
    '''
    Generates tuples of elements from any number of input lists in a cyclic manner.

    Creates a list of tuples where each tuple contains one element from each input list.
    The pairing continues cyclically until the length of the generated list equals
    the product of the lengths of all input lists. When the end of any list is reached, 
    the iteration continues from the beginning of that list, effectively cycling through 
    the shorter lists until all combinations are created.

    This is a form of "cyclic pairing" or "modulo-based pairing" and is 
    different from computing the Cartesian product.

    Parameters
    ----------
    *lists
        Any number of input lists.

    Returns
    -------
    tuple
        A tuple of tuples where each inner tuple contains one element
        from each input list.

    Raises
    ------
    ValueError
        If no lists are provided.

    Examples
    --------
    >>> iso_pairs([1, 2], ['a', 'b', 'c'])
    ((1, 'a'), (2, 'b'), (1, 'c'), (2, 'a'), (1, 'b'), (2, 'c'))
    '''
    if not lists:
        raise ValueError("At least one list must be provided")

    total_length = prod(len(lst) for lst in lists)

    return tuple(tuple(lst[i % len(lst)] for lst in lists) for i in range(total_length))

# ------------------------------------------------------------------------------------

# Not Haddad's. Klotho's own width-2 variant -- see the warning below.
def pair_adjacent(elements):
    '''
    Creates groups where elements are paired with their adjacent elements.

    Each element becomes the head of a ``(D, S)`` pair whose tail is the
    **next two** elements, circularly.

    .. warning::

       This is **not** Haddad's substitution. His section 2.3.6, "De la
       substitution" ("On substitution"), pairs each proportion with its
       **successor only** -- "la proportion en cours avec celle qui lui
       succede", "the current proportion with the one that succeeds it" --
       so his tails have width one where these have width two. The
       difference is structural, not a parameter. For his operation use
       :func:`substitute`.

    Parameters
    ----------
    elements : tuple
        A tuple of elements to be grouped.

    Returns
    -------
    tuple
        A tuple of valid groups.

    Examples
    --------
    >>> pair_adjacent((1, 2, 3, 4, 5))
    ((1, (2, 3)), (2, (3, 4)), (3, (4, 5)), (4, (5, 1)), (5, (1, 2)))
    '''
    if not elements:
        return ()
    
    n = len(elements)
    if n == 1:
        return ((elements[0], ()),)
    
    if n == 2:
        return ((elements[0], (elements[1],)), (elements[1], (elements[0],)))
    
    result = []
    for i in range(n):
        next_idx = (i + 1) % n
        next_next_idx = (i + 2) % n
        result.append((elements[i], (elements[next_idx], elements[next_next_idx])))
    
    return tuple(result)

# Section 2.3.6: rhythmic substitution.
def substitute(elements):
    '''
    Haddad's rhythmic substitution: pair each proportion with its successor.

    Each element becomes the head of a ``(D, S)`` pair whose tail holds the
    **single** next element, circularly. The result is a rhythm-tree
    subdivision spec in which every group has exactly one child.

    Parameters
    ----------
    elements : tuple
        A tuple of proportions to substitute.

    Returns
    -------
    tuple
        A tuple of ``(D, S)`` pairs, one per element.

    Notes
    -----
    From section 2.3.6, "De la substitution" ("On substitution"): "on lui
    substitue ses propres proportions couples deux a deux ... renvoyant ainsi
    la proportion en cours avec celle qui lui succede" -- "one substitutes
    for it its own proportions coupled two by two ... thus returning the
    current proportion together with the one that succeeds it."

    His own worked example, from the proportions ``(5 3 4 2 1 5)``, is the
    pair list ``((5 3) (3 4) (4 2) (2 1) (1 5) (5 5))``. Klotho wraps each
    tail in a one-element tuple so the pair is a legal ``(D, S)`` node; the
    content is his list unchanged.

    .. warning::

       **That pair list is the only published oracle for this function.**
       Figure 2.16, which should show the resulting rhythm tree, prints
       figure 2.15's tree verbatim -- a copy-paste error in the thesis,
       recorded at
       ``projects/klotho-evolution/evidence/haddad-sources/FINDINGS.md``.
       Do not "correct" this implementation against that printed tree.

    A footnote to the same section notes the obvious variants: "l'on peut
    imaginer le contraire, c'est-a-dire, la proportion qui precede avec celle
    en cours, ou toutes autres combinaisons de proportions" -- "one can
    imagine the opposite, that is, the proportion that precedes together with
    the current one, or any other combinations of proportions." Klotho
    implements only the successor form he actually uses; the predecessor form
    is ``substitute(elements[::-1])`` reversed.

    See Also
    --------
    pair_adjacent : Klotho's width-two variant, which is NOT this.

    Examples
    --------
    >>> substitute((5, 3, 4, 2, 1, 5))
    ((5, (3,)), (3, (4,)), (4, (2,)), (2, (1,)), (1, (5,)), (5, (5,)))
    '''
    if not elements:
        return ()

    n = len(elements)
    if n == 1:
        # A lone proportion has no distinct successor to substitute in.
        # Matching pair_adjacent, nested_chain and alternate_sequence, which
        # all return ``(e, ())`` for a singleton, rather than the bare
        # formula's self-referential ``(e, (e,))``.
        return ((elements[0], ()),)

    return tuple((elt, (elements[(i + 1) % n],)) for i, elt in enumerate(elements))

def nested_chain(elements):
    '''
    Creates a nested chain structure with elements.
    
    Parameters
    ----------
    elements : tuple
        A tuple of elements to chain.

    Returns
    -------
    tuple
        A valid group with a nested chain structure.

    Examples
    --------
    >>> nested_chain((1, 2, 3, 4, 5))
    (1, (2, 3, 4, 5))
    '''
    if not elements:
        return None
    
    if len(elements) == 1:
        return (elements[0], ())
    
    if len(elements) == 2:
        return (elements[0], (elements[1],))
    
    return (elements[0], elements[1:])

def alternate_sequence(elements):
    '''
    Creates a sequence where elements alternate between being part of the head and tail.
    
    Parameters
    ----------
    elements : tuple
        A tuple of elements to alternate.

    Returns
    -------
    tuple
        A valid group with alternating elements.

    Examples
    --------
    >>> alternate_sequence((1, 2, 3, 4, 5))
    (1, (2, 4, 3, 5))
    '''
    if not elements:
        return None
    
    if len(elements) == 1:
        return (elements[0], ())
    
    if len(elements) == 2:
        return (elements[0], (elements[1],))
    
    odds = elements[1::2]
    evens = elements[2::2]
    
    return (elements[0], odds + evens)
