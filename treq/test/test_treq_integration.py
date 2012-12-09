from twisted.trial.unittest import TestCase
from twisted.internet.defer import inlineCallbacks

from treq.test.util import is_pypy

import treq

HTTPBIN_URL = "http://httpbin.org"
HTTPSBIN_URL = "https://httpbin.org"

def with_baseurl(method):
    def _request(self, url, *args, **kwargs):
        return method(self.baseurl + url, *args, persistent=False, **kwargs)

    return _request


class TreqIntegrationTests(TestCase):
    baseurl = HTTPBIN_URL
    get = with_baseurl(treq.get)
    head = with_baseurl(treq.head)
    post = with_baseurl(treq.post)
    put = with_baseurl(treq.put)
    delete = with_baseurl(treq.delete)

    @inlineCallbacks
    def assert_data(self, response, expected_data):
        body = yield treq.json_content(response)
        self.assertIn('data', body)
        self.assertEqual(body['data'], expected_data)

    @inlineCallbacks
    def assert_sent_header(self, response, header, expected_value):
        body = yield treq.json_content(response)
        self.assertIn(header, body['headers'])
        self.assertEqual(body['headers'][header], expected_value)

    @inlineCallbacks
    def test_get(self):
        response = yield self.get('/get')
        self.assertEqual(response.code, 200)

    @inlineCallbacks
    def test_get_headers(self):
        response = yield self.get('/get', {'X-Blah': ['Foo', 'Bar']})
        self.assertEqual(response.code, 200)
        yield self.assert_sent_header(response, 'X-Blah', 'Foo, Bar')

    @inlineCallbacks
    def test_get_302_redirect_allowed(self):
        response = yield self.get('/redirect/1')
        self.assertEqual(response.code, 200)

    @inlineCallbacks
    def test_get_302_redirect_disallowed(self):
        response = yield self.get('/redirect/1', allow_redirects=False)
        self.assertEqual(response.code, 302)

    @inlineCallbacks
    def test_head(self):
        response = yield self.head('/get')
        body = yield treq.content(response)
        self.assertEqual('', body)

    @inlineCallbacks
    def test_head_302_redirect_allowed(self):
        response = yield self.head('/redirect/1')
        self.assertEqual(response.code, 200)

    @inlineCallbacks
    def test_head_302_redirect_disallowed(self):
        response = yield self.head('/redirect/1', allow_redirects=False)
        self.assertEqual(response.code, 302)

    @inlineCallbacks
    def test_post(self):
        response = yield self.post('/post', 'Hello!')
        self.assertEqual(response.code, 200)
        self.assert_data(response, 'Hello!')

    @inlineCallbacks
    def test_post_headers(self):
        response = yield self.post(
            '/post',
            '{msg: "Hello!"}',
            headers={'Content-Type': ['application/json']}
        )

        self.assertEqual(response.code, 200)
        yield self.assert_sent_header(response, 'Content-Type', 'application/json')
        yield self.assert_data(response, '{msg: "Hello!"}')

    @inlineCallbacks
    def test_put(self):
        yield self.put('/put', data='Hello!')

    @inlineCallbacks
    def test_delete(self):
        response = yield self.delete('/delete')
        self.assertEqual(response.code, 200)


class HTTPSTreqIntegrationTests(TreqIntegrationTests):
    baseurl = HTTPSBIN_URL

    if is_pypy:
        skip = "These tests segfault (or hang) on PyPy."
