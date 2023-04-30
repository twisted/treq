import io
import mimetypes
import uuid
from collections import abc
from http.cookiejar import Cookie, CookieJar
from json import dumps as json_dumps
from typing import (Any, Callable, Iterable, Iterator, List, Mapping,
                    Optional, Tuple, Union)
from urllib.parse import quote_plus
from urllib.parse import urlencode as _urlencode

from hyperlink import DecodedURL, EncodedURL
from requests.cookies import merge_cookies
from twisted.internet.defer import Deferred
from twisted.internet.interfaces import IProtocol
from twisted.python.components import proxyForInterface, registerAdapter
from twisted.python.filepath import FilePath
from twisted.web.client import (BrowserLikeRedirectAgent, ContentDecoderAgent,
                                CookieAgent, FileBodyProducer, GzipDecoder,
                                IAgent, RedirectAgent)
from twisted.web.http_headers import Headers
from twisted.web.iweb import IBodyProducer, IResponse

from treq import multipart
from treq._types import (_CookiesType, _DataType, _FilesType, _FileValue,
                         _HeadersType, _ITreqReactor, _JSONType, _ParamsType,
                         _URLType)
from treq.auth import add_auth
from treq.response import _Response


class _Nothing:
    """Type of the sentinel `_NOTHING`"""


_NOTHING = _Nothing()


def urlencode(query: _ParamsType, doseq: bool) -> bytes:
    s = _urlencode(query, doseq)
    return s.encode("ascii")


def _scoped_cookiejar_from_dict(
    url_object: EncodedURL, cookie_dict: Optional[Mapping[str, str]]
) -> CookieJar:
    """
    Create a CookieJar from a dictionary whose cookies are all scoped to the
    given URL's origin.

    @note: This does not scope the cookies to any particular path, only the
        host, port, and scheme of the given URL.
    """
    cookie_jar = CookieJar()
    if cookie_dict is None:
        return cookie_jar
    for k, v in cookie_dict.items():
        secure = url_object.scheme == "https"
        port_specified = not (
            (url_object.scheme == "https" and url_object.port == 443)
            or (url_object.scheme == "http" and url_object.port == 80)
        )
        port = str(url_object.port) if port_specified else None
        domain = url_object.host
        netscape_domain = domain if "." in domain else domain + ".local"

        cookie_jar.set_cookie(
            Cookie(
                # Scoping
                domain=netscape_domain,
                port=port,
                secure=secure,
                port_specified=port_specified,
                # Contents
                name=k,
                value=v,
                # Constant/always-the-same stuff
                version=0,
                path="/",
                expires=None,
                discard=False,
                comment=None,
                comment_url=None,
                rfc2109=False,
                path_specified=False,
                domain_specified=False,
                domain_initial_dot=False,
                rest={},
            )
        )
    return cookie_jar


class _BodyBufferingProtocol(proxyForInterface(IProtocol)):  # type: ignore
    def __init__(self, original, buffer, finished):
        self.original = original
        self.buffer = buffer
        self.finished = finished

    def dataReceived(self, data: bytes) -> None:
        self.buffer.append(data)
        self.original.dataReceived(data)

    def connectionLost(self, reason: Exception) -> None:
        self.original.connectionLost(reason)
        self.finished.errback(reason)


class _BufferedResponse(proxyForInterface(IResponse)):  # type: ignore
    def __init__(self, original):
        self.original = original
        self._buffer = []
        self._waiters = []
        self._waiting = None
        self._finished = False
        self._reason = None

    def _deliverWaiting(self, reason):
        self._reason = reason
        self._finished = True
        for waiter in self._waiters:
            for segment in self._buffer:
                waiter.dataReceived(segment)
            waiter.connectionLost(reason)

    def deliverBody(self, protocol):
        if self._waiting is None and not self._finished:
            self._waiting = Deferred()
            self._waiting.addBoth(self._deliverWaiting)
            self.original.deliverBody(
                _BodyBufferingProtocol(protocol, self._buffer, self._waiting)
            )
        elif self._finished:
            for segment in self._buffer:
                protocol.dataReceived(segment)
            protocol.connectionLost(self._reason)
        else:
            self._waiters.append(protocol)


