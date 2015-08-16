from __future__ import absolute_import, division, print_function

from pkg_resources import resource_string

from treq.api import head, get, post, put, patch, delete, request
from treq.content import collect, content, text_content, json_content

__all__ = ['head', 'get', 'post', 'put', 'patch', 'delete', 'request',
           'collect', 'content', 'text_content', 'json_content']

__version__ = resource_string(__name__, "_version").strip()
