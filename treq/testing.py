"""
In-memory version of treq for testing.
"""

from __future__ import absolute_import, division, print_function

from contextlib import contextmanager
from functools import wraps

from twisted.test.proto_helpers import StringTransport, MemoryReactor

from twisted.internet.address import IPv4Address
from twisted.internet.error import ConnectionDone
from twisted.internet.defer import succeed
from twisted.internet.interfaces import ISSLTransport

from twisted.python.urlpath import URLPath
from twisted.python.compat import unicode

from twisted.web.client import Agent
from twisted.web.resource import Resource
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


class StringStubbingResource(Resource):
    """
    A resource that takes a callable with 5 parameters
    ``(method, url, params, headers, data)`` and returns
    ``(code, headers, body)``.

    The resource uses the callable to return a real response as a result of a
    request.

    The parameters for the callable are::

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
    in its place).  The callable, or whomever creates the callable, should
    have a way to handle error reporting.
    """
    isLeaf = True

    def __init__(self, get_response_for):
        """
        See ``StringStubbingResource``.
        """
        Resource.__init__(self)
        self._get_response_for = get_response_for

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

        status_code, headers, body = self._get_response_for(
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


class RequestSequence(object):
    """
    For an example usage, see :meth:`RequestSequence.consume`.

    Takes a sequence of::

        [((method, url, params, headers, data), (code, headers, body)),
         ...]

    Expects the requests to arrive in sequence order.  If there are no more
    responses, or the request's paramters do not match the next item's expected
    request paramters, raises :obj:`AssertionError`.

    For the expected request arguments::

    - ``method`` should be normalized to lowercase.
    - ``url`` should be normalized as per the transformations in
        https://en.wikipedia.org/wiki/URL_normalization that (usually) preserve
        semantics.  A url to `http://something-that-looks-like-a-directory`
        would be normalized to `http://something-that-looks-like-a-directory/`
        and a url to `http://something-that-looks-like-a-page/page.html`
        remains unchanged.
    - ``params`` is a dictionary mapping `str` to `lists` of `str`
    - ``headers`` is a dictionary mapping `str` to `lists` of `str` - note that
        :obj:`twisted.web.client.Agent` may adds its own headers though, which
        are not guaranteed (for instance, `user-agent` or `content-length`),
        so it's better to use some kind of matcher like :obj:`HasHeaders`.
    - ``data`` is a `str`

    For the response::

    - ``code`` is an integer representing the HTTP status code to return
    - ``headers`` is a dictionary mapping `str` to `str` or `lists` of `str`
    - ``body`` is a `str`

    :ivar list sequence: The sequence of expected request arguments mapped to
        stubbed responses
    :ivar async_failure_reporter: A callable that takes a single message
        reporting failures - it's asynchronous because it cannot just raise
        an exception - if it does, :obj:`Resource.render` will just convert
        that into a 500 response, and there will be no other failure reporting
        mechanism.
    """
    def __init__(self, sequence, async_failure_reporter):
        self._sequence = sequence
        self._async_reporter = async_failure_reporter

    def consumed(self):
        """
        :return: `bool` representing whether the entire sequence has been
            consumed.  This is useful in tests to assert that the expected
            requests have all been made.
        """
        return len(self._sequence) == 0

    @contextmanager
    def consume(self, sync_failure_reporter):
        """
        Usage::

            sequence_stubs = RequestSequence([...])
            stub_treq = StubTreq(StringStubbingResource(sequence_stubs))
            with sequence_stubs.consume(self.fail):  # self = unittest.TestCase
                stub_treq.get('http://fakeurl.com')
                stub_treq.get('http://another-fake-url.com')

        If there are still remaining expected requests to be made in the
        sequence, fails the provided test case.

        :param sync_failure_reporter: A callable that takes a single message
            reporting failures.  This can just raise an exception - it does
            not need to be asynchronous, since the exception would not get
            raised within a Resource.

        :return: a context manager that can be used to ensure all expected
            requests have been made.
        """
        yield
        if not self.consumed():
            sync_failure_reporter("\n".join(
                ["Not all expected requests were made.  Still expecting:"] +
                ["- {0}(url={1}, params={2}, headers={3}, data={4})".format(
                    *expected) for expected, _ in self._sequence]))

    def __call__(self, method, url, params, headers, data):
        """
        :return: the next response in the sequence, provided that the
            parameters match the next in the sequence.
        """
        if len(self._sequence) == 0:
            self._async_reporter(
                "No more requests expected, but request {0!r} made.".format(
                    (method, url, params, headers, data)))
            return (500, {}, "StubbingError")

        expected, response = self._sequence[0]
        e_method, e_url, e_params, e_headers, e_data = expected

        checks = [
            (e_method == method.lower(), "method"),
            (e_url == url, "url"),
            (e_params == params, 'parameters'),
            (e_headers == headers, "headers"),
            (e_data == data, "data")
        ]
        mismatches = [param for success, param in checks if not success]
        if mismatches:
            self._async_reporter(
                "\nExpected the next request to be: {0!r}"
                "\nGot request                    : {1!r}\n"
                "\nMismatches: {2!r}"
                .format(expected, (method, url, params, headers, data),
                        mismatches))
            return (500, {}, "StubbingError")

        self._sequence = self._sequence[1:]

        return response
