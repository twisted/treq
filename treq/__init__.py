import os.path

from treq.api import head, get, post, put, delete, request
head, get, post, put, delete, request

__all__ = ('head', 'get', 'post', 'put', 'delete')


with open(os.path.join(os.path.dirname(__file__), "_version")) as ver:
    __version__ = ver.readline().strip()
