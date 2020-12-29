from __future__ import absolute_import, division, print_function

import mimetypes
import uuid
import warnings

import io

import six
from six.moves.collections_abc import Mapping
from six.moves.http_cookiejar import CookieJar
from six.moves.urllib.parse import quote_plus, urlencode as _urlencode

from twisted.internet.interfaces import IProtocol
from twisted.internet.defer import Deferred
from twisted.python.components import proxyForInterface
from twisted.python.filepath import FilePath
from hyperlink import DecodedURL, EncodedURL

from twisted.web.http_headers import Headers
from twisted.web.iweb import IBodyProducer, IResponse

from twisted.web.client import (
    FileBodyProducer,
    RedirectAgent,
    BrowserLikeRedirectAgent,
    ContentDecoderAgent,
    GzipDecoder,
    CookieAgent
)

from twisted.python.components import registerAdapter
from json import dumps as json_dumps

from treq.auth import add_auth
from treq import multipart
from treq.response import _Response
from requests.cookies import cookiejar_from_dict, merge_cookies


_NOTHING = object()


def urlencode(query, doseq):
    return six.ensure_binary(_urlencode(query, doseq), encoding='ascii')


class _BodyBufferingProtocol(proxyForInterface(IProtocol)):
    def __init__(self, original, buffer, finished):
        self.original = original
        self.buffer = buffer
        self.finished = finished

    def dataReceived(self, data):
        self.buffer.append(data)
        self.original.dataReceived(data)

    def connectionLost(self, reason):
        self.original.connectionLost(reason)
        self.finished.errback(reason)


class _BufferedResponse(proxyForInterface(IResponse)):
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
                _BodyBufferingProtocol(
                    protocol,
                    self._buffer,
                    self._waiting
                )
            )
        elif self._finished:
            for segment in self._buffer:
                protocol.dataReceived(segment)
            protocol.connectionLost(self._reason)
        else:
            self._waiters.append(protocol)


class HTTPClient(object):
    def __init__(self, agent, cookiejar=None,
                 data_to_body_producer=IBodyProducer):
        self._agent = agent
        self._cookiejar = cookiejar or cookiejar_from_dict({})
        self._data_to_body_producer = data_to_body_producer

    def get(self, url, **kwargs):
        """
        See :func:`treq.get()`.
        """
        kwargs.setdefault('_stacklevel', 3)
        return self.request('GET', url, **kwargs)

    def put(self, url, data=None, **kwargs):
        """
        See :func:`treq.put()`.
        """
        kwargs.setdefault('_stacklevel', 3)
        return self.request('PUT', url, data=data, **kwargs)

    def patch(self, url, data=None, **kwargs):
        """
        See :func:`treq.patch()`.
        """
        kwargs.setdefault('_stacklevel', 3)
        return self.request('PATCH', url, data=data, **kwargs)

    def post(self, url, data=None, **kwargs):
        """
        See :func:`treq.post()`.
        """
        kwargs.setdefault('_stacklevel', 3)
        return self.request('POST', url, data=data, **kwargs)

    def head(self, url, **kwargs):
        """
        See :func:`treq.head()`.
        """
        kwargs.setdefault('_stacklevel', 3)
        return self.request('HEAD', url, **kwargs)

    def delete(self, url, **kwargs):
        """
        See :func:`treq.delete()`.
        """
        kwargs.setdefault('_stacklevel', 3)
        return self.request('DELETE', url, **kwargs)

    def request(self, method, url, **kwargs):
        """
        See :func:`treq.request()`.
        """
        method = method.encode('ascii').upper()
        stacklevel = kwargs.pop('_stacklevel', 2)

        if isinstance(url, DecodedURL):
            parsed_url = url.encoded_url
        elif isinstance(url, EncodedURL):
            parsed_url = url
        elif isinstance(url, six.text_type):
            # We use hyperlink in lazy mode so that users can pass arbitrary
            # bytes in the path and querystring.
            parsed_url = EncodedURL.from_text(url)
        else:
            parsed_url = EncodedURL.from_text(url.decode('ascii'))

        # Join parameters provided in the URL
        # and the ones passed as argument.
        params = kwargs.pop('params', None)
        if params:
            parsed_url = parsed_url.replace(
                query=parsed_url.query + tuple(_coerced_query_params(params))
            )

        url = parsed_url.to_uri().to_text().encode('ascii')

        headers = self._request_headers(kwargs.pop('headers', None), stacklevel + 1)

        bodyProducer, contentType = self._request_body(
            data=kwargs.pop('data', None),
            files=kwargs.pop('files', None),
            json=kwargs.pop('json', _NOTHING),
            stacklevel=stacklevel + 1,
        )
        if contentType is not None:
            headers.setRawHeaders(b'Content-Type', [contentType])

        cookies = kwargs.pop('cookies', {})

        if not isinstance(cookies, CookieJar):
            cookies = cookiejar_from_dict(cookies)

        cookies = merge_cookies(self._cookiejar, cookies)
        wrapped_agent = CookieAgent(self._agent, cookies)

        browser_like_redirects = kwargs.pop('browser_like_redirects', False)
        if kwargs.pop('allow_redirects', True):
            if browser_like_redirects:
                wrapped_agent = BrowserLikeRedirectAgent(wrapped_agent)
            else:
                wrapped_agent = RedirectAgent(wrapped_agent)

        wrapped_agent = ContentDecoderAgent(wrapped_agent,
                                            [(b'gzip', GzipDecoder)])

        auth = kwargs.pop('auth', None)
        if auth:
            wrapped_agent = add_auth(wrapped_agent, auth)

        d = wrapped_agent.request(
            method, url, headers=headers,
            bodyProducer=bodyProducer)

        reactor = kwargs.pop('reactor', None)
        if reactor is None:
            from twisted.internet import reactor
        timeout = kwargs.pop('timeout', None)
        if timeout:
            delayedCall = reactor.callLater(timeout, d.cancel)

            def gotResult(result):
                if delayedCall.active():
                    delayedCall.cancel()
                return result

            d.addBoth(gotResult)

        if not kwargs.pop('unbuffered', False):
            d.addCallback(_BufferedResponse)

        if kwargs:
            warnings.warn(
                (
                    "Got unexpected keyword argument: {}."
                    " treq will ignore this argument,"
                    " but will raise TypeError in the next treq release."
                ).format(", ".join(repr(k) for k in kwargs)),
                DeprecationWarning,
                stacklevel=stacklevel,
            )

        return d.addCallback(_Response, cookies)

    def _request_headers(self, headers, stacklevel):
        """
        Convert the *headers* argument to a :class:`Headers` instance

        :returns:
            :class:`twisted.web.http_headers.Headers`
        """
        if isinstance(headers, dict):
            h = Headers({})
            for k, v in headers.items():
                if isinstance(v, (bytes, six.text_type)):
                    h.addRawHeader(k, v)
                elif isinstance(v, list):
                    h.setRawHeaders(k, v)
                else:
                    warnings.warn(
                        (
                            "The value of headers key {!r} has non-string type {}"
                            " and will be dropped."
                            " This will raise TypeError in the next treq release."
                        ).format(k, type(v)),
                        DeprecationWarning,
                        stacklevel=stacklevel,
                    )
            return h
        if isinstance(headers, Headers):
            return headers
        if headers is None:
            return Headers({})

        warnings.warn(
            (
                "headers must be a dict, twisted.web.http_headers.Headers, or None,"
                " but found {}, which will be ignored."
                " This will raise TypeError in the next treq release."
            ).format(type(headers)),
            DeprecationWarning,
            stacklevel=stacklevel,
        )
        return Headers({})

    def _request_body(self, data, files, json, stacklevel):
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
        if json is not _NOTHING and (files or data):
            warnings.warn(
                (
                    "Argument 'json' will be ignored because '{}' was also passed."
                    " This will raise TypeError in the next treq release."
                ).format("data" if data else "files"),
                DeprecationWarning,
                stacklevel=stacklevel,
            )

        if files:
            # If the files keyword is present we will issue a
            # multipart/form-data request as it suits better for cases
            # with files and/or large objects.
            files = list(_convert_files(files))
            boundary = str(uuid.uuid4()).encode('ascii')
            if data:
                data = _convert_params(data)
            else:
                data = []

            return (
                multipart.MultiPartProducer(data + files, boundary=boundary),
                b'multipart/form-data; boundary=' + boundary,
            )

        # Otherwise stick to x-www-form-urlencoded format
        # as it's generally faster for smaller requests.
        if isinstance(data, (dict, list, tuple)):
            return (
                self._data_to_body_producer(urlencode(data, doseq=True)),
                b'application/x-www-form-urlencoded',
            )
        elif data:
            return (
                self._data_to_body_producer(data),
                None,
            )

        if json is not _NOTHING:
            return (
                self._data_to_body_producer(
                    json_dumps(json, separators=(u',', u':')).encode('utf-8'),
                ),
                b'application/json; charset=UTF-8',
            )

        return None, None


