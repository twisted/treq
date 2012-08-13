from pkg_resources import resource_string

from treq.api import head, get, post, put, delete, request
head, get, post, put, delete, request

__all__ = ('head', 'get', 'post', 'put', 'delete')
__version__ = resource_string(__name__, "_version").strip()
