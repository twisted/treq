from io import BytesIO

from twisted.python.url import URL

from twisted.trial.unittest import TestCase
from twisted.internet.defer import CancelledError, inlineCallbacks
from twisted.internet.task import deferLater
from twisted.internet import reactor
from twisted.internet.tcp import Client
from twisted.internet.ssl import Certificate, trustRootFromCertificates
from twisted.python.monkey import MonkeyPatcher

from twisted.web.client import (Agent, BrowserLikePolicyForHTTPS,
                                HTTPConnectionPool, ResponseFailed)

from treq.test.util import DEBUG, skip_on_windows_because_of_199

from .local_httpbin.parent import _HTTPBinProcess

import treq
from treq.auth import HTTPDigestAuth, UnknownQopForDigestAuth


skip = skip_on_windows_because_of_199()


@inlineCallbacks
def print_response(response):
    if DEBUG:
        print()
        print('---')
        print(response.code)
        print(response.headers)
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
    def test_digest_auth(self):
        """
            Test successful Digest authentication
        :return:
        """
        response = yield self.get('/digest-auth/auth/treq/treq',
                                  auth=HTTPDigestAuth('treq', 'treq'))
        self.assertEqual(response.code, 200)
        yield print_response(response)
        json = yield treq.json_content(response)
        self.assertTrue(json['authenticated'])
        self.assertEqual(json['user'], 'treq')

    @inlineCallbacks
    def test_digest_auth_multi_qop(self):
        """
            Test successful Digest authentication with multiple qop types
        :return:
        """
        response = yield self.get('/digest-auth/undefined/treq/treq',
                                  auth=HTTPDigestAuth('treq', 'treq'))
        self.assertEqual(response.code, 200)
        yield print_response(response)
        json = yield treq.json_content(response)
        self.assertTrue(json['authenticated'])
        self.assertEqual(json['user'], 'treq')

    @inlineCallbacks
    def test_digest_auth_multiple_calls(self):
        """
            Test proper Digest authentication credentials caching
        """

        # A mutable holder for call counter
        agent_request_call_storage = {
            'c': 0,
            'i': []
        }

        # Original Agent request call
        agent_request_orig = Agent.request

        def agent_request_patched(*args, **kwargs):
            """
                Patched Agent.request function,
                that inscreaces call count on every HTTP request
                and appends
            """
            response_deferred = agent_request_orig(*args, **kwargs)
            agent_request_call_storage['c'] += 1
            agent_request_call_storage['i'].append((args, kwargs))
            return response_deferred

        patcher = MonkeyPatcher(
            (Agent, 'request', agent_request_patched)
        )
        patcher.patch()

        auth = HTTPDigestAuth('treq-digest-auth-multiple', 'treq')

        response1 = yield self.get(
            '/digest-auth/auth/treq-digest-auth-multiple/treq',
            auth=auth
        )
        self.assertEqual(response1.code, 200)
        yield print_response(response1)
        json1 = yield treq.json_content(response1)

        # Assume we did two actual HTTP requests - one to obtain credentials
        # and second is original request with authentication
        self.assertEqual(
            agent_request_call_storage['c'],
            2
        )
        headers_for_second_request = agent_request_call_storage['i'][1][0][3]
        self.assertIn(
            b'Authorization',
            dict(headers_for_second_request.getAllRawHeaders())
        )

        response2 = yield self.get(
            '/digest-auth/auth/treq-digest-auth-multiple/treq',
            auth=auth,
            cookies=response1.cookies()
        )
        self.assertEqual(response2.code, 200)
        yield print_response(response2)
        json2 = yield treq.json_content(response2)
        self.assertTrue(json1['authenticated'])
        self.assertEqual(json1['user'], 'treq-digest-auth-multiple')

        # Assume that responses are the same
        self.assertEqual(json1, json2)

        # Assume we need only one call to obtain second response
        self.assertEqual(
            agent_request_call_storage['c'],
            3
        )
        patcher.restore()

    @inlineCallbacks
    def test_digest_auth_sha256(self):
        """
            Test successful Digest authentication with sha256
        :return:
        """
        response = yield self.get('/digest-auth/auth/treq/treq/SHA-256',
                                  auth=HTTPDigestAuth('treq', 'treq'))
        self.assertEqual(response.code, 200)
        yield print_response(response)
        json = yield treq.json_content(response)
        self.assertTrue(json['authenticated'])
        self.assertEqual(json['user'], 'treq')

    @inlineCallbacks
    def test_digest_auth_sha512(self):
        """
            Test successful Digest authentication with sha512
        :return:
        """
        response = yield self.get('/digest-auth/auth/treq/treq/SHA-512',
                                  auth=HTTPDigestAuth('treq', 'treq'))
        self.assertEqual(response.code, 200)
        yield print_response(response)
        json = yield treq.json_content(response)
        self.assertTrue(json['authenticated'])
        self.assertEqual(json['user'], 'treq')

    @inlineCallbacks
    def test_failed_digest_auth(self):
        """
            Test digest auth with invalid credentials
        """
        response = yield self.get('/digest-auth/auth/treq/treq',
                                  auth=HTTPDigestAuth('not-treq', 'not-treq'))
        self.assertEqual(response.code, 401)
        yield print_response(response)

    @inlineCallbacks
    def test_failed_digest_auth_int(self):
        """
            Test failed Digest authentication when qop type is unsupported
        :return:
        """
        with self.assertRaises(UnknownQopForDigestAuth):
            yield self.get('/digest-auth/auth-int/treq/treq',
                           auth=HTTPDigestAuth('treq', 'treq'))

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
