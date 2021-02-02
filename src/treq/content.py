import cgi
import json

from twisted.internet.defer import (
    Deferred, succeed, inlineCallbacks, maybeDeferred,
)

from twisted.internet.protocol import Protocol
from twisted.web.client import ResponseDone
from twisted.web.http import PotentialDataLoss


def _encoding_from_headers(headers):
    content_types = headers.getRawHeaders(u'content-type')
    if content_types is None:
        return None

    # This seems to be the choice browsers make when encountering multiple
    # content-type headers.
    content_type, params = cgi.parse_header(content_types[-1])

    if 'charset' in params:
        return params.get('charset').strip("'\"")

    if content_type == 'application/json':
        return 'UTF-8'


class _NullTransport(object):
    @staticmethod
    def pauseProducing():
        pass

    @staticmethod
    def resumeProducing():
        pass

    @staticmethod
    def stopProducing():
        pass


class _BodyCollector(Protocol):
    def __init__(self, finished, collector):
        self.buffer = b''
        self.writing = False
        self.finished = finished
        self.collector = collector

    def getTransport(self):
        return self.transport or _NullTransport

    @inlineCallbacks
    def dataReceived(self, data):
        try:
            self.buffer += data
            if self.writing:
                return

            w = Deferred()
            self.writing = w
            self.getTransport().pauseProducing()
            while self.buffer:
                bufferred = self.buffer
                self.buffer = b''
                yield self.collector(bufferred)
            self.writing = False
            self.getTransport().resumeProducing()
            w.callback(None)
        except Exception as e:
            self.finished.errback(e)
            self.getTransport().stopProducing()

    @inlineCallbacks
    def connectionLost(self, reason):
        if self.finished.called:
            return
        yield self.writing

        # PotentialDataLoss due to http://twistedmatrix.com/trac/ticket/4840
        if reason.check(ResponseDone, PotentialDataLoss):
            self.finished.callback(None)
        else:
            self.finished.errback(reason)


def collect(response, collector):
    """
    Incrementally collect the body of the response. Respecting flow control.

    This function may only be called **once** for a given response.

    :param IResponse response: The HTTP response to collect the body from.
    :param collector: A callable to be called each time data is available
        from the response body. If callable returns a Deferred, it will be
        callable will not be called again until that Deferred completes.
    :type collector: single argument callable

    :rtype: Deferred that fires with None when the entire body has been read.
    """
    if response.length == 0:
        return succeed(None)

    d = Deferred()
    response.deliverBody(_BodyCollector(d, collector))
    return d


class _Reduce(object):
    def __init__(self, reducer, response, initializer):
        self.reducer = reducer
        self.response = response
        self.initializer = initializer

    def apply(self):
        return (
            collect(self.response, self.collector)
            .addCallback(lambda _: self.initializer)
        )

    def collector(self, data):
        return (
            maybeDeferred(self.reducer, self.initializer, data)
            .addCallback(self.update)
        )

    def update(self, v):
        self.initializer = v


def reduce(reducer, response, initializer):
    """
    Incrementally collect the body of the response. Respecting flow control.

    This function may only be called **once** for a given response.

    :param IResponse response: The HTTP response to collect the body from.
    :param reducer: A reducer function called with accumulator and next data
    :type collector: two argument callable

    :rtype: Deferred that fires with the accumulator when the entire body has
    been read.
    """
    return _Reduce(reducer, response, initializer).apply()


def content(response):
    """
    Read the contents of an HTTP response.

    This function may be called multiple times for a response, it uses a
    ``WeakKeyDictionary`` to cache the contents of the response.

    :param IResponse response: The HTTP Response to get the contents of.

    :rtype: Deferred that fires with the content as a str.
    """
    _content = []
    d = collect(response, _content.append)
    d.addCallback(lambda _: b''.join(_content))
    return d


def json_content(response, **kwargs):
    """
    Read the contents of an HTTP response and attempt to decode it as JSON.

    This function relies on :py:func:`content` and so may be called more than
    once for a given response.

    :param IResponse response: The HTTP Response to get the contents of.

    :param kwargs: Any keyword arguments accepted by :py:func:`json.loads`

    :rtype: Deferred that fires with the decoded JSON.
    """
    # RFC7159 (8.1): Default JSON character encoding is UTF-8
    d = text_content(response, encoding='utf-8')

    d.addCallback(lambda text: json.loads(text, **kwargs))
    return d


def text_content(response, encoding='ISO-8859-1'):
    """
    Read the contents of an HTTP response and decode it with an appropriate
    charset, which may be guessed from the ``Content-Type`` header.

    :param IResponse response: The HTTP Response to get the contents of.
    :param str encoding: A charset, such as ``UTF-8`` or ``ISO-8859-1``,
        used if the response does not specify an encoding.

    :rtype: Deferred that fires with a unicode string.
    """
    def _decode_content(c):

        e = _encoding_from_headers(response.headers)

        if e is not None:
            return c.decode(e)

        return c.decode(encoding)

    d = content(response)
    d.addCallback(_decode_content)
    return d
