"""
Strictly internal utilities.
"""

from __future__ import absolute_import, division, print_function

from twisted.web.client import HTTPConnectionPool


def default_reactor(reactor):
    """
    Return the specified reactor or the default.
    """
    if reactor is None:
        from twisted.internet import reactor

    return reactor


_global_pool = [None]


def get_global_pool():
    return _global_pool[0]


def set_global_pool(pool):
    _global_pool[0] = pool


def default_pool(reactor, pool, persistent):
    """
    Return the specified pool or a a pool with the specified reactor and
    persistence.
    """
    reactor = default_reactor(reactor)

    if pool is not None:
        return pool

    if persistent is False:
        return HTTPConnectionPool(reactor, persistent=persistent)

    if get_global_pool() is None:
        set_global_pool(HTTPConnectionPool(reactor, persistent=True))

    return get_global_pool()
