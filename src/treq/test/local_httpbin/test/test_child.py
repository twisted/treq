"""
Tests for :py:mod:`treq.test.local_httpbin.child`
"""
import attr

from cryptography.hazmat.primitives.asymmetric import padding

import functools

import io

from twisted.trial.unittest import SynchronousTestCase

try:
    from twisted.internet.testing import MemoryReactor
except ImportError:
    from twisted.test.proto_helpers import MemoryReactor

from twisted.internet import defer

from treq.test.util import skip_on_windows_because_of_199

from twisted.web.server import Site
from twisted.web.resource import Resource

from service_identity.cryptography import verify_certificate_hostname

from .. import child, shared


skip = skip_on_windows_because_of_199()


class CertificatesForAuthorityAndServerTests(SynchronousTestCase):
    """
    Tests for :py:func:`child._certificates_for_authority_and_server`
    """

    def setUp(self):
        self.hostname = u".example.org"
        (
            self.ca_cert,
            self.server_private_key,
            self.server_x509_cert,
        ) = child._certificates_for_authority_and_server(
            self.hostname,
        )

    def test_pkey_x509_paired(self):
        """
        The returned private key corresponds to the X.509
        certificate's public key.
        """
        server_private_key = self.server_private_key.to_cryptography_key()
        server_x509_cert = self.server_x509_cert.to_cryptography()

        plaintext = b'plaintext'
        ciphertext = server_x509_cert.public_key().encrypt(
            plaintext,
            padding.PKCS1v15(),
        )

        self.assertEqual(
            server_private_key.decrypt(
                ciphertext,
                padding.PKCS1v15(),
            ),
            plaintext,
        )

    def test_ca_signed_x509(self):
        """
        The returned X.509 certificate was signed by the returned
        certificate authority's certificate.
        """
        ca_cert = self.ca_cert.original.to_cryptography()
        server_x509_cert = self.server_x509_cert.to_cryptography()

        # Raises an InvalidSignature exception on failure.
        ca_cert.public_key().verify(
            server_x509_cert.signature,
            server_x509_cert.tbs_certificate_bytes,
            padding.PKCS1v15(),
            server_x509_cert.signature_hash_algorithm
        )

    def test_x509_matches_hostname(self):
        """
        The returned X.509 certificate is valid for the hostname.
        """
        verify_certificate_hostname(
            self.server_x509_cert.to_cryptography(),
            self.hostname,
        )


@attr.s
class FakeThreadPoolState(object):
    """
    State for :py:class:`FakeThreadPool`.
    """
    init_call_count = attr.ib(default=0)
    start_call_count = attr.ib(default=0)


@attr.s
class FakeThreadPool(object):
    """
    A fake :py:class:`twisted.python.threadpool.ThreadPool`
    """
    _state = attr.ib()

    def init(self):
        self._state.init_call_count += 1
        return self

    def start(self):
        """
        See :py:meth:`twisted.python.threadpool.ThreadPool.start`
        """
        self._state.start_call_count += 1

    def stop(self):
        """
        See :py:meth:`twisted.python.threadpool.ThreadPool.stop`
        """


class MakeHTTPBinSiteTests(SynchronousTestCase):
    """
    Tests for :py:func:`_make_httpbin_site`.
    """

    def setUp(self):
        self.fake_threadpool_state = FakeThreadPoolState()
        self.fake_threadpool = FakeThreadPool(self.fake_threadpool_state)
        self.reactor = MemoryReactor()

    def test_threadpool_management(self):
        """
        A thread pool is created that will be shut down when the
        reactor shuts down.
        """
        child._make_httpbin_site(
            self.reactor,
            threadpool_factory=self.fake_threadpool.init,
        )

        self.assertEqual(self.fake_threadpool_state.init_call_count, 1)
        self.assertEqual(self.fake_threadpool_state.start_call_count, 1)

        self.assertEqual(len(self.reactor.triggers['before']['shutdown']), 1)
        [(stop, _, _)] = self.reactor.triggers['before']['shutdown']

        self.assertEqual(stop, self.fake_threadpool.stop)


