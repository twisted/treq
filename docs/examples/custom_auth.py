from __future__ import print_function
from twisted.internet.endpoints import serverFromString
from twisted.internet.task import react
from twisted.internet.defer import inlineCallbacks, maybeDeferred
from twisted.web.resource import Resource
from twisted.web.server import Site
from twisted.web.http_headers import Headers
from twisted.web.http import FORBIDDEN

import treq


class SillyAuthResource(Resource, object):
    """
    A resource that uses a silly, header-based authentication
    mechanism.
    """
    isLeaf = True

    def __init__(self, header, secret):
        self._header = header
        self._secret = secret

    def render_GET(self, request):
        headers = request.requestHeaders
        request_secret = headers.getRawHeaders(self._header, [b''])[0]
        if request_secret != self._secret:
            request.setResponseCode(FORBIDDEN)
            return b"No good."
        return b"It's good!"


class SillyAuth(object):
    """
    I implement a silly, header-based authentication mechanism.
    """

    def __init__(self, header, secret, agent):
        self._header = header
        self._secret = secret
        self._agent = agent

    def request(self, method, uri, headers=None, bodyProducer=None):
        if headers is None:
            headers = Headers({})
        headers.setRawHeaders(self._header, [self._secret])
        return self._agent.request(method, uri, headers, bodyProducer)


@inlineCallbacks
def main(reactor, *args):
    header = b'x-silly-auth'
    secret = b'secret'

    auth_resource = SillyAuthResource(header=header, secret=secret)

    endpoint = serverFromString(reactor, "tcp:8080")
    listener = yield endpoint.listen(Site(auth_resource))

    def sillyAuthCallable(agent):
        return SillyAuth(header, secret, agent)

    response = yield treq.get(
        'http://localhost:8080/',
        auth=sillyAuthCallable,
    )

    content = yield response.content()
    print(content)

    yield maybeDeferred(listener.stopListening)


react(main, [])
