from unittest.mock import patch, sentinel

from twisted.internet import defer
from twisted.trial.unittest import TestCase
from twisted.web.client import HTTPConnectionPool
from twisted.web.iweb import IAgent
from zope.interface import implementer

import treq
from treq._agentspy import agent_spy
from treq._types import _NOTHING
from treq.api import default_pool, default_reactor, get_global_pool, set_global_pool

try:
    from twisted.internet.testing import MemoryReactorClock
except ImportError:
    from twisted.test.proto_helpers import MemoryReactorClock


class SyntacticAbominationHTTPConnectionPool(HTTPConnectionPool):
    """
    A HTTP connection pool that always fails to return a connection,
    but counts the number of requests made.
    """

    requests = 0

    def __init__(self) -> None:
        super().__init__(MemoryReactorClock())

    def getConnection(self, key, endpoint):
        """
        Count each request, then fail with `IndentationError`.
        """
        self.requests += 1
        return defer.fail(TabError())


@implementer(IAgent)
class CounterAgent:
    """
    An agent that counts requests, but never delivers on its promises.

    :ivar requests: The number of requests received.
    """

    requests = 0

    def request(self, method, uri, headers=None, bodyProducer=None):
        """
        Increment the request counter

        :returns: A deferred that will never fire
        """
        self.requests += 1
        return defer.Deferred()


class TreqAPITests(TestCase):
    """
    Test the module-level API defined in `treq.api` and re-exported by `treq`.
    """

    def test_default_pool(self) -> None:
        """
        The module-level API uses the global connection pool by default.
        """
        pool = SyntacticAbominationHTTPConnectionPool()
        set_global_pool(pool)

        d = treq.get("http://test.com")

        self.assertEqual(pool.requests, 1)
        self.failureResultOf(d, TabError)

    def test_cached_pool(self) -> None:
        """
        The first use of the module-level API populates the global connection
        pool, which is used for all subsequent requests.
        """
        pool = SyntacticAbominationHTTPConnectionPool()
        self.patch(treq.api, "HTTPConnectionPool", lambda reactor, persistent: pool)

        self.failureResultOf(treq.head("http://test.com"), TabError)
        self.failureResultOf(treq.get("http://test.com"), TabError)
        self.failureResultOf(treq.post("http://test.com"), TabError)
        self.failureResultOf(treq.put("http://test.com"), TabError)
        self.failureResultOf(treq.delete("http://test.com"), TabError)
        self.failureResultOf(treq.request("OPTIONS", "http://test.com"), TabError)

        self.assertEqual(pool.requests, 6)

    def test_custom_pool(self) -> None:
        """
        `treq.post()` accepts a *pool* argument to use for the request. The
        global pool is unaffected.
        """
        pool = SyntacticAbominationHTTPConnectionPool()

        d = treq.post("http://foo", data=b"bar", pool=pool)

        self.assertEqual(pool.requests, 1)
        self.failureResultOf(d, TabError)
        self.assertIsNot(pool, get_global_pool())

    def test_custom_agent_methods(self) -> None:
        """
        The module API functions named for HTTP methods use a custom
        IAgent if passed one in the *agent* parameter.
        """

        for method, func in (
            ("HEAD", treq.head),
            ("GET", treq.get),
            ("POST", treq.post),
            ("PUT", treq.put),
            ("PATCH", treq.patch),
            ("DELETE", treq.delete),
        ):
            with self.subTest(method=method):
                agent, requests = agent_spy()
                d = func("https://www.example.org/", agent=agent)

                self.assertNoResult(d)
                [req] = requests
                self.assertEqual(req.method, method.encode())
                self.assertEqual(req.uri, b"https://www.example.org/")

    def test_custom_agent_request(self) -> None:
        """
        `treq.request()` uses a custom *agent* if passed that parameter.
        """
        counter_agent = CounterAgent()
        d = treq.request("HEAD", "https://www.example.org/", agent=counter_agent)

        self.assertNoResult(d)
        self.assertEqual(1, counter_agent.requests)

    def test_request_reactor(self) -> None:
        """
        `treq.request()` uses the *reactor* parameter both when building
        the `HTTPClient` (to make TCP connections) and when making the request
        (to set timeouts).
        """
        global_pool = treq.api.get_global_pool()
        self.addCleanup(treq.api.set_global_pool, global_pool)

        # FIXME: End the mockery
        with (
            patch(
                "treq.api.HTTPConnectionPool", autospec=True, return_value=sentinel.pool
            ) as pool_mock,
            patch(
                "treq.api.Agent", autospec=True, return_value=sentinel.agent
            ) as agent_mock,
            patch("treq.api.HTTPClient", autospec=True) as client_mock,
        ):
            client_mock.return_value.request.return_value = sentinel.deferred

            d = treq.request(
                "HEAD", "http://foo.example", reactor=sentinel.reactor, persistent=False
            )

            self.assertIs(d, sentinel.deferred)
            pool_mock.assert_called_with(sentinel.reactor, persistent=False)
            agent_mock.assert_called_with(sentinel.reactor, pool=sentinel.pool)
            client_mock.return_value.request.assert_called_with(
                "HEAD",
                "http://foo.example",
                _stacklevel=3,
                params=None,
                headers=None,
                data=None,
                files=None,
                json=_NOTHING,
                auth=None,
                cookies=None,
                allow_redirects=True,
                browser_like_redirects=False,
                unbuffered=False,
                reactor=sentinel.reactor,
                timeout=None,
            )

    def test_request_other_params(self) -> None:
        """
        `treq.request()` forwards most parameters to the underlying
        `HTTPClient.request` method.
        """

        class HTTPClientFake:
            """
            A no-op HTTPClient that only records the parameter passed to it.
            """

            def __init__(self):
                self.requests = []

            def request(self, method, url, **kwargs):
                self.requests.append({"method": method, "url": url, **kwargs})
                return defer.Deferred()

        client = HTTPClientFake()
        self.patch(treq.api, "HTTPClient", lambda agent: client)

        # This is not exhaustive, as some parameters are mutually-exclusive.
        d = treq.request(
            "POST",
            "http://foo.example",
            auth=("open", "sesame"),
            params={"foo": "bar"},
            # FIXME: This should type-check
            headers={"Content-Type": "text/plain"},  # type: ignore[arg-type]
            data=b"foo\n",
            cookies={"foo": "bar"},
            allow_redirects=False,
            browser_like_redirects=False,
            unbuffered=True,
            timeout=30,
        )
        self.assertNoResult(d)

        [kwargs] = client.requests
        self.assertEqual(
            kwargs,
            dict(
                method="POST",
                url="http://foo.example",
                auth=("open", "sesame"),
                params={"foo": "bar"},
                headers={"Content-Type": "text/plain"},
                data=b"foo\n",
                cookies={"foo": "bar"},
                files=None,
                json=_NOTHING,
                allow_redirects=False,
                browser_like_redirects=False,
                unbuffered=True,
                # FIXME: Shouldn't this be the same reactor as used by the pool
                # and agent? None means to use twisted.internet.reactor.
                reactor=None,
                timeout=30,
                _stacklevel=3,
            ),
        )

    def test_request_invalid_param(self) -> None:
        """
        `treq.request()` raises `TypeError` when it receives unknown keyword
        arguments.
        """
        with self.assertRaises(TypeError) as c:
            treq.request(
                "GET",
                "https://foo.bar",
                invalid=True,  # type: ignore[call-arg]
                pool=SyntacticAbominationHTTPConnectionPool(),
            )

        self.assertIn("invalid", str(c.exception))

    def test_post_json_with_data(self) -> None:
        """
        `treq.post()` raises TypeError when the *data* and *json* arguments
        are mixed.
        """
        with self.assertRaises(TypeError) as c:
            treq.post(
                "https://test.example/",
                data={"hello": "world"},
                json={"goodnight": "moon"},
                pool=SyntacticAbominationHTTPConnectionPool(),
            )

        self.assertEqual(
            "Argument 'json' cannot be combined with 'data'.",
            str(c.exception),
        )


