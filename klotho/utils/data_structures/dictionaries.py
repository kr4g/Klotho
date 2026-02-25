
class SafeDict(dict):
    """
    A dictionary with a fixed set of keys that cannot be added to or removed from.

    Values for existing keys can be updated, but new keys cannot be inserted
    and existing keys cannot be deleted. Supports key aliases that resolve
    to canonical keys.

    Parameters
    ----------
    *args
        Positional arguments passed to ``dict``.
    aliases : dict, optional
        Mapping of alias keys to canonical keys. Each alias must
        resolve to a key present in the initial data.
    **kwargs
        Keyword arguments passed to ``dict``.

    Raises
    ------
    KeyError
        If any alias target is not a key in the initial data.

    Examples
    --------
    >>> d = SafeDict({'a': 1, 'b': 2}, aliases={'x': 'a'})
    >>> d['x']
    1
    >>> d['a'] = 10
    >>> d['a']
    10
    """

    def __init__(self, *args, aliases=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._allowed_keys = set(super().keys())
        self._aliases = dict(aliases) if aliases else {}
        for alias, target in self._aliases.items():
            if target not in self._allowed_keys:
                raise KeyError(target)
    
    def _resolve_key(self, key):
        """
        Resolve an alias to its canonical key.

        Parameters
        ----------
        key : hashable
            The key or alias to resolve.

        Returns
        -------
        hashable
            The canonical key.
        """
        return self._aliases.get(key, key)
    
    def __getitem__(self, key):
        """
        Retrieve the value for *key*, resolving aliases.

        Parameters
        ----------
        key : hashable
            The key or alias to look up.

        Returns
        -------
        object or None
            The associated value, or ``None`` if the resolved key
            is not present.
        """
        resolved = self._resolve_key(key)
        if resolved in self:
            return super().__getitem__(resolved)
        return None
    
    def __setitem__(self, key, value):
        """
        Set *value* for *key* only if the resolved key is in the allowed set.

        Parameters
        ----------
        key : hashable
            The key or alias to set.
        value : object
            The value to assign.
        """
        resolved = self._resolve_key(key)
        if resolved in self._allowed_keys:
            super().__setitem__(resolved, value)
    
    def __delitem__(self, key):
        """
        Prevent deletion of keys.

        Parameters
        ----------
        key : hashable
            The key to delete.

        Raises
        ------
        KeyError
            Always raised; keys cannot be removed from a ``SafeDict``.
        """
        resolved = self._resolve_key(key)
        if resolved in self._allowed_keys:
            raise KeyError(key)
    
    def clear(self):
        """
        Prevent clearing all entries.

        Raises
        ------
        KeyError
            Always raised when the dictionary has allowed keys.
        """
        if self._allowed_keys:
            raise KeyError("SafeDict keys are fixed")
    
    def pop(self, key, default=None):
        """
        Prevent popping a key from the dictionary.

        Parameters
        ----------
        key : hashable
            The key to pop.
        default : object, optional
            Fallback value (returned for non-allowed keys).

        Returns
        -------
        object
            *default* if the key is not in the allowed set.

        Raises
        ------
        KeyError
            If the resolved key is in the allowed set.
        """
        resolved = self._resolve_key(key)
        if resolved in self._allowed_keys:
            raise KeyError(key)
        return default
    
    def popitem(self):
        """
        Prevent popping an arbitrary item.

        Raises
        ------
        KeyError
            Always raised; keys are fixed.
        """
        raise KeyError("SafeDict keys are fixed")
    
    def setdefault(self, key, default=None):
        """
        Return the value for *key* if present, else set and return *default*.

        Only sets the value if the resolved key is in the allowed set.

        Parameters
        ----------
        key : hashable
            The key or alias.
        default : object, optional
            Value to set if absent.

        Returns
        -------
        object
            The current or newly set value, or *default* if the key
            is not allowed.
        """
        resolved = self._resolve_key(key)
        if resolved in self._allowed_keys:
            return super().setdefault(resolved, default)
        return default
    
    def update(self, *args, **kwargs):
        """
        Update allowed keys with values from another mapping or keywords.

        Keys not in the allowed set are silently ignored.

        Parameters
        ----------
        *args
            A mapping or iterable of key-value pairs.
        **kwargs
            Keyword arguments to merge.
        """
        updates = dict(*args, **kwargs)
        for key in updates.keys():
            resolved = self._resolve_key(key)
            if resolved in self._allowed_keys:
                super().__setitem__(resolved, updates[key])
