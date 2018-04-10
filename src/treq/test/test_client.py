# -*- encoding: utf-8 -*-
from io import BytesIO

import mock

from twisted.internet.defer import Deferred, succeed, CancelledError
from twisted.internet.protocol import Protocol

from twisted.python.failure import Failure

from twisted.trial.unittest import TestCase

from twisted.web.client import Agent, ResponseFailed
from twisted.web.http_headers import Headers

from treq.test.util import with_clock

from treq.client import (
    HTTPClient, _BodyBufferingProtocol, _BufferedResponse
)


class HTTPClientTests(TestCase):
    def setUp(self):
        self.agent = mock.Mock(Agent)
        self.client = HTTPClient(self.agent)

        self.fbp_patcher = mock.patch('treq.client.FileBodyProducer')
        self.FileBodyProducer = self.fbp_patcher.start()
        self.addCleanup(self.fbp_patcher.stop)

        self.mbp_patcher = mock.patch('treq.multipart.MultiPartProducer')
        self.MultiPartProducer = self.mbp_patcher.start()
        self.addCleanup(self.mbp_patcher.stop)

    def assertBody(self, expected):
        body = self.FileBodyProducer.mock_calls[0][1][0]
        self.assertEqual(body.read(), expected)

    def test_post(self):
        self.client.post('http://example.com/')
        self.agent.request.assert_called_once_with(
            b'POST', b'http://example.com/',
            Headers({b'accept-encoding': [b'gzip']}), None)

    def test_request_uri_idn(self):
        self.client.request('GET', u'http://č.net')
        self.agent.request.assert_called_once_with(
            b'GET', b'http://xn--bea.net',
            Headers({b'accept-encoding': [b'gzip']}), None)

    def test_request_case_insensitive_methods(self):
        self.client.request('gEt', 'http://example.com/')
        self.agent.request.assert_called_once_with(
            b'GET', b'http://example.com/',
            Headers({b'accept-encoding': [b'gzip']}), None)

    def test_request_query_params(self):
        self.client.request('GET', 'http://example.com/',
                            params={'foo': ['bar']})

        self.agent.request.assert_called_once_with(
            b'GET', b'http://example.com/?foo=bar',
            Headers({b'accept-encoding': [b'gzip']}), None)

    def test_request_tuple_query_values(self):
        self.client.request('GET', 'http://example.com/',
                            params={'foo': ('bar',)})

        self.agent.request.assert_called_once_with(
            b'GET', b'http://example.com/?foo=bar',
            Headers({b'accept-encoding': [b'gzip']}), None)

    def test_request_merge_query_params(self):
        self.client.request('GET', 'http://example.com/?baz=bax',
                            params={'foo': ['bar', 'baz']})

        self.agent.request.assert_called_once_with(
            b'GET', b'http://example.com/?baz=bax&foo=bar&foo=baz',
            Headers({b'accept-encoding': [b'gzip']}), None)

    def test_request_merge_tuple_query_params(self):
        self.client.request('GET', 'http://example.com/?baz=bax',
                            params=[('foo', 'bar')])

        self.agent.request.assert_called_once_with(
            b'GET', b'http://example.com/?baz=bax&foo=bar',
            Headers({b'accept-encoding': [b'gzip']}), None)

    def test_request_dict_single_value_query_params(self):
        self.client.request('GET', 'http://example.com/',
                            params={'foo': 'bar'})

        self.agent.request.assert_called_once_with(
            b'GET', b'http://example.com/?foo=bar',
            Headers({b'accept-encoding': [b'gzip']}), None)

    def test_request_data_dict(self):
        self.client.request('POST', 'http://example.com/',
                            data={'foo': ['bar', 'baz']})

        self.agent.request.assert_called_once_with(
            b'POST', b'http://example.com/',
            Headers({b'Content-Type': [b'application/x-www-form-urlencoded'],
                     b'accept-encoding': [b'gzip']}),
            self.FileBodyProducer.return_value)

        self.assertBody(b'foo=bar&foo=baz')

    def test_request_data_single_dict(self):
        self.client.request('POST', 'http://example.com/',
                            data={'foo': 'bar'})

        self.agent.request.assert_called_once_with(
            b'POST', b'http://example.com/',
            Headers({b'Content-Type': [b'application/x-www-form-urlencoded'],
                     b'accept-encoding': [b'gzip']}),
            self.FileBodyProducer.return_value)

        self.assertBody(b'foo=bar')

    def test_request_data_tuple(self):
        self.client.request('POST', 'http://example.com/',
                            data=[('foo', 'bar')])

        self.agent.request.assert_called_once_with(
            b'POST', b'http://example.com/',
            Headers({b'Content-Type': [b'application/x-www-form-urlencoded'],
                     b'accept-encoding': [b'gzip']}),
            self.FileBodyProducer.return_value)

        self.assertBody(b'foo=bar')

    def test_request_data_file(self):
        temp_fn = self.mktemp()

        with open(temp_fn, "wb") as temp_file:
            temp_file.write(b'hello')

        self.client.request('POST', 'http://example.com/',
                            data=open(temp_fn, 'rb'))

        self.agent.request.assert_called_once_with(
            b'POST', b'http://example.com/',
            Headers({b'accept-encoding': [b'gzip']}),
            self.FileBodyProducer.return_value)

        self.assertBody(b'hello')

    def test_request_json_dict(self):
        self.client.request('POST', 'http://example.com/', json={'foo': 'bar'})
        self.agent.request.assert_called_once_with(
            b'POST', b'http://example.com/',
            Headers({b'Content-Type': [b'application/json; charset=UTF-8'],
                     b'accept-encoding': [b'gzip']}),
            self.FileBodyProducer.return_value)
        self.assertBody(b'{"foo":"bar"}')

    def test_request_json_tuple(self):
        self.client.request('POST', 'http://example.com/', json=('foo', 1))
        self.agent.request.assert_called_once_with(
            b'POST', b'http://example.com/',
            Headers({b'Content-Type': [b'application/json; charset=UTF-8'],
                     b'accept-encoding': [b'gzip']}),
            self.FileBodyProducer.return_value)
        self.assertBody(b'["foo",1]')

    def test_request_json_number(self):
        self.client.request('POST', 'http://example.com/', json=1.)
        self.agent.request.assert_called_once_with(
            b'POST', b'http://example.com/',
            Headers({b'Content-Type': [b'application/json; charset=UTF-8'],
                     b'accept-encoding': [b'gzip']}),
            self.FileBodyProducer.return_value)
        self.assertBody(b'1.0')

    def test_request_json_string(self):
        self.client.request('POST', 'http://example.com/', json='hello')
        self.agent.request.assert_called_once_with(
            b'POST', b'http://example.com/',
            Headers({b'Content-Type': [b'application/json; charset=UTF-8'],
                     b'accept-encoding': [b'gzip']}),
            self.FileBodyProducer.return_value)
        self.assertBody(b'"hello"')

    def test_request_json_bool(self):
        self.client.request('POST', 'http://example.com/', json=True)
        self.agent.request.assert_called_once_with(
            b'POST', b'http://example.com/',
            Headers({b'Content-Type': [b'application/json; charset=UTF-8'],
                     b'accept-encoding': [b'gzip']}),
            self.FileBodyProducer.return_value)
        self.assertBody(b'true')

    def test_request_json_none(self):
        self.client.request('POST', 'http://example.com/', json=None)
        self.agent.request.assert_called_once_with(
            b'POST', b'http://example.com/',
            Headers({b'Content-Type': [b'application/json; charset=UTF-8'],
                     b'accept-encoding': [b'gzip']}),
            self.FileBodyProducer.return_value)
        self.assertBody(b'null')

    @mock.patch('treq.client.uuid.uuid4', mock.Mock(return_value="heyDavid"))
    def test_request_no_name_attachment(self):

        self.client.request(
            'POST', 'http://example.com/', files={"name": BytesIO(b"hello")})

        self.agent.request.assert_called_once_with(
            b'POST', b'http://example.com/',
            Headers({
                b'accept-encoding': [b'gzip'],
                b'Content-Type': [b'multipart/form-data; boundary=heyDavid']}),
            self.MultiPartProducer.return_value)

        FP = self.FileBodyProducer.return_value
        self.assertEqual(
            mock.call(
                [('name', (None, 'application/octet-stream', FP))],
                boundary=b'heyDavid'),
            self.MultiPartProducer.call_args)

    @mock.patch('treq.client.uuid.uuid4', mock.Mock(return_value="heyDavid"))
    def test_request_named_attachment(self):

        self.client.request(
            'POST', 'http://example.com/', files={
                "name": ('image.jpg', BytesIO(b"hello"))})

        self.agent.request.assert_called_once_with(
            b'POST', b'http://example.com/',
            Headers({
                b'accept-encoding': [b'gzip'],
                b'Content-Type': [b'multipart/form-data; boundary=heyDavid']}),
            self.MultiPartProducer.return_value)

        FP = self.FileBodyProducer.return_value
        self.assertEqual(
            mock.call(
                [('name', ('image.jpg', 'image/jpeg', FP))],
                boundary=b'heyDavid'),
            self.MultiPartProducer.call_args)

    @mock.patch('treq.client.uuid.uuid4', mock.Mock(return_value="heyDavid"))
    def test_request_named_attachment_and_ctype(self):

        self.client.request(
            'POST', 'http://example.com/', files={
                "name": ('image.jpg', 'text/plain', BytesIO(b"hello"))})

        self.agent.request.assert_called_once_with(
            b'POST', b'http://example.com/',
            Headers({
                b'accept-encoding': [b'gzip'],
                b'Content-Type': [b'multipart/form-data; boundary=heyDavid']}),
            self.MultiPartProducer.return_value)

        FP = self.FileBodyProducer.return_value
        self.assertEqual(
            mock.call(
                [('name', ('image.jpg', 'text/plain', FP))],
                boundary=b'heyDavid'),
            self.MultiPartProducer.call_args)

    @mock.patch('treq.client.uuid.uuid4', mock.Mock(return_value="heyDavid"))
    def test_request_mixed_params(self):

        class NamedFile(BytesIO):
            def __init__(self, val):
                BytesIO.__init__(self, val)
                self.name = "image.png"

        self.client.request(
            'POST', 'http://example.com/',
            data=[("a", "b"), ("key", "val")],
            files=[
                ("file1", ('image.jpg', BytesIO(b"hello"))),
                ("file2", NamedFile(b"yo"))])

        self.agent.request.assert_called_once_with(
            b'POST', b'http://example.com/',
            Headers({
                b'accept-encoding': [b'gzip'],
                b'Content-Type': [b'multipart/form-data; boundary=heyDavid']}),
            self.MultiPartProducer.return_value)

        FP = self.FileBodyProducer.return_value
        self.assertEqual(
            mock.call([
                ('a', 'b'),
                ('key', 'val'),
                ('file1', ('image.jpg', 'image/jpeg', FP)),
                ('file2', ('image.png', 'image/png', FP))],
                boundary=b'heyDavid'),
            self.MultiPartProducer.call_args)

    @mock.patch('treq.client.uuid.uuid4', mock.Mock(return_value="heyDavid"))
    def test_request_mixed_params_dict(self):

        self.client.request(
            'POST', 'http://example.com/',
            data={"key": "a", "key2": "b"},
            files={"file1": BytesIO(b"hey")})

        self.agent.request.assert_called_once_with(
            b'POST', b'http://example.com/',
            Headers({
                b'accept-encoding': [b'gzip'],
                b'Content-Type': [b'multipart/form-data; boundary=heyDavid']}),
            self.MultiPartProducer.return_value)

        FP = self.FileBodyProducer.return_value
        self.assertEqual(
            mock.call([
                ('key', 'a'),
                ('key2', 'b'),
                ('file1', (None, 'application/octet-stream', FP))],
                boundary=b'heyDavid'),
            self.MultiPartProducer.call_args)

    def test_request_unsupported_params_combination(self):
        self.assertRaises(ValueError,
                          self.client.request,
                          'POST', 'http://example.com/',
                          data=BytesIO(b"yo"),
                          files={"file1": BytesIO(b"hey")})

    def test_request_dict_headers(self):
        self.client.request('GET', 'http://example.com/', headers={
            'User-Agent': 'treq/0.1dev',
            'Accept': ['application/json', 'text/plain']
        })

        self.agent.request.assert_called_once_with(
            b'GET', b'http://example.com/',
            Headers({b'User-Agent': [b'treq/0.1dev'],
                     b'accept-encoding': [b'gzip'],
                     b'Accept': [b'application/json', b'text/plain']}),
            None)

    @with_clock
    def test_request_timeout_fired(self, clock):
        """
        Verify the request is cancelled if a response is not received
        within specified timeout period.
        """
        self.agent.request.return_value = d = Deferred()
        self.client.request('GET', 'http://example.com', timeout=2)

        # simulate we haven't gotten a response within timeout seconds
        clock.advance(3)

        # a deferred should have been cancelled
        self.failureResultOf(d, CancelledError)

    @with_clock
    def test_request_timeout_cancelled(self, clock):
        """
        Verify timeout is cancelled if a response is received before
        timeout period elapses.
        """
        self.agent.request.return_value = d = Deferred()
        self.client.request('GET', 'http://example.com', timeout=2)

        # simulate a response
        d.callback(mock.Mock(code=200, headers=Headers({})))

        # now advance the clock but since we already got a result,
        # a cancellation timer should have been cancelled
        clock.advance(3)

        self.successResultOf(d)

    def test_response_is_buffered(self):
        response = mock.Mock(deliverBody=mock.Mock(),
                             headers=Headers({}))

        self.agent.request.return_value = succeed(response)

        d = self.client.get('http://www.example.com')

        result = self.successResultOf(d)

        protocol = mock.Mock(Protocol)
        result.deliverBody(protocol)
        self.assertEqual(response.deliverBody.call_count, 1)

        result.deliverBody(protocol)
        self.assertEqual(response.deliverBody.call_count, 1)

    def test_response_buffering_is_disabled_with_unbufferred_arg(self):
        response = mock.Mock(headers=Headers({}))

        self.agent.request.return_value = succeed(response)

        d = self.client.get('http://www.example.com', unbuffered=True)

        # YOLO public attribute.
        self.assertEqual(self.successResultOf(d).original, response)

    def test_request_post_redirect_denied(self):
        response = mock.Mock(code=302, headers=Headers({'Location': ['/']}))
        self.agent.request.return_value = succeed(response)
        d = self.client.post('http://www.example.com')
        self.failureResultOf(d, ResponseFailed)

    def test_request_browser_like_redirects(self):
        response = mock.Mock(code=302, headers=Headers({'Location': ['/']}))

        self.agent.request.return_value = succeed(response)

        raw = mock.Mock(return_value=[])
        final_resp = mock.Mock(code=200, headers=mock.Mock(getRawHeaders=raw))
        with mock.patch('twisted.web.client.RedirectAgent._handleRedirect',
                        return_value=final_resp):
            d = self.client.post('http://www.google.com',
                                 browser_like_redirects=True,
                                 unbuffered=True)

        self.assertEqual(self.successResultOf(d).original, final_resp)


