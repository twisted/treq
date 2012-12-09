import cgi
import json
from weakref import WeakKeyDictionary

from twisted.internet.defer import Deferred, succeed

from twisted.internet.protocol import Protocol
from twisted.web.client import ResponseDone


def _encoding_from_headers(headers, default):
    content_types = headers.getAllRawHeaders('content-type')

    if not content_types:
        return None

    # This seems to be the choice browsers make when encountering multiple
    # content-type headers.
    content_type, params = cgi.parse_header(content_types[-1])

    if 'charset' in params:
        return params.get('charset').strip("'\"")

    if content_type.startswith('text/'):
        return default


class _BodyCollector(Protocol):
    def __init__(self, finished, collector):
        self.finished = finished
        self.collector = collector

    def dataReceived(self, data):
        self.collector(data)

    def connectionLost(self, reason):
        if reason.check(ResponseDone):
            self.finished.callback(None)
            return

        self.finished.errback(reason)


def collect(response, collector):
    if response.length == 0:
        return succeed(None)

    d = Deferred()
    response.deliverBody(_BodyCollector(d, collector))
    return d


_content_cache = WeakKeyDictionary()


def content(response):
    if response in _content_cache:
        return succeed(_content_cache[response])

    def _cache_content(c):
        _content_cache[response] = c
        return c

    _content = []
    d = collect(response, _content.append)
    d.addCallback(lambda _: ''.join(_content))
    d.addCallback(_cache_content)
    return d


def json_content(response):
    d = content(response)
    d.addCallback(json.loads)
    return d


def text_content(response, encoding='ISO-8859-1'):
    def _decode_content(c):
        encoding = _encoding_from_headers(response.headers)

        if encoding is not None:
            return c.decode(encoding)

        return c

    d = content(response)
    d.addCallback(_decode_content)
    return d
