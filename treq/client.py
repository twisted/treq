from StringIO import StringIO

from twisted.web.http_headers import Headers
from twisted.web.iweb import IBodyProducer
from twisted.web.client import FileBodyProducer
from twisted.web.client import Agent, HTTPConnectionPool, RedirectAgent

from twisted.python.components import registerAdapter

from treq.response import Response


def _from_bytes(orig_bytes):
    return FileBodyProducer(StringIO(orig_bytes))


def _from_file(orig_file):
    return FileBodyProducer(orig_file)


registerAdapter(_from_bytes, str, IBodyProducer)
registerAdapter(_from_file, file, IBodyProducer)
registerAdapter(_from_file, StringIO, IBodyProducer)


class HTTPClient(object):
    def __init__(self, agent):
        self._agent = agent

    @classmethod
    def with_config(cls, **kwargs):
        reactor = kwargs.get('reactor')
        if not reactor:
            from twisted.internet import reactor

        agent = Agent(
            reactor,
            pool=HTTPConnectionPool(
                reactor,
                persistent=kwargs.get('persistent', True)))

        if kwargs.get('allow_redirects', True):
            agent = RedirectAgent(agent)

        return cls(agent)

    def get(self, url, **kwargs):
        return self.request('GET', url, **kwargs)

    def put(self, url, data=None, **kwargs):
        return self.request('PUT', url, data=data, **kwargs)

    def post(self, url, data=None, **kwargs):
        return self.request('POST', url, data=data, **kwargs)

    def head(self, url, **kwargs):
        return self.request('HEAD', url, **kwargs)

    def delete(self, url, **kwargs):
        return self.request('DELETE', url, **kwargs)

    def request(self, method, url, **kwargs):
        method = method.upper()

        data = kwargs.get('data')
        bodyProducer = None
        if data:
            bodyProducer = IBodyProducer(data)

        headers = kwargs.get('headers')
        if headers:
            if isinstance(headers, dict):
                h = Headers({})
                for k, v in headers.iteritems():
                    if isinstance(v, str):
                        h.addRawHeaders(k, v)
                    else:
                        h.setRawHeaders(k, v)

                headers = h

        d = self._agent.request(
            method, url, headers=headers, bodyProducer=bodyProducer)

        return d
