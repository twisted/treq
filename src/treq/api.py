# -*- test-case-name: treq.test.test_api -*-
from __future__ import annotations

from typing import TypeVar

from twisted.internet.defer import Deferred
from twisted.internet.interfaces import IReactorTCP
from twisted.web.client import Agent, HTTPConnectionPool
from twisted.web.iweb import IAgent

from treq._types import (
    _NOTHING,
    _CookiesType,
    _FilesType,
    _ITreqReactor,
    _JSONType,
    _Nothing,
    _ParamsType,
    _SomeURL,
)
from treq.client import HTTPClient
from treq.response import _Response

from ._types import _DataType, _HeadersType

R = TypeVar("R")


def head(
    url: _SomeURL,
    *,
    agent: IAgent | None = None,
    pool: HTTPConnectionPool | None = None,
    persistent: bool | None = None,
    params: _ParamsType | None = None,
    headers: _HeadersType | None = None,
    data: _DataType | None = None,
    files: _FilesType | None = None,
    json: _JSONType | _Nothing = _NOTHING,
    auth: tuple[str | bytes, str | bytes] | None = None,
    cookies: _CookiesType | None = None,
    allow_redirects: bool = True,
    browser_like_redirects: bool = False,
    unbuffered: bool = False,
    reactor: _ITreqReactor | None = None,
    timeout: float | None = None,
) -> Deferred[_Response]:
    """
    Make a ``HEAD`` request.

    See :py:func:`treq.request`
    """
    return _client(agent, pool, persistent, reactor).head(
        url,
        _stacklevel=4,
        params=params,
        headers=headers,
        data=data,
        files=files,
        json=json,
        auth=auth,
        cookies=cookies,
        allow_redirects=allow_redirects,
        browser_like_redirects=browser_like_redirects,
        unbuffered=unbuffered,
        reactor=reactor,
        timeout=timeout,
    )


def get(
    url: _SomeURL,
    headers: _HeadersType | None = None,
    *,
    agent: IAgent | None = None,
    pool: HTTPConnectionPool | None = None,
    persistent: bool | None = None,
    params: _ParamsType | None = None,
    data: _DataType | None = None,
    files: _FilesType | None = None,
    json: _JSONType | _Nothing = _NOTHING,
    auth: tuple[str | bytes, str | bytes] | None = None,
    cookies: _CookiesType | None = None,
    allow_redirects: bool = True,
    browser_like_redirects: bool = False,
    unbuffered: bool = False,
    reactor: _ITreqReactor | None = None,
    timeout: float | None = None,
) -> Deferred[_Response]:
    """
    Make a ``GET`` request.

    See :py:func:`treq.request`
    """
    return _client(agent, pool, persistent, reactor).get(
        url,
        _stacklevel=4,
        params=params,
        headers=headers,
        data=data,
        files=files,
        json=json,
        auth=auth,
        cookies=cookies,
        allow_redirects=allow_redirects,
        browser_like_redirects=browser_like_redirects,
        unbuffered=unbuffered,
        reactor=reactor,
        timeout=timeout,
    )


def post(
    url: _SomeURL,
    data: _DataType | None = None,
    *,
    agent: IAgent | None = None,
    pool: HTTPConnectionPool | None = None,
    persistent: bool | None = None,
    params: _ParamsType | None = None,
    headers: _HeadersType | None = None,
    files: _FilesType | None = None,
    json: _JSONType | _Nothing = _NOTHING,
    auth: tuple[str | bytes, str | bytes] | None = None,
    cookies: _CookiesType | None = None,
    allow_redirects: bool = True,
    browser_like_redirects: bool = False,
    unbuffered: bool = False,
    reactor: _ITreqReactor | None = None,
    timeout: float | None = None,
) -> Deferred[_Response]:
    """
    Make a ``POST`` request.

    See :py:func:`treq.request`
    """
    return _client(agent, pool, persistent, reactor).post(
        url,
        _stacklevel=4,
        params=params,
        headers=headers,
        data=data,
        files=files,
        json=json,
        auth=auth,
        cookies=cookies,
        allow_redirects=allow_redirects,
        browser_like_redirects=browser_like_redirects,
        unbuffered=unbuffered,
        reactor=reactor,
        timeout=timeout,
    )


