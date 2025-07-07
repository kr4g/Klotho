
class SafeDict(dict):
    
    def __getitem__(self, key):
        if key in self:
            return super().__getitem__(key)
        else:
            return None
    
    def __setitem__(self, key, value):
        if key in self:
            super().__setitem__(key, value)
