import mock

from twisted.trial.unittest import TestCase

from treq._utils import default_reactor, default_pool, set_global_pool


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

        pool_patcher = mock.patch('treq._utils.HTTPConnectionPool')

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
