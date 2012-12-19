import os
import platform

from twisted.trial.unittest import TestCase
from twisted.python.failure import Failure

DEBUG = os.getenv("TREQ_DEBUG", False) == "true"

is_pypy = platform.python_implementation() == 'PyPy'


try:
    import OpenSSL
    has_ssl = OpenSSL is not None
except ImportError:
    has_ssl = False


class TestCase(TestCase):
    def successResultOf(self, d, expected):
        results = []
        d.addBoth(results.append)

        if isinstance(results[0], Failure):
            results[0].raiseException()

        self.assertEqual(results[0], expected)

    def failureResultOf(self, d, errorType):
        results = []
        d.addBoth(results.append)

        if not isinstance(results[0], Failure):
            self.fail("Expected {0} got {1}.".format(errorType, results[0]))

        self.assertTrue(results[0].check(errorType))
