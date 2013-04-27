from StringIO import StringIO

from urlparse import urlparse, urlunparse
from urllib import urlencode

from twisted.web.http_headers import Headers
from twisted.web.iweb import IBodyProducer

from twisted.web.client import (
    Agent,
    FileBodyProducer,
    HTTPConnectionPool,
    RedirectAgent,
    ContentDecoderAgent,
    GzipDecoder
)

from twisted.python.components import registerAdapter

from treq.auth import add_auth
from treq._utils import default_reactor


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


registerAdapter(_from_bytes, str, IBodyProducer)
registerAdapter(_from_file, file, IBodyProducer)
registerAdapter(_from_file, StringIO, IBodyProducer)


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

        params = kwargs.get('params')
        if params:
            url = _combine_query_params(url, params)

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

        data = kwargs.get('data')
        bodyProducer = None
        if data:
            if isinstance(data, (dict, list, tuple)):
                headers.setRawHeaders(
                    'content-type', ['application/x-www-form-urlencoded'])
                data = urlencode(data, doseq=True)

            bodyProducer = IBodyProducer(data)

        d = self._agent.request(
            method, url, headers=headers, bodyProducer=bodyProducer)

        return d
