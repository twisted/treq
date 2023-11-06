from treq.api import delete, get, head, patch, post, put, request
from treq.content import collect, content, json_content, text_content

from ._version import __version__ as _version

__version__: str = _version.base()

__all__ = [
    "head",
    "get",
    "post",
    "put",
    "patch",
    "delete",
    "request",
    "collect",
    "content",
    "text_content",
    "json_content",
]
