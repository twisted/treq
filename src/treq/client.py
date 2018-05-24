from __future__ import absolute_import, division, print_function

import mimetypes
import uuid

from io import BytesIO

from twisted.internet.interfaces import IProtocol
from twisted.internet.defer import Deferred
from twisted.python.components import proxyForInterface
from twisted.python.compat import _PY3, unicode
from twisted.python.filepath import FilePath
from twisted.python.url import URL

from twisted.web.http import urlparse

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

from treq._utils import default_reactor
from treq.auth import add_auth
from treq import multipart
from treq.response import _Response
from requests.cookies import cookiejar_from_dict, merge_cookies

if _PY3:
    from urllib.parse import urlunparse, urlencode as _urlencode

    def urlencode(query, doseq):
        return _urlencode(query, doseq).encode('ascii')
    from http.cookiejar import CookieJar
else:
    from cookielib import CookieJar
    from urlparse import urlunparse
    from urllib import urlencode


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
        return self.request('GET', url, **kwargs)

    def put(self, url, data=None, **kwargs):
        """
        See :func:`treq.put()`.
        """
        return self.request('PUT', url, data=data, **kwargs)

    def patch(self, url, data=None, **kwargs):
        """
        See :func:`treq.patch()`.
        """
        return self.request('PATCH', url, data=data, **kwargs)

    def post(self, url, data=None, **kwargs):
        """
        See :func:`treq.post()`.
        """
        return self.request('POST', url, data=data, **kwargs)

    def head(self, url, **kwargs):
        """
        See :func:`treq.head()`.
        """
        return self.request('HEAD', url, **kwargs)

    def delete(self, url, **kwargs):
        """
        See :func:`treq.delete()`.
        """
        return self.request('DELETE', url, **kwargs)

    def request(self, method, url, **kwargs):
        """
        See :func:`treq.request()`.
        """
        method = method.encode('ascii').upper()

        # Join parameters provided in the URL
        # and the ones passed as argument.
        params = kwargs.get('params')
        if params:
            url = _combine_query_params(url, params)

        if isinstance(url, unicode):
            url = URL.fromText(url).asURI().asText().encode('ascii')

        # Convert headers dictionary to
        # twisted raw headers format.
        headers = kwargs.get('headers')
        if headers:
            if isinstance(headers, dict):
                h = Headers({})
                for k, v in headers.items():
                    if isinstance(v, (bytes, unicode)):
                        h.addRawHeader(k, v)
                    elif isinstance(v, list):
                        h.setRawHeaders(k, v)

                headers = h
        else:
            headers = Headers({})

        # Here we choose a right producer
        # based on the parameters passed in.
        bodyProducer = None
        data = kwargs.get('data')
        files = kwargs.get('files')
        # since json=None needs to be serialized as 'null', we need to
        # explicitly check kwargs for this key
        has_json = 'json' in kwargs

        if files:
            # If the files keyword is present we will issue a
            # multipart/form-data request as it suits better for cases
            # with files and/or large objects.
            files = list(_convert_files(files))
            boundary = str(uuid.uuid4()).encode('ascii')
            headers.setRawHeaders(
                b'content-type', [
                    b'multipart/form-data; boundary=' + boundary])
            if data:
                data = _convert_params(data)
            else:
                data = []

            bodyProducer = multipart.MultiPartProducer(
                data + files, boundary=boundary)
        elif data:
            # Otherwise stick to x-www-form-urlencoded format
            # as it's generally faster for smaller requests.
            if isinstance(data, (dict, list, tuple)):
                headers.setRawHeaders(
                    b'content-type', [b'application/x-www-form-urlencoded'])
                data = urlencode(data, doseq=True)
            bodyProducer = self._data_to_body_producer(data)
        elif has_json:
            # If data is sent as json, set Content-Type as 'application/json'
            headers.setRawHeaders(
                b'content-type', [b'application/json; charset=UTF-8'])
            content = kwargs['json']
            json = json_dumps(content, separators=(u',', u':')).encode('utf-8')
            bodyProducer = self._data_to_body_producer(json)

        cookies = kwargs.get('cookies', {})

        if not isinstance(cookies, CookieJar):
            cookies = cookiejar_from_dict(cookies)

        cookies = merge_cookies(self._cookiejar, cookies)
        wrapped_agent = CookieAgent(self._agent, cookies)

        if kwargs.get('allow_redirects', True):
            if kwargs.get('browser_like_redirects', False):
                wrapped_agent = BrowserLikeRedirectAgent(wrapped_agent)
            else:
                wrapped_agent = RedirectAgent(wrapped_agent)

        wrapped_agent = ContentDecoderAgent(wrapped_agent,
                                            [(b'gzip', GzipDecoder)])

        auth = kwargs.get('auth')
        if auth:
            wrapped_agent = add_auth(wrapped_agent, auth)

        d = wrapped_agent.request(
            method, url, headers=headers,
            bodyProducer=bodyProducer)

        timeout = kwargs.get('timeout')
        if timeout:
            delayedCall = default_reactor(kwargs.get('reactor')).callLater(
                timeout, d.cancel)

            def gotResult(result):
                if delayedCall.active():
                    delayedCall.cancel()
                return result

            d.addBoth(gotResult)

        if not kwargs.get('unbuffered', False):
            d.addCallback(_BufferedResponse)

        return d.addCallback(_Response, cookies)


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
            fobj = val
            if hasattr(fobj, "name"):
                file_name = FilePath(fobj.name).basename()

        if not content_type:
            content_type = _guess_content_type(file_name)

        yield (param, (file_name, content_type, IBodyProducer(fobj)))


def _combine_query_params(url, params):
    parsed_url = urlparse(url.encode('ascii'))

    qs = []

    if parsed_url.query:
        qs.extend([parsed_url.query, b'&'])

    qs.append(urlencode(params, doseq=True))

    return urlunparse((parsed_url[0], parsed_url[1],
                       parsed_url[2], parsed_url[3],
                       b''.join(qs), parsed_url[5]))


def _from_bytes(orig_bytes):
    return FileBodyProducer(BytesIO(orig_bytes))


def _from_file(orig_file):
    return FileBodyProducer(orig_file)


def _guess_content_type(filename):
    if filename:
        guessed = mimetypes.guess_type(filename)[0]
    else:
        guessed = None
    return guessed or 'application/octet-stream'


registerAdapter(_from_bytes, bytes, IBodyProducer)
registerAdapter(_from_file, BytesIO, IBodyProducer)

if not _PY3:
    from StringIO import StringIO
    registerAdapter(_from_file, StringIO, IBodyProducer)
    registerAdapter(_from_file, file, IBodyProducer)
else:
    import io
    # file()/open() equiv on Py3
    registerAdapter(_from_file, io.BufferedReader, IBodyProducer)