class ServeTLSTests(SynchronousTestCase):
    """
    Tests for :py:func:`_serve_tls`
    """

    def setUp(self):
        self.reactor = MemoryReactor()
        self.site = Site(Resource())

    def test_tls_listener_matches_description(self):
        """
        An SSL listener is established on the requested host and port,
        and the host, port, and CA certificate are returned in its
        description.
        """
        expected_host = 'host'
        expected_port = 123

        description_deferred = child._serve_tls(
            self.reactor,
            host=expected_host,
            port=expected_port,
            site=self.site,
        )

        self.assertEqual(len(self.reactor.sslServers), 1)

        [
            (actual_port, actual_site, _, _, actual_host)
        ] = self.reactor.sslServers

        self.assertEqual(actual_host, expected_host)
        self.assertEqual(actual_port, expected_port)
        self.assertIs(actual_site, self.site)

        description = self.successResultOf(description_deferred)

        self.assertEqual(description.host, expected_host)
        self.assertEqual(description.port, expected_port)
        self.assertTrue(description.cacert)


class ServeTCPTests(SynchronousTestCase):
    """
    Tests for :py:func:`_serve_tcp`
    """

    def setUp(self):
        self.reactor = MemoryReactor()
        self.site = Site(Resource)

    def test_tcp_listener_matches_description(self):
        """
        A TCP listeneris established on the request host and port, and
        the host and port are returned in its description.
        """
        expected_host = 'host'
        expected_port = 123

        description_deferred = child._serve_tcp(
            self.reactor,
            host=expected_host,
            port=expected_port,
            site=self.site,
        )

        self.assertEqual(len(self.reactor.tcpServers), 1)

        [
            (actual_port, actual_site, _, actual_host)
        ] = self.reactor.tcpServers

        self.assertEqual(actual_host, expected_host)
        self.assertEqual(actual_port, expected_port)
        self.assertIs(actual_site, self.site)

        description = self.successResultOf(description_deferred)

        self.assertEqual(description.host, expected_host)
        self.assertEqual(description.port, expected_port)
        self.assertFalse(description.cacert)


@attr.s
class FlushableBytesIOState(object):
    """
    State for :py:class:`FlushableBytesIO`
    """
    bio = attr.ib(default=attr.Factory(io.BytesIO))
    flush_count = attr.ib(default=0)


@attr.s
class FlushableBytesIO(object):
    """
    A :py:class:`io.BytesIO` wrapper that records flushes.
    """
    _state = attr.ib()

    def write(self, data):
        self._state.bio.write(data)

    def flush(self):
        self._state.flush_count += 1


@attr.s
class BufferedStandardOut(object):
    """
    A standard out that whose ``buffer`` is a
    :py:class:`FlushableBytesIO` instance.
    """
    buffer = attr.ib()


class OutputProcessDescriptionTests(SynchronousTestCase):
    """
    Tests for :py:func:`_output_process_description`
    """

    def setUp(self):
        self.stdout_state = FlushableBytesIOState()
        self.stdout = BufferedStandardOut(FlushableBytesIO(self.stdout_state))

    def test_description_written(self):
        """
        An :py:class:`shared._HTTPBinDescription` is written to
        standard out and the line flushed.
        """
        description = shared._HTTPBinDescription(host="host",
                                                 port=123,
                                                 cacert="cacert")

        child._output_process_description(description, self.stdout)

        written = self.stdout_state.bio.getvalue()

        self.assertEqual(
            written,
            b'{"cacert": "cacert", "host": "host", "port": 123}' + b'\n',
        )

        self.assertEqual(self.stdout_state.flush_count, 1)