class BodyBufferingProtocolTests(TestCase):
    def test_buffers_data(self):
        buffer = []
        protocol = _BodyBufferingProtocol(
            mock.Mock(Protocol),
            buffer,
            None
        )

        protocol.dataReceived("foo")
        self.assertEqual(buffer, ["foo"])

        protocol.dataReceived("bar")
        self.assertEqual(buffer, ["foo", "bar"])

    def test_propagates_data_to_destination(self):
        destination = mock.Mock(Protocol)
        protocol = _BodyBufferingProtocol(
            destination,
            [],
            None
        )

        protocol.dataReceived(b"foo")
        destination.dataReceived.assert_called_once_with(b"foo")

        protocol.dataReceived(b"bar")
        destination.dataReceived.assert_called_with(b"bar")

    def test_fires_finished_deferred(self):
        finished = Deferred()
        protocol = _BodyBufferingProtocol(
            mock.Mock(Protocol),
            [],
            finished
        )

        class TestResponseDone(Exception):
            pass

        protocol.connectionLost(TestResponseDone())

        self.failureResultOf(finished, TestResponseDone)

    def test_propogates_connectionLost_reason(self):
        destination = mock.Mock(Protocol)
        protocol = _BodyBufferingProtocol(
            destination,
            [],
            Deferred().addErrback(lambda ign: None)
        )

        class TestResponseDone(Exception):
            pass

        reason = TestResponseDone()
        protocol.connectionLost(reason)
        destination.connectionLost.assert_called_once_with(reason)


