from __future__ import absolute_import, division, print_function

from twisted.python.components import proxyForInterface
from twisted.web.iweb import IResponse

from requests.cookies import cookiejar_from_dict

from treq.content import content, json_content, text_content


class _Response(proxyForInterface(IResponse)):
    def __init__(self, original, cookiejar):
        self.original = original
        self._cookiejar = cookiejar

    def content(self):
        return content(self.original)

    def json(self, *args, **kwargs):
        return json_content(self.original, *args, **kwargs)

    def text(self, *args, **kwargs):
        return text_content(self.original, *args, **kwargs)

    def history(self):
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
        jar = cookiejar_from_dict({})

        if self._cookiejar is not None:
            for cookie in self._cookiejar:
                jar.set_cookie(cookie)

        return jar
