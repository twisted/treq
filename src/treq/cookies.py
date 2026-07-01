# -*- test-case-name: treq.test.test_treq_integration -*-
"""
Convenience helpers for :mod:`http.cookiejar`
"""

from collections.abc import Iterable
from http.cookiejar import Cookie, CookieJar
from typing import Optional, Union

from hyperlink import EncodedURL


class CookieCollision(Exception):
    """
    Raised by :meth:`IndexableCookieJar.__getitem__` when more than one
    matching cookie is found.
    """


class IndexableCookieJar(CookieJar):
    """
    An :py:class:`IndexableCookieJar` is Treq's subclass of the standard library
    :py:class:`http.cookiejar.CookieJar`, which, like the one from `requests`_,
    allows for indexing to retrieve cookie values.  This is for convenience and
    for compatibility with `requests`_ users' expectations.

    .. _requests: https://requests.readthedocs.io/en/latest/

    .. note::

        In general, you should not need to import or instantiate a
        :py:class:`IndexableCookieJar` directly; anywhere that Treq requires cookies, a
        :py:class:`http.cookiejar.CookieJar` or ``dict`` of ``str`` to ``str``
        should be acceptable; but :py:meth:`treq.response._Response.cookies`
        returns one that is also indexable.
    """

    def __getitem__(self, name: str) -> str:
        """
        Search the jar for a uniquely-named cookie.

        This is O(n) on the number of cookies in the jar.

        .. note::

            This method exists for compatibility with `RequestsCookieJar`_, but is
            difficult to use securely when following HTTP redirects. Prefer
            :func:`treq.cookies.search()`, which lets you limit the search to a
            specific domain name.

        .. note::

            This method ignores cookies with no value (`None`), but may return an
            empty string, `unlike requests`_.

        :param name: The name of the cookie to retrieve.

        :raises KeyError: when no cookie with a value has the given name.

        :raises CookieCollision: when more than one cookie has the given name.

        .. _RequestsCookieJar: https://requests.readthedocs.io/en/latest/api/#requests.cookies.RequestsCookieJar
        .. _unlike requests: https://github.com/psf/requests/issues/7003
        """
        value: str | None = None
        for cookie in self:
            if cookie.name == name and cookie.value is not None:
                if value is None:
                    value = cookie.value
                else:
                    raise CookieCollision(name)
        if value is None:
            raise KeyError(name)
        return value


def scoped_cookie(origin: Union[str, EncodedURL], name: str, value: str) -> Cookie:
    """
    Create a cookie scoped to a given URL's origin.

    You can insert the result directly into a `CookieJar`, like::

        from http.cookiejar import CookieJar

        jar = CookieJar()
        jar.set_cookie(scoped_cookie("https://example.tld", "flavor", "chocolate"))

        await treq.get("https://domain.example", cookies=jar)

    :param origin:
        A URL that specifies the domain and port number of the cookie.

        If the protocol is HTTP*S* the cookie is marked ``Secure``, meaning
        it will not be attached to HTTP requests. Otherwise the cookie will be
        attached to both HTTP and HTTPS requests

    :param name: Name of the cookie.

    :param value: Value of the cookie.

    .. note::

        This does not scope the cookies to any particular path, only the
        host, port, and scheme of the given URL.
    """
    if isinstance(origin, EncodedURL):
        url_object = origin
    else:
        url_object = EncodedURL.from_text(origin)

    secure = url_object.scheme == "https"
    port_specified = not (
        (url_object.scheme == "https" and url_object.port == 443)
        or (url_object.scheme == "http" and url_object.port == 80)
    )
    port = str(url_object.port) if port_specified else None
    domain = url_object.host
    netscape_domain = domain if "." in domain else domain + ".local"
    return Cookie(
        # Scoping
        domain=netscape_domain,
        port=port,
        secure=secure,
        port_specified=port_specified,
        # Contents
        name=name,
        value=value,
        # Constant/always-the-same stuff
        version=0,
        path="/",
        expires=None,
        discard=False,
        comment=None,
        comment_url=None,
        rfc2109=False,
        path_specified=False,
        domain_specified=False,
        domain_initial_dot=False,
        rest={},
    )


def search(
    jar: CookieJar, *, domain: str, name: Optional[str] = None
) -> Iterable[Cookie]:
    """
    Raid the cookie jar for matching cookies.

    This is O(n) on the number of cookies in the jar.

    :param jar: The `CookieJar` (or subclass thereof) to search.

    :param domain:
        Domain, as in the URL, to match. ``.local`` is appended to
        a bare hostname. Subdomains are not matched (i.e., searching
        for ``foo.bar.tld`` won't return a cookie set for ``bar.tld``).

    :param name: Cookie name to match (exactly)
    """
    netscape_domain = domain if "." in domain else domain + ".local"

    for c in jar:
        if c.domain != netscape_domain:
            continue
        if name is not None and c.name != name:
            continue
        yield c
