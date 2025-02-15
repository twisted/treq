"""
Utilities related to retrieving the contents of the response-body.
"""

import json
from typing import Any, Callable, FrozenSet, List, Optional, cast

from ._multipart import parse_options_header
from twisted.internet.defer import Deferred, succeed
from twisted.internet.protocol import Protocol, connectionDone
from twisted.python.failure import Failure
from twisted.web.client import ResponseDone
from twisted.web.http import PotentialDataLoss
from twisted.web.http_headers import Headers
from twisted.web.iweb import IResponse


"""Characters that are valid in a charset name per RFC 2978.

See https://www.rfc-editor.org/errata/eid5433
"""
_MIME_CHARSET_CHARS: FrozenSet[str] = frozenset(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"  # ALPHA
    "0123456789"  # DIGIT
    "!#$%&+-^_`~"  # symbols
)


def _encoding_from_headers(headers: Headers) -> Optional[str]:
    content_types = headers.getRawHeaders("content-type")
    if content_types is None:
        return None

    # This seems to be the choice browsers make when encountering multiple
    # content-type headers.
    media_type, params = parse_options_header(content_types[-1])

    charset = params.get("charset")
    if charset:
        assert isinstance(charset, str)  # for MyPy
        charset = charset.strip("'\"").lower()
        if not charset:
            return None
        if not set(charset).issubset(_MIME_CHARSET_CHARS):
            return None
        return charset

    if media_type == "application/json":
        return "utf-8"

    return None


class _BodyCollector(Protocol):
    finished: "Optional[Deferred[None]]"

    def __init__(
        self, finished: "Deferred[None]", collector: Callable[[bytes], None]
    ) -> None:
        self.finished = finished
        self.collector = collector

    def dataReceived(self, data: bytes) -> None:
        try:
            self.collector(data)
        except BaseException:
            if self.transport:
                self.transport.loseConnection()
            if self.finished:
                self.finished.errback(Failure())
            self.finished = None

    def connectionLost(self, reason: Failure = connectionDone) -> None:
        if self.finished is None:
            return
        if reason.check(ResponseDone):
            self.finished.callback(None)
        elif reason.check(PotentialDataLoss):
            # http://twistedmatrix.com/trac/ticket/4840
            self.finished.callback(None)
        else:
            self.finished.errback(reason)


def collect(
    response: IResponse, collector: Callable[[bytes], None]
) -> "Deferred[None]":
    """
    Incrementally collect the body of the response.

    This function may only be called **once** for a given response.

    If the ``collector`` raises an exception, it will be set as the error value
    on response ``Deferred`` returned from this function, and the underlying
    HTTP transport will be closed.

    :param IResponse response: The HTTP response to collect the body from.
    :param collector: A callable to be called each time data is available from
        the response body.
    :type collector: single argument callable

    :rtype: Deferred that fires with None when the entire body has been read.
    """
    if response.length == 0:
        return succeed(None)

    d: "Deferred[None]" = Deferred()
    response.deliverBody(_BodyCollector(d, collector))
    return d


def content(response: IResponse) -> "Deferred[bytes]":
    """
    Read the contents of an HTTP response.

    This function may be called multiple times for a response, it uses a
    ``WeakKeyDictionary`` to cache the contents of the response.

    :param IResponse response: The HTTP Response to get the contents of.

    :rtype: Deferred that fires with the content as a str.
    """
    _content: List[bytes] = []
    d = collect(response, _content.append)
    return cast(
        "Deferred[bytes]",
        d.addCallback(lambda _: b"".join(_content)),
    )


def json_content(response: IResponse, **kwargs: Any) -> "Deferred[Any]":
    """
    Read the contents of an HTTP response and attempt to decode it as JSON.

    This function relies on :py:func:`content` and so may be called more than
    once for a given response.

    :param IResponse response: The HTTP Response to get the contents of.

    :param kwargs: Any keyword arguments accepted by :py:func:`json.loads`

    :rtype: Deferred that fires with the decoded JSON.
    """
    # RFC7159 (8.1): Default JSON character encoding is UTF-8
    d = text_content(response, encoding="utf-8")
    return d.addCallback(lambda text: json.loads(text, **kwargs))


def text_content(response: IResponse, encoding: str = "ISO-8859-1") -> "Deferred[str]":
    """
    Read the contents of an HTTP response and decode it with an appropriate
    charset, which may be guessed from the ``Content-Type`` header.

    :param IResponse response: The HTTP Response to get the contents of.
    :param str encoding: A charset, such as ``UTF-8`` or ``ISO-8859-1``,
        used if the response does not specify an encoding.

    :rtype: Deferred that fires with a unicode string.
    """

    def _decode_content(c: bytes) -> str:

        e = _encoding_from_headers(response.headers)

        if e is not None:
            return c.decode(e)

        return c.decode(encoding)

    d = content(response)
    return cast("Deferred[str]", d.addCallback(_decode_content))
