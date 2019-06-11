# src for treq.response (Python 3)
from http.cookiejar import CookieJar
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from requests.cookies import RequestsCookieJar
from twisted.internet.defer import Deferred
from twisted.internet.interfaces import IProtocol
from twisted.web.http_headers import Headers
from twisted.web.iweb import IClientRequest, IResponse

class _Response:

    original: IResponse
    def __init__(
        self, original: IResponse, cookiejar: Optional[Union[CookieJar, Dict[str, Any]]]
    ) -> None: ...
    def collect(self, collector: Callable[[bytes], Any]) -> Deferred[None]: ...
    def content(self) -> Deferred[bytes]: ...
    def json(
        self, **kwargs: Any
    ) -> Deferred[Any]: ...  # Should be _JSON but so many errors
    def text(self, encoding: str = ...) -> Deferred[str]: ...
    def history(self) -> List[_Response]: ...
    def cookies(self) -> RequestsCookieJar: ...
    # From IResponse
    version: Tuple[str, int, int]
    code: int
    phrase: str
    headers: Headers
    length: int
    request: IClientRequest
    previousResponse: Optional[IResponse]
    def deliverBody(self, protocol: IProtocol) -> None: ...
    def setPreviousResponse(self, response: IResponse) -> None: ...