class DefaultReactorTests(TestCase):
    """
    Test `treq.api.default_reactor()`
    """

    def test_passes_reactor(self) -> None:
        """
        `default_reactor()` returns any reactor passed.
        """
        reactor = MemoryReactorClock()

        self.assertIs(default_reactor(reactor), reactor)

    def test_uses_default_reactor(self) -> None:
        """
        `default_reactor()` returns the global reactor when passed ``None``.
        """
        from twisted.internet import reactor

        self.assertEqual(default_reactor(None), reactor)


class DefaultPoolTests(TestCase):
    """
    Test `treq.api.default_pool`.
    """

    def setUp(self) -> None:
        set_global_pool(None)
        self.reactor = MemoryReactorClock()

    def test_persistent_false(self) -> None:
        """
        When *persistent=False* is passed a non-persistent pool is created.
        """
        pool = default_pool(self.reactor, None, False)

        self.assertTrue(isinstance(pool, HTTPConnectionPool))
        self.assertFalse(pool.persistent)

    def test_persistent_false_not_stored(self) -> None:
        """
        When *persistent=False* is passed the resulting pool is not stored as
        the global pool.
        """
        pool = default_pool(self.reactor, None, persistent=False)

        self.assertIsNot(pool, get_global_pool())

    def test_persistent_false_new(self) -> None:
        """
        When *persistent=False* is passed a new pool is returned each time.
        """
        pool1 = default_pool(self.reactor, None, persistent=False)
        pool2 = default_pool(self.reactor, None, persistent=False)

        self.assertIsNot(pool1, pool2)

    def test_pool_none_persistent_none(self) -> None:
        """
        When *persistent=None* is passed a _persistent_ pool is created for
        backwards compatibility.
        """
        pool = default_pool(self.reactor, None, None)

        self.assertTrue(pool.persistent)

    def test_pool_none_persistent_true(self) -> None:
        """
        When *persistent=True* is passed a persistent pool is created and
        stored as the global pool.
        """
        pool = default_pool(self.reactor, None, True)

        self.assertTrue(isinstance(pool, HTTPConnectionPool))
        self.assertTrue(pool.persistent)

    def test_cached_global_pool(self) -> None:
        """
        When *persistent=True* or *persistent=None* is passed the pool created
        is cached as the global pool.
        """
        pool1 = default_pool(self.reactor, None, None)
        pool2 = default_pool(self.reactor, None, True)

        self.assertEqual(pool1, pool2)

    def test_specified_pool(self) -> None:
        """
        When the user passes a pool it is returned directly. The *persistent*
        argument is ignored. It is not cached as the global pool.
        """
        user_pool = HTTPConnectionPool(self.reactor, persistent=True)
        pool1 = default_pool(self.reactor, user_pool, None)
        pool2 = default_pool(self.reactor, user_pool, True)
        pool3 = default_pool(self.reactor, user_pool, False)

        self.assertIs(pool1, user_pool)
        self.assertIs(pool2, user_pool)
        self.assertIs(pool3, user_pool)
        self.assertIsNot(get_global_pool(), user_pool)
