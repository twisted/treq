# src for treq.client (Python 3)
from http.cookiejar import CookieJar
from typing import Any, Callable, List, Optional, Tuple

from treq.response import _Response
from twisted.internet.defer import Deferred
from twisted.internet.interfaces import IProtocol, IReactorTime
from twisted.python.failure import Failure
from twisted.web.client import Agent
from twisted.web.http_headers import Headers
from twisted.web.iweb import IBodyProducer, IResponse

from ._types import _JSON, _CookiesType, _DataType, _ParamType

def urlencode(query: _ParamType, doseq: bool) -> str: ...

class _BodyBufferingProtocol:
    original: IProtocol = ...
    buffer: List[str] = ...
    finished: Deferred[Any] = ...
    def __init__(
        self, original: IProtocol, buffer: List[str], finished: Deferred[Any]
    ) -> None: ...
    def dataReceived(self, data: bytes) -> None: ...
    def connectionLost(self, reason: Failure) -> None: ...

class _BufferedResponse:
    original: IResponse = ...
    def __init__(self, original: IResponse) -> None: ...
    def deliverBody(self, protocol: IProtocol) -> None: ...

class HTTPClient:
    def __init__(
        self,
        agent: Agent,
        cookiejar: Optional[CookieJar] = ...,
        data_to_body_producer: Callable[[_DataType], IBodyProducer] = ...,
    ) -> None: ...
    def get(
        self,
        url: str,
        *,
        headers: Optional[Headers] = ...,
        params: Optional[_ParamType] = ...,
        data: Optional[_DataType] = ...,
        json: _JSON = ...,
        reactor: Optional[IReactorTime] = ...,
        persistent: bool = ...,
        allow_redirects: bool = ...,
        auth: Optional[Tuple[str, str]] = ...,
        cookies: Optional[_CookiesType] = ...,
        timeout: Optional[int] = ...,
        browser_like_redirects: bool = ...,
        unbuffered: bool = ...,
    ) -> Deferred[_Response]: ...
    def put(
        self,
        url: str,
        data: Optional[_DataType] = ...,
        *,
        headers: Optional[Headers] = ...,
        params: Optional[_ParamType] = ...,
        json: _JSON = ...,
        reactor: Optional[IReactorTime] = ...,
        persistent: bool = ...,
        allow_redirects: bool = ...,
        auth: Optional[Tuple[str, str]] = ...,
        cookies: Optional[_CookiesType] = ...,
        timeout: Optional[int] = ...,
        browser_like_redirects: bool = ...,
        unbuffered: bool = ...,
    ) -> Deferred[_Response]: ...
    def patch(
        self,
        url: str,
        data: Optional[_DataType] = ...,
        *,
        headers: Optional[Headers] = ...,
        params: Optional[_ParamType] = ...,
        json: _JSON = ...,
        reactor: Optional[IReactorTime] = ...,
        persistent: bool = ...,
        allow_redirects: bool = ...,
        auth: Optional[Tuple[str, str]] = ...,
        cookies: Optional[_CookiesType] = ...,
        timeout: Optional[int] = ...,
        browser_like_redirects: bool = ...,
        unbuffered: bool = ...,
    ) -> Deferred[_Response]: ...
    def post(
        self,
        url: str,
        data: Optional[_DataType] = ...,
        *,
        headers: Optional[Headers] = ...,
        params: Optional[_ParamType] = ...,
        json: _JSON = ...,
        reactor: Optional[IReactorTime] = ...,
        persistent: bool = ...,
        allow_redirects: bool = ...,
        auth: Optional[Tuple[str, str]] = ...,
        cookies: Optional[_CookiesType] = ...,
        timeout: Optional[int] = ...,
        browser_like_redirects: bool = ...,
        unbuffered: bool = ...,
    ) -> Deferred[_Response]: ...
    def head(
        self,
        url: str,
        *,
        headers: Optional[Headers] = ...,
        params: Optional[_ParamType] = ...,
        data: Optional[_DataType] = ...,
        json: _JSON = ...,
        reactor: Optional[IReactorTime] = ...,
        persistent: bool = ...,
        allow_redirects: bool = ...,
        auth: Optional[Tuple[str, str]] = ...,
        cookies: Optional[_CookiesType] = ...,
        timeout: Optional[int] = ...,
        browser_like_redirects: bool = ...,
        unbuffered: bool = ...,
    ) -> Deferred[_Response]: ...
    def delete(
        self,
        url: str,
        *,
        headers: Optional[Headers] = ...,
        params: Optional[_ParamType] = ...,
        data: Optional[_DataType] = ...,
        json: _JSON = ...,
        reactor: Optional[IReactorTime] = ...,
        persistent: bool = ...,
        allow_redirects: bool = ...,
        auth: Optional[Tuple[str, str]] = ...,
        cookies: Optional[_CookiesType] = ...,
        timeout: Optional[int] = ...,
        browser_like_redirects: bool = ...,
        unbuffered: bool = ...,
    ) -> Deferred[_Response]: ...
    def request(
        self,
        method: str,
        url: str,
        *,
        headers: Optional[Headers] = ...,
        params: Optional[_ParamType] = ...,
        data: Optional[_DataType] = ...,
        json: _JSON = ...,
        reactor: Optional[IReactorTime] = ...,
        persistent: bool = ...,
        allow_redirects: bool = ...,
        auth: Optional[Tuple[str, str]] = ...,
        cookies: Optional[_CookiesType] = ...,
        timeout: Optional[int] = ...,
        browser_like_redirects: bool = ...,
        unbuffered: bool = ...,
    ) -> Deferred[_Response]: ...
