import os
import platform

import mock

from twisted.internet import reactor
from twisted.internet.task import Clock
from twisted.trial.unittest import TestCase
from twisted.python.failure import Failure

DEBUG = os.getenv("TREQ_DEBUG", False) == "true"

is_pypy = platform.python_implementation() == 'PyPy'


try:
    import OpenSSL
    has_ssl = OpenSSL is not None
except ImportError:
    has_ssl = False


if hasattr(TestCase, "successResultOf"):
    TestCase = TestCase
else:
    class TestCase(TestCase):
        def successResultOf(self, d):
            results = []
            d.addBoth(results.append)

            if isinstance(results[0], Failure):
                results[0].raiseException()

            results[0]

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
