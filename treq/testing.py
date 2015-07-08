"""
In-memory version of treq for testing.
"""
from functools import wraps

from zope.interface import Attribute, Interface, directlyProvides, implementer

from twisted.test.proto_helpers import StringTransport, MemoryReactor

from twisted.internet.address import IPv4Address
from twisted.internet.error import ConnectionDone
from twisted.internet.defer import succeed
from twisted.internet.interfaces import ISSLTransport

from twisted.python.urlpath import URLPath

from twisted.web.client import Agent
from twisted.web.resource import Resource
from twisted.web.server import Site
from twisted.web.iweb import IAgent, IBodyProducer

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
        if scheme == "https":
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
        if scheme == "https":
            directlyProvides(serverTransport, ISSLTransport)
        serverTransport.hostAddr = IPv4Address('TCP', '127.0.0.1', port)
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
                                  data_to_body_producer=SynchronousProducer)
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
    failures = Attribute(
        "An iterable of failures that may have occurred when getting testing "
        "making requests - failures must be stored here, because any "
        "exception raised by :meth:`get_response_for` will be eaten by "
        ":obj:`Resource` and a 500 response returned instead.")

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

        If there is a stubbing error, the return value is undefined (if an
        exception is raised, :obj:`Resource` will just eat it and return 500
        in its place).  But the stubbing error should definitely be recorded
        in the failures attribute.
        """


class StringStubbingResource(Resource):
    """
    A resource that takes a :obj:`IStringResponseStubs` provider and returns
    a real response as a result.

    Note that if the :obj:`IStringResponseStubs` raises an Exception, Twisted
    will catch it and return a 500 instead.  So the
    implementation of :obj:`IStringResponseStubs` may want to do its own error
    reporting.
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
        headers = {}
        for k, v in request.requestHeaders.getAllRawHeaders():
            headers[k] = v

        for dictionary in (params, headers):
            for k in dictionary:
                dictionary[k] = sorted(dictionary[k])

        # The incoming request does not have the absoluteURI property, because
        # an incoming request is a IRequest, not an IClientRequest, so it
        # the absolute URI needs to be synthesized.

        # But request.URLPath() only returns the scheme and hostname, because
        # that is the URL for this resource (because this resource handles
        # everything from the root on down).

        # So we need to add the request.path (not request.uri, which includes
        # the query parameters)
        absoluteURI = str(request.URLPath().click(request.path))

        status_code, headers, body = self._istubs.get_response_for(
            request.method, absoluteURI, params, headers,
            request.content.read())

        request.setResponseCode(status_code)
        for k, v in headers.items():
            request.setHeader(k, v)

        return body


class HasHeaders(object):
    """
    Since Twisted adds headers to a request, such as the host and the content
    length, it's necessary to test whether request headers CONTAIN the expected
    headers (the ones that are not automatically added by Twisted).

    This wraps a set of headers, and can be used in an equality test against
    a superset if the provided headers.
    """
    def __init__(self, headers):
        self._headers = dict([(k.lower(), v) for k, v in headers.items()])

    def __repr__(self):
        return "HasHeaders({0})".format(repr(self._headers))

    def __eq__(self, other_headers):
        compare_to = dict([(k.lower(), v) for k, v in other_headers.items()])

        return (set(self._headers.keys()).issubset(set(compare_to.keys())) and
                all([set(v).issubset(set(compare_to[k]))
                     for k, v in self._headers.items()]))

    def __ne__(self, other_headers):
        return not self.__eq__(other_headers)


@implementer(IStringResponseStubs)
class SequenceStringStubs(object):
    """
    Takes a sequence of::

        [((method, url, params, headers, data), (code, headers, body)),
         ...]

    Expects the requests to arrive in sequence order.  If there are no more
    responses, or the request's paramters do not match the next item's expected
    request paramters, raises :obj:`AssertionError`.

    If any of the parameters passed is `None` (as opposed to an empty list or
    dictionary for params or)

    :ivar list sequence: The sequence of expected request arguments mapped to
        stubbed responses
    :ivar list failures: A mutable list containing request failures and
        mismatches.  Failures have to be stored here, because any attempt to
        raise an exception will just be eaten by :obj:`Resource` and returned
        as a 500 error instead.
    """
    def __init__(self, sequence):
        self._sequence = sequence
        self._failures = []

    @property
    def sequence(self):
        return tuple(self._sequence)

    @property
    def failures(self):
        return tuple(self._failures)

    def get_response_for(self, method, url, params, headers, data):
        """
        :return: the next response in the sequence, provided that the
            parameters match the next in the sequence.
        :see: :obj:`IStringResponseStubs.get_response_for`
        """
        if len(self.sequence) == 0:
            self._failures.append("No more requests expected.")
            return (500, {}, "StubbingError")

        expected, response = self.sequence[0]
        e_method, e_url, e_params, e_headers, e_data = expected

        checks = [
            (e_method is None or e_method.lower() == method.lower(), "method"),
            (e_url is None or
             # URLPath does not have an __eq__ function
             str(URLPath.fromString(e_url)) == str(URLPath.fromString(url)),
             "url"),
            (e_params is None or e_params == params, 'parameters'),
            (e_headers is None or HasHeaders(e_headers) == headers, "headers"),
            (e_data is None or e_data == data, "data")
        ]

        mismatches = [param for success, param in checks if not success]
        if mismatches:
            self._failures.append(
                "\nExpected: {0!r}\n     Got: {1!r}\nMismatches: {2!r}"
                .format(expected, (method, url, params, headers, data),
                        mismatches))
            return (500, {}, "StubbingError")

        self._sequence = self._sequence[1:]

        return response
