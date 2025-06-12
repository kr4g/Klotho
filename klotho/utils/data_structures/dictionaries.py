
class SafeDict(dict):
    def __setitem__(self, key, value):
        if key in self:
            super().__setitem__(key, value)
