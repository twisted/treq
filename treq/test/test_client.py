import mock

from twisted.web.client import Agent
from twisted.web.http_headers import Headers

from treq.test.util import TestCase

from treq.client import HTTPClient


class HTTPClientTests(TestCase):
    def setUp(self):
        self.agent = mock.Mock(Agent)
        self.client = HTTPClient(self.agent)

        self.fbp_patcher = mock.patch('treq.client.FileBodyProducer')
        self.FileBodyProducer = self.fbp_patcher.start()
        self.addCleanup(self.fbp_patcher.stop)

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
