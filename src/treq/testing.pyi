# Stubs for treq.testing (Python 3)
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple, Union, ContextManager

from treq.response import _Response
from twisted.internet.defer import Deferred
from twisted.internet.interfaces import IConsumer, IReactorTime
from twisted.web.http_headers import Headers
from twisted.web.iweb import IBodyProducer, IRequest, IResponse
from twisted.web.resource import IResource, Resource

from ._types import _JSON, _CookiesType, _DataType, _EitherStr, _ParamType

class RequestTraversalAgent:
    def __init__(self, rootResource: IResource) -> None: ...
    def request(
        self,
        method: bytes,
        uri: bytes,
        headers: Optional[Headers] = ...,
        bodyProducer: Optional[IBodyProducer] = ...,
    ) -> Deferred[IResponse]: ...
    def flush(self) -> None: ...

class _SynchronousProducer:
    body: bytes = ...
    length: int = ...
    def __init__(self, body: Union[str, bytes]) -> None: ...
    def startProducing(self, consumer: IConsumer) -> Deferred[None]: ...

class StubTreq:
    def __init__(self, resource: IResource) -> None: ...
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
    def collect(
        self, response: IResponse, collector: Callable[[str], Any]
    ) -> Deferred[None]: ...
    def content(self, response: IResponse) -> Deferred[bytes]: ...
    def json_content(self, response: IResponse, **kwargs: Any) -> Deferred[Any]: ...
    def text_content(
        self, response: IResponse, encoding: str = ...
    ) -> Deferred[str]: ...
    def flush(self) -> None: ...

_HeadersType = Mapping[_EitherStr, Sequence[_EitherStr]]

class StringStubbingResource(Resource):
    isLeaf: bool = ...
    def __init__(
        self,
        get_response_for: Callable[
            [bytes, str, _ParamType, _HeadersType, bytes],
            Union[int, bytes],
        ],
    ) -> None: ...
    def render(self, request: IRequest) -> Union[int, bytes]: ...

class HasHeaders:
    def __init__(self, headers: _HeadersType) -> None: ...

_RequestTuple = Tuple[bytes, str, _ParamType, Union[HasHeaders, _HeadersType], bytes]
_ResponseTuple = Tuple[int, _HeadersType, bytes]

class RequestSequence:
    def __init__(
        self,
        sequence: List[Tuple[_RequestTuple, _ResponseTuple]],
        async_failure_reporter: Optional[Callable[[str], Any]] = ...,
    ) -> None: ...
    def consumed(self) -> bool: ...
    def consume(self, sync_failure_reporter: Callable[[str], Any]) -> ContextManager[None]: ...
    def __call__(
        self,
        method: bytes,
        url: str,
        params: _ParamType,
        headers: _HeadersType,
        data: bytes,
    ) -> bytes: ...
