from twisted.python.components import proxyForInterface
from twisted.web.iweb import IResponse

from treq.content import content, json_content, text_content


class _Response(proxyForInterface(IResponse)):
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
            history.append(_Response(response.previousResponse))
            response = response.previousResponse

        history.reverse()
        return history
