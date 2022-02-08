# src for treq.multipart (Python 3)
from typing import Any, Mapping, Optional, Sequence, Sized, Tuple, Union

from twisted.internet.defer import Deferred
from twisted.internet.interfaces import IConsumer
from twisted.internet.task import Cooperator
from twisted.web.iweb import IBodyProducer

from ._types import _EitherStr

long = int
CRLF: bytes

_FieldValue = Union[str, Tuple[Optional[str], Optional[str], IBodyProducer]]

class MultiPartProducer:
    boundary: bytes = ...
    length: int = ...
    def __init__(
        self,
        fields: Union[Sequence[Tuple[str, _FieldValue]], Mapping[_EitherStr, _FieldValue]],
        boundary: Union[bytes, str, None] = ...,
        cooperator: Cooperator = ...,
    ) -> None: ...
    def startProducing(self, consumer: IConsumer) -> Deferred[None]: ...
    def stopProducing(self) -> None: ...
    def pauseProducing(self) -> None: ...
    def resumeProducing(self) -> None: ...

class _LengthConsumer:
    length: int = ...
    def __init__(self) -> None: ...
    def write(self, value: Union[int, str, Sized]) -> None: ...

class _Header:
    name: bytes = ...
    value: object = ...
    params: Sequence[Tuple[object, object]] = ...
    def __init__(
        self, name: bytes, value: str, params: Optional[Sequence[Tuple[str, str]]] = ...
    ) -> None: ...
    def add_param(self, name: Any, value: Any) -> None: ...
    def __bytes__(self) -> bytes: ...