"""
In-memory version of treq for testing.
"""
from functools import wraps

from zope.interface import implementer

from twisted.test.proto_helpers import StringTransport, MemoryReactor

from twisted.internet.address import IPv4Address
from twisted.internet.error import ConnectionDone
from twisted.internet.defer import succeed

from twisted.python.urlpath import URLPath

from twisted.web.client import Agent
from twisted.web.resource import Resource
from twisted.web.server import Site
from twisted.web.iweb import IBodyProducer

from twisted.python.failure import Failure

import treq
from treq.client import HTTPClient


class AbortableStringTransport(StringTransport):
    """
    A :obj:`StringTransport` that supports ``abortConnection``.
    """

    def abortConnection(self):
        """
        Since all connection cessation is immediate in this in-memory
        transport, just call ``loseConnection``.
        """
        self.loseConnection()


class RequestTraversalAgent(object):
    """
    :obj:`IAgent` implementation that issues an in-memory request rather than
    going out to a real network socket.
    """

    def __init__(self, rootResource):
        """
        :param rootResource: The twisted IResource at the root of the resource
            tree.
        """
        self._memoryReactor = MemoryReactor()
        self._realAgent = Agent(reactor=self._memoryReactor)
        self._rootResource = rootResource

    def request(self, method, uri, headers=None, bodyProducer=None):
        """
        Implement IAgent.request.
        """
        # We want to use Agent to parse the HTTP response, so let's ask it to
        # make a request against our in-memory reactor.
        response = self._realAgent.request(method, uri, headers, bodyProducer)

        # That will try to establish an HTTP connection with the reactor's
        # connectTCP method, and MemoryReactor will place Agent's factory into
        # the tcpClients list.  Alternately, it will try to establish an HTTPS
        # connection with the reactor's connectSSL method, and MemoryReactor
        # will place it into the sslClients list.  We'll extract that.
        scheme = URLPath.fromString(uri).scheme
        if scheme == "https":
            host, port, factory, context_factory, timeout, bindAddress = (
                self._memoryReactor.sslClients[-1])
        else:
            host, port, factory, timeout, bindAddress = (
                self._memoryReactor.tcpClients[-1])

        # Then we need to convince that factory it's connected to something and
        # it will give us a protocol for that connection.
        protocol = factory.buildProtocol(None)

        # We want to capture the output of that connection so we'll make an
        # in-memory transport.
        clientTransport = AbortableStringTransport()

        # When the protocol is connected to a transport, it ought to send the
        # whole request because callers of this should not use an asynchronous
        # bodyProducer.
        protocol.makeConnection(clientTransport)

        # Get the data from the request.
        requestData = clientTransport.io.getvalue()

        # Now time for the server to do its job.  Ask it to build an HTTP
        # channel.
        channel = Site(self._rootResource).buildProtocol(None)

        # Connect the channel to another in-memory transport so we can collect
        # the response.
        serverTransport = StringTransport()
        serverTransport.hostAddr = IPv4Address('TCP', '127.0.0.1', 80)
        channel.makeConnection(serverTransport)

        # Feed it the data that the Agent synthesized.
        channel.dataReceived(requestData)

        # Tell it that the connection is now complete so it can clean up.
        channel.connectionLost(Failure(ConnectionDone()))

        # Now we have the response data, let's give it back to the Agent.
        protocol.dataReceived(serverTransport.io.getvalue())

        # By now the Agent should have all it needs to parse a response.
        protocol.connectionLost(Failure(ConnectionDone()))

        # Return the response in the accepted format (Deferred firing
        # IResponse).  This should be synchronously fired, and if not, it's the
        # system under test's problem.
        return response

try:
    # Prior to Twisted 13.1.0, there was no formally specified Agent interface
    from twisted.web.iweb import IAgent
except ImportError:
    pass
else:
    RequestTraversalAgent = implementer(IAgent)(RequestTraversalAgent)


@implementer(IBodyProducer)
class SynchronousProducer(object):
    """
    An IBodyProducer which produces its entire payload immediately.
    """

    def __init__(self, body):
        """
        Create a synchronous producer with some bytes.
        """
        self.body = body
        self.length = len(body)

    def startProducing(self, consumer):
        """
        Immediately produce all data.
        """
        consumer.write(self.body)
        return succeed(None)

    def stopProducing(self):
        """
        No-op.
        """


def _reject_files(f):
    """
    Decorator that rejects the 'files' keyword argument to the request
    functions, because that is not handled by this yet.
    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'files' in kwargs:
            raise AssertionError("StubTreq cannot handle files.")
        return f(*args, **kwargs)
    return wrapper


class StubTreq(object):
    """
    A fake version of the treq module that can be used for testing that
    provides all the function calls exposed in treq.__all__.

    :ivar resource: A :obj:`Resource` object that provides the fake responses
    """
    def __init__(self, resource):
        """
        Construct a client, and pass through client methods and/or
        treq.content functions.
        """
        self._client = HTTPClient(agent=RequestTraversalAgent(resource),
                                  bodyproducer=SynchronousProducer)
        for function_name in treq.__all__:
            function = getattr(self._client, function_name, None)
            if function is None:
                function = getattr(treq, function_name)
            else:
                function = _reject_files(function)

            setattr(self, function_name, function)


class IStringResponseStubs(Interface):
    """
    An interface that :class:`StringStubbingResource` expects to provide it
    with a response based on what the
    """
    def get_response_for(method, url, params, headers, data):
        """
        :param bytes method: An HTTP method
        :param bytes url: The full URL of the request
        :param dict params: A dictionary of query parameters mapping query keys
            lists of values (sorted alphabetically)
        :param dict headers: A dictionary of headers mapping header keys to
            a list of header values (sorted alphabetically)
        :param str data: The request body.

        :return: a ``tuple`` of (code, headers, body) where the code is
            the HTTP status code, the headers is a dictionary of bytes
            (unlike the `headers` parameter, which is a dictionary of lists),
            and body is a string that will be returned as the response body.
        """


class StringStubbingResource(Resource):
    """
    A resource that takes a :obj:`IStringResponseStubs` provider and returns
    a real response as a result.
    """
    isLeaf = True

    def __init__(self, istubs):
        """
        :param istubs: a :obj:`IStringResponseStubs` provider.
        """
        Resource.__init__(self)
        self._istubs = istubs

    def render(self, request):
        """
        Produce a response according to the stubs provided.
        """
        params = request.args
        headers = defaultdict(list)
        for k, v in request.requestHeaders.getAllRawHeaders():
            headers[k].append(v)

        for dictionary in (params, headers):
            for k in dictionary:
                dictionary[k] = sorted(dictionary[k])

        status_code, headers, body = self._istubs.get_response_for(
            request.method, request.uri, params, headers,
            request.content.read())

        request.setResponseCode(status_code)
        for k, v in headers.items():
            request.setHeader(k, v)

        return body