class ForeverHTTPBinTests(SynchronousTestCase):
    """
    Tests for :py:func:`_forever_httpbin`
    """

    def setUp(self):
        self.make_httpbin_site_returns = Site(Resource())

        self.serve_tcp_calls = []
        self.serve_tcp_returns = defer.Deferred()

        self.serve_tls_calls = []
        self.serve_tls_returns = defer.Deferred()

        self.output_process_description_calls = []
        self.output_process_description_returns = None

        self.reactor = MemoryReactor()

        self.forever_httpbin = functools.partial(
            child._forever_httpbin,
            _make_httpbin_site=self.make_httpbin_site,
            _serve_tcp=self.serve_tcp,
            _serve_tls=self.serve_tls,
            _output_process_description=self.output_process_description,
        )

    def make_httpbin_site(self, reactor, *args, **kwargs):
        """
        A fake :py:func:`child._make_httpbin_site`.
        """
        return self.make_httpbin_site_returns

    def serve_tcp(self, reactor, host, port, site):
        """
        A fake :py:func:`child._serve_tcp`.
        """
        self.serve_tcp_calls.append((reactor, host, port, site))
        return self.serve_tcp_returns

    def serve_tls(self, reactor, host, port, site):
        """
        A fake :py:func:`child._serve_tls`.
        """
        self.serve_tls_calls.append((reactor, host, port, site))
        return self.serve_tls_returns

    def output_process_description(self, description, *args, **kwargs):
        """
        A fake :py:func:`child._output_process_description`
        """
        self.output_process_description_calls.append(description)
        return self.output_process_description_returns

    def assertDescriptionAndDeferred(self,
                                     description_deferred,
                                     forever_deferred):
        """
        Assert that firing ``description_deferred`` outputs the
        description but that ``forever_deferred`` never fires.
        """
        description_deferred.callback("description")

        self.assertEqual(self.output_process_description_calls,
                         ["description"])

        self.assertNoResult(forever_deferred)

    def test_default_arguments(self):
        """
        The default command line arguments host ``httpbin`` on
        ``localhost`` and a randomly-assigned port, returning a
        :py:class:`Deferred` that never fires.
        """
        deferred = self.forever_httpbin(self.reactor, [])

        self.assertEqual(
            self.serve_tcp_calls,
            [
                (self.reactor, 'localhost', 0, self.make_httpbin_site_returns)
            ]
        )

        self.assertDescriptionAndDeferred(
            description_deferred=self.serve_tcp_returns,
            forever_deferred=deferred,
        )

    def test_https(self):
        """
        The ``--https`` command line argument serves ``httpbin`` over
        HTTPS, returning a :py:class:`Deferred` that never fires.
        """
        deferred = self.forever_httpbin(self.reactor, ['--https'])

        self.assertEqual(
            self.serve_tls_calls,
            [
                (self.reactor, 'localhost', 0, self.make_httpbin_site_returns)
            ]
        )

        self.assertDescriptionAndDeferred(
            description_deferred=self.serve_tls_returns,
            forever_deferred=deferred,
        )

    def test_host(self):
        """
        The ``--host`` command line argument serves ``httpbin`` on
        provided host, returning a :py:class:`Deferred` that never
        fires.
        """
        deferred = self.forever_httpbin(self.reactor,
                                        ['--host', 'example.org'])

        self.assertEqual(
            self.serve_tcp_calls,
            [
                (
                    self.reactor,
                    'example.org',
                    0,
                    self.make_httpbin_site_returns,
                )
            ]
        )

        self.assertDescriptionAndDeferred(
            description_deferred=self.serve_tcp_returns,
            forever_deferred=deferred,
        )

    def test_port(self):
        """
        The ``--port`` command line argument serves ``httpbin`` on
        the provided port, returning a :py:class:`Deferred` that never
        fires.
        """
        deferred = self.forever_httpbin(self.reactor, ['--port', '91'])

        self.assertEqual(
            self.serve_tcp_calls,
            [
                (self.reactor, 'localhost', 91, self.make_httpbin_site_returns)
            ]
        )

        self.assertDescriptionAndDeferred(
            description_deferred=self.serve_tcp_returns,
            forever_deferred=deferred,
        )
