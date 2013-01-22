from twisted.trial.unittest import TestCase
from twisted.internet.defer import inlineCallbacks
from twisted.internet.task import deferLater
from twisted.internet import reactor
from twisted.internet.tcp import Client

from twisted.web.client import HTTPConnectionPool

from treq.test.util import DEBUG, is_pypy, has_ssl

import treq

HTTPBIN_URL = "http://httpbin.org"
HTTPSBIN_URL = "https://httpbin.org"


@inlineCallbacks
def print_response(response):
    if DEBUG:
        print
        print '---'
        print response.code
        print response.headers
        text = yield treq.text_content(response)
        print text
        print '---'


def with_baseurl(method):
    def _request(self, url, *args, **kwargs):
        return method(self.baseurl + url, *args, pool=self.pool, **kwargs)

    return _request


class TreqIntegrationTests(TestCase):
    baseurl = HTTPBIN_URL
    get = with_baseurl(treq.get)
    head = with_baseurl(treq.head)
    post = with_baseurl(treq.post)
    put = with_baseurl(treq.put)
    patch = with_baseurl(treq.patch)
    delete = with_baseurl(treq.delete)

    def setUp(self):
        self.pool = HTTPConnectionPool(reactor, False)

    def tearDown(self):
        def _check_fds(_):
            # This appears to only be necessary for HTTPS tests.
            # For the normal HTTP tests then closeCachedConnections is
            # sufficient.
            fds = set(reactor.getReaders() + reactor.getReaders())
            if not [fd for fd in fds if isinstance(fd, Client)]:
                return

            return deferLater(reactor, 0, _check_fds, None)

        return self.pool.closeCachedConnections().addBoth(_check_fds)

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
        yield print_response(response)

    @inlineCallbacks
    def test_get_headers(self):
        response = yield self.get('/get', {'X-Blah': ['Foo', 'Bar']})
        self.assertEqual(response.code, 200)
        yield self.assert_sent_header(response, 'X-Blah', 'Foo, Bar')
        yield print_response(response)

    @inlineCallbacks
    def test_get_302_redirect_allowed(self):
        response = yield self.get('/redirect/1')
        self.assertEqual(response.code, 200)
        yield print_response(response)

    @inlineCallbacks
    def test_get_302_redirect_disallowed(self):
        response = yield self.get('/redirect/1', allow_redirects=False)
        self.assertEqual(response.code, 302)
        yield print_response(response)

    @inlineCallbacks
    def test_head(self):
        response = yield self.head('/get')
        body = yield treq.content(response)
        self.assertEqual('', body)
        yield print_response(response)

    @inlineCallbacks
    def test_head_302_redirect_allowed(self):
        response = yield self.head('/redirect/1')
        self.assertEqual(response.code, 200)
        yield print_response(response)

    @inlineCallbacks
    def test_head_302_redirect_disallowed(self):
        response = yield self.head('/redirect/1', allow_redirects=False)
        self.assertEqual(response.code, 302)
        yield print_response(response)

    @inlineCallbacks
    def test_post(self):
        response = yield self.post('/post', 'Hello!')
        self.assertEqual(response.code, 200)
        yield self.assert_data(response, 'Hello!')
        yield print_response(response)

    @inlineCallbacks
    def test_post_headers(self):
        response = yield self.post(
            '/post',
            '{msg: "Hello!"}',
            headers={'Content-Type': ['application/json']}
        )

        self.assertEqual(response.code, 200)
        yield self.assert_sent_header(
            response, 'Content-Type', 'application/json')
        yield self.assert_data(response, '{msg: "Hello!"}')
        yield print_response(response)

    @inlineCallbacks
    def test_put(self):
        response = yield self.put('/put', data='Hello!')
        yield print_response(response)

    @inlineCallbacks
    def test_patch(self):
        response = yield self.patch('/patch', data='Hello!')
        self.assertEqual(response.code, 200)
        yield self.assert_data(response, 'Hello!')
        yield print_response(response)

    @inlineCallbacks
    def test_delete(self):
        response = yield self.delete('/delete')
        self.assertEqual(response.code, 200)
        yield print_response(response)

    @inlineCallbacks
    def test_gzip(self):
        response = yield self.get('/gzip')
        self.assertEqual(response.code, 200)
        yield print_response(response)
        json = yield treq.json_content(response)
        self.assertTrue(json['gzipped'])

    @inlineCallbacks
    def test_basic_auth(self):
        response = yield self.get('/basic-auth/treq/treq',
                                  auth=('treq', 'treq'))
        self.assertEqual(response.code, 200)
        yield print_response(response)
        json = yield treq.json_content(response)
        self.assertTrue(json['authenticated'])
        self.assertEqual(json['user'], 'treq')

    @inlineCallbacks
    def test_failed_basic_auth(self):
        response = yield self.get('/basic-auth/treq/treq',
                                  auth=('not-treq', 'not-treq'))
        self.assertEqual(response.code, 401)
        yield print_response(response)


class HTTPSTreqIntegrationTests(TreqIntegrationTests):
    baseurl = HTTPSBIN_URL

    if is_pypy:
        skip = "These tests segfault (or hang) on PyPy."

    if not has_ssl:
        skip = "These tests require pyOpenSSL."
