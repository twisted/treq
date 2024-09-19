import unittest
from unittest import mock
from typing import Optional

from twisted.python.failure import Failure

from twisted.internet.error import ConnectionDone
from twisted.trial.unittest import TestCase
from twisted.web.http_headers import Headers
from twisted.web.client import ResponseDone, ResponseFailed
from twisted.web.http import PotentialDataLoss
from twisted.web.resource import Resource
from twisted.web.server import NOT_DONE_YET

from treq import collect, content, json_content, text_content
from treq.content import _encoding_from_headers
from treq.client import _BufferedResponse
from treq.testing import StubTreq


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

        self.protocol.dataReceived(b'{')
        self.protocol.dataReceived(b'"msg": "hell')
        self.protocol.dataReceived(b'o"}')

        self.protocol.connectionLost(Failure(ResponseDone()))

        self.assertEqual(self.successResultOf(d), None)

        self.assertEqual(data, [b'{', b'"msg": "hell', b'o"}'])

    def test_collect_failure(self):
        data = []

        d = collect(self.response, data.append)

        self.protocol.dataReceived(b'foo')

        self.protocol.connectionLost(Failure(ResponseFailed("test failure")))

        self.failureResultOf(d, ResponseFailed)

        self.assertEqual(data, [b'foo'])

    def test_collect_failure_potential_data_loss(self):
        """
        PotentialDataLoss failures are treated as success.
        """
        data = []

        d = collect(self.response, data.append)

        self.protocol.dataReceived(b'foo')

        self.protocol.connectionLost(Failure(PotentialDataLoss()))

        self.assertEqual(self.successResultOf(d), None)

        self.assertEqual(data, [b'foo'])

    def test_collect_0_length(self):
        self.response.length = 0

        d = collect(
            self.response,
            lambda d: self.fail("Unexpectedly called with: {0}".format(d)))

        self.assertEqual(self.successResultOf(d), None)

    def test_content(self):
        d = content(self.response)

        self.protocol.dataReceived(b'foo')
        self.protocol.dataReceived(b'bar')
        self.protocol.connectionLost(Failure(ResponseDone()))

        self.assertEqual(self.successResultOf(d), b'foobar')

    def test_content_cached(self):
        d1 = content(self.response)

        self.protocol.dataReceived(b'foo')
        self.protocol.dataReceived(b'bar')
        self.protocol.connectionLost(Failure(ResponseDone()))

        self.assertEqual(self.successResultOf(d1), b'foobar')

        def _fail_deliverBody(protocol):
            self.fail("deliverBody unexpectedly called.")

        self.response.original.deliverBody.side_effect = _fail_deliverBody

        d3 = content(self.response)

        self.assertEqual(self.successResultOf(d3), b'foobar')

        self.assertNotIdentical(d1, d3)

    def test_content_multiple_waiters(self):
        d1 = content(self.response)
        d2 = content(self.response)

        self.protocol.dataReceived(b'foo')
        self.protocol.connectionLost(Failure(ResponseDone()))

        self.assertEqual(self.successResultOf(d1), b'foo')
        self.assertEqual(self.successResultOf(d2), b'foo')

        self.assertNotIdentical(d1, d2)

    def test_json_content(self):
        self.response.headers = Headers()
        d = json_content(self.response)

        self.protocol.dataReceived(b'{"msg":"hello!"}')
        self.protocol.connectionLost(Failure(ResponseDone()))

        self.assertEqual(self.successResultOf(d), {"msg": "hello!"})

    def test_json_content_unicode(self):
        """
        When Unicode JSON content is received, the JSON text should be
        correctly decoded.
        RFC7159 (8.1): "JSON text SHALL be encoded in UTF-8, UTF-16, or UTF-32.
        The default encoding is UTF-8"
        """
        self.response.headers = Headers()
        d = json_content(self.response)

        self.protocol.dataReceived(u'{"msg":"hëlló!"}'.encode('utf-8'))
        self.protocol.connectionLost(Failure(ResponseDone()))

        self.assertEqual(self.successResultOf(d), {u'msg': u'hëlló!'})

    def test_json_content_utf16(self):
        """
        JSON received is decoded according to the charset given in the
        Content-Type header.
        """
        self.response.headers = Headers({
            b'Content-Type': [b"application/json; charset='UTF-16LE'"],
        })
        d = json_content(self.response)

        self.protocol.dataReceived(u'{"msg":"hëlló!"}'.encode('UTF-16LE'))
        self.protocol.connectionLost(Failure(ResponseDone()))

        self.assertEqual(self.successResultOf(d), {u'msg': u'hëlló!'})

    def test_text_content(self):
        self.response.headers = Headers(
            {b'Content-Type': [b'text/plain; charset=utf-8']})

        d = text_content(self.response)

        self.protocol.dataReceived(b'\xe2\x98\x83')
        self.protocol.connectionLost(Failure(ResponseDone()))

        self.assertEqual(self.successResultOf(d), u'\u2603')

    def test_text_content_default_encoding_no_param(self):
        self.response.headers = Headers(
            {b'Content-Type': [b'text/plain']})

        d = text_content(self.response)

        self.protocol.dataReceived(b'\xa1')
        self.protocol.connectionLost(Failure(ResponseDone()))

        self.assertEqual(self.successResultOf(d), u'\xa1')

    def test_text_content_default_encoding_no_header(self):
        self.response.headers = Headers()

        d = text_content(self.response)

        self.protocol.dataReceived(b'\xa1')
        self.protocol.connectionLost(Failure(ResponseDone()))

        self.assertEqual(self.successResultOf(d), u'\xa1')

    def test_content_application_json_default_encoding(self):
        self.response.headers = Headers(
            {b'Content-Type': [b'application/json']})

        d = text_content(self.response)

        self.protocol.dataReceived(b'gr\xc3\xbcn')
        self.protocol.connectionLost(Failure(ResponseDone()))

        self.assertEqual(self.successResultOf(d), u'grün')

    def test_text_content_unicode_headers(self):
        """
        Parsing of the Content-Type header is robust in the face of
        Unicode gunk in the header value, which is ignored.
        """
        self.response.headers = Headers(
            {
                b"Content-Type": [
                    'text/plain; charset="UTF-16BE"; u=ᛃ'.encode("utf-8")
                ],
            }
        )

        d = text_content(self.response)

        self.protocol.dataReceived(u'ᚠᚡ'.encode('UTF-16BE'))
        self.protocol.connectionLost(Failure(ResponseDone()))

        self.assertEqual(self.successResultOf(d), u'ᚠᚡ')


