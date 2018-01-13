# -*- coding: utf-8 -*-
import mock

from twisted.python.failure import Failure

from twisted.trial.unittest import TestCase
from twisted.web.http_headers import Headers
from twisted.web.client import ResponseDone, ResponseFailed
from twisted.web.http import PotentialDataLoss

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
        Header parsing is robust against unicode header names and values.
        """
        self.response.headers = Headers({
            b'Content-Type': [
                u'text/plain; charset="UTF-16BE"; u=ᛃ'.encode('utf-8')],
            u'Coördination'.encode('iso-8859-1'): [
                u'koʊˌɔrdɪˈneɪʃən'.encode('utf-8')],
        })

        d = text_content(self.response)

        self.protocol.dataReceived(u'ᚠᚡ'.encode('UTF-16BE'))
        self.protocol.connectionLost(Failure(ResponseDone()))

        self.assertEqual(self.successResultOf(d), u'ᚠᚡ')
