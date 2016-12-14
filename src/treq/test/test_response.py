from twisted.trial.unittest import TestCase

from twisted import version
from twisted.python.versions import Version

from twisted.web.http_headers import Headers

from treq.response import _Response


skip_history = None

if version < Version("twisted", 13, 1, 0):
    skip_history = "Response history not supported on Twisted < 13.1.0."


class FakeResponse(object):
    def __init__(self, code, headers):
        self.code = code
        self.headers = headers
        self.previousResponse = None

    def setPreviousResponse(self, response):
        self.previousResponse = response


class ResponseTests(TestCase):
    def test_history(self):
        redirect1 = FakeResponse(
            301,
            Headers({'location': ['http://example.com/']})
        )

        redirect2 = FakeResponse(
            302,
            Headers({'location': ['https://example.com/']})
        )
        redirect2.setPreviousResponse(redirect1)

        final = FakeResponse(200, Headers({}))
        final.setPreviousResponse(redirect2)

        wrapper = _Response(final, None)

        history = wrapper.history()

        self.assertEqual(wrapper.code, 200)
        self.assertEqual(history[0].code, 301)
        self.assertEqual(history[1].code, 302)

    def test_no_history(self):
        wrapper = _Response(FakeResponse(200, Headers({})), None)
        self.assertEqual(wrapper.history(), [])

    if skip_history:
        test_history.skip = skip_history
        test_no_history.skip = skip_history

    def test_history_notimplemented(self):
        wrapper = _Response(FakeResponse(200, Headers({})), None)
        self.assertRaises(NotImplementedError, wrapper.history)

    if not skip_history:
        test_history_notimplemented.skip = "History supported."
