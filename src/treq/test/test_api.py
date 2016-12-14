from __future__ import absolute_import, division

import mock

from twisted.trial.unittest import TestCase

import treq
from treq._utils import set_global_pool


class TreqAPITests(TestCase):
    def setUp(self):
        set_global_pool(None)

        agent_patcher = mock.patch('treq.api.Agent')
        self.Agent = agent_patcher.start()
        self.addCleanup(agent_patcher.stop)

        client_patcher = mock.patch('treq.api.HTTPClient')
        self.HTTPClient = client_patcher.start()
        self.addCleanup(client_patcher.stop)

        pool_patcher = mock.patch('treq._utils.HTTPConnectionPool')
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
