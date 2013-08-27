from pkg_resources import resource_string

from treq.api import head, get, post, put, patch, delete, request
from treq.content import (
    collect, content, text_content, json_content, CollectorResult)

__all__ = ['head', 'get', 'post', 'put', 'patch', 'delete', 'request',
           'collect', 'content', 'text_content', 'json_content',
           'CollectorResult']

__version__ = resource_string(__name__, "_version").strip()
