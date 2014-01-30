import mimetypes
import uuid

from io import BytesIO
from StringIO import StringIO
from os import path

from urlparse import urlparse, urlunparse
from urllib import urlencode

from twisted.internet.interfaces import IProtocol
from twisted.internet.defer import Deferred
from twisted.python.components import proxyForInterface

from twisted.web.http_headers import Headers
from twisted.web.iweb import IBodyProducer, IResponse

from twisted.web.client import (
    Agent,
    FileBodyProducer,
    HTTPConnectionPool,
    RedirectAgent,
    ContentDecoderAgent,
    GzipDecoder
)

from twisted.python.components import registerAdapter

from treq._utils import default_reactor
from treq.auth import add_auth
from treq import multipart
from treq.response import _Response


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
    def __init__(self, agent):
        self._agent = agent

    @classmethod
    def with_config(cls, **kwargs):
        reactor = default_reactor(kwargs.get('reactor'))

        pool = kwargs.get('pool')
        if not pool:
            persistent = kwargs.get('persistent', True)
            pool = HTTPConnectionPool(reactor, persistent=persistent)

        agent = Agent(reactor, pool=pool)

        if kwargs.get('allow_redirects', True):
            agent = RedirectAgent(agent)

        agent = ContentDecoderAgent(agent, [('gzip', GzipDecoder)])

        auth = kwargs.get('auth')
        if auth:
            agent = add_auth(agent, auth)

        return cls(agent)

    def get(self, url, **kwargs):
        return self.request('GET', url, **kwargs)

    def put(self, url, data=None, **kwargs):
        return self.request('PUT', url, data=data, **kwargs)

    def patch(self, url, data=None, **kwargs):
        return self.request('PATCH', url, data=data, **kwargs)

    def post(self, url, data=None, **kwargs):
        return self.request('POST', url, data=data, **kwargs)

    def head(self, url, **kwargs):
        return self.request('HEAD', url, **kwargs)

    def delete(self, url, **kwargs):
        return self.request('DELETE', url, **kwargs)

    def request(self, method, url, **kwargs):
        method = method.upper()

        # Join parameters provided in the URL
        # and the ones passed as argument.
        params = kwargs.get('params')
        if params:
            url = _combine_query_params(url, params)

        # Convert headers dictionary to
        # twisted raw headers format.
        headers = kwargs.get('headers')
        if headers:
            if isinstance(headers, dict):
                h = Headers({})
                for k, v in headers.iteritems():
                    if isinstance(v, str):
                        h.addRawHeader(k, v)
                    else:
                        h.setRawHeaders(k, v)

                headers = h
        else:
            headers = Headers({})

        # Here we choose a right producer
        # based on the parameters passed in.
        bodyProducer = None
        data = kwargs.get('data')
        files = kwargs.get('files')
        if files:
            # If the files keyword is present we will issue a
            # multipart/form-data request as it suits better for cases
            # with files and/or large objects.
            files = list(_convert_files(files))
            boundary = uuid.uuid4()
            headers.setRawHeaders(
                'content-type', [
                    'multipart/form-data; boundary=%s' % (boundary,)])
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
                    'content-type', ['application/x-www-form-urlencoded'])
                data = urlencode(data, doseq=True)
            bodyProducer = IBodyProducer(data)

        d = self._agent.request(
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

        return d.addCallback(_Response)


def _convert_params(params):
    if hasattr(params, "iteritems"):
        return list(sorted(params.iteritems()))
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
                file_name = path.basename(fobj.name)

        if not content_type:
            content_type = _guess_content_type(file_name)

        yield (param, (file_name, content_type, IBodyProducer(fobj)))


def _combine_query_params(url, params):
    parsed_url = urlparse(url)

    qs = []

    if parsed_url.query:
        qs.extend([parsed_url.query, '&'])

    qs.append(urlencode(params, doseq=True))

    return urlunparse((parsed_url[0], parsed_url[1],
                       parsed_url[2], parsed_url[3],
                       ''.join(qs), parsed_url[5]))


def _from_bytes(orig_bytes):
    return FileBodyProducer(StringIO(orig_bytes))


def _from_file(orig_file):
    return FileBodyProducer(orig_file)


def _guess_content_type(filename):
    if filename:
        guessed = mimetypes.guess_type(filename)[0]
    else:
        guessed = None
    return guessed or 'application/octet-stream'


registerAdapter(_from_bytes, str, IBodyProducer)
registerAdapter(_from_file, file, IBodyProducer)
registerAdapter(_from_file, StringIO, IBodyProducer)
registerAdapter(_from_file, BytesIO, IBodyProducer)