def _convert_params(params):
    if hasattr(params, "iteritems"):
        return list(sorted(params.iteritems()))
    elif hasattr(params, "items"):
        return list(sorted(params.items()))
    elif isinstance(params, (tuple, list)):
        return list(params)
    else:
        raise ValueError("Unsupported format")


def _convert_files(files):
    """Files can be passed in a variety of formats:

        * {'file': open("bla.f")}
        * {'file': (name, open("bla.f"))}
        * {'file': (name, content-type, open("bla.f"))}
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


def _query_quote(v):
    # (Any) -> Text
    """
    Percent-encode a querystring name or value.

    :param v: A value.

    :returns:
        The value, coerced to a string and percent-encoded as appropriate for
        a querystring (with space as ``+``).
    """
    if not isinstance(v, (str, bytes)):
        v = six.text_type(v)
    if not isinstance(v, bytes):
        v = v.encode("utf-8")
    q = quote_plus(v)
    if isinstance(q, bytes):
        # Python 2.7 returnes bytes when given bytes, but Python 3.x always
        # returns str.  Coverage disabled here to stop Coveralls complaining
        # until we can drop Python 2.7 support.
        q = q.decode("ascii")  # pragma: no cover
    return q


def _coerced_query_params(params):
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
    :rtype:
        Iterator[Tuple[Text, Text]]
    """
    if isinstance(params, Mapping):
        items = params.items()
    else:
        items = params

    for key, values in items:
        key_quoted = _query_quote(key)

        if not isinstance(values, (list, tuple)):
            values = (values,)
        for value in values:
            yield key_quoted, _query_quote(value)


def _from_bytes(orig_bytes):
    return FileBodyProducer(io.BytesIO(orig_bytes))


def _from_file(orig_file):
    return FileBodyProducer(orig_file)


def _guess_content_type(filename):
    if filename:
        guessed = mimetypes.guess_type(filename)[0]
    else:
        guessed = None
    return guessed or 'application/octet-stream'


registerAdapter(_from_bytes, bytes, IBodyProducer)
registerAdapter(_from_file, io.BytesIO, IBodyProducer)

if six.PY2:
    registerAdapter(_from_file, six.StringIO, IBodyProducer)
    # Suppress lint failure on Python 3.
    registerAdapter(_from_file, file, IBodyProducer)  # noqa: F821
else:
    # file()/open() equiv on Py3
    registerAdapter(_from_file, io.BufferedReader, IBodyProducer)
