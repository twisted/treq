import json

from twisted.trial.unittest import TestCase
from twisted.internet.defer import inlineCallbacks

import treq

HTTPBIN_URL = "http://httpbin.org"
HTTPSBIN_URL = "https://httpbin.org"

debug = True


def print_response(response):
    if debug:
        print
        print '---'
        print response.version, response.code, response.phrase
        print response.headers
        print
        if hasattr(response, 'body'):
            print response.body
        print '---'


def with_baseurl(method, baseurl):
    def _request(self, url, *args, **kwargs):
        return method(baseurl + url, *args, **kwargs)

    return _request


class TreqIntegrationTests(TestCase):
    get = with_baseurl(treq.get, HTTPBIN_URL)
    head = with_baseurl(treq.head, HTTPBIN_URL)
    post = with_baseurl(treq.post, HTTPBIN_URL)
    put = with_baseurl(treq.put, HTTPBIN_URL)
    delete = with_baseurl(treq.delete, HTTPBIN_URL)

    def assert_data(self, response, expected_data):
        body = json.loads(response.body)
        self.assertIn('data', body)
        self.assertEqual(body['data'], expected_data)

    def assert_sent_header(self, response, header, expected_value):
        body = json.loads(response.body)
        self.assertIn(header, body['headers'])
        self.assertEqual(body['headers'][header], expected_value)

    @inlineCallbacks
    def test_get(self):
        response = yield self.get('/get')
        self.assertEqual(response.code, 200)
        print_response(response)

    @inlineCallbacks
    def test_get_headers(self):
        response = yield self.get('/get', {'X-Blah': ['Foo']})
        self.assertEqual(response.code, 200)
        self.assert_sent_header(response, 'X-Blah', 'Foo')
        print_response(response)

    @inlineCallbacks
    def test_head(self):
        response = yield self.head('/get')
        self.assertEqual(response.body, '')
        print_response(response)

    @inlineCallbacks
    def test_post(self):
        response = yield self.post('/post', body='Hello!')
        self.assertEqual(response.code, 200)
        self.assert_data(response, 'Hello!')
        print_response(response)

    @inlineCallbacks
    def test_post_headers(self):
        response = yield self.post(
            '/post',
            {'Content-Type': ['application/json']},
            '{msg: "Hello!"}'
        )

        self.assertEqual(response.code, 200)
        self.assert_sent_header(response, 'Content-Type', 'application/json')
        self.assert_data(response, '{msg: "Hello!"}')

        print_response(response)

    @inlineCallbacks
    def test_put(self):
        response = yield self.put('/put', body='Hello!')
        print_response(response)

    @inlineCallbacks
    def test_delete(self):
        response = yield self.delete('/delete')
        self.assertEqual(response.code, 200)
        print_response(response)


class HTTPSTreqIntegrationTests(TreqIntegrationTests):
    get = with_baseurl(treq.get, HTTPSBIN_URL)
    head = with_baseurl(treq.head, HTTPSBIN_URL)
    post = with_baseurl(treq.post, HTTPSBIN_URL)
    put = with_baseurl(treq.put, HTTPSBIN_URL)
    delete = with_baseurl(treq.delete, HTTPSBIN_URL)
