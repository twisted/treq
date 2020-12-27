from __future__ import absolute_import, division, print_function

from twisted.web.client import Agent, HTTPConnectionPool

from treq.client import HTTPClient


def head(url, **kwargs):
    """
    Make a ``HEAD`` request.

    See :py:func:`treq.request`
    """
    return _client(kwargs).head(url, _stacklevel=4, **kwargs)


def get(url, headers=None, **kwargs):
    """
    Make a ``GET`` request.

    See :py:func:`treq.request`
    """
    return _client(kwargs).get(url, headers=headers, _stacklevel=4, **kwargs)


def post(url, data=None, **kwargs):
    """
    Make a ``POST`` request.

    See :py:func:`treq.request`
    """
    return _client(kwargs).post(url, data=data, _stacklevel=4, **kwargs)


def put(url, data=None, **kwargs):
    """
    Make a ``PUT`` request.

    See :py:func:`treq.request`
    """
    return _client(kwargs).put(url, data=data, _stacklevel=4, **kwargs)


def patch(url, data=None, **kwargs):
    """
    Make a ``PATCH`` request.

    See :py:func:`treq.request`
    """
    return _client(kwargs).patch(url, data=data, _stacklevel=4, **kwargs)


def delete(url, **kwargs):
    """
    Make a ``DELETE`` request.

    See :py:func:`treq.request`
    """
    return _client(kwargs).delete(url, _stacklevel=4, **kwargs)


def request(method, url, **kwargs):
    """
    Make an HTTP request.

    :param str method: HTTP method. Example: ``'GET'``, ``'HEAD'``. ``'PUT'``,
         ``'POST'``.

    :param url: http or https URL, which may include query arguments.
    :type url: :class:`hyperlink.DecodedURL`, `str`, `bytes`, or
        :class:`hyperlink.EncodedURL`

    :param headers: Optional HTTP Headers to send with this request.
    :type headers: Headers or None

    :param params: Optional parameters to be append as the query string to
        the URL, any query string parameters in the URL already will be
        preserved.

    :type params: dict w/ str or list/tuple of str values, list of 2-tuples, or
        None.

    :param data: Optional request body.
    :type data: str, file-like, IBodyProducer, or None

    :param json: Optional JSON-serializable content to pass in body.
    :type json: dict, list/tuple, int, string/unicode, bool, or None

    :param reactor: Optional twisted reactor.

    :param bool persistent: Use persistent HTTP connections.  Default: ``True``
    :param bool allow_redirects: Follow HTTP redirects.  Default: ``True``

    :param auth: HTTP Basic Authentication information --- see
        :func:`treq.auth.add_auth`.
    :type auth: tuple of ``('username', 'password')``.

    :param cookies: Cookies to send with this request.  The HTTP kind, not the
        tasty kind.
    :type cookies: ``dict`` or ``cookielib.CookieJar``

    :param int timeout: Request timeout seconds. If a response is not
        received within this timeframe, a connection is aborted with
        ``CancelledError``.

    :param bool browser_like_redirects: Use browser like redirects
        (i.e. Ignore  RFC2616 section 10.3 and follow redirects from
        POST requests).  Default: ``False``

    :param bool unbuffered: Pass ``True`` to to disable response buffering.  By
        default treq buffers the entire response body in memory.

    :param agent: Provide your own custom agent. Use this to override things
                  like ``connectTimeout`` or ``BrowserLikePolicyForHTTPS``. By
                  default, treq will create its own Agent with reasonable
                  defaults.
    :type agent: twisted.web.iweb.IAgent

    :rtype: Deferred that fires with an IResponse provider.

    .. versionchanged:: treq 20.9.0

        The *url* param now accepts :class:`hyperlink.DecodedURL` and
        :class:`hyperlink.EncodedURL` objects.
    """
    return _client(kwargs).request(method, url, _stacklevel=3, **kwargs)


#
# Private API
#


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
    Return the specified pool or a pool with the specified reactor and
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


def _client(kwargs):
    agent = kwargs.pop("agent", None)
    pool = kwargs.pop("pool", None)
    persistent = kwargs.pop("persistent", None)
    if agent is None:
        # "reactor" isn't removed from kwargs because it must also be passed
        # down for use in the timeout logic.
        reactor = default_reactor(kwargs.get("reactor"))
        pool = default_pool(reactor, pool, persistent)
        agent = Agent(reactor, pool=pool)
    return HTTPClient(agent)
