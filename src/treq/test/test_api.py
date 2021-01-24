from __future__ import absolute_import, division

from twisted.web.iweb import IAgent
from twisted.web.client import HTTPConnectionPool
from twisted.trial.unittest import TestCase
from twisted.internet import defer
from zope.interface import implementer

import treq
from treq.api import default_reactor, default_pool, set_global_pool, get_global_pool

try:
    from twisted.internet.testing import MemoryReactorClock
except ImportError:
    from twisted.test.proto_helpers import MemoryReactorClock


class SyntacticAbominationHTTPConnectionPool:
    """
    A HTTP connection pool that always fails to return a connection,
    but counts the number of requests made.
    """

    requests = 0

    def getConnection(self, key, endpoint):
        """
        Count each request, then fail with `IndentationError`.
        """
        self.requests += 1
        return defer.fail(TabError())


class TreqAPITests(TestCase):
    def test_default_pool(self):
        """
        The module-level API uses the global connection pool by default.
        """
        pool = SyntacticAbominationHTTPConnectionPool()
        set_global_pool(pool)

        d = treq.get("http://test.com")

        self.assertEqual(pool.requests, 1)
        self.failureResultOf(d, TabError)

    def test_cached_pool(self):
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

    def test_custom_pool(self):
        """
        `treq.post()` accepts a *pool* argument to use for the request. The
        global pool is unaffected.
        """
        pool = SyntacticAbominationHTTPConnectionPool()

        d = treq.post("http://foo", data=b"bar", pool=pool)

        self.assertEqual(pool.requests, 1)
        self.failureResultOf(d, TabError)
        self.assertIsNot(pool, get_global_pool())

    def test_custom_agent(self):
        """
        A custom Agent is used if specified.
        """

        @implementer(IAgent)
        class CounterAgent:
            requests = 0

            def request(self, method, uri, headers=None, bodyProducer=None):
                self.requests += 1
                return defer.Deferred()

        custom_agent = CounterAgent()
        d = treq.get("https://www.example.org/", agent=custom_agent)

        self.assertNoResult(d)
        self.assertEqual(1, custom_agent.requests)

    def test_request_invalid_param(self):
        """
        `treq.request()` warns that it ignores unknown keyword arguments, but
        this is deprecated.

        This test verifies that stacklevel is set appropriately when issuing
        the warning.
        """
        with self.assertRaises(TypeError) as c:
            treq.request(
                "GET",
                "https://foo.bar",
                invalid=True,
                pool=SyntacticAbominationHTTPConnectionPool(),
            )

        self.assertIn("invalid", str(c.exception))

    def test_post_json_with_data(self):
        """
        `treq.post()` warns that mixing *data* and *json* is deprecated.

        This test verifies that stacklevel is set appropriately when issuing
        the warning.
        """
        self.failureResultOf(
            treq.post(
                "https://test.example/",
                data={"hello": "world"},
                json={"goodnight": "moon"},
                pool=SyntacticAbominationHTTPConnectionPool(),
            )
        )

        [w] = self.flushWarnings([self.test_post_json_with_data])
        self.assertEqual(DeprecationWarning, w["category"])
        self.assertEqual(
            (
                "Argument 'json' will be ignored because 'data' was also passed."
                " This will raise TypeError in the next treq release."
            ),
            w["message"],
        )


class DefaultReactorTests(TestCase):
    """
    Test `treq.api.default_reactor()`
    """

    def test_passes_reactor(self):
        """
        `default_reactor()` returns any reactor passed.
        """
        reactor = MemoryReactorClock()

        self.assertIs(default_reactor(reactor), reactor)

    def test_uses_default_reactor(self):
        """
        `default_reactor()` returns the global reactor when passed ``None``.
        """
        from twisted.internet import reactor

        self.assertEqual(default_reactor(None), reactor)


class DefaultPoolTests(TestCase):
    """
    Test `treq.api.default_pool`.
    """

    def setUp(self):
        set_global_pool(None)
        self.reactor = MemoryReactorClock()

    def test_persistent_false(self):
        """
        When *persistent=False* is passed a non-persistent pool is created.
        """
        pool = default_pool(self.reactor, None, False)

        self.assertTrue(isinstance(pool, HTTPConnectionPool))
        self.assertFalse(pool.persistent)

    def test_persistent_false_not_stored(self):
        """
        When *persistent=False* is passed the resulting pool is not stored as
        the global pool.
        """
        pool = default_pool(self.reactor, None, persistent=False)

        self.assertIsNot(pool, get_global_pool())

    def test_persistent_false_new(self):
        """
        When *persistent=False* is passed a new pool is returned each time.
        """
        pool1 = default_pool(self.reactor, None, persistent=False)
        pool2 = default_pool(self.reactor, None, persistent=False)

        self.assertIsNot(pool1, pool2)

    def test_pool_none_persistent_none(self):
        """
        When *persistent=None* is passed a _persistent_ pool is created for
        backwards compatibility.
        """
        pool = default_pool(self.reactor, None, None)

        self.assertTrue(pool.persistent)

    def test_pool_none_persistent_true(self):
        """
        When *persistent=True* is passed a persistent pool is created and
        stored as the global pool.
        """
        pool = default_pool(self.reactor, None, True)

        self.assertTrue(isinstance(pool, HTTPConnectionPool))
        self.assertTrue(pool.persistent)

    def test_cached_global_pool(self):
        """
        When *persistent=True* or *persistent=None* is passed the pool created
        is cached as the global pool.
        """
        pool1 = default_pool(self.reactor, None, None)
        pool2 = default_pool(self.reactor, None, True)

        self.assertEqual(pool1, pool2)

    def test_specified_pool(self):
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
