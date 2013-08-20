from StringIO import StringIO

import mock

from twisted.web.client import Agent
from twisted.web.http_headers import Headers

from treq.test.util import TestCase, with_clock

from treq.client import HTTPClient


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

    def test_request_case_insensitive_methods(self):
        self.client.request('gEt', 'http://example.com/')
        self.agent.request.assert_called_once_with(
            'GET', 'http://example.com/',
            headers=Headers({}), bodyProducer=None)

    def test_request_query_params(self):
        self.client.request('GET', 'http://example.com/',
                            params={'foo': ['bar']})

        self.agent.request.assert_called_once_with(
            'GET', 'http://example.com/?foo=bar',
            headers=Headers({}), bodyProducer=None)

    def test_request_tuple_query_values(self):
        self.client.request('GET', 'http://example.com/',
                            params={'foo': ('bar',)})

        self.agent.request.assert_called_once_with(
            'GET', 'http://example.com/?foo=bar',
            headers=Headers({}), bodyProducer=None)

    def test_request_merge_query_params(self):
        self.client.request('GET', 'http://example.com/?baz=bax',
                            params={'foo': ['bar', 'baz']})

        self.agent.request.assert_called_once_with(
            'GET', 'http://example.com/?baz=bax&foo=bar&foo=baz',
            headers=Headers({}), bodyProducer=None)

    def test_request_merge_tuple_query_params(self):
        self.client.request('GET', 'http://example.com/?baz=bax',
                            params=[('foo', 'bar')])

        self.agent.request.assert_called_once_with(
            'GET', 'http://example.com/?baz=bax&foo=bar',
            headers=Headers({}), bodyProducer=None)

    def test_request_dict_single_value_query_params(self):
        self.client.request('GET', 'http://example.com/',
                            params={'foo': 'bar'})

        self.agent.request.assert_called_once_with(
            'GET', 'http://example.com/?foo=bar',
            headers=Headers({}), bodyProducer=None)

    def test_request_data_dict(self):
        self.client.request('POST', 'http://example.com/',
                            data={'foo': ['bar', 'baz']})

        self.agent.request.assert_called_once_with(
            'POST', 'http://example.com/',
            headers=Headers(
                {'Content-Type': ['application/x-www-form-urlencoded']}),
            bodyProducer=self.FileBodyProducer.return_value)

        self.assertBody('foo=bar&foo=baz')

    def test_request_data_single_dict(self):
        self.client.request('POST', 'http://example.com/',
                            data={'foo': 'bar'})

        self.agent.request.assert_called_once_with(
            'POST', 'http://example.com/',
            headers=Headers(
                {'Content-Type': ['application/x-www-form-urlencoded']}),
            bodyProducer=self.FileBodyProducer.return_value)

        self.assertBody('foo=bar')

    def test_request_data_tuple(self):
        self.client.request('POST', 'http://example.com/',
                            data=[('foo', 'bar')])

        self.agent.request.assert_called_once_with(
            'POST', 'http://example.com/',
            headers=Headers(
                {'Content-Type': ['application/x-www-form-urlencoded']}),
            bodyProducer=self.FileBodyProducer.return_value)

        self.assertBody('foo=bar')

    def test_request_data_file(self):
        temp_fn = self.mktemp()

        with open(temp_fn, "w") as temp_file:
            temp_file.write('hello')

        self.client.request('POST', 'http://example.com/', data=file(temp_fn))

        self.agent.request.assert_called_once_with(
            'POST', 'http://example.com/',
            headers=Headers({}),
            bodyProducer=self.FileBodyProducer.return_value)

        self.assertBody('hello')

    @mock.patch('treq.client.uuid.uuid4', mock.Mock(return_value="heyDavid"))
    def test_request_no_name_attachment(self):

        self.client.request(
            'POST', 'http://example.com/', files={"name": StringIO("hello")})

        self.agent.request.assert_called_once_with(
            'POST', 'http://example.com/',
            headers=Headers({
                    'Content-Type': [
                        'multipart/form-data; boundary=heyDavid']}),
            bodyProducer=self.MultiPartProducer.return_value)

        FP = self.FileBodyProducer.return_value
        self.assertEqual(
            mock.call(
                [('name', (None, 'application/octet-stream', FP))],
                boundary='heyDavid'),
            self.MultiPartProducer.call_args)

    @mock.patch('treq.client.uuid.uuid4', mock.Mock(return_value="heyDavid"))
    def test_request_named_attachment(self):

        self.client.request(
            'POST', 'http://example.com/', files={
                "name": ('image.jpg', StringIO("hello"))})

        self.agent.request.assert_called_once_with(
            'POST', 'http://example.com/',
            headers=Headers({
                    'Content-Type': [
                        'multipart/form-data; boundary=heyDavid']}),
            bodyProducer=self.MultiPartProducer.return_value)

        FP = self.FileBodyProducer.return_value
        self.assertEqual(
            mock.call(
                [('name', ('image.jpg', 'image/jpeg', FP))],
                boundary='heyDavid'),
            self.MultiPartProducer.call_args)

    @mock.patch('treq.client.uuid.uuid4', mock.Mock(return_value="heyDavid"))
    def test_request_named_attachment_and_ctype(self):

        self.client.request(
            'POST', 'http://example.com/', files={
                "name": ('image.jpg', 'text/plain', StringIO("hello"))})

        self.agent.request.assert_called_once_with(
            'POST', 'http://example.com/',
            headers=Headers({
                    'Content-Type': [
                        'multipart/form-data; boundary=heyDavid']}),
            bodyProducer=self.MultiPartProducer.return_value)

        FP = self.FileBodyProducer.return_value
        self.assertEqual(
            mock.call(
                [('name', ('image.jpg', 'text/plain', FP))],
                boundary='heyDavid'),
            self.MultiPartProducer.call_args)

    @mock.patch('treq.client.uuid.uuid4', mock.Mock(return_value="heyDavid"))
    def test_request_mixed_params(self):

        class NamedFile(StringIO):
            def __init__(self, val):
                StringIO.__init__(self, val)
                self.name = "image.png"

        self.client.request(
            'POST', 'http://example.com/',
            data=[("a", "b"), ("key", "val")],
            files=[
                ("file1", ('image.jpg', StringIO("hello"))),
                ("file2", NamedFile("yo"))])

        self.agent.request.assert_called_once_with(
            'POST', 'http://example.com/',
            headers=Headers({
                    'Content-Type': [
                        'multipart/form-data; boundary=heyDavid']}),
            bodyProducer=self.MultiPartProducer.return_value)

        FP = self.FileBodyProducer.return_value
        self.assertEqual(
            mock.call([
                ('a', 'b'),
                ('key', 'val'),
                ('file1', ('image.jpg', 'image/jpeg', FP)),
                ('file2', ('image.png', 'image/png', FP))],
                boundary='heyDavid'),
            self.MultiPartProducer.call_args)

    @mock.patch('treq.client.uuid.uuid4', mock.Mock(return_value="heyDavid"))
    def test_request_mixed_params_dict(self):

        self.client.request(
            'POST', 'http://example.com/',
            data={"key": "a", "key2": "b"},
            files={"file1": StringIO("hey")})

        self.agent.request.assert_called_once_with(
            'POST', 'http://example.com/',
            headers=Headers({
                    'Content-Type': [
                        'multipart/form-data; boundary=heyDavid']}),
            bodyProducer=self.MultiPartProducer.return_value)

        FP = self.FileBodyProducer.return_value
        self.assertEqual(
            mock.call([
                ('key', 'a'),
                ('key2', 'b'),
                ('file1', (None, 'application/octet-stream', FP))],
                boundary='heyDavid'),
            self.MultiPartProducer.call_args)

    def test_request_unsupported_params_combination(self):
        self.assertRaises(ValueError,
                          self.client.request,
                          'POST', 'http://example.com/',
                          data=StringIO("yo"),
                          files={"file1": StringIO("hey")})

    def test_request_dict_headers(self):
        self.client.request('GET', 'http://example.com/', headers={
            'User-Agent': 'treq/0.1dev',
            'Accept': ['application/json', 'text/plain']
        })

        self.agent.request.assert_called_once_with(
            'GET', 'http://example.com/',
            headers=Headers({'User-Agent': ['treq/0.1dev'],
                             'Accept': ['application/json', 'text/plain']}),
            bodyProducer=None)

    @with_clock
    def test_request_timeout_fired(self, clock):
        """
        Verify the request is cancelled if a response is not received
        within specified timeout period.
        """
        self.client.request('GET', 'http://example.com', timeout=2)

        # simulate we haven't gotten a response within timeout seconds
        clock.advance(3)
        deferred = self.agent.request.return_value

        # a deferred should have been cancelled
        self.assertTrue(deferred.cancel.called)

    @with_clock
    def test_request_timeout_cancelled(self, clock):
        """
        Verify timeout is cancelled if a response is received before
        timeout period elapses.
        """
        self.client.request('GET', 'http://example.com', timeout=2)

        # simulate a response
        deferred = self.agent.request.return_value
        gotResult = deferred.addBoth.call_args[0][0]
        gotResult('result')

        # now advance the clock but since we already got a result,
        # a cancellation timer should have been cancelled
        clock.advance(3)
        self.assertFalse(deferred.cancel.called)
