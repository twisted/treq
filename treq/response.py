import json

from twisted.internet.defer import succeed, Deferred
from twisted.internet.protocol import Protocol


class _BodyCollector(Protocol):
    def __init__(self, finished):
        self.finished = finished
        self.data = []

    def dataReceived(self, data):
        self.data.append(data)

    def connectionLost(self, reason):
        self.finished.callback(''.join(self.data))


class Response(object):
    _content_d = None
    _content = None
    _text = None
    _json = None

    def __init__(self, response, method):
        self._response = response
        self._method = method
        self.status_code = response.code
        self.headers = response.headers

    @property
    def content(self):
        def _add_content(data):
            self._content = data
            return self._content

        if self._method == 'HEAD':
            return succeed('')

        if self._content is not None:
            return succeed(self._content)

        if self._content_d is not None:
            d = Deferred()
            d.chainDeferred(self._content_d)
            return d

        d = Deferred()
        d.addCallback(_add_content)
        self._content_d = d
        self._response.deliverBody(_BodyCollector(d))
        return d

    @property
    def json(self):
        def _json_decode(data):
            self._json = json.loads(data)
            return self._json

        if self._json is not None:
            return succeed(self._json)

        if self.headers.getRawHeaders('content-type') != ['application/json']:
            return None

        return self.content.addCallback(_json_decode)

    @property
    def text(self):
        def _text_decode(data):
            self._text = data.decode('utf-8')
            return self._text

        if self._text is not None:
            return succeed(self._text)

        return self.content.addCallback(_text_decode)
