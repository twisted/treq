from __future__ import absolute_import, division

import mock

from twisted.trial.unittest import TestCase

import treq
from treq.api import default_reactor, default_pool, set_global_pool


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
    def setUp(self):
        set_global_pool(None)

        pool_patcher = mock.patch('treq.api.HTTPConnectionPool')

        self.HTTPConnectionPool = pool_patcher.start()
        self.addCleanup(pool_patcher.stop)

        self.reactor = mock.Mock()

    def test_persistent_false(self):
        self.assertEqual(
            default_pool(self.reactor, None, False),
            self.HTTPConnectionPool.return_value
        )

        self.HTTPConnectionPool.assert_called_once_with(
            self.reactor, persistent=False
        )

    def test_pool_none_persistent_none(self):
        self.assertEqual(
            default_pool(self.reactor, None, None),
            self.HTTPConnectionPool.return_value
        )

        self.HTTPConnectionPool.assert_called_once_with(
            self.reactor, persistent=True
        )

    def test_pool_none_persistent_true(self):
        self.assertEqual(
            default_pool(self.reactor, None, True),
            self.HTTPConnectionPool.return_value
        )

        self.HTTPConnectionPool.assert_called_once_with(
            self.reactor, persistent=True
        )

    def test_cached_global_pool(self):
        pool1 = default_pool(self.reactor, None, None)

        self.HTTPConnectionPool.return_value = mock.Mock()

        pool2 = default_pool(self.reactor, None, True)

        self.assertEqual(pool1, pool2)

    def test_specified_pool(self):
        pool = mock.Mock()

        self.assertEqual(
            default_pool(self.reactor, pool, None),
            pool
        )

        self.HTTPConnectionPool.assert_not_called()
