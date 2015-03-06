import os
import platform

import mock
import twisted

from twisted.internet import reactor
from twisted.internet.tcp import Client
from twisted.internet.task import Clock, deferLater

from twisted.web.client import HTTPConnectionPool
from twisted.trial.unittest import TestCase
from twisted.python.failure import Failure
from twisted.python.versions import Version

import treq

DEBUG = os.getenv("TREQ_DEBUG", False) == "true"

is_pypy = platform.python_implementation() == 'PyPy'


if twisted.version < Version('twisted', 13, 1, 0):
    class TestCase(TestCase):
        def successResultOf(self, d):
            results = []
            d.addBoth(results.append)

            if isinstance(results[0], Failure):
                results[0].raiseException()

            return results[0]

        def failureResultOf(self, d, *errorTypes):
            results = []
            d.addBoth(results.append)

            if not isinstance(results[0], Failure):
                self.fail("Expected one of {0} got {1}.".format(
                    errorTypes, results[0]))

            self.assertTrue(results[0].check(*errorTypes))
            return results[0]


def with_clock(fn):
    def wrapper(*args, **kwargs):
        clock = Clock()
        with mock.patch.object(reactor, 'callLater', clock.callLater):
            return fn(*(args + (clock,)), **kwargs)
    return wrapper


def with_baseurl(method):
    def _request(self, url, *args, **kwargs):
        return method(self.baseurl + url, *args, pool=self.pool, **kwargs)

    return _request


class IntegrationTestCase(TestCase):

    get = with_baseurl(treq.get)
    head = with_baseurl(treq.head)
    post = with_baseurl(treq.post)
    put = with_baseurl(treq.put)
    patch = with_baseurl(treq.patch)
    delete = with_baseurl(treq.delete)

    def setUp(self):
        self.pool = HTTPConnectionPool(reactor, False)

    def tearDown(self):
        def _check_fds(_):
            # This appears to only be necessary for HTTPS tests.
            # For the normal HTTP tests then closeCachedConnections is
            # sufficient.
            fds = set(reactor.getReaders() + reactor.getReaders())
            if not [fd for fd in fds if isinstance(fd, Client)]:
                return

            return deferLater(reactor, 0, _check_fds, None)

        return self.pool.closeCachedConnections().addBoth(_check_fds)