class HTTPClient:
    def __init__(
        self,
        agent: IAgent,
        cookiejar: Optional[CookieJar] = None,
        data_to_body_producer: Callable[[Any], IBodyProducer] = IBodyProducer,
    ) -> None:
        self._agent = agent
        if cookiejar is None:
            cookiejar = CookieJar()
        self._cookiejar = cookiejar
        self._data_to_body_producer = data_to_body_producer

    def get(self, url: _URLType, **kwargs: Any) -> "Deferred[_Response]":
        """
        See :func:`treq.get()`.
        """
        kwargs.setdefault("_stacklevel", 3)
        return self.request("GET", url, **kwargs)

    def put(
        self, url: _URLType, data: Optional[_DataType] = None, **kwargs: Any
    ) -> "Deferred[_Response]":
        """
        See :func:`treq.put()`.
        """
        kwargs.setdefault("_stacklevel", 3)
        return self.request("PUT", url, data=data, **kwargs)

    def patch(
        self, url: _URLType, data: Optional[_DataType] = None, **kwargs: Any
    ) -> "Deferred[_Response]":
        """
        See :func:`treq.patch()`.
        """
        kwargs.setdefault("_stacklevel", 3)
        return self.request("PATCH", url, data=data, **kwargs)

    def post(
        self, url: _URLType, data: Optional[_DataType] = None, **kwargs: Any
    ) -> "Deferred[_Response]":
        """
        See :func:`treq.post()`.
        """
        kwargs.setdefault("_stacklevel", 3)
        return self.request("POST", url, data=data, **kwargs)

    def head(self, url: _URLType, **kwargs: Any) -> "Deferred[_Response]":
        """
        See :func:`treq.head()`.
        """
        kwargs.setdefault("_stacklevel", 3)
        return self.request("HEAD", url, **kwargs)

    def delete(self, url: _URLType, **kwargs: Any) -> "Deferred[_Response]":
        """
        See :func:`treq.delete()`.
        """
        kwargs.setdefault("_stacklevel", 3)
        return self.request("DELETE", url, **kwargs)

    def request(
        self,
        method: str,
        url: _URLType,
        *,
        params: Optional[_ParamsType] = None,
        headers: Optional[_HeadersType] = None,
        data: Optional[_DataType] = None,
        files: Optional[_FilesType] = None,
        json: Union[_JSONType, _Nothing] = _NOTHING,
        auth: Optional[Tuple[Union[str, bytes], Union[str, bytes]]] = None,
        cookies: Optional[_CookiesType] = None,
        allow_redirects: bool = True,
        browser_like_redirects: bool = False,
        unbuffered: bool = False,
        reactor: Optional[_ITreqReactor] = None,
        timeout: Optional[float] = None,
        _stacklevel: int = 2,
    ) -> "Deferred[_Response]":
        """
        See :func:`treq.request()`.
        """
        method_: bytes = method.encode("ascii").upper()

        if isinstance(url, DecodedURL):
            parsed_url = url.encoded_url
        elif isinstance(url, EncodedURL):
            parsed_url = url
        elif isinstance(url, str):
            # We use hyperlink in lazy mode so that users can pass arbitrary
            # bytes in the path and querystring.
            parsed_url = EncodedURL.from_text(url)
        else:
            parsed_url = EncodedURL.from_text(url.decode("ascii"))

        # Join parameters provided in the URL
        # and the ones passed as argument.
        if params:
            parsed_url = parsed_url.replace(
                query=parsed_url.query + tuple(_coerced_query_params(params))
            )

        url = parsed_url.to_uri().to_text().encode("ascii")

        headers = self._request_headers(headers, _stacklevel + 1)

        bodyProducer, contentType = self._request_body(
            data, files, json, stacklevel=_stacklevel + 1
        )
        if contentType is not None:
            headers.setRawHeaders(b"Content-Type", [contentType])

        if not isinstance(cookies, CookieJar):
            cookies = _scoped_cookiejar_from_dict(parsed_url, cookies)

        cookies = merge_cookies(self._cookiejar, cookies)
        wrapped_agent: IAgent = CookieAgent(self._agent, cookies)

        if allow_redirects:
            if browser_like_redirects:
                wrapped_agent = BrowserLikeRedirectAgent(wrapped_agent)
            else:
                wrapped_agent = RedirectAgent(wrapped_agent)

        wrapped_agent = ContentDecoderAgent(wrapped_agent, [(b"gzip", GzipDecoder)])

        if auth:
            wrapped_agent = add_auth(wrapped_agent, auth)

        d = wrapped_agent.request(
            method_, url, headers=headers, bodyProducer=bodyProducer
        )

        if reactor is None:
            from twisted.internet import reactor  # type: ignore
        assert reactor is not None

        if timeout:
            delayedCall = reactor.callLater(timeout, d.cancel)

            def gotResult(result):
                if delayedCall.active():
                    delayedCall.cancel()
                return result

            d.addBoth(gotResult)

        if not unbuffered:
            d.addCallback(_BufferedResponse)

        return d.addCallback(_Response, cookies)

    def _request_headers(
        self, headers: Optional[_HeadersType], stacklevel: int
    ) -> Headers:
        """
        Convert the *headers* argument to a :class:`Headers` instance
        """
        if isinstance(headers, dict):
            h = Headers({})
            for k, v in headers.items():
                if isinstance(v, (bytes, str)):
                    h.addRawHeader(k, v)
                elif isinstance(v, list):
                    h.setRawHeaders(k, v)
                else:
                    raise TypeError(
                        "The value of headers key {!r} has non-string type {}.".format(
                            k, type(v)
                        )
                    )
            return h
        if isinstance(headers, Headers):
            return headers
        if headers is None:
            return Headers({})

        raise TypeError(
            (
                "headers must be a dict, twisted.web.http_headers.Headers, or None,"
                " but found {}."
            ).format(type(headers))
        )

    def _request_body(
        self,
        data: Optional[_DataType],
        files: Optional[_FilesType],
        json: Union[_JSONType, _Nothing],
        stacklevel: int,
    ) -> Tuple[Optional[IBodyProducer], Optional[bytes]]:
        """
        Here we choose a right producer based on the parameters passed in.

        :params data:
            Arbitrary request body data.

            If *files* is also passed this must be a :class:`dict`,
            a :class:`tuple` or :class:`list` of field tuples as accepted by
            :class:`MultiPartProducer`. The request is assigned a Content-Type
            of ``multipart/form-data``.

            If a :class:`dict`, :class:`list`, or :class:`tuple` it is
            URL-encoded and the request assigned a Content-Type of
            ``application/x-www-form-urlencoded``.

            Otherwise, any non-``None`` value is passed to the client's
            *data_to_body_producer* callable (by default,
            :class:`IBodyProducer`), which accepts file-like objects.

        :params files:
            Files to include in the request body, in any of the several formats
            described in :func:`_convert_files()`.

        :params json:
            JSON-encodable data, or the sentinel `_NOTHING`. The sentinel is
            necessary because ``None`` is a valid JSON value.
        """
        if json is not _NOTHING:
            if files or data:
                raise TypeError(
                    "Argument 'json' cannot be combined with '{}'.".format(
                        "data" if data else "files"
                    )
                )
            return (
                self._data_to_body_producer(
                    json_dumps(json, separators=(",", ":")).encode("utf-8"),
                ),
                b"application/json; charset=UTF-8",
            )

        if files:
            # If the files keyword is present we will issue a
            # multipart/form-data request as it suits better for cases
            # with files and/or large objects.
            fields: List[Tuple[str, _FileValue]] = []
            if data:
                for field in _convert_params(data):
                    fields.append(field)
            for field in _convert_files(files):
                fields.append(field)

            boundary = str(uuid.uuid4()).encode("ascii")
            return (
                multipart.MultiPartProducer(fields, boundary=boundary),
                b"multipart/form-data; boundary=" + boundary,
            )

        # Otherwise stick to x-www-form-urlencoded format
        # as it's generally faster for smaller requests.
        if isinstance(data, (dict, list, tuple)):
            return (
                # FIXME: The use of doseq here is not permitted in the types, and
                # sequence values aren't supported in the files codepath. It is
                # maintained here for backwards compatibility. See
                # https://github.com/twisted/treq/issues/360.
                self._data_to_body_producer(urlencode(data, doseq=True)),
                b"application/x-www-form-urlencoded",
            )
        elif data:
            return (
                self._data_to_body_producer(data),
                None,
            )

        return None, None


