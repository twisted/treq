# -*- coding: utf-8 -*-
"""
In-memory version of treq for testing.
"""

from __future__ import absolute_import, division, print_function

from six import text_type, PY3

from contextlib import contextmanager
from functools import wraps

try:
    from twisted.internet.testing import MemoryReactorClock
except ImportError:
    from twisted.test.proto_helpers import MemoryReactorClock

from twisted.test import iosim

from twisted.internet.address import IPv4Address
from twisted.internet.defer import succeed
from twisted.internet.interfaces import ISSLTransport

from twisted.logger import Logger

from twisted.python.failure import Failure
from twisted.python.urlpath import URLPath

from twisted.internet.endpoints import TCP4ClientEndpoint
from twisted.web.client import Agent
from twisted.web.error import SchemeNotSupported
from twisted.web.iweb import IAgent, IAgentEndpointFactory, IBodyProducer
from twisted.web.resource import Resource
from twisted.web.server import Site

from zope.interface import directlyProvides, implementer

import treq
from treq.client import HTTPClient
import attr


@implementer(IAgentEndpointFactory)
@attr.s
class _EndpointFactory(object):
    """
    An endpoint factory used by :class:`RequestTraversalAgent`.

    :ivar reactor: The agent's reactor.
    :type reactor: :class:`MemoryReactorClock`
    """

    reactor = attr.ib()

    def endpointForURI(self, uri):
        """
        Create an endpoint that represents an in-memory connection to
        a URI.

        Note: This always creates a
        :class:`~twisted.internet.endpoints.TCP4ClientEndpoint` on the
        assumption :class:`RequestTraversalAgent` ignores everything
        about the endpoint but its port.

        :param uri: The URI to connect to.
        :type uri: :class:`~twisted.web.client.URI`

        :return: The endpoint.
        :rtype: An
                :class:`~twisted.internet.interfaces.IStreamClientEndpoint`
                provider.
        """

        if uri.scheme not in {b'http', b'https'}:
            raise SchemeNotSupported("Unsupported scheme: %r" % (uri.scheme,))
        return TCP4ClientEndpoint(self.reactor, "127.0.0.1", uri.port)


@implementer(IAgent)
class RequestTraversalAgent(object):
    """
    :obj:`~twisted.web.iweb.IAgent` implementation that issues an in-memory
    request rather than going out to a real network socket.
    """

    def __init__(self, rootResource):
        """
        :param rootResource: The Twisted `IResource` at the root of the
            resource tree.
        """
        self._memoryReactor = MemoryReactorClock()
        self._realAgent = Agent.usingEndpointFactory(
            reactor=self._memoryReactor,
            endpointFactory=_EndpointFactory(self._memoryReactor))
        self._rootResource = rootResource
        self._pumps = set()

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
        if PY3:
            scheme = URLPath.fromBytes(uri).scheme
        else:
            scheme = URLPath.fromString(uri).scheme

        host, port, factory, timeout, bindAddress = (
            self._memoryReactor.tcpClients[-1])

        serverAddress = IPv4Address('TCP', '127.0.0.1', port)
        clientAddress = IPv4Address('TCP', '127.0.0.1', 31337)

        # Create the protocol and fake transport for the client and server,
        # using the factory that was passed to the MemoryReactor for the
        # client, and a Site around our rootResource for the server.
        serverFactory = Site(self._rootResource, reactor=self._memoryReactor)
        serverProtocol = serverFactory.buildProtocol(clientAddress)
        serverTransport = iosim.FakeTransport(
            serverProtocol, isServer=True,
            hostAddress=serverAddress, peerAddress=clientAddress)
        clientProtocol = factory.buildProtocol(None)
        clientTransport = iosim.FakeTransport(
            clientProtocol, isServer=False,
            hostAddress=clientAddress, peerAddress=serverAddress)

        if scheme == b"https":
            # Provide ISSLTransport on both transports, so everyone knows that
            # this is HTTPS.
            directlyProvides(serverTransport, ISSLTransport)
            directlyProvides(clientTransport, ISSLTransport)

        # Make a pump for wiring the client and server together.
        pump = iosim.connect(
            serverProtocol, serverTransport, clientProtocol, clientTransport)
        self._pumps.add(pump)

        return response

    def flush(self):
        """
        Flush all data between pending client/server pairs.

        This is only necessary if a :obj:`Resource` under test returns
        :obj:`NOT_DONE_YET` from its ``render`` method, making a response
        asynchronous. In that case, after each write from the server,
        :meth:`flush()` must be called so the client can see it.
        """
        old_pumps = self._pumps
        new_pumps = self._pumps = set()
        for p in old_pumps:
            p.flush()
            if p.clientIO.disconnected and p.serverIO.disconnected:
                continue
            new_pumps.add(p)


