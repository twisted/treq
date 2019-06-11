# src for treq.response (Python 3)
#
# NOTE: This dynamically typed stub was automatically generated by stubgen.

from typing import Any

class _Response:
    version: Any
    code: Any
    phrase: Any
    headers: Any
    length: Any
    request: Any
    previousResponse: Any
    def deliverBody(self, protocol): ...
    def setPreviousResponse(self, response): ...

    original: Any = ...
    def __init__(self, original: Any, cookiejar: Any) -> None: ...
    def collect(self, collector: Any): ...
    def content(self): ...
    def json(self, **kwargs: Any): ...
    def text(self, encoding: str = ...): ...
    def history(self): ...
    def cookies(self): ...