def _convert_params(params: _DataType) -> Iterable[Tuple[str, str]]:
    items_method = getattr(params, "items", None)
    if items_method:
        return list(sorted(items_method()))
    elif isinstance(params, (tuple, list)):
        return list(params)
    else:
        raise ValueError("Unsupported format")


def _convert_files(files):
    """
    Files can be passed in a variety of formats:

    * {"fieldname": open("bla.f", "rb")}
    * {"fieldname": ("filename", open("bla.f", "rb"))}
    * {"fieldname": ("filename", "content-type", open("bla.f", "rb"))}
    * Anything that has iteritems method, e.g. MultiDict:
      MultiDict([(name, open()), (name, open())]

    Our goal is to standardize it to unified form of:

    * [(param, (file name, content type, producer))]
    """

    if hasattr(files, "iteritems"):
        files = files.iteritems()
    elif hasattr(files, "items"):
        files = files.items()

    for param, val in files:
        file_name, content_type, fobj = (None, None, None)
        if isinstance(val, tuple):
            if len(val) == 2:
                file_name, fobj = val
            elif len(val) == 3:
                file_name, content_type, fobj = val
            else:
                # NB: This is TypeError for backward compatibility. This case
                # used to fall through to `IBodyProducer`, below, which raised
                # TypeError about being unable to coerce None.
                raise TypeError(
                    (
                        "`files` argument must be a sequence of tuples of"
                        " (file_name, file_obj) or"
                        " (file_name, content_type, file_obj),"
                        " but the {!r} tuple has length {}: {!r}"
                    ).format(param, len(val), val),
                )
        else:
            fobj = val
            if hasattr(fobj, "name"):
                file_name = FilePath(fobj.name).basename()

        if not content_type:
            content_type = _guess_content_type(file_name)

        # XXX: Shouldn't this call self._data_to_body_producer?
        yield (param, (file_name, content_type, IBodyProducer(fobj)))


