from __future__ import absolute_import, division, print_function

from ._version import __version__

from treq.api import head, get, post, put, patch, delete, request
from treq.content import collect, content, text_content, json_content
from treq.response import _Response

__version__ = __version__.base()

check_status = _Response.check_status

__all__ = ['head', 'get', 'post', 'put', 'patch', 'delete', 'request',
           'check_status', 'collect', 'content', 'text_content',
           'json_content']
