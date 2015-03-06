import re
import base64
import urlparse

from twisted.web.proxy import Proxy, ProxyRequest
from twisted.web.http import HTTPFactory


def with_baseurl_and_proxy(method):

    def _request(self, url, *args, **kwargs):
        kwargs.update({'proxy': self.proxy_params})
        return method(self.baseurl + url, *args, pool=self.pool, **kwargs)

    return _request


class TestProxyRequestFactory(ProxyRequest):

    def process(self):
        # We need to override this method since the original twisted.web.proxy
        # lacks support of sending multiple header values
        parsed = urlparse.urlparse(self.uri)
        protocol = parsed[0]
        host = parsed[1]
        port = self.ports[protocol]
        if ':' in host:
            host, port = host.split(':')
            port = int(port)
        rest = urlparse.urlunparse(('', '') + parsed[2:])
        if not rest:
            rest = rest + '/'
        class_ = self.protocols[protocol]

        # Here we go:

        headers = {}
        for k, v in self.requestHeaders.getAllRawHeaders():
            if len(v) == 1:
                headers[k.lower()] = v[0]
            else:
                headers[k.lower()] = ",".join(v)

        if 'host' not in headers:
            headers['host'] = host
        self.content.seek(0, 0)
        s = self.content.read()
        clientFactory = class_(self.method, rest, self.clientproto, headers,
                               s, self)
        self.reactor.connectTCP(host, port, clientFactory)

    def finish(self):
        # We need to override this method to do the proper timeout testing,
        # since twisted.web.proxy fires RuntimeError when receives response
        # after Treq disconnection; this does not affect the library logic,
        # but saves us from internal proxy errors
        try:
            return ProxyRequest.finish(self)
        except RuntimeError:
            pass


class TestProxyProtocol(Proxy):

    requestFactory = TestProxyRequestFactory


class TestProxyFactory(HTTPFactory):

    def buildProtocol(self, addr):
        return TestProxyProtocol()


class TestProxyRequestFactoryWithAuthentication(ProxyRequest):

    def checkAuthCredentials(self, username, password, proxy_auth_header):
        creds_serialized = re.sub(r'Basic ', '', proxy_auth_header)
        return creds_serialized == base64.b64encode(
            "%s:%s" % (username, password)
        )

    def process(self):
        parsed = urlparse.urlparse(self.uri)
        protocol = parsed[0]
        host = parsed[1]
        port = self.ports[protocol]
        if ':' in host:
            host, port = host.split(':')
            port = int(port)
        rest = urlparse.urlunparse(('', '') + parsed[2:])
        if not rest:
            rest = rest + '/'
        class_ = self.protocols[protocol]

        # Here we go:

        headers = {}
        for k, v in self.requestHeaders.getAllRawHeaders():
            if len(v) == 1:
                headers[k.lower()] = v[0]
            else:
                headers[k.lower()] = ",".join(v)

        if 'host' not in headers:
            headers['host'] = host

        username, password = self.channel.credentials

        if 'proxy-authorization' not in headers or not \
            self.checkAuthCredentials(
                username, password, headers['proxy-authorization']
            ):
            self.transport.write(
                "bHTTP/1.1 407 Proxy Authentication Required\r\n\r\n"
            )
            self.transport.loseConnection()
            return
        else:
            headers.pop('proxy-authorization')

        self.content.seek(0, 0)
        s = self.content.read()
        clientFactory = class_(self.method, rest, self.clientproto, headers,
                               s, self)
        self.reactor.connectTCP(host, port, clientFactory)


class TestProxyWithAuthentication(Proxy):

    requestFactory = TestProxyRequestFactoryWithAuthentication

    def __init__(self, credentials):
        self.credentials = credentials
        Proxy.__init__(self)


class TestProxyFactoryWithAuthentication(HTTPFactory):

    def __init__(self, credentials, *args, **kwargs):
        self.credentials = credentials
        HTTPFactory.__init__(self, *args, **kwargs)

    def buildProtocol(self, addr):
        return TestProxyWithAuthentication(self.credentials)
