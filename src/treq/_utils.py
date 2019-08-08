"""
Strictly internal utilities.
"""

from __future__ import absolute_import, division, print_function

import inspect
import warnings

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


def warn(*args, **kwargs):
    """
    Utility function to raise warnings with stack level set automatically to
    the first position outside a given namespace.

    Notice that if you pass the stacklevel keyword, it will be increased by 1
    in order to ignore this wrapper function and that will be passed directly
    to warnings.warn. That is: it is functionally equivalent to warnings.warn.

    @param namespace: calls within this namespace (aka startswith) will not
        be accounted for in the stacklevel variable if possible.
        If not defined, the default is the top level package of this code.
    @param default_stacklevel: in those cases in which there is no code
        outside of namespace in the stack, we will default to this value.
        This utility function already takes into account the fact that it is a
        wrapper around warnings.warn and secretly passes default_stacklevel+1
        when necessary.
        Defaults to 1, which would match the place where this was called from.
    """
    # Default to top-level package
    namespace = kwargs.pop('namespace', __name__.partition('.')[0])
    default_stacklevel = kwargs.pop('default_stacklevel', 1)
    stacklevel = kwargs.pop('stacklevel', None)

    if stacklevel is not None:
        # Increase in order to ignore this wrapper function
        # Users would not expect this function to count.
        stacklevel += 1
    else:
        stack = inspect.stack()

        # We skip the first stack frame in order to be able to use this
        # utility function from other packages.
        for current_stacklevel, frame_info in enumerate(stack[1:], 2):
            module = inspect.getmodule(frame_info[0])
            module_name = module.__name__ if module else None
            if not (module_name and module_name.startswith(namespace + '.')):
                break
            stacklevel = current_stacklevel

    if stacklevel is None:
        stacklevel = default_stacklevel + 1
    kwargs['stacklevel'] = stacklevel

    warnings.warn(*args, **kwargs)
