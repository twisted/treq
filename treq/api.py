from zope.interface import implements

from twisted.internet import reactor
from twisted.internet.defer import succeed

from twisted.web.client import Agent, RedirectAgent
from twisted.web.iweb import IBodyProducer
from twisted.web.http_headers import Headers

from treq.response import Response


_agent = Agent(reactor)


def head(url, headers=None, params=None, allow_redirects=True):
    return request(
        'HEAD', url, headers, params, allow_redirects=allow_redirects,
    )


def get(url, headers=None, params=None, allow_redirects=True):
    return request(
        'GET', url, headers, params, allow_redirects=allow_redirects,
    )


def post(url, headers=None, body=None):
    return request('POST', url, headers, body)


def put(url, headers=None, body=None):
    return request('PUT', url, headers, body)


def delete(url, headers=None):
    return request('DELETE', url, headers)


def request(
    method, url, headers=None, body=None, allow_redirects=True, agent=_agent
):
    if body:
        body = _StringProducer(body)
    if allow_redirects:
        agent = RedirectAgent(agent)

    d = agent.request(method, url, Headers(headers), body)
    d.addCallback(Response, method)

    return d


#
# Private API
#

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


