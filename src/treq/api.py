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
    :type headers: :class:`~twisted.web.http_headers.Headers` or None

    :param params: Optional parameters to be append to the URL query string.
        Any query string parameters in the *url* will be preserved.
    :type params: dict w/ str or list/tuple of str values, list of 2-tuples, or
        None.

    :param data:
        Arbitrary request body data.

        If *files* is also passed this must be a :class:`dict`,
        a :class:`tuple` or :class:`list` of field tuples as accepted by
        :class:`MultiPartProducer`. The request is assigned a Content-Type of
        ``multipart/form-data``.

        If a :class:`dict`, :class:`list`, or :class:`tuple` it is URL-encoded
        and the request assigned a Content-Type of
        ``application/x-www-form-urlencoded``.

        Otherwise, any non-``None`` value is passed to the client's
        *data_to_body_producer* callable (by default, :class:`IBodyProducer`),
        which accepts :class:`bytes` and binary files like returned by
        ``open(..., "rb")``.
    :type data: `bytes`, `typing.BinaryIO`, `IBodyProducer`, or `None`

    :param files:
        Files to include in the request body, in any of the several formats:

        - ``[("fieldname", binary_file)]``
        - ``[("fieldname", "filename", binary_file)]``
        - ``[("fieldname, "filename', "content-type", binary_file)]``

        Or a mapping:

        - ``{"fieldname": binary_file}``
        - ``{"fieldname": ("filename", binary_file)}``
        - ``{"fieldname": ("filename", "content-type", binary_file)}``

        Each ``binary_file`` is a file-like object open in binary mode (like
        returned by ``open("filename", "rb")``). The filename is taken from
        the file's ``name`` attribute if not specified. The Content-Type is
        guessed based on the filename using :func:`mimetypes.guess_type()` if
        not specified, falling back to ``application/octet-stream``.

        While uploading Treq will measure the length of seekable files to
        populate the Content-Length header of the file part.

        If *files* is given the request is assigned a Content-Type of
        ``multipart/form-data``. Additional fields may be given in the *data*
        argument.

    :param json: Optional JSON-serializable content for the request body.
        Mutually exclusive with *data* and *files*.
    :type json: `dict`, `list`, `tuple`, `int`, `str`, `bool`, or `None`

    :param auth: HTTP Basic Authentication information --- see
        :func:`treq.auth.add_auth`.
    :type auth: tuple of ``('username', 'password')``

    :param cookies: Cookies to send with this request.  The HTTP kind, not the
        tasty kind.
    :type cookies: ``dict`` or ``cookielib.CookieJar``

    :param int timeout: Request timeout seconds. If a response is not
        received within this timeframe, a connection is aborted with
        ``CancelledError``.

    :param bool allow_redirects: Follow HTTP redirects.  Default: ``True``

    :param bool browser_like_redirects: Follow redirects like a web browser:
        When a 301 or 302 redirect is received in response to a POST request
        convert the method to GET.
        See :rfc:`7231 <7231#section-6.4.3>` and
        :class:`~twisted.web.client.BrowserLikeRedirectAgent`). Default: ``False``

    :param bool unbuffered: Pass ``True`` to to disable response buffering.  By
        default treq buffers the entire response body in memory.

    :param reactor: Optional Twisted reactor.

    :param bool persistent: Use persistent HTTP connections.  Default: ``True``

    :param agent: Provide your own custom agent. Use this to override things
                  like ``connectTimeout`` or ``BrowserLikePolicyForHTTPS``. By
                  default, treq will create its own Agent with reasonable
                  defaults.
    :type agent: twisted.web.iweb.IAgent

    :rtype: Deferred that fires with an :class:`IResponse`

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
