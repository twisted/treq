from collections import MutableMapping


class CaseInsensitiveDict(MutableMapping):
    def __init__(self, content=(), **kwcontent):
        self._content = {}
        self.update(content, **kwcontent)

    def __iter__(self):
        return iter(self._content)

    def __len__(self):
        return len(self._content)

    def __getitem__(self, k):
        return self._content[k.lower()]

    def __setitem__(self, k, v):
        self._content[k.lower()] = v

    def __delitem__(self, k):
        del self._content[k.lower()]

    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__, repr(self._content))
