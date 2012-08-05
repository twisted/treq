from collections import MutableMapping
import cgi


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


def get_encoding_from_headers(headers):
    """
    Retrieve the character encoding from a (case-insensitive) dict of headers.

    Returns None if the Content-Type didn't include a charset, or wasn't
    present at all.

    """

    content_type = headers.get('content-type')

    if not content_type:
        return None

    content_type, params = cgi.parse_header(content_type)

    if 'charset' in params:
        return params['charset'].strip("'\"")

    if 'text' in content_type:
        return 'ISO-8859-1'
