import attr
from io import BytesIO
import os
import json
import platform
import signal
import sys

from twisted.python.url import URL

from twisted.trial.unittest import TestCase
from twisted.internet.defer import (Deferred, succeed, CancelledError,
                                    inlineCallbacks)
from twisted.internet.task import deferLater
from twisted.protocols import basic, policies
from twisted.internet import protocol, endpoints, error, reactor
from twisted.internet.tcp import Client
from twisted.internet.ssl import Certificate, trustRootFromCertificates

from twisted.web.client import (Agent, BrowserLikePolicyForHTTPS,
                                HTTPConnectionPool, ResponseFailed)

from treq.test.util import DEBUG
from treq.test.httpbin_server import _HTTPBinDescription

import treq

HTTPBIN_URL = "http://httpbin.org"
HTTPSBIN_URL = "https://httpbin.org"


class _HTTPBinServerProcessProtocol(basic.LineOnlyReceiver):
    """
    Manage the lifecycle of an ``httpbin`` process.
    """
    delimiter = os.linesep.encode('ascii')

    def __init__(self, https, allDataReceived, terminated):
        """
        Manage the lifecycle of an ``httpbin`` process.

        :param https: Should this process serve HTTPS?
        :type https: :py:class:`bool`

        :param allDataReceived: A Deferred that will be called back
            with an :py:class:`_HTTPBinDescription` object
        :type allDataReceived: :py:class:`Deferred`

        :param terminated: A Deferred that will be called back when
            the process has ended.
        :type terminated: :py:class:`Deferred`
        """
        self._https = https
        self._allDataReceived = allDataReceived
        self._fired = False
        self._terminated = terminated

    def lineReceived(self, line):
        deserialized = json.loads(line.decode('ascii'))
        self._fired = True

        # Remove readers that leave the reactor in a dirty state after
        # a test.
        self.transport.closeStdin()
        self.transport.closeStdout()
        self.transport.closeStderr()

        self._allDataReceived.callback(
            _HTTPBinDescription.from_dictionary(deserialized)
        )

    def connectionLost(self, reason):
        if not self._fired:
            self._allDataReceived.errback(reason)
        self._terminated.errback(reason)


@attr.s
class _HTTPBinProcess(object):
    """
    Manage an ``httpbin`` server process.

    :ivar _allDataReceived: See
        :py:attr:`_HTTPBinServerProcessProtocol.allDataReceived`
    :ivar _terminated: See
        :py:attr:`_HTTPBinServerProcessProtocol.terminated`
    """
    _https = attr.ib()

    _allDataReceived = attr.ib(init=False, default=attr.Factory(Deferred))
    _terminated = attr.ib(init=False, default=attr.Factory(Deferred))

    _process = attr.ib(init=False, default=None)
    _processDescription = attr.ib(init=False, default=None)

    def _spawnHTTPBinProcess(self, reactor):
        """
        Spawn an ``httpbin`` process, returning a :py:class:`Deferred`
        that fires with the process transport and result.
        """
        server = _HTTPBinServerProcessProtocol(
            self._https,
            allDataReceived=self._allDataReceived,
            terminated=self._terminated
        )

        argv = [
            sys.executable,
            '-m',
            'treq.test.httpbin_server',
        ]

        if self._https:
            argv.append('--https')

        endpoint = endpoints.ProcessEndpoint(
            reactor,
            sys.executable,
            argv,
        )

        spawned = endpoint.connect(
            # ProtocolWrapper, WrappingFactory's protocol, has a
            # disconnecting attribute.  See
            # https://twistedmatrix.com/trac/ticket/6606
            policies.WrappingFactory(
                protocol.Factory.forProtocol(lambda: server),
            ),
        )

        def waitForProtocol(connectedProtocol):
            process = connectedProtocol.transport
            return self._allDataReceived.addCallback(
                returnResultAndProcess, process,
            )

        def returnResultAndProcess(description, process):
            return description, process

        return spawned.addCallback(waitForProtocol)

    def serverDescription(self, reactor):
        """
        Return a :py:class:`Deferred` that fires with the the process'
        :py:class:`_HTTPBinDescription`, spawning the process if
        necessary.
        """
        if self._process is None:
            ready = self._spawnHTTPBinProcess(reactor)

            def storeAndScheduleTermination(descriptionAndProcess):
                description, process = descriptionAndProcess

                self._process = process
                self._processDescription = description

                reactor.addSystemEventTrigger("before", "shutdown", self.kill)

                return self._processDescription

            return ready.addCallback(storeAndScheduleTermination)
        else:
            return succeed(self._processDescription)

    def kill(self):
        """
        Kill the ``httpbin`` process.
        """
        if platform.system() == "Windows":
            signo = signal.SIGTERM
            self._process.signalProcess("TERMINATE")
        else:
            signo = signal.SIGKILL
            self._process.signalProcess("KILL")

        def suppressProcessTerminated(exitFailure):
            exitFailure.trap(error.ProcessTerminated)
            if exitFailure.value.signal != signo:
                return exitFailure

        return self._terminated.addErrback(suppressProcessTerminated)


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

    _httpbinProcess = _HTTPBinProcess(https=False)

    @inlineCallbacks
    def setUp(self):
        processDescription = yield self._httpbinProcess.serverDescription(
            reactor)
        self.baseurl = URL(scheme=u"http",
                           host=processDescription.host,
                           port=processDescription.port).to_text()
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
    _httpbinProcess = _HTTPBinProcess(https=True)

    @inlineCallbacks
    def setUp(self):
        processDescription = yield self._httpbinProcess.serverDescription(
            reactor)
        self.baseurl = URL(scheme=u"https",
                           host=processDescription.host,
                           port=processDescription.port).to_text()

        root = trustRootFromCertificates(
            [Certificate.loadPEM(processDescription.cacert)],
        )
        self.agent = Agent(
            reactor,
            contextFactory=BrowserLikePolicyForHTTPS(root),
        )

        self.pool = HTTPConnectionPool(reactor, False)
