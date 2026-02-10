
class SafeDict(dict):
    def __init__(self, *args, aliases=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._allowed_keys = set(super().keys())
        self._aliases = dict(aliases) if aliases else {}
        for alias, target in self._aliases.items():
            if target not in self._allowed_keys:
                raise KeyError(target)
    
    def _resolve_key(self, key):
        return self._aliases.get(key, key)
    
    def __getitem__(self, key):
        resolved = self._resolve_key(key)
        if resolved in self:
            return super().__getitem__(resolved)
        return None
    
    def __setitem__(self, key, value):
        resolved = self._resolve_key(key)
        if resolved in self._allowed_keys:
            super().__setitem__(resolved, value)
    
    def __delitem__(self, key):
        resolved = self._resolve_key(key)
        if resolved in self._allowed_keys:
            raise KeyError(key)
    
    def clear(self):
        if self._allowed_keys:
            raise KeyError("SafeDict keys are fixed")
    
    def pop(self, key, default=None):
        resolved = self._resolve_key(key)
        if resolved in self._allowed_keys:
            raise KeyError(key)
        return default
    
    def popitem(self):
        raise KeyError("SafeDict keys are fixed")
    
    def setdefault(self, key, default=None):
        resolved = self._resolve_key(key)
        if resolved in self._allowed_keys:
            return super().setdefault(resolved, default)
        return default
    
    def update(self, *args, **kwargs):
        updates = dict(*args, **kwargs)
        for key in updates.keys():
            resolved = self._resolve_key(key)
            if resolved in self._allowed_keys:
                super().__setitem__(resolved, updates[key])
