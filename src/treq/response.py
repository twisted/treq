from __future__ import absolute_import, division, print_function

from twisted.python.components import proxyForInterface
from twisted.web.iweb import IResponse, UNKNOWN_LENGTH
from twisted.python import reflect

from requests.cookies import cookiejar_from_dict

from treq.content import collect, content, json_content, text_content


class _Response(proxyForInterface(IResponse)):
    """
    A wrapper for :class:`twisted.web.iweb.IResponse` which manages cookies and
    adds a few convenience methods.
    """

    def __init__(self, original, cookiejar):
        self.original = original
        self._cookiejar = cookiejar

    def __repr__(self):
        """
        Generate a representation of the response which includes the HTTP
        status code, Content-Type header, and body size, if available.
        """
        if self.original.length == UNKNOWN_LENGTH:
            size = 'unknown size'
        else:
            size = '{:,d} bytes'.format(self.original.length)
        # Display non-ascii bits of the content-type header as backslash
        # escapes.
        content_type_bytes = b', '.join(
            self.original.headers.getRawHeaders(b'content-type', ()))
        content_type = repr(content_type_bytes).lstrip('b')[1:-1]
        return "<{} {} '{:.40s}' {}>".format(
            reflect.qual(self.__class__),
            self.original.code,
            content_type,
            size,
        )

    def collect(self, collector):
        """
        Incrementally collect the body of the response, per
        :func:`treq.collect()`.

        :param collector: A single argument callable that will be called
            with chunks of body data as it is received.

        :returns: A `Deferred` that fires when the entire body has been
            received.
        """
        return collect(self.original, collector)

    def content(self):
        """
        Read the entire body all at once, per :func:`treq.content()`.

        :returns: A `Deferred` that fires with a `bytes` object when the entire
            body has been received.
        """
        return content(self.original)

    def json(self, **kwargs):
        """
        Collect the response body as JSON per :func:`treq.json_content()`.

        :param kwargs: Any keyword arguments accepted by :py:func:`json.loads`

        :rtype: Deferred that fires with the decoded JSON when the entire body
            has been read.
        """
        return json_content(self.original, **kwargs)

    def text(self, encoding='ISO-8859-1'):
        """
        Read the entire body all at once as text, per
        :func:`treq.text_content()`.

        :rtype: A `Deferred` that fires with a unicode string when the entire
            body has been received.
        """
        return text_content(self.original, encoding)

    def history(self):
        """
        Get a list of all responses that (such as intermediate redirects),
        that ultimately ended in the current response. The responses are
        ordered chronologically.

        :returns: A `list` of :class:`~treq.response._Response` objects
        """
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
