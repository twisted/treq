from http.cookiejar import Cookie, CookieJar

import attrs
from twisted.internet.interfaces import IProtocol
from twisted.internet.testing import StringTransport
from twisted.python.failure import Failure
from twisted.trial.unittest import SynchronousTestCase
from twisted.web.client import ResponseDone
from twisted.web.http_headers import Headers
from twisted.web.iweb import IClientRequest, IResponse
from zope.interface import implementer

from treq._agentspy import RequestRecord, agent_spy
from treq.client import HTTPClient
from treq.cookies import scoped_cookie, search

from ..cookies import CookieCollision, IndexableCookieJar


@implementer(IClientRequest)
@attrs.define
class _ClientRequest:
    absoluteURI: bytes
    headers: Headers
    method: bytes


@implementer(IResponse)
class QuickResponse:
    """A response that immediately delivers the body."""

    version = (b"HTTP", 1, 1)
    code = 200
    phrase = "OK"
    previousResponse = None

    def __init__(
        self, record: RequestRecord, headers: Headers, body: bytes = b""
    ) -> None:
        self.request = _ClientRequest(
            record.uri, record.headers or Headers(), record.method
        )
        self.headers = headers
        self.length = len(body)
        self._body = body

    def deliverBody(self, protocol: IProtocol) -> None:
        t = StringTransport()
        protocol.makeConnection(t)
        if t.producerState != "producing":
            raise NotImplementedError("pausing IPushProducer")
        protocol.dataReceived(self._body)
        protocol.connectionLost(Failure(ResponseDone()))

    def setPreviousResponse(self, response: IResponse) -> None:
        raise NotImplementedError


class ScopedCookieTests(SynchronousTestCase):
    """Test `treq.cookies.scoped_cookie()`"""

    def test_http(self) -> None:
        """Scoping an HTTP origin produces a non-Secure cookie."""
        c = scoped_cookie("http://foo.bar", "x", "y")
        self.assertEqual(c.domain, "foo.bar")
        self.assertIsNone(c.port)
        self.assertFalse(c.port_specified)
        self.assertFalse(c.secure)

    def test_https(self) -> None:
        """
        Scoping to an HTTPS origin produces a Secure cookie that
        won't be sent to HTTP origins.
        """
        c = scoped_cookie("https://foo.bar", "x", "y")
        self.assertEqual(c.domain, "foo.bar")
        self.assertIsNone(c.port)
        self.assertFalse(c.port_specified)
        self.assertTrue(c.secure)

    def test_port(self) -> None:
        """
        Setting a non-default port produces a cookie with that port.
        """
        c = scoped_cookie("https://foo.bar:4433", "x", "y")
        self.assertEqual(c.domain, "foo.bar")
        self.assertEqual(c.port, "4433")
        self.assertTrue(c.port_specified)
        self.assertTrue(c.secure)

    def test_hostname(self) -> None:
        """
        When the origin has a bare hostname, a ``.local`` suffix is applied
        to form the cookie domain.
        """
        c = scoped_cookie("http://mynas", "x", "y")
        self.assertEqual(c.domain, "mynas.local")


class SearchTests(SynchronousTestCase):
    """Test `treq.cookies.search()`"""

    def test_domain(self) -> None:
        """`search()` filters by domain."""
        jar = CookieJar()
        jar.set_cookie(scoped_cookie("http://an.example", "http", "a"))
        jar.set_cookie(scoped_cookie("https://an.example", "https", "b"))
        jar.set_cookie(scoped_cookie("https://f.an.example", "subdomain", "c"))
        jar.set_cookie(scoped_cookie("https://f.an.example", "https", "d"))
        jar.set_cookie(scoped_cookie("https://host", "v", "n"))

        self.assertEqual(
            {(c.name, c.value) for c in search(jar, domain="an.example")},
            {("http", "a"), ("https", "b")},
        )
        self.assertEqual(
            {(c.name, c.value) for c in search(jar, domain="f.an.example")},
            {("subdomain", "c"), ("https", "d")},
        )
        self.assertEqual(
            {(c.name, c.value) for c in search(jar, domain="host")},
            {("v", "n")},
        )

    def test_name(self) -> None:
        """`search()` filters by cookie name."""
        jar = CookieJar()
        jar.set_cookie(scoped_cookie("https://host", "a", "1"))
        jar.set_cookie(scoped_cookie("https://host", "b", "2"))

        self.assertEqual({c.value for c in search(jar, domain="host", name="a")}, {"1"})
        self.assertEqual({c.value for c in search(jar, domain="host", name="b")}, {"2"})


