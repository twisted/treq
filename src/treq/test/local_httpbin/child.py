"""
A local ``httpbin`` server to run integration tests against.

This ensures tests do not depend on `httpbin <https://httpbin.org/>`_.
"""
from __future__ import print_function
import argparse
import datetime
import sys

import httpbin

import six

from twisted.internet.defer import Deferred, inlineCallbacks, returnValue
from twisted.internet.endpoints import TCP4ServerEndpoint, SSL4ServerEndpoint
from twisted.internet.task import react
from twisted.internet.ssl import (Certificate,
                                  CertificateOptions)

from OpenSSL.crypto import PKey, X509

from twisted.python.threadpool import ThreadPool
from twisted.web.server import Site
from twisted.web.wsgi import WSGIResource

from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa

from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives.serialization import Encoding

from .shared import _HTTPBinDescription


def _certificates_for_authority_and_server(service_identity, key_size=2048):
    """
    Create a self-signed CA certificate and server certificate signed
    by the CA.

    :param service_identity: The identity (hostname) of the server.
    :type service_identity: :py:class:`unicode`

    :param key_size: (optional) The size of CA's and server's private
        RSA keys.  Defaults to 2048 bits, which is the minimum allowed
        by OpenSSL Contexts at the default security level.
    :type key_size: :py:class:`int`

    :return: a 3-tuple of ``(certificate_authority_certificate,
             server_private_key, server_certificate)``.
    :rtype: :py:class:`tuple` of (:py:class:`sslverify.Certificate`,
            :py:class:`OpenSSL.crypto.PKey`,
            :py:class:`OpenSSL.crypto.X509`)
    """
    common_name_for_ca = x509.Name(
        [x509.NameAttribute(NameOID.COMMON_NAME, u'Testing Example CA')]
    )
    common_name_for_server = x509.Name(
        [x509.NameAttribute(NameOID.COMMON_NAME, u'Testing Example Server')]
    )
    one_day = datetime.timedelta(1, 0, 0)
    private_key_for_ca = rsa.generate_private_key(
        public_exponent=65537,
        key_size=key_size,
        backend=default_backend()
    )
    public_key_for_ca = private_key_for_ca.public_key()
    ca_certificate = (
        x509.CertificateBuilder()
        .subject_name(common_name_for_ca)
        .issuer_name(common_name_for_ca)
        .not_valid_before(datetime.datetime.today() - one_day)
        .not_valid_after(datetime.datetime.today() + one_day)
        .serial_number(x509.random_serial_number())
        .public_key(public_key_for_ca)
        .add_extension(
            x509.BasicConstraints(ca=True, path_length=9), critical=True,
        )
        .sign(
            private_key=private_key_for_ca, algorithm=hashes.SHA256(),
            backend=default_backend()
        )
    )
    private_key_for_server = rsa.generate_private_key(
        public_exponent=65537,
        key_size=key_size,
        backend=default_backend()
    )
    public_key_for_server = private_key_for_server.public_key()
    server_certificate = (
        x509.CertificateBuilder()
        .subject_name(common_name_for_server)
        .issuer_name(common_name_for_ca)
        .not_valid_before(datetime.datetime.today() - one_day)
        .not_valid_after(datetime.datetime.today() + one_day)
        .serial_number(x509.random_serial_number())
        .public_key(public_key_for_server)
        .add_extension(
            x509.BasicConstraints(ca=False, path_length=None), critical=True,
        )
        .add_extension(
            x509.SubjectAlternativeName(
                [x509.DNSName(service_identity)]
            ),
            critical=True,
        )
        .sign(
            private_key=private_key_for_ca, algorithm=hashes.SHA256(),
            backend=default_backend()
        )
    )

    ca_self_cert = Certificate.loadPEM(
        ca_certificate.public_bytes(Encoding.PEM)
    )

    pkey = PKey.from_cryptography_key(private_key_for_server)
    x509_server_certificate = X509.from_cryptography(server_certificate)

    return ca_self_cert, pkey, x509_server_certificate