class BufferedResponseTests(TestCase):
    def test_wraps_protocol(self):
        wrappers = []
        wrapped = mock.Mock(Protocol)
        response = mock.Mock(deliverBody=mock.Mock(wraps=wrappers.append))

        br = _BufferedResponse(response)

        br.deliverBody(wrapped)
        response.deliverBody.assert_called_once_with(wrappers[0])
        self.assertNotEqual(wrapped, wrappers[0])

    def test_concurrent_receivers(self):
        wrappers = []
        wrapped = mock.Mock(Protocol)
        unwrapped = mock.Mock(Protocol)
        response = mock.Mock(deliverBody=mock.Mock(wraps=wrappers.append))

        br = _BufferedResponse(response)

        br.deliverBody(wrapped)
        br.deliverBody(unwrapped)
        response.deliverBody.assert_called_once_with(wrappers[0])

        wrappers[0].dataReceived(b"foo")
        wrapped.dataReceived.assert_called_once_with(b"foo")

        self.assertEqual(unwrapped.dataReceived.call_count, 0)

        class TestResponseDone(Exception):
            pass

        done = Failure(TestResponseDone())

        wrappers[0].connectionLost(done)
        wrapped.connectionLost.assert_called_once_with(done)
        unwrapped.dataReceived.assert_called_once_with(b"foo")
        unwrapped.connectionLost.assert_called_once_with(done)

    def test_receiver_after_finished(self):
        wrappers = []
        finished = mock.Mock(Protocol)

        response = mock.Mock(deliverBody=mock.Mock(wraps=wrappers.append))

        br = _BufferedResponse(response)
        br.deliverBody(mock.Mock(Protocol))
        wrappers[0].dataReceived(b"foo")

        class TestResponseDone(Exception):
            pass

        done = Failure(TestResponseDone())

        wrappers[0].connectionLost(done)

        br.deliverBody(finished)

        finished.dataReceived.assert_called_once_with(b"foo")
        finished.connectionLost.assert_called_once_with(done)
