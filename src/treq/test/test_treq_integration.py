from io import BytesIO

from twisted.python.url import URL

from twisted.trial.unittest import TestCase
from twisted.internet.defer import CancelledError, inlineCallbacks
from twisted.internet.task import deferLater
from twisted.internet import reactor
from twisted.internet.tcp import Client
from twisted.internet.ssl import Certificate, trustRootFromCertificates

from twisted.web.client import (Agent, BrowserLikePolicyForHTTPS,
                                HTTPConnectionPool, ResponseFailed)

from treq.test.util import DEBUG, skip_on_windows_because_of_199

from .local_httpbin.parent import _HTTPBinProcess

import treq


skip = skip_on_windows_because_of_199()


@inlineCallbacks
def print_response(response):
    if DEBUG:
        print()
        print('---')
        print(response.code)
        print(response.headers)
        print(response.request.headers)
        text = yield treq.text_content(response)
        print(text)
        print('---')


def with_baseurl(method):
    def _request(self, url, *args, **kwargs):
        return method(self.baseurl + url,
                      *args,
                      agent=self.agent,
                      pool=self.pool,
                      **kwargs)

    return _request


class TreqIntegrationTests(TestCase):
    get = with_baseurl(treq.get)
    head = with_baseurl(treq.head)
    post = with_baseurl(treq.post)
    put = with_baseurl(treq.put)
    patch = with_baseurl(treq.patch)
    delete = with_baseurl(treq.delete)

    _httpbin_process = _HTTPBinProcess(https=False)

    @inlineCallbacks
    def setUp(self):
        description = yield self._httpbin_process.server_description(
            reactor)
        self.baseurl = URL(scheme=u"http",
                           host=description.host,
                           port=description.port).asText()
        self.agent = Agent(reactor)
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
        response = yield self.get('/get', {b'X-Blah': [b'Foo', b'Bar']})
        self.assertEqual(response.code, 200)
        yield self.assert_sent_header(response, 'X-Blah', 'Foo,Bar')
        yield print_response(response)

    @inlineCallbacks
    def test_get_headers_unicode(self):
        response = yield self.get('/get', {u'X-Blah': [u'Foo', b'Bar']})
        self.assertEqual(response.code, 200)
        yield self.assert_sent_header(response, 'X-Blah', 'Foo,Bar')
        yield print_response(response)

    @inlineCallbacks
    def test_get_302_absolute_redirect(self):
        response = yield self.get(
            '/redirect-to?url={0}/get'.format(self.baseurl))
        self.assertEqual(response.code, 200)
        yield print_response(response)

    @inlineCallbacks
    def test_get_302_relative_redirect(self):
        response = yield self.get('/relative-redirect/1')
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
        self.assertEqual(b'', body)
        yield print_response(response)

    @inlineCallbacks
    def test_head_302_absolute_redirect(self):
        response = yield self.head(
            '/redirect-to?url={0}/get'.format(self.baseurl))
        self.assertEqual(response.code, 200)
        yield print_response(response)

    @inlineCallbacks
    def test_head_302_relative_redirect(self):
        response = yield self.head('/relative-redirect/1')
        self.assertEqual(response.code, 200)
        yield print_response(response)

    @inlineCallbacks
    def test_head_302_redirect_disallowed(self):
        response = yield self.head('/redirect/1', allow_redirects=False)
        self.assertEqual(response.code, 302)
        yield print_response(response)

    @inlineCallbacks
    def test_post(self):
        response = yield self.post('/post', b'Hello!')
        self.assertEqual(response.code, 200)
        yield self.assert_data(response, 'Hello!')
        yield print_response(response)

    @inlineCallbacks
    def test_multipart_post(self):
        class FileLikeObject(BytesIO):
            def __init__(self, val):
                BytesIO.__init__(self, val)
                self.name = "david.png"

            def read(*args, **kwargs):
                return BytesIO.read(*args, **kwargs)

        response = yield self.post(
            '/post',
            data={"a": "b"},
            files={"file1": FileLikeObject(b"file")})
        self.assertEqual(response.code, 200)

        body = yield treq.json_content(response)
        self.assertEqual('b', body['form']['a'])
        self.assertEqual('file', body['files']['file1'])
        yield print_response(response)

    @inlineCallbacks
    def test_post_headers(self):
        response = yield self.post(
            '/post',
            b'{msg: "Hello!"}',
            headers={'Content-Type': ['application/json']}
        )

        self.assertEqual(response.code, 200)
        yield self.assert_sent_header(
            response, 'Content-Type', 'application/json')
        yield self.assert_data(response, '{msg: "Hello!"}')
        yield print_response(response)

    @inlineCallbacks
    def test_put(self):
        response = yield self.put('/put', data=b'Hello!')
        yield print_response(response)

    @inlineCallbacks
    def test_patch(self):
        response = yield self.patch('/patch', data=b'Hello!')
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

    @inlineCallbacks
    def test_timeout(self):
        """
        Verify a timeout fires if a request takes too long.
        """
        yield self.assertFailure(self.get('/delay/2', timeout=1),
                                 CancelledError,
                                 ResponseFailed)

    @inlineCallbacks
    def test_cookie(self):
        response = yield self.get('/cookies', cookies={'hello': 'there'})
        self.assertEqual(response.code, 200)
        yield print_response(response)
        json = yield treq.json_content(response)
        self.assertEqual(json['cookies']['hello'], 'there')

    @inlineCallbacks
    def test_set_cookie(self):
        response = yield self.get('/cookies/set',
                                  allow_redirects=False,
                                  params={'hello': 'there'})
        # self.assertEqual(response.code, 200)
        yield print_response(response)
        self.assertEqual(response.cookies()['hello'], 'there')


class HTTPSTreqIntegrationTests(TreqIntegrationTests):
    _httpbin_process = _HTTPBinProcess(https=True)

    @inlineCallbacks
    def setUp(self):
        description = yield self._httpbin_process.server_description(
            reactor)
        self.baseurl = URL(scheme=u"https",
                           host=description.host,
                           port=description.port).asText()

        root = trustRootFromCertificates(
            [Certificate.loadPEM(description.cacert)],
        )
        self.agent = Agent(
            reactor,
            contextFactory=BrowserLikePolicyForHTTPS(root),
        )

        self.pool = HTTPConnectionPool(reactor, False)
