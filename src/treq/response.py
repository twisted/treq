from __future__ import absolute_import, division, print_function

from twisted.python.components import proxyForInterface
from twisted.web.iweb import IResponse

from requests.cookies import cookiejar_from_dict

from treq.content import content, json_content, text_content


class _Response(proxyForInterface(IResponse)):
    """
    A wrapper for :class:`twisted.web.iweb.IResponse` which manages cookies and
    adds a few convenience methods.
    """

    def __init__(self, original, cookiejar):
        self.original = original
        self._cookiejar = cookiejar

    def content(self):
        """
        Collect the response body as bytes per :func:`treq.content.content()`.

        :rtype: Deferred that fires with bytes when the entire body has been read.
        """
        return content(self.original)

    def json(self):
        """
        Collect the response body as JSON per :func:`treq.content.json_response()`.

        :rtype: Deferred that fires with the decoded JSON when the entire body
            has been read.
        """
        return json_content(self.original)

    def text(self, *args, **kwargs):
        """
        Collect the response body as a unicode string per
        :func:`treq.content.text_content()`.

        :rtype: Deferred that fires with a unicode string when the entire body
            has been read.
        """
        return text_content(self.original, *args, **kwargs)

    def history(self):
        """
        List response history chronologically: this is the list of responses
        (redirects) which led to this one.

        :rtype: list of :class:`_Response` in chronological order
        """
        if not hasattr(self, "previousResponse"):
            raise NotImplementedError(
                "Twisted < 13.1.0 does not support response history.")

        response = self
        history = []

        while response.previousResponse is not None:
            history.append(_Response(response.previousResponse,
                                     self._cookiejar))
            response = response.previousResponse

        history.reverse()
        return history

    def cookies(self):
        """
        Get a copy of this response's cookies.

        :rtype: :class:`requests.cookies.RequestsCookieJar`
        """
        jar = cookiejar_from_dict({})

        if self._cookiejar is not None:
            for cookie in self._cookiejar:
                jar.set_cookie(cookie)

        return jar
