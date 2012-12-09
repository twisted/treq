from pkg_resources import resource_string

from treq.api import head, get, post, put, delete, request
from treq.content import json_content, content, collect

__all__ = ['head', 'get', 'post', 'put', 'delete', 'request',
           'collect', 'content', 'json_content']

__version__ = resource_string(__name__, "_version").strip()