@implementer(IBodyProducer)
class _SynchronousProducer(object):
    """
    A partial implementation of an :obj:`IBodyProducer` which produces its
    entire payload immediately.  There is no way to access to an instance of
    this object from :obj:`RequestTraversalAgent` or :obj:`StubTreq`, or even a
    :obj:`Resource: passed to :obj:`StubTreq`.

    This does not implement the :func:`IBodyProducer.stopProducing` method,
    because that is very difficult to trigger.  (The request from
    `RequestTraversalAgent` would have to be canceled while it is still in the
    transmitting state), and the intent is to use `RequestTraversalAgent` to
    make synchronous requests.
    """

    def __init__(self, body):
        """
        Create a synchronous producer with some bytes.
        """
        self.body = body
        msg = ("StubTreq currently only supports url-encodable types, bytes, "
               "or unicode as data.")
        assert isinstance(body, (bytes, text_type)), msg
        if isinstance(body, text_type):
            self.body = body.encode('utf-8')
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
    provides all the function calls exposed in :obj:`treq.__all__`.
    """
    def __init__(self, resource):
        """
        Construct a client, and pass through client methods and/or
        treq.content functions.

        :param resource: A :obj:`Resource` object that provides the fake
            responses
        """
        _agent = RequestTraversalAgent(resource)
        _client = HTTPClient(agent=_agent,
                             data_to_body_producer=_SynchronousProducer)
        for function_name in treq.__all__:
            function = getattr(_client, function_name, None)
            if function is None:
                function = getattr(treq, function_name)
            else:
                function = _reject_files(function)

            setattr(self, function_name, function)
        self.flush = _agent.flush


class StringStubbingResource(Resource):
    """
    A resource that takes a callable with 5 parameters
    ``(method, url, params, headers, data)`` and returns
    ``(code, headers, body)``.

    The resource uses the callable to return a real response as a result of a
    request.

    The parameters for the callable are:

    - ``method``, the HTTP method as `bytes`.
    - ``url``, the full URL of the request as text.
    - ``params``, a dictionary of query parameters mapping query keys
      lists of values (sorted alphabetically).
    - ``headers``, a dictionary of headers mapping header keys to
      a list of header values (sorted alphabetically).
    - ``data``, the request body as `bytes`.

    The callable must return a ``tuple`` of (code, headers, body) where the
    code is the HTTP status code, the headers is a dictionary of bytes (unlike
    the `headers` parameter, which is a dictionary of lists), and body is
    a string that will be returned as the response body.

    If there is a stubbing error, the return value is undefined (if an
    exception is raised, :obj:`~twisted.web.resource.Resource` will just eat it
    and return 500 in its place).  The callable, or whomever creates the
    callable, should have a way to handle error reporting.
    """
    isLeaf = True

    def __init__(self, get_response_for):
        """
        See :class:`StringStubbingResource`.
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


def _maybeEncode(someStr):
    """
    Encode `someStr` to ASCII if required.
    """
    if isinstance(someStr, text_type):
        return someStr.encode('ascii')
    return someStr


def _maybeEncodeHeaders(headers):
    """ Convert a headers mapping to its bytes-encoded form. """
    return {_maybeEncode(k).lower(): [_maybeEncode(v) for v in vs]
            for k, vs in headers.items()}