def put(
    url: _SomeURL,
    data: _DataType | None = None,
    *,
    agent: IAgent | None = None,
    pool: HTTPConnectionPool | None = None,
    persistent: bool | None = None,
    params: _ParamsType | None = None,
    headers: _HeadersType | None = None,
    files: _FilesType | None = None,
    json: _JSONType | _Nothing = _NOTHING,
    auth: tuple[str | bytes, str | bytes] | None = None,
    cookies: _CookiesType | None = None,
    allow_redirects: bool = True,
    browser_like_redirects: bool = False,
    unbuffered: bool = False,
    reactor: _ITreqReactor | None = None,
    timeout: float | None = None,
) -> Deferred[_Response]:
    """
    Make a ``PUT`` request.

    See :py:func:`treq.request`
    """
    return _client(agent, pool, persistent, reactor).put(
        url,
        _stacklevel=4,
        params=params,
        headers=headers,
        data=data,
        files=files,
        json=json,
        auth=auth,
        cookies=cookies,
        allow_redirects=allow_redirects,
        browser_like_redirects=browser_like_redirects,
        unbuffered=unbuffered,
        reactor=reactor,
        timeout=timeout,
    )


def patch(
    url: _SomeURL,
    data: _DataType | None = None,
    *,
    agent: IAgent | None = None,
    pool: HTTPConnectionPool | None = None,
    persistent: bool | None = None,
    params: _ParamsType | None = None,
    headers: _HeadersType | None = None,
    files: _FilesType | None = None,
    json: _JSONType | _Nothing = _NOTHING,
    auth: tuple[str | bytes, str | bytes] | None = None,
    cookies: _CookiesType | None = None,
    allow_redirects: bool = True,
    browser_like_redirects: bool = False,
    unbuffered: bool = False,
    reactor: _ITreqReactor | None = None,
    timeout: float | None = None,
) -> Deferred[_Response]:
    """
    Make a ``PATCH`` request.

    See :py:func:`treq.request`
    """
    return _client(agent, pool, persistent, reactor).patch(
        url,
        _stacklevel=4,
        params=params,
        headers=headers,
        data=data,
        files=files,
        json=json,
        auth=auth,
        cookies=cookies,
        allow_redirects=allow_redirects,
        browser_like_redirects=browser_like_redirects,
        unbuffered=unbuffered,
        reactor=reactor,
        timeout=timeout,
    )


def delete(
    url: _SomeURL,
    *,
    agent: IAgent | None = None,
    pool: HTTPConnectionPool | None = None,
    persistent: bool | None = None,
    params: _ParamsType | None = None,
    headers: _HeadersType | None = None,
    data: _DataType | None = None,
    files: _FilesType | None = None,
    json: _JSONType | _Nothing = _NOTHING,
    auth: tuple[str | bytes, str | bytes] | None = None,
    cookies: _CookiesType | None = None,
    allow_redirects: bool = True,
    browser_like_redirects: bool = False,
    unbuffered: bool = False,
    reactor: _ITreqReactor | None = None,
    timeout: float | None = None,
) -> Deferred[_Response]:
    """
    Make a ``DELETE`` request.

    See :py:func:`treq.request`
    """
    return _client(agent, pool, persistent, reactor).delete(
        url,
        _stacklevel=4,
        params=params,
        headers=headers,
        data=data,
        files=files,
        json=json,
        auth=auth,
        cookies=cookies,
        allow_redirects=allow_redirects,
        browser_like_redirects=browser_like_redirects,
        unbuffered=unbuffered,
        reactor=reactor,
        timeout=timeout,
    )


