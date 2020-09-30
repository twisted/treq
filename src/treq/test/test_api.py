from __future__ import absolute_import, division

import mock

from twisted.web.client import HTTPConnectionPool
from twisted.trial.unittest import TestCase
from twisted.internet.testing import MemoryReactorClock

import treq
from treq.api import default_reactor, default_pool, set_global_pool, get_global_pool


class TreqAPITests(TestCase):
    def setUp(self):
        set_global_pool(None)

        agent_patcher = mock.patch('treq.api.Agent')
        self.Agent = agent_patcher.start()
        self.addCleanup(agent_patcher.stop)

        client_patcher = mock.patch('treq.api.HTTPClient')
        self.HTTPClient = client_patcher.start()
        self.addCleanup(client_patcher.stop)

        pool_patcher = mock.patch('treq.api.HTTPConnectionPool')
        self.HTTPConnectionPool = pool_patcher.start()
        self.addCleanup(pool_patcher.stop)

        self.client = self.HTTPClient.return_value

    def test_default_pool(self):
        resp = treq.get('http://test.com')

        self.Agent.assert_called_once_with(
            mock.ANY,
            pool=self.HTTPConnectionPool.return_value
        )

        self.assertEqual(self.client.get.return_value, resp)

    def test_cached_pool(self):
        pool = self.HTTPConnectionPool.return_value

        treq.get('http://test.com')

        self.HTTPConnectionPool.return_value = mock.Mock()

        treq.get('http://test.com')

        self.Agent.assert_called_with(mock.ANY, pool=pool)

    def test_custom_agent(self):
        """
        A custom Agent is used if specified.
        """
        custom_agent = mock.Mock()
        treq.get('https://www.example.org/', agent=custom_agent)
        self.HTTPClient.assert_called_once_with(custom_agent)


class DefaultReactorTests(TestCase):
    def test_passes_reactor(self):
        mock_reactor = mock.Mock()

        self.assertEqual(default_reactor(mock_reactor), mock_reactor)

    def test_uses_default_reactor(self):
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
