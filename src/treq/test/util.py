import os
import platform

import mock

from twisted.internet import reactor
from twisted.internet.task import Clock

DEBUG = os.getenv("TREQ_DEBUG", False) == "true"

is_pypy = platform.python_implementation() == 'PyPy'


def with_clock(fn):
    def wrapper(*args, **kwargs):
        clock = Clock()
        with mock.patch.object(reactor, 'callLater', clock.callLater):
            return fn(*(args + (clock,)), **kwargs)
    return wrapper
