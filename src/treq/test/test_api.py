from __future__ import absolute_import, division

import mock

from treq.test.util import TestCase
import treq
from treq._utils import set_global_pool
from treq.testing import RequestTraversalAgent


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

        tcp_endpoint = mock.patch('treq.api.clientFromString')
        self.TCPEndpoint = tcp_endpoint.start()
        self.addCleanup(tcp_endpoint.stop)

        self.client = self.HTTPClient.return_value

    def test_default_pool(self):
        resp = treq.get('http://test.com')

        self.Agent.assert_called_once_with(
            mock.ANY,
            pool=self.HTTPConnectionPool.return_value
        )

        self.assertEqual(self.client.get.return_value, resp)

    def test_proxy(self):
        """
        Ensure that eventually a ProxyAgent is used to make the request.

        ProxyAgent just wraps agent with a similar interface, so
        this is a fairly safe assumption to make.
        """
        agent = RequestTraversalAgent
        resp = treq.get('http://test.com', proxy=('proxy', 8080), proxy_agent_cls=agent)

        self.TCPEndpoint.assert_called_once_with(
            mock.ANY,
            'tcp:host=proxy:8080'
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