class HTTPClientCookieTests(SynchronousTestCase):
    """Test how HTTPClient's request methods handle the *cookies* argument."""

    def setUp(self) -> None:
        self.agent, self.requests = agent_spy()
        self.cookiejar = IndexableCookieJar()
        self.client = HTTPClient(self.agent, self.cookiejar)

    def test_cookies_in_jars(self) -> None:
        """
        Issuing a request with cookies merges them into the client's cookie jar.
        Cookies received in a response are also merged into the client's cookie jar.
        """
        self.cookiejar.set_cookie(
            Cookie(
                domain="twisted.example",
                port=None,
                secure=True,
                port_specified=False,
                name="a",
                value="b",
                version=0,
                path="/",
                expires=None,
                discard=False,
                comment=None,
                comment_url=None,
                rfc2109=False,
                path_specified=False,
                domain_specified=False,
                domain_initial_dot=False,
                rest={},
            )
        )
        d = self.client.request("GET", "https://twisted.example", cookies={"b": "c"})
        self.assertNoResult(d)

        [request] = self.requests
        assert request.headers is not None
        self.assertEqual(request.headers.getRawHeaders("Cookie"), ["a=b; b=c"])

        request.deferred.callback(
            QuickResponse(request, Headers({"Set-Cookie": ["a=c"]}))
        )

        response = self.successResultOf(d)
        expected = {"a": "c", "b": "c"}
        self.assertEqual({c.name: c.value for c in self.cookiejar}, expected)
        self.assertEqual({c.name: c.value for c in response.cookies()}, expected)

    def test_cookies_pass_jar(self) -> None:
        """
        Passing the *cookies* argument to `HTTPClient.request()` updates
        the client's cookie jar and sends cookies with the request. Upon
        receipt of the response the client's cookie jar is updated.
        """
        self.cookiejar.set_cookie(scoped_cookie("https://tx.example", "a", "a"))
        self.cookiejar.set_cookie(scoped_cookie("http://tx.example", "p", "q"))
        self.cookiejar.set_cookie(scoped_cookie("https://rx.example", "b", "b"))

        jar = CookieJar()
        jar.set_cookie(scoped_cookie("https://tx.example", "a", "b"))
        jar.set_cookie(scoped_cookie("https://rx.example", "a", "c"))

        d = self.client.request("GET", "https://tx.example", cookies=jar)
        self.assertNoResult(d)

        self.assertEqual(
            {(c.domain, c.name, c.value) for c in self.cookiejar},
            {
                ("tx.example", "a", "b"),
                ("tx.example", "p", "q"),
                ("rx.example", "a", "c"),
                ("rx.example", "b", "b"),
            },
        )

        [request] = self.requests
        assert request.headers is not None
        self.assertEqual(request.headers.getRawHeaders("Cookie"), ["a=b; p=q"])

    def test_cookies_dict(self) -> None:
        """
        Passing a dict for the *cookies* argument to `HTTPClient.request()`
        creates cookies that are bound to the

        the client's cookie jar and sends cookies with the request. Upon
        receipt of the response the client's cookie jar is updated.
        """
        d = self.client.request("GET", "https://twisted.example", cookies={"a": "b"})
        self.assertNoResult(d)

        [cookie] = self.cookiejar
        self.assertEqual(cookie.name, "a")
        self.assertEqual(cookie.value, "b")
        # Attributes inferred from the URL:
        self.assertEqual(cookie.domain, "twisted.example")
        self.assertFalse(cookie.port_specified)
        self.assertTrue(cookie.secure)

        [request] = self.requests
        assert request.headers is not None
        self.assertEqual(request.headers.getRawHeaders("Cookie"), ["a=b"])

    def test_response_cookies(self) -> None:
        """
        The `_Request.cookies()` method returns a copy of the request
        cookiejar merged with any cookies from the response. This jar
        matches the client cookiejar at the instant the request was
        received.
        """
        self.cookiejar.set_cookie(scoped_cookie("http://twisted.example", "a", "1"))
        self.cookiejar.set_cookie(scoped_cookie("https://twisted.example", "b", "1"))

        d = self.client.request("GET", "https://twisted.example")
        [request] = self.requests
        request.deferred.callback(
            QuickResponse(request, Headers({"Set-Cookie": ["a=2; Secure"]}))
        )
        response = self.successResultOf(d)

        # The client jar was updated.
        [a] = search(self.cookiejar, domain="twisted.example", name="a")
        self.assertEqual(a.value, "2")
        self.assertTrue(a.secure, True)

        responseJar = response.cookies()
        self.assertIsNot(self.cookiejar, responseJar)  # It's a copy.
        self.assertIsNot(self.cookiejar, response.cookies())  # Another copy.

        # They contain the same cookies.
        self.assertEqual(
            {(c.name, c.value, c.secure) for c in self.cookiejar},
            {(c.name, c.value, c.secure) for c in response.cookies()},
        )


class IndexableCookieJarTests(SynchronousTestCase):
    """Test `treq.cookies.IndexableCookieJar`"""

    def test_getitem(self) -> None:
        """
        `IndexableCookieJar.__getitem__` retrieves an unambiguously-named cookie,
        but raises `KeyError` when no matching cookie exists, and `CookieCollision`
        when the name matches more than one cookie.
        """
        jar = IndexableCookieJar()
        jar.set_cookie(
            scoped_cookie("http://test.kitchen", "snickerdoodle", "cinnamon")
        )
        jar.set_cookie(scoped_cookie("http://test.kitchen", "chocolate", "sea-salt"))
        jar.set_cookie(scoped_cookie("http://flavortown.kitchen", "chocolate", "chunk"))

        self.assertEqual(jar["snickerdoodle"], "cinnamon")
        self.assertRaises(KeyError, jar.__getitem__, "shortbread")
        self.assertRaises(CookieCollision, jar.__getitem__, "chocolate")

    def test_getitem_none(self) -> None:
        """
        `IndexableCookieJar.__getitem__` ignores cookies with a value of `None`.
        """
        jar = IndexableCookieJar()
        c = scoped_cookie("http://test.kitchen", "molasses", "")
        c.value = None
        jar.set_cookie(c)
        jar.set_cookie(scoped_cookie("http://test.kitchen", "molasses", "pie-spice"))

        self.assertEqual(jar["molasses"], "pie-spice")