class UnfinishedResponse(Resource):
    """Write some data, but never finish."""

    isLeaf = True

    def __init__(self):
        Resource.__init__(self)
        # Track how requests finished.
        self.request_finishes = []

    def render(self, request):
        request.write(b"HELLO")
        request.notifyFinish().addBoth(self.request_finishes.append)
        return NOT_DONE_YET


class MoreRealisticContentTests(TestCase):
    """Tests involving less mocking."""

    def test_exception_handling(self):
        """
        An exception in the collector function:

            1. Always gets returned in the result ``Deferred`` from
               ``treq.collect()``.

            2. Closes the transport.
        """
        resource = UnfinishedResponse()
        stub = StubTreq(resource)
        response = self.successResultOf(stub.request("GET", "http://127.0.0.1/"))
        self.assertEqual(response.code, 200)

        def error(data):
            1 / 0

        d = collect(response, error)

        # Exceptions in the collector are passed on to the caller via the
        # response Deferred:
        self.failureResultOf(d, ZeroDivisionError)

        # An exception in the protocol results in the transport for the request
        # being closed.
        stub.flush()
        self.assertEqual(len(resource.request_finishes), 1)
        self.assertIsInstance(resource.request_finishes[0].value, ConnectionDone)


class EncodingFromHeadersTests(unittest.TestCase):
    def _encodingFromContentType(self, content_type: str) -> Optional[str]:
        """
        Invoke `_encoding_from_headers()` for a header value.

        :param content_type: A Content-Type header value.
        :returns: The result of `_encoding_from_headers()`
        """
        h = Headers({"Content-Type": [content_type]})
        return _encoding_from_headers(h)

    def test_rfcExamples(self):
        """
        The examples from RFC 9110 § 8.3.1 are normalized to
        canonical (lowercase) form.
        """
        for example in [
            "text/html;charset=utf-8",
            'Text/HTML;Charset="utf-8"',
            'text/html; charset="utf-8"',
            "text/html;charset=UTF-8",
        ]:
            self.assertEqual("utf-8", self._encodingFromContentType(example))

    def test_multipleParams(self):
        """The charset parameter is extracted even if mixed with other params."""
        for example in [
            "a/b;c=d;charSet=ascii",
            "a/b;c=d;charset=ascii; e=f",
            "a/b;c=d; charsEt=ascii;e=f",
            "a/b;c=d;   charset=ascii;  e=f",
        ]:
            self.assertEqual("ascii", self._encodingFromContentType(example))

    def test_quotedString(self):
        """Any quotes that surround the value of the charset param are removed."""
        self.assertEqual(
            "ascii", self._encodingFromContentType("foo/bar; charset='ASCII'")
        )
        self.assertEqual(
            "shift_jis", self._encodingFromContentType('a/b; charset="Shift_JIS"')
        )

    def test_noCharset(self):
        """None is returned when no valid charset parameter is found."""
        for example in [
            "application/octet-stream",
            "text/plain;charset=",
            "text/plain;charset=''",
            "text/plain;charset=\"'\"",
            "text/plain;charset=🙃",
        ]:
            self.assertIsNone(self._encodingFromContentType(example))
