from zope.interface import implements

from twisted.internet import reactor
from twisted.internet.protocol import Protocol
from twisted.internet.defer import succeed, Deferred


from twisted.web.client import Agent
from twisted.web.iweb import IBodyProducer
from twisted.web.http_headers import Headers


#
# Public API
#


def head(url, headers=None, params=None):
    return _request('HEAD', url, headers, params)


def get(url, headers=None, params=None):
    return _request('GET', url, headers, params)


def post(url, headers=None, body=None):
    return _request('POST', url, headers, body)


def put(url, headers=None, body=None):
    return _request('PUT', url, headers, body)


def delete(url, headers=None):
    return _request('DELETE', url, headers)


#
# Private API
#


class _BodyCollector(Protocol):
    def __init__(self, finished):
        self.finished = finished
        self.data = []

    def dataReceived(self, data):
        self.data.append(data)

    def connectionLost(self, reason):
        self.finished.callback(''.join(self.data))


def _prepResponse(response):
    response.body = ''
    return response


def _addBody(body, response):
    response.body = body
    return response


def _collectBody(response):
    f = Deferred()
    f.addCallback(_addBody, response)

    response.deliverBody(_BodyCollector(f))

    return f


class _StringProducer(object):
    implements(IBodyProducer)

    def __init__(self, body):
        self.body = body
        self.length = len(body)

    def startProducing(self, consumer):
        consumer.write(self.body)
        return succeed(None)

    def pauseProducing(self):
        pass

    def stopProducing(self):
        pass


def _request(method, url, headers=None, body=None):
    if body is not None:
        body = _StringProducer(body)

    d = _getAgent().request(method, url, Headers(headers), body)
    d.addCallback(_prepResponse)

    if method != 'HEAD':
        d.addCallback(_collectBody)

    return d

_agent = None


def _getAgent():
    global _agent

    if _agent is not None:
        return _agent

    _agent = Agent(reactor)
    return _agent
