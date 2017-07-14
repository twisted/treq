from twisted.trial.unittest import TestCase

from twisted.python.failure import Failure
from twisted.web.client import ResponseDone
from twisted.web.error import Error
from twisted.web.http_headers import Headers

from treq.response import _Response


class FakeResponse(object):
    def __init__(self, code, headers, body=()):
        self.code = code
        self.headers = headers
        self.previousResponse = None
        self._body = body
        self.length = sum(len(c) for c in body)

    def setPreviousResponse(self, response):
        self.previousResponse = response

    def deliverBody(self, protocol):
        for chunk in self._body:
            protocol.dataReceived(chunk)
        protocol.connectionLost(Failure(ResponseDone()))


class ResponseTests(TestCase):
    def test_collect(self):
        original = FakeResponse(200, Headers(), body=[b'foo', b'bar', b'baz'])
        calls = []
        _Response(original, None).collect(calls.append)
        self.assertEqual([b'foo', b'bar', b'baz'], calls)

    def test_content(self):
        original = FakeResponse(200, Headers(), body=[b'foo', b'bar', b'baz'])
        self.assertEqual(
            b'foobarbaz',
            self.successResultOf(_Response(original, None).content()),
        )

    def test_json(self):
        original = FakeResponse(200, Headers(), body=[b'{"foo": ', b'"bar"}'])
        self.assertEqual(
            {'foo': 'bar'},
            self.successResultOf(_Response(original, None).json()),
        )

    def test_text(self):
        headers = Headers({b'content-type': [b'text/plain;charset=utf-8']})
        original = FakeResponse(200, headers, body=[b'\xe2\x98', b'\x83'])
        self.assertEqual(
            u'\u2603',
            self.successResultOf(_Response(original, None).text()),
        )

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


    def test_check_status_ok(self):
        original = FakeResponse(200, Headers(), body=[b''])
        response = _Response(original, None)
        d = response.check_status()
        self.assertEqual(self.successResultOf(d), response)

    def test_check_status_error(self):
        original = FakeResponse(400, Headers(), body=[b'body'])
        response = _Response(original, None)
        error = self.failureResultOf(response.check_status(), Error).value
        self.assertEqual(error.status, b'400')
        self.assertEqual(error.response, b'body')

    def test_check_status_is_available_through_treq(self):
        original = FakeResponse(200, Headers(), body=[b''])
        response = _Response(original, None)
        d = response.check_status()
        self.assertEqual(self.successResultOf(d), response)
