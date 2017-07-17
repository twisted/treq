"""
A local ``httpbin`` server to run integration tests against.

This ensures tests do not depend on `httpbin <https://httpbin.org/>`_.
"""
from __future__ import print_function
import attr
import argparse
import datetime
import json
import sys

import httpbin

from twisted.internet.defer import Deferred
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


@attr.s
class _HTTPBinDescription(object):
    """
    Describe an ``httpbin`` process.

    :param host: The host on which the process listens.
    :type host: :py:class:`str`

    :param port: The port on which the process listens.
    :type port: :py:class:`int`

    :param cacert: (optional) The PEM-encoded certificate authority's
        certificate.  The calling process' treq must trust this when
        running HTTPS tests.
    :type cacert: :py:class:`str` or :py:class:`None`
    """
    host = attr.ib()
    port = attr.ib()
    cacert = attr.ib(default=None)

    @classmethod
    def from_dictionary(cls, dictionary):
        return cls(**dictionary)


def certificatesForAuthorityAndServer(serviceIdentity):
    """
    Create a self-signed CA certificate and server certificate signed
    by the CA.

    @param serviceIdentity: The identity (hostname) of the server.
    @type serviceIdentity: L{unicode}

    @return: a 3-tuple of C{(certificate_authority_certificate,
        server_private_key, server_certificate)}
    @rtype: L{tuple} of (L{sslverify.Certificate},
        L{OpenSSL.crypto.PKey, OpenSSL.crypto.X509})
    """
    commonNameForCA = x509.Name(
        [x509.NameAttribute(NameOID.COMMON_NAME, u'Testing Example CA')]
    )
    commonNameForServer = x509.Name(
        [x509.NameAttribute(NameOID.COMMON_NAME, u'Testing Example Server')]
    )
    oneDay = datetime.timedelta(1, 0, 0)
    privateKeyForCA = rsa.generate_private_key(
        public_exponent=65537,
        key_size=1024,
        backend=default_backend()
    )
    publicKeyForCA = privateKeyForCA.public_key()
    caCertificate = (
        x509.CertificateBuilder()
        .subject_name(commonNameForCA)
        .issuer_name(commonNameForCA)
        .not_valid_before(datetime.datetime.today() - oneDay)
        .not_valid_after(datetime.datetime.today() + oneDay)
        .serial_number(x509.random_serial_number())
        .public_key(publicKeyForCA)
        .add_extension(
            x509.BasicConstraints(ca=True, path_length=9), critical=True,
        )
        .sign(
            private_key=privateKeyForCA, algorithm=hashes.SHA256(),
            backend=default_backend()
        )
    )
    privateKeyForServer = rsa.generate_private_key(
        public_exponent=65537,
        key_size=1024,
        backend=default_backend()
    )
    publicKeyForServer = privateKeyForServer.public_key()
    serverCertificate = (
        x509.CertificateBuilder()
        .subject_name(commonNameForServer)
        .issuer_name(commonNameForCA)
        .not_valid_before(datetime.datetime.today() - oneDay)
        .not_valid_after(datetime.datetime.today() + oneDay)
        .serial_number(x509.random_serial_number())
        .public_key(publicKeyForServer)
        .add_extension(
            x509.BasicConstraints(ca=False, path_length=None), critical=True,
        )
        .add_extension(
            x509.SubjectAlternativeName(
                [x509.DNSName(serviceIdentity)]
            ),
            critical=True,
        )
        .sign(
            private_key=privateKeyForCA, algorithm=hashes.SHA256(),
            backend=default_backend()
        )
    )

    caSelfCert = Certificate.loadPEM(
        caCertificate.public_bytes(Encoding.PEM)
    )

    pkey = PKey.from_cryptography_key(privateKeyForServer)
    x509ServerCertificate = X509.from_cryptography(serverCertificate)

    return caSelfCert, pkey, x509ServerCertificate


def forever_httpbin(reactor, argv):
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
                        action="store_true",
                        default=False)
    parser.add_argument("--host",
                        help="The host on which the server will listen.",
                        type=str,
                        default="localhost")
    parser.add_argument("--port",
                        help="The on which the server will listen.",
                        type=int,
                        default=0)

    arguments = parser.parse_args(argv)

    host = arguments.host
    if sys.version_info.major == 2:
        host = host.decode('ascii')

    if arguments.https:
        caCert, privateKey, certificate = certificatesForAuthorityAndServer(
            host)

        contextFactory = CertificateOptions(privateKey=privateKey,
                                            certificate=certificate)

        endpoint = SSL4ServerEndpoint(reactor,
                                      arguments.port,
                                      sslContextFactory=contextFactory,
                                      interface=host)
    else:
        endpoint = TCP4ServerEndpoint(reactor,
                                      arguments.port,
                                      interface=host)

    wsgiThreads = ThreadPool()
    wsgiThreads.start()
    reactor.addSystemEventTrigger("before", "shutdown", wsgiThreads.stop)

    wsgiResource = WSGIResource(reactor, wsgiThreads, httpbin.app)

    listenDeferred = endpoint.listen(Site(wsgiResource))

    def whenListening(port):
        address = port.getHost()
        if arguments.https:
            description = _HTTPBinDescription(host=arguments.host,
                                              port=address.port,
                                              cacert=caCert.dumpPEM())
        else:
            description = _HTTPBinDescription(host=arguments.host,
                                              port=address.port)

        print(json.dumps(attr.asdict(description)))
        sys.stdout.flush()

        return Deferred()

    return listenDeferred.addCallback(whenListening)


if __name__ == '__main__':
    react(forever_httpbin, (sys.argv[1:],))
