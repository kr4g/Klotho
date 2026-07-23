"""
Symbol-to-action interpreters ("draw rules").

An :class:`Interpreter` walks a word one token at a time, dispatching each
symbol to a registered action. Actions receive a mutable state and an
``emit`` callable; whatever they emit is collected, in order, as the run's
output. What the emissions *are* — pitches, chords, event dicts — is up to
the caller: interpretation stays in user code.

When brackets are enabled, an opening bracket pushes a copy of the state
onto a stack and a closing bracket pops it, so bracketed material runs in
its own state scope (the L-system branching pattern).

Examples
--------
>>> interp = Interpreter(state={'level': 0.0}, brackets=('[', ']'))
>>> @interp.on('p')
... def emit_event(state, emit):
...     emit({'level': state['level']})
>>> @interp.on('+')
... def up(state, emit):
...     state['level'] += 0.1
>>> events = interp.run('p+p[+p]p')
"""

from .alphabet import _normalize_brackets

__all__ = ['Interpreter', 'State']


class State(dict):
    """
    Interpreter state: a plain dict plus a bracket ``depth`` attribute.

    Parameters
    ----------
    *args, **kwargs
        Forwarded to ``dict``.
    depth : int, optional
        Bracket nesting depth. Default is 0.
    """

    def __init__(self, *args, depth=0, **kwargs):
        super().__init__(*args, **kwargs)
        self.depth = depth

    def copy(self):
        """Return a shallow copy of this state, preserving its bracket depth."""
        return State(self, depth=self.depth)


class Interpreter:
    """
    A stateful symbol-to-action interpreter.

    Parameters
    ----------
    state : dict, optional
        Initial state (copied at the start of each run).
    actions : dict, optional
        Mapping of symbol to action callable ``(state, emit) -> None``.
        Actions may also be registered with the :meth:`on` decorator.
        Unknown symbols are no-ops.
    brackets : None, True, or (open, close) pair, optional
        When set, the opening symbol pushes a copy of the state onto a
        stack and the closing symbol pops it. ``True`` means the default
        pair ``('[', ']')``.
    on_push : callable, optional
        ``(state) -> state`` producing the child state on an opening
        bracket. Defaults to a shallow copy of the current state.
    on_pop : callable, optional
        ``(state) -> state`` applied to the restored parent state on a
        closing bracket. Defaults to the identity.
    """

    def __init__(self, state=None, actions=None, brackets=None,
                 on_push=None, on_pop=None):
        self._initial_state = dict(state) if state is not None else {}
        self._actions = dict(actions) if actions is not None else {}
        self._brackets = _normalize_brackets(brackets)
        self._on_push = on_push
        self._on_pop = on_pop

    @property
    def brackets(self):
        """tuple or None : The ``(open, close)`` pair, if enabled."""
        return self._brackets

    def on(self, symbol):
        """
        Register an action for *symbol* (decorator form).

        The action is called as ``action(state, emit)``.
        """
        def decorator(fn):
            self._actions[symbol] = fn
            return fn
        return decorator

    def run(self, word):
        """
        Interpret *word* and return the list of emitted payloads, in order.

        Parameters
        ----------
        word : str or sequence of str
            The word to interpret.

        Returns
        -------
        list
            Everything the actions emitted, in encounter order.
        """
        state = State(self._initial_state)
        stack = []
        events = []
        emit = events.append
        open_, close_ = self._brackets if self._brackets is not None else (None, None)

        for symbol in word:
            if open_ is not None and symbol == open_:
                stack.append(state)
                child = self._on_push(state) if self._on_push is not None else state.copy()
                if not isinstance(child, State):
                    child = State(child)
                child.depth = state.depth + 1
                state = child
            elif close_ is not None and symbol == close_:
                if stack:
                    parent = stack.pop()
                    if self._on_pop is not None:
                        parent = self._on_pop(parent)
                        if not isinstance(parent, State):
                            parent = State(parent, depth=max(0, state.depth - 1))
                    state = parent
            else:
                action = self._actions.get(symbol)
                if action is not None:
                    action(state, emit)
        return events

    def __repr__(self):
        brackets = f", brackets={self._brackets}" if self._brackets is not None else ""
        return f"Interpreter({len(self._actions)} actions{brackets})"
