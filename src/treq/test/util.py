import os
import platform

from unittest import mock

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


def skip_on_windows_because_of_199():
    """
    Return a skip describing issue #199 under Windows.

    :return: A :py:class:`str` skip reason.
    """
    if platform.system() == 'Windows':
        return ("HTTPBin process cannot run under Windows."
                " See https://github.com/twisted/treq/issues/199")
    return None