class HasHeaders(object):
    """
    Since Twisted adds headers to a request, such as the host and the content
    length, it's necessary to test whether request headers CONTAIN the expected
    headers (the ones that are not automatically added by Twisted).

    This wraps a set of headers, and can be used in an equality test against
    a superset if the provided headers. The headers keys are lowercased, and
    keys and values are compared in their bytes-encoded forms.

    Headers should be provided as a mapping from strings or bytes to a list of
    strings or bytes.
    """
    def __init__(self, headers):
        self._headers = _maybeEncodeHeaders(headers)

    def __repr__(self):
        return "HasHeaders({0})".format(repr(self._headers))

    def __eq__(self, other_headers):
        compare_to = _maybeEncodeHeaders(other_headers)

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
    responses, or the request's parameters do not match the next item's
    expected request parameters, calls `sync_failure_reporter` or
    `async_failure_reporter`.

    For the expected request tuples:

    - ``method`` should be :class:`bytes` normalized to lowercase.
    - ``url`` should be a `str` normalized as per the `transformations in that
      (usually) preserve semantics
      <https://en.wikipedia.org/wiki/URL_normalization>`_.  A URL to
      `http://something-that-looks-like-a-directory` would be normalized to
      `http://something-that-looks-like-a-directory/`
      and a URL to `http://something-that-looks-like-a-page/page.html`
      remains unchanged.
    - ``params`` is a dictionary mapping :class:`bytes` to :class:`list` of
      :class:`bytes`.
    - ``headers`` is a dictionary mapping :class:`bytes` to :class:`list` of
      :class:`bytes` -- note that :class:`twisted.web.client.Agent` may add its
      own headers which are not guaranteed to be present (for instance,
      `user-agent` or `content-length`), so it's better to use some kind of
      matcher like :class:`HasHeaders`.
    - ``data`` is a :class:`bytes`.

    For the response tuples:

    - ``code`` is an integer representing the HTTP status code to return.
    - ``headers`` is a dictionary mapping :class:`bytes` to :class:`bytes` or
      :class:`str`. Note that the value is *not* a list.
    - ``body`` is a :class:`bytes`.

    :ivar list sequence: A sequence of (request tuple, response tuple)
        two-tuples, as described above.
    :ivar async_failure_reporter: An optional callable that takes
        a :class:`str` message indicating a failure. It's asynchronous because
        it cannot just raise an exception—if it does, :meth:`Resource.render
        <twisted.web.resource.Resource.render>` will just convert that into
        a 500 response, and there will be no other failure reporting mechanism.

    When the `async_failure_reporter` parameter is not passed, async failures
    will be reported via a :class:`twisted.logger.Logger` instance, which
    Trial's test case classes (:class:`twisted.trial.unittest.TestCase` and
    :class:`~twisted.trial.unittest.SynchronousTestCase`) will translate into
    a test failure.

    .. note::

        Some versions of
        :class:`twisted.trial.unittest.SynchronousTestCase` report
        logged errors on the wrong test: see `Twisted #9267
        <https://twistedmatrix.com/trac/ticket/9267>`_.

    ..  TODO Update the above note to say what version of
        SynchronousTestCase is fixed once Twisted >17.5.0 is released.

    When not subclassing Trial's classes you must pass `async_failure_reporter`
    and implement equivalent behavior or errors will pass silently. For
    example::

        async_failures = []
        sequence_stubs = RequestSequence([...], async_failures.append)
        stub_treq = StubTreq(StringStubbingResource(sequence_stubs))
        with sequence_stubs.consume(self.fail):  # self = unittest.TestCase
            stub_treq.get('http://fakeurl.com')

        self.assertEqual([], async_failures)
    """
    _log = Logger()

    def __init__(self, sequence, async_failure_reporter=None):
        self._sequence = sequence
        self._async_reporter = async_failure_reporter or self._log_async_error

    def _log_async_error(self, message):
        """
        The default async failure reporter—see `async_failure_reporter`. Logs
        a failure which wraps an :ex:`AssertionError`.

        :param str message: Failure message
        """
        # Passing message twice may look redundant, but Trial only preserves
        # the Failure, not the log message.
        self._log.failure(
            "RequestSequence async error: {message}",
            message=message,
            failure=Failure(AssertionError(message)),
        )

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
            # self = twisted.trial.unittest.SynchronousTestCase
            with sequence_stubs.consume(self.fail):
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
            return (500, {}, b"StubbingError")

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
            return (500, {}, b"StubbingError")

        self._sequence = self._sequence[1:]

        return response