def request(
    method: str,
    url: _SomeURL,
    data: _DataType | None = None,
    *,
    agent: IAgent | None = None,
    pool: HTTPConnectionPool | None = None,
    persistent: bool | None = None,
    params: _ParamsType | None = None,
    headers: _HeadersType | None = None,
    files: _FilesType | None = None,
    json: _JSONType | _Nothing = _NOTHING,
    auth: tuple[str | bytes, str | bytes] | None = None,
    cookies: _CookiesType | None = None,
    allow_redirects: bool = True,
    browser_like_redirects: bool = False,
    unbuffered: bool = False,
    reactor: _ITreqReactor | None = None,
    timeout: float | None = None,
) -> Deferred[_Response]:
    """
    Make an HTTP request.

    :param str method: HTTP method. Example: ``'GET'``, ``'HEAD'``. ``'PUT'``,
         ``'POST'``.

    :param url: http or https URL, which may include query arguments.
    :type url: :class:`hyperlink.DecodedURL`, `str`, `bytes`, or
        :class:`hyperlink.EncodedURL`

    :param headers: Optional HTTP Headers to send with this request.

    :param params: Optional parameters to be append to the URL query string.
        Any query string parameters in the *url* will be preserved.

    :param data:
        Arbitrary request body data.

        If *files* is also passed this must be a :class:`dict`,
        a :class:`tuple` or :class:`list` of field tuples as accepted by
        :class:`~treq.multipart.MultiPartProducer`. The request is assigned
        a Content-Type of ``multipart/form-data``.

        If a :class:`dict`, :class:`list`, or :class:`tuple` it is URL-encoded
        and the request assigned a Content-Type of
        ``application/x-www-form-urlencoded``.

        Otherwise, any non-``None`` value is passed to the client's
        *data_to_body_producer* callable (by default,
        :class:`~twisted.web.iweb.IBodyProducer`),
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
        the file's ``name`` attribute, if not specified. The Content-Type is
        guessed based on the filename using :func:`mimetypes.guess_type()`, if
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
        tasty kind. If you pass a :class:`dict`, the cookies therein will be
        scoped to the origin of *url* (see :func:`~treq.cookies.scoped_cookie()`).
    :type cookies: :class:`dict` or :class:`http.cookiejar.CookieJar`

    :param int timeout: Request timeout seconds. If a response is not
        received within this timeframe, a connection is aborted with
        :exc:`~twisted.internet.defer.CancelledError`.

    :param bool allow_redirects: Follow HTTP redirects.  Default: ``True``

    :param bool browser_like_redirects: Follow redirects like a web browser:
        When a 301 or 302 redirect is received in response to a POST request
        convert the method to GET.
        See :rfc:`RFC 9110 <9110#section-15.4.3>` and
        :class:`~twisted.web.client.BrowserLikeRedirectAgent`). Default: ``False``

    :param bool unbuffered: Pass ``True`` to to disable response buffering.  By
        default treq buffers the entire response body in memory.

    :param reactor: Optional Twisted reactor.

    :param bool persistent: Use persistent HTTP connections.  Default: ``True``

    :param agent: Provide your own custom agent. Use this to override things
                  like ``connectTimeout`` or ``BrowserLikePolicyForHTTPS``. By
                  default, treq will create its own IAgent with reasonable
                  defaults.
    :type agent: twisted.web.iweb.IAgent

    :rtype: Deferred that fires with an :class:`IResponse`

    .. versionchanged:: treq 20.9.0

        The *url* param now accepts :class:`hyperlink.DecodedURL` and
        :class:`hyperlink.EncodedURL` objects.
    """
    return _client(agent, pool, persistent, reactor).request(
        method,
        url,
        _stacklevel=3,
        params=params,
        headers=headers,
        data=data,
        files=files,
        json=json,
        auth=auth,
        cookies=cookies,
        allow_redirects=allow_redirects,
        browser_like_redirects=browser_like_redirects,
        unbuffered=unbuffered,
        reactor=reactor,
        timeout=timeout,
    )


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

    # NOTE: This doesn't necessarily return a pool that matches
    # the *reactor* parameter, which can produce confusing behavior
    # in tests that use a fake reactor.
    return get_global_pool()


def _client(
    agent: IAgent | None = None,
    pool: HTTPConnectionPool | None = None,
    persistent: bool | None = None,
    reactor: IReactorTCP | None = None,
) -> HTTPClient:
    if agent is None:
        # "reactor" isn't removed from kwargs because it must also be passed
        # down for use in the timeout logic.
        reactor = default_reactor(reactor)
        pool = default_pool(reactor, pool, persistent)
        agent = Agent(reactor, pool=pool)
    return HTTPClient(agent)
