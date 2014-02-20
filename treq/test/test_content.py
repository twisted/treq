import mock

from twisted.python.failure import Failure

from twisted.web.http_headers import Headers
from twisted.web.client import ResponseDone, ResponseFailed
from twisted.web.http import PotentialDataLoss

from treq.test.util import TestCase

from treq import collect, content, json_content, text_content
from treq.client import _BufferedResponse


class ContentTests(TestCase):
    def setUp(self):
        self.response = mock.Mock()
        self.protocol = None

        def deliverBody(protocol):
            self.protocol = protocol

        self.response.deliverBody.side_effect = deliverBody
        self.response = _BufferedResponse(self.response)

    def test_collect(self):
        data = []

        d = collect(self.response, data.append)

        self.protocol.dataReceived('{')
        self.protocol.dataReceived('"msg": "hell')
        self.protocol.dataReceived('o"}')

        self.protocol.connectionLost(Failure(ResponseDone()))

        self.assertEqual(self.successResultOf(d), None)

        self.assertEqual(data, ['{', '"msg": "hell', 'o"}'])

    def test_collect_failure(self):
        data = []

        d = collect(self.response, data.append)

        self.protocol.dataReceived('foo')

        self.protocol.connectionLost(Failure(ResponseFailed("test failure")))

        self.failureResultOf(d, ResponseFailed)

        self.assertEqual(data, ['foo'])

    def test_collect_failure_potential_data_loss(self):
        """
        PotentialDataLoss failures are treated as success.
        """
        data = []

        d = collect(self.response, data.append)

        self.protocol.dataReceived('foo')

        self.protocol.connectionLost(Failure(PotentialDataLoss()))

        self.assertEqual(self.successResultOf(d), None)

        self.assertEqual(data, ['foo'])

    def test_collect_0_length(self):
        self.response.length = 0

        d = collect(
            self.response,
            lambda d: self.fail("Unexpectedly called with: {0}".format(d)))

        self.assertEqual(self.successResultOf(d), None)

    def test_content(self):
        d = content(self.response)

        self.protocol.dataReceived('foo')
        self.protocol.dataReceived('bar')
        self.protocol.connectionLost(Failure(ResponseDone()))

        self.assertEqual(self.successResultOf(d), 'foobar')

    def test_content_cached(self):
        d1 = content(self.response)

        self.protocol.dataReceived('foo')
        self.protocol.dataReceived('bar')
        self.protocol.connectionLost(Failure(ResponseDone()))

        self.assertEqual(self.successResultOf(d1), 'foobar')

        def _fail_deliverBody(protocol):
            self.fail("deliverBody unexpectedly called.")

        self.response.original.deliverBody.side_effect = _fail_deliverBody

        d3 = content(self.response)

        self.assertEqual(self.successResultOf(d3), 'foobar')

        self.assertNotIdentical(d1, d3)

    def test_content_multiple_waiters(self):
        d1 = content(self.response)
        d2 = content(self.response)

        self.protocol.dataReceived('foo')
        self.protocol.connectionLost(Failure(ResponseDone()))

        self.assertEqual(self.successResultOf(d1), 'foo')
        self.assertEqual(self.successResultOf(d2), 'foo')

        self.assertNotIdentical(d1, d2)

    def test_json_content(self):
        d = json_content(self.response)

        self.protocol.dataReceived('{"msg":"hello!"}')
        self.protocol.connectionLost(Failure(ResponseDone()))

        self.assertEqual(self.successResultOf(d), {"msg": "hello!"})

    def test_text_content(self):
        self.response.headers = Headers(
            {'Content-Type': ['text/plain; charset=utf-8']})

        d = text_content(self.response)

        self.protocol.dataReceived('\xe2\x98\x83')
        self.protocol.connectionLost(Failure(ResponseDone()))

        self.assertEqual(self.successResultOf(d), u'\u2603')

    def test_text_content_default_encoding_no_param(self):
        self.response.headers = Headers(
            {'Content-Type': ['text/plain']})

        d = text_content(self.response)

        self.protocol.dataReceived('\xa1')
        self.protocol.connectionLost(Failure(ResponseDone()))

        self.assertEqual(self.successResultOf(d), u'\xa1')

    def test_text_content_default_encoding_no_header(self):
        self.response.headers = Headers()

        d = text_content(self.response)

        self.protocol.dataReceived('\xa1')
        self.protocol.connectionLost(Failure(ResponseDone()))

        self.assertEqual(self.successResultOf(d), u'\xa1')
