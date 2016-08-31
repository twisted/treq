from __future__ import absolute_import, division, print_function

from treq.api import head, get, post, put, patch, delete, request
from treq.content import collect, content, text_content, json_content

__all__ = ['head', 'get', 'post', 'put', 'patch', 'delete', 'request',
           'collect', 'content', 'text_content', 'json_content']

from twisted.python.modules import getModule as _getModule

__version__ = _getModule(__name__).filePath.sibling("_version").strip()
