"""
In-memory version of treq for testing.
"""
from __future__ import absolute_import, division, print_function

from functools import wraps

from twisted.test.proto_helpers import StringTransport, MemoryReactor

from twisted.internet.address import IPv4Address
from twisted.internet.error import ConnectionDone
from twisted.internet.defer import succeed
from twisted.internet.interfaces import ISSLTransport

from twisted.python.urlpath import URLPath
from twisted.python.compat import unicode

from twisted.web.client import Agent
from twisted.web.server import Site
from twisted.web.iweb import IAgent, IBodyProducer

from twisted.python.failure import Failure

from zope.interface import directlyProvides, implementer

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


@implementer(IAgent)
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

        # If the request has already finished, just propagate the result.  In
        # reality this would only happen in failure, but if the agent ever adds
        # a local cache this might be a success.
        already_called = []

        def check_already_called(r):
            already_called.append(r)
            return r
        response.addBoth(check_already_called)
        if already_called:
            return response

        # That will try to establish an HTTP connection with the reactor's
        # connectTCP method, and MemoryReactor will place Agent's factory into
        # the tcpClients list.  Alternately, it will try to establish an HTTPS
        # connection with the reactor's connectSSL method, and MemoryReactor
        # will place it into the sslClients list.  We'll extract that.
        scheme = URLPath.fromString(uri).scheme
        if scheme == b"https":
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
        if scheme == b"https":
            directlyProvides(clientTransport, ISSLTransport)

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
        serverTransport = AbortableStringTransport()
        if scheme == b"https":
            directlyProvides(serverTransport, ISSLTransport)
        serverTransport.hostAddr = IPv4Address('TCP', '127.0.0.1', port)
        channel.makeConnection(serverTransport)

        # Feed it the data that the Agent synthesized.
        channel.dataReceived(requestData)

        # Now we have the response data, let's give it back to the Agent.
        protocol.dataReceived(serverTransport.io.getvalue())

        def finish(r):
            # By now the Agent should have all it needs to parse a response.
            protocol.connectionLost(Failure(ConnectionDone()))
            # Tell it that the connection is now complete so it can clean up.
            channel.connectionLost(Failure(ConnectionDone()))
            # Propogate the response.
            return r

        # Return the response in the accepted format (Deferred firing
        # IResponse).  This should be synchronously fired, and if not, it's the
        # system under test's problem.
        return response.addBoth(finish)


@implementer(IBodyProducer)
class _SynchronousProducer(object):
    """
    A partial implementation of an :obj:`IBodyProducer` which produces its
    entire payload immediately.  There is no way to access to an instance of
    this object from :obj:`RequestTraversalAgent` or :obj:`StubTreq`, or even a
    :obj:`Resource: passed to :obj:`StubTreq`.

    This does not implement the :func:`IBodyProducer.stopProducing` method,
    because that is very difficult to trigger.  (The request from
    RequestTraversalAgent would have to be canceled while it is still in the
    transmitting state), and the intent is to use RequestTraversalAgent to
    make synchronous requests.
    """

    def __init__(self, body):
        """
        Create a synchronous producer with some bytes.
        """
        self.body = body
        msg = ("StubTreq currently only supports url-encodable types, bytes, "
               "or unicode as data.")
        assert isinstance(body, (bytes, unicode)), msg
        self.length = len(body)

    def startProducing(self, consumer):
        """
        Immediately produce all data.
        """
        consumer.write(self.body)
        return succeed(None)


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
        _client = HTTPClient(agent=RequestTraversalAgent(resource),
                             data_to_body_producer=_SynchronousProducer)
        for function_name in treq.__all__:
            function = getattr(_client, function_name, None)
            if function is None:
                function = getattr(treq, function_name)
            else:
                function = _reject_files(function)

            setattr(self, function_name, function)