def _query_quote(v: Any) -> str:
    """
    Percent-encode a querystring name or value.

    :param v: A value.

    :returns:
        The value, coerced to a string and percent-encoded as appropriate for
        a querystring (with space as ``+``).
    """
    if not isinstance(v, (str, bytes)):
        v = str(v)
    if not isinstance(v, bytes):
        v = v.encode("utf-8")
    q = quote_plus(v)
    return q


def _coerced_query_params(params: _ParamsType) -> Iterator[Tuple[str, str]]:
    """
    Carefully coerce *params* in the same way as `urllib.parse.urlencode()`

    Parameter names and values are coerced to unicode, which is encoded as
    UTF-8 and then percent-encoded. As a special case, `bytes` are directly
    percent-encoded.

    :param params:
        A mapping or sequence of (name, value) two-tuples. The value may be
        a list or tuple of multiple values. Names and values may be pretty much
        any type.

    :returns:
        A generator that yields two-tuples containing percent-encoded text
        strings.
    """
    items: Iterable[Tuple[str, Union[str, Tuple[str, ...], List[str]]]]
    if isinstance(params, abc.Mapping):
        items = params.items()
    else:
        items = params

    for key, values in items:
        key_quoted = _query_quote(key)

        if not isinstance(values, (list, tuple)):
            values = (values,)
        for value in values:
            yield key_quoted, _query_quote(value)


def _from_bytes(orig_bytes: bytes) -> IBodyProducer:
    return FileBodyProducer(io.BytesIO(orig_bytes))


def _from_file(orig_file: Union[io.BytesIO, io.BufferedReader]) -> IBodyProducer:
    return FileBodyProducer(orig_file)


def _guess_content_type(filename: str) -> Optional[str]:
    if filename:
        guessed = mimetypes.guess_type(filename)[0]
    else:
        guessed = None
    return guessed or "application/octet-stream"


registerAdapter(_from_bytes, bytes, IBodyProducer)
registerAdapter(_from_file, io.BytesIO, IBodyProducer)

# file()/open() equiv
registerAdapter(_from_file, io.BufferedReader, IBodyProducer)
