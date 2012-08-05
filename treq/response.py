import json

import cgi

from twisted.internet.defer import succeed, Deferred
from twisted.internet.protocol import Protocol

from requests.structures import CaseInsensitiveDict
from requests.utils import get_encoding_from_headers


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
        self.headers = CaseInsensitiveDict((
            (header, ', '.join(values)) for header, values in
            response.headers.getAllRawHeaders()))
        self.encoding = get_encoding_from_headers(self.headers) or 'ISO-8859-1'
        self._waiting_for_content = []

    @property
    def content(self):
        def _add_content(data):
            self._content = data

            waiting_for_content = self._waiting_for_content
            self._waiting_for_content = []

            for d in waiting_for_content:
                d.callback(self._content)

            return self._content

        if self._method == 'HEAD':
            return succeed('')

        if self._content is not None:
            return succeed(self._content)

        if self._content_d is not None:
            d = Deferred()
            d.addCallback(lambda _: self._content)
            self._waiting_for_content.append(d)
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

        content_type, params = cgi.parse_header(self.headers['content-type'])

        if content_type != 'application/json':
            return None

        return self.content.addCallback(_json_decode)

    @property
    def text(self):
        def _text_decode(data):
            self._text = data.decode(self.encoding)
            return self._text

        if self._text is not None:
            return succeed(self._text)

        return self.content.addCallback(_text_decode)