def _make_httpbin_site(reactor, threadpool_factory=ThreadPool):
    """
    Return a :py:class:`Site` that hosts an ``httpbin`` WSGI
    application.

    :param reactor: The reactor.
    :param threadpool_factory: (optional) A callable that creates a
        :py:class:`ThreadPool`.

    :return: A :py:class:`Site` that hosts ``httpbin``
    """
    wsgi_threads = threadpool_factory()
    wsgi_threads.start()
    reactor.addSystemEventTrigger("before", "shutdown", wsgi_threads.stop)

    wsgi_resource = WSGIResource(reactor, wsgi_threads, httpbin.app)

    return Site(wsgi_resource)


@inlineCallbacks
def _serve_tls(reactor, host, port, site):
    """
    Serve a site over TLS.

    :param reactor: The reactor.
    :param host: The host on which to listen.
    :type host: :py:class:`str`

    :param port: The host on which to listen.
    :type port: :py:class:`int`
    :type site: The :py:class:`Site` to serve.

    :return: A :py:class:`Deferred` that fires with a
             :py:class:`_HTTPBinDescription`
    """
    cert_host = host.decode('ascii') if six.PY2 else host

    (
        ca_cert, private_key, certificate,
    ) = _certificates_for_authority_and_server(cert_host)

    context_factory = CertificateOptions(privateKey=private_key,
                                         certificate=certificate)

    endpoint = SSL4ServerEndpoint(reactor,
                                  port,
                                  sslContextFactory=context_factory,
                                  interface=host)

    port = yield endpoint.listen(site)

    description = _HTTPBinDescription(host=host,
                                      port=port.getHost().port,
                                      cacert=ca_cert.dumpPEM().decode('ascii'))

    returnValue(description)


@inlineCallbacks
def _serve_tcp(reactor, host, port, site):
    """
    Serve a site over plain TCP.

    :param reactor: The reactor.
    :param host: The host on which to listen.
    :type host: :py:class:`str`

    :param port: The host on which to listen.
    :type port: :py:class:`int`

    :return: A :py:class:`Deferred` that fires with a
             :py:class:`_HTTPBinDescription`
    """
    endpoint = TCP4ServerEndpoint(reactor, port, interface=host)

    port = yield endpoint.listen(site)

    description = _HTTPBinDescription(host=host, port=port.getHost().port)

    returnValue(description)


def _output_process_description(description, stdout=sys.stdout):
    """
    Write a process description to standard out.

    :param description: The process description.
    :type description: :py:class:`_HTTPBinDescription`

    :param stdout: (optional) Standard out.
    """
    if six.PY2:
        write = stdout.write
        flush = stdout.flush
    else:
        write = stdout.buffer.write
        flush = stdout.buffer.flush

    write(description.to_json_bytes() + b'\n')
    flush()


def _forever_httpbin(reactor, argv,
                     _make_httpbin_site=_make_httpbin_site,
                     _serve_tcp=_serve_tcp,
                     _serve_tls=_serve_tls,
                     _output_process_description=_output_process_description):
    """
    Run ``httpbin`` forever.

    :param reactor: The Twisted reactor.
    :param argv: The arguments with which the script was ran.
    :type argv: :py:class:`list` of :py:class:`str`

    :return: a :py:class:`Deferred` that never fires.
    """
    parser = argparse.ArgumentParser(
        description="""
                    Run httpbin forever.  This writes a JSON object to
                    standard out.  The host and port properties
                    contain the host and port on which httpbin
                    listens.  When run with HTTPS, the cacert property
                    contains the PEM-encode CA certificate that
                    clients must trust.
                    """
    )
    parser.add_argument("--https",
                        help="Serve HTTPS",
                        action="store_const",
                        dest='serve',
                        const=_serve_tls,
                        default=_serve_tcp)
    parser.add_argument("--host",
                        help="The host on which the server will listen.",
                        type=str,
                        default="localhost")
    parser.add_argument("--port",
                        help="The on which the server will listen.",
                        type=int,
                        default=0)

    arguments = parser.parse_args(argv)

    site = _make_httpbin_site(reactor)

    description_deferred = arguments.serve(reactor,
                                           arguments.host,
                                           arguments.port,
                                           site)
    description_deferred.addCallback(_output_process_description)
    description_deferred.addCallback(lambda _: Deferred())

    return description_deferred


if __name__ == '__main__':
    react(_forever_httpbin, (sys.argv[1:],))
