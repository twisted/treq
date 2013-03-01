import mock

from treq.test.util import TestCase

import treq
from treq._utils import set_global_pool


class TreqAPITests(TestCase):
    def setUp(self):
        set_global_pool(None)

        client_patcher = mock.patch('treq.api.HTTPClient')
        self.HTTPClient = client_patcher.start()
        self.addCleanup(client_patcher.stop)

        pool_patcher = mock.patch('treq._utils.HTTPConnectionPool')
        self.HTTPConnectionPool = pool_patcher.start()
        self.addCleanup(pool_patcher.stop)

        self.client = self.HTTPClient.with_config.return_value

    def test_default_pool(self):
        resp = treq.get('http://test.com')

        self.HTTPClient.with_config.assert_called_once_with(
            pool=self.HTTPConnectionPool.return_value
        )

        self.assertEqual(self.client.get.return_value, resp)

    def test_cached_pool(self):
        pool = self.HTTPConnectionPool.return_value

        treq.get('http://test.com')

        self.HTTPConnectionPool.return_value = mock.Mock()

        treq.get('http://test.com')

        self.HTTPClient.with_config.assert_called_with(pool=pool)
