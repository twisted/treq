from twisted.trial.unittest import TestCase
from twisted.internet.defer import inlineCallbacks

import treq

HTTPBIN_URL = "http://httpbin.org"
HTTPSBIN_URL = "https://httpbin.org"

debug = True


@inlineCallbacks
def print_response(response):
    if debug:
        print
        print '---'
        print response.status_code
        print response.headers
        text = yield response.text
        print text
        print '---'


def with_baseurl(method):
    def _request(self, url, *args, **kwargs):
        return method(self.baseurl + url, *args, **kwargs)

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
        body = yield response.json
        self.assertIn('data', body)
        self.assertEqual(body['data'], expected_data)

    @inlineCallbacks
    def assert_sent_header(self, response, header, expected_value):
        body = yield response.json
        self.assertIn(header, body['headers'])
        self.assertEqual(body['headers'][header], expected_value)

    @inlineCallbacks
    def test_get(self):
        response = yield self.get('/get')
        self.assertEqual(response.status_code, 200)
        yield print_response(response)

    @inlineCallbacks
    def test_get_headers(self):
        response = yield self.get('/get', {'X-Blah': ['Foo']})
        self.assertEqual(response.status_code, 200)
        yield self.assert_sent_header(response, 'X-Blah', 'Foo')
        yield print_response(response)

    @inlineCallbacks
    def test_get_302_redirect_allowed(self):
        response = yield self.get('/redirect/1')
        self.assertEqual(response.status_code, 200)
        yield print_response(response)

    @inlineCallbacks
    def test_get_302_redirect_disallowed(self):
        response = yield self.get('/redirect/1', allow_redirects=False)
        self.assertEqual(response.status_code, 302)
        yield print_response(response)

    @inlineCallbacks
    def test_head(self):
        response = yield self.head('/get')
        body = yield response.content
        self.assertEqual('', body)
        yield print_response(response)

    @inlineCallbacks
    def test_head_302_redirect_allowed(self):
        response = yield self.head('/redirect/1')
        self.assertEqual(response.status_code, 200)
        yield print_response(response)

    @inlineCallbacks
    def test_head_302_redirect_disallowed(self):
        response = yield self.head('/redirect/1', allow_redirects=False)
        self.assertEqual(response.status_code, 302)
        yield print_response(response)

    @inlineCallbacks
    def test_post(self):
        response = yield self.post('/post', body='Hello!')
        self.assertEqual(response.status_code, 200)
        self.assert_data(response, 'Hello!')
        yield print_response(response)

    @inlineCallbacks
    def test_post_headers(self):
        response = yield self.post(
            '/post',
            {'Content-Type': ['application/json']},
            '{msg: "Hello!"}'
        )

        self.assertEqual(response.status_code, 200)
        self.assert_sent_header(response, 'Content-Type', 'application/json')
        self.assert_data(response, '{msg: "Hello!"}')

        yield print_response(response)

    @inlineCallbacks
    def test_put(self):
        response = yield self.put('/put', body='Hello!')
        yield print_response(response)

    @inlineCallbacks
    def test_delete(self):
        response = yield self.delete('/delete')
        self.assertEqual(response.status_code, 200)
        yield print_response(response)


class HTTPSTreqIntegrationTests(TreqIntegrationTests):
    baseurl = HTTPSBIN_URL
