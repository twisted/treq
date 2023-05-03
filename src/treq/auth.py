# Copyright 2012-2020 The treq Authors.
# See LICENSE for details.
from __future__ import absolute_import, division, print_function
import re
import time
import hashlib

import binascii
from enum import Enum
from typing import Union, Optional
from urllib.parse import urlparse

from twisted.python.randbytes import secureRandom
from twisted.web.http_headers import Headers
from twisted.web.iweb import IAgent, IBodyProducer, IResponse
from zope.interface import implementer
from requests.utils import parse_dict_header


_DIGEST_HEADER_PREFIX_REGEXP = re.compile(b'digest ', flags=re.IGNORECASE)


class _DIGEST_ALGO(str, Enum):
    MD5 = 'MD5'
    MD5_SESS = 'MD5-SESS'
    SHA = 'SHA'
    SHA_256 = 'SHA-256'
    SHA_512 = 'SHA-512'


def _generate_client_nonce(server_side_nonce: str) -> str:
    return hashlib.sha1(
        hashlib.sha1(server_side_nonce.encode('utf-8')).digest() +
        secureRandom(16) + time.ctime().encode('utf-8')
    ).hexdigest()[:16]


def _md5_utf_digest(x: str) -> str:
    return hashlib.md5(x.encode('utf-8')).hexdigest()


def _sha1_utf_digest(x: str) -> str:
    return hashlib.sha1(x.encode('utf-8')).hexdigest()


def _sha256_utf_digest(x: str) -> str:
    return hashlib.sha256(x.encode('utf-8')).hexdigest()


def _sha512_utf_digest(x: str) -> str:
    return hashlib.sha512(x.encode('utf-8')).hexdigest()


class HTTPDigestAuth(object):
    """
    The container for HTTP Digest authentication credentials.

    This container will cache digest auth parameters,
    in order not to recompute these for each request.
    """

    def __init__(self, username: Union[str, bytes],
                 password: Union[str, bytes]):
        if isinstance(username, bytes):
            self._username: str = username.decode('utf-8')
        else:
            self._username: str = username
        if isinstance(password, bytes):
            self._password: str = password.decode('utf-8')
        else:
            self._password: str = password

        # (method,uri) --> digest auth cache
        self._digest_auth_cache = {}

    def _build_authentication_header(
            self, url: bytes, method: bytes, cached: bool, nonce: str,
            realm: str, qop: Optional[str] = None,
            algorithm: _DIGEST_ALGO = _DIGEST_ALGO.MD5,
            opaque: Optional[str] = None
            ) -> str:
        """
        Build the authorization header for credentials got from the server.
        Algorithm is accurately ported from https://github.com/psf/requests
            with small adjustments.
        See
        https://github.com/psf/requests/blob/v2.5.1/requests/auth.py#L72
            for details.

        :param algorithm: algorithm to be used for authentication,
            defaults to MD5, supported values are
            "MD5", "MD5-SESS" and "SHA"
        :param realm: HTTP Digest authentication realm
        :param nonce: "nonce" HTTP Digest authentication param
        :param qop: Quality Of Protection HTTP Digest auth param
        :param opaque: "opaque" HTTP Digest authentication param
             (should be sent back to server unchanged)
        :param cached: Identifies that authentication already have been
             performed for URI/method,
             and new request should use the same params as first
             authenticated request
        :param url: the URI path where we are authenticating
        :param method: HTTP method to be used when requesting

        :return: HTTP Digest authentication string
        """
        algo = algorithm.upper()
        p_parsed = urlparse(url.decode('utf-8'))
        # path is request-uri defined in RFC 2616 which should not be empty
        path = p_parsed.path or "/"
        if p_parsed.query:
            path += f"?{p_parsed.query}"

        A1 = f"{self._username}:{realm}:{self._password}"
        A2 = f"{method.decode('utf-8')}:{path}"

        if algo == _DIGEST_ALGO.MD5 or algo == _DIGEST_ALGO.MD5_SESS:
            digest_hash_func = _md5_utf_digest
        elif algo == _DIGEST_ALGO.SHA:
            digest_hash_func = _sha1_utf_digest
        elif algo == _DIGEST_ALGO.SHA_256:
            digest_hash_func = _sha256_utf_digest
        elif algo == _DIGEST_ALGO.SHA_512:
            digest_hash_func = _sha512_utf_digest
        else:
            raise ValueError(f"Unsupported Digest Auth algorithm identifier "
                             f"passed: {algo.name}")

        KD = lambda s, d: digest_hash_func(f"{s}:{d}")  # noqa:E731

        HA1 = digest_hash_func(A1)
        HA2 = digest_hash_func(A2)

        if cached:
            self._digest_auth_cache[(method, url)]['c'] += 1
            nonce_count = self._digest_auth_cache[(method, url)]['c']
        else:
            nonce_count = 1

        ncvalue = '%08x' % nonce_count

        cnonce = _generate_client_nonce(nonce)
        if algo == _DIGEST_ALGO.MD5_SESS:
            HA1 = digest_hash_func(f"{HA1}:{nonce}:{cnonce}")

        if not qop:
            respdig = KD(HA1, f"{HA2}:{nonce}")
        elif qop == "auth" or "auth" in qop.split(","):
            noncebit = f"{nonce}:{ncvalue}:{cnonce}:auth:{HA2}"
            respdig = KD(HA1, noncebit)
        else:
            raise UnknownQopForDigestAuth(qop)

        base = (
            f'username="{self._username}", realm="{realm}", nonce="{nonce}", '
            f'uri="{path}", response="{respdig}"'
        )
        if opaque:
            base += f', opaque="{opaque}"'
        if algorithm:
            base += f', algorithm="{algorithm}"'
        if qop:
            base += f', qop="auth", nc={ncvalue}, cnonce="{cnonce}"'

        if not cached:
            cache_params = {
                'path': url,
                'method': method,
                'cached': cached,
                'nonce': nonce,
                'realm': realm,
                'qop': qop,
                'algorithm': algorithm,
                'opaque': opaque
            }
            self._digest_auth_cache[(method, url)] = {
                'p': cache_params,
                'c': 1
            }

        return f"Digest {base}"

    def _cached_metadata_for(self, method: bytes, uri: bytes) -> Optional[dict]:
        return self._digest_auth_cache.get((method, uri))


class UnknownAuthConfig(Exception):
    """
    The authentication config provided couldn't be interpreted.
    """
    def __init__(self, config):
        super(Exception, self).__init__(
            '{0!r} not of a known type.'.format(config))


class UnknownQopForDigestAuth(Exception):

    def __init__(self, qop: Optional[str]):
        super(Exception, self).__init__(
            'Unsupported Quality Of Protection value passed: {qop}'.format(
                qop=qop
            )
        )


@implementer(IAgent)
class _RequestHeaderSetterAgent:
    """
    Wrap an agent to set request headers

    :ivar _agent: The wrapped agent.

    :ivar _request_headers:
        Headers to set on each request before forwarding it to the wrapped
        agent.
    """
    def __init__(self, agent, headers):
        self._agent = agent
        self._headers = headers

    def request(self, method, uri, headers=None, bodyProducer=None):
        if headers is None:
            requestHeaders = self._headers
        else:
            requestHeaders = headers.copy()
            for header, values in self._headers.getAllRawHeaders():
                requestHeaders.setRawHeaders(header, values)

        return self._agent.request(
            method, uri, headers=requestHeaders, bodyProducer=bodyProducer)


@implementer(IAgent)
class _RequestDigestAuthenticationAgent:

    def __init__(self, agent: IAgent, auth: HTTPDigestAuth):
        self._agent = agent
        self._auth = auth

    def _on_401_response(self, www_authenticate_response: IResponse,
                         method: bytes, uri: bytes,
                         headers: Optional[Headers],
                         bodyProducer: Optional[IBodyProducer]):
        """
        Handle the server`s 401 response, that is capable with authentication
            headers, build the Authorization header
        for

        :param www_authenticate_response: t.w.client.Response object
        :param method: HTTP method to be used to perform the request
        :param uri: URI to be used
        :param headers: Additional headers to be sent with the request,
            instead of "Authorization" header
        :param bodyProducer: IBodyProducer implementer instance that would be
            used to fetch the response body

        :return:
        """
        assert www_authenticate_response.code == 401, \
            """Got invalid pre-authentication response code, probably URL
            does not support Digest auth
        """
        www_authenticate_header_string = www_authenticate_response.\
            headers._rawHeaders.get(b'www-authenticate', [b''])[0]
        digest_header = _DIGEST_HEADER_PREFIX_REGEXP.sub(
            b'', www_authenticate_header_string, count=1
        )
        digest_authentication_params = \
            parse_dict_header(digest_header.decode("utf-8"))

        digest_authentication_header = \
            self._auth._build_authentication_header(
                uri,
                method,
                False,
                digest_authentication_params['nonce'],
                digest_authentication_params['realm'],
                qop=digest_authentication_params.get('qop', None),
                algorithm=_DIGEST_ALGO(digest_authentication_params.get(
                    'algorithm', 'MD5')),
                opaque=digest_authentication_params.get('opaque', None)
            )
        return self._perform_request(
            digest_authentication_header, method, uri, headers, bodyProducer
        )

    def _perform_request(self, digest_authentication_header: str,
                         method: bytes, uri: bytes, headers: Optional[Headers],
                         bodyProducer: Optional[IBodyProducer]):
        """
        Add Authorization header and perform the request with
            actual credentials

        :param digest_authentication_header: HTTP Digest Authorization
            header string
        :param method: HTTP method to be used to perform the request
        :param uri: URI to be used
        :param headers: Headers to be sent with the request
        :param bodyProducer: IBodyProducer implementer instance that would be
            used to fetch the response body

        :return: t.i.defer.Deferred (holding the result of the request)
        """
        if not headers:
            headers = Headers(
                {b'Authorization': digest_authentication_header.encode("utf-8")}
            )
        else:
            headers.addRawHeader(b'Authorization',
                                 digest_authentication_header.encode("utf-8"))
        return self._agent.request(
            method, uri, headers=headers, bodyProducer=bodyProducer
        )

    def request(self, method: bytes, uri: bytes,
                headers: Optional[Headers] = None,
                bodyProducer: Optional[IBodyProducer] = None):
        """
        Wrap the agent with HTTP Digest authentication.

        :param method: HTTP method to be used to perform the request
        :param uri: URI to be used
        :param headers: Headers to be sent with the request
        :param bodyProducer: IBodyProducer implementer instance that would be
            used to fetch the response body

        :return: t.i.defer.Deferred (holding the result of the request)
        """

        digest_auth_metadata = self._auth._cached_metadata_for(method, uri)

        if digest_auth_metadata is None:
            # Perform first request for getting the realm;
            # the client awaits for 401 response code here
            d = self._agent.request(b'GET', uri,
                                    headers=headers, bodyProducer=None)
            d.addCallback(self._on_401_response, method, uri,
                          headers, bodyProducer)
        else:
            # We have performed authentication on that URI already
            digest_params_from_cache = digest_auth_metadata['p']
            digest_params_from_cache['cached'] = True
            digest_authentication_header = \
                self._auth._build_authentication_header(
                    digest_params_from_cache['path'],
                    digest_params_from_cache['method'],
                    digest_params_from_cache['cached'],
                    digest_params_from_cache['nonce'],
                    digest_params_from_cache['realm'],
                    qop=digest_params_from_cache['qop'],
                    algorithm=digest_params_from_cache['algorithm'],
                    opaque=digest_params_from_cache['opaque']
                )
            d = self._perform_request(
                digest_authentication_header, method,
                uri, headers, bodyProducer
            )
        return d


def add_basic_auth(agent, username, password):
    # type: (IAgent, Union[str, bytes], Union[str, bytes]) -> IAgent
    """
    Wrap an agent to add HTTP basic authentication

    The returned agent sets the *Authorization* request header according to the
    basic authentication scheme described in :rfc:`7617`. This header contains
    the given *username* and *password* in plaintext, and thus should only be
    used over an encrypted transport (HTTPS).

    Note that the colon (``:``) is used as a delimiter between the *username*
    and *password*, so if either parameter includes a colon the interpretation
    of the *Authorization* header is server-defined.

    :param agent: Agent to wrap.
    :param username: The username.
    :param password: The password.

    :returns: :class:`~twisted.web.iweb.IAgent`
    """
    if not isinstance(username, bytes):
        username = username.encode('utf-8')
    if not isinstance(password, bytes):
        password = password.encode('utf-8')

    creds = binascii.b2a_base64(b'%s:%s' % (username, password)).rstrip(b'\n')
    return _RequestHeaderSetterAgent(
        agent,
        Headers({b'Authorization': [b'Basic ' + creds]}),
    )


def add_digest_auth(agent: IAgent, http_digest_auth: HTTPDigestAuth) -> IAgent:
    return _RequestDigestAuthenticationAgent(agent, http_digest_auth)


def add_auth(agent: IAgent, auth_config: Union[tuple, HTTPDigestAuth]):
    """
    Wrap an agent to perform authentication

    :param agent: Agent to wrap.

    :param auth_config:
        A ``('username', 'password')`` tuple --- see :func:`add_basic_auth`.

    :returns: :class:`~twisted.web.iweb.IAgent`

    :raises UnknownAuthConfig:
        When the format *auth_config* isn't supported.
    """
    if isinstance(auth_config, tuple):
        return add_basic_auth(agent, auth_config[0], auth_config[1])
    elif isinstance(auth_config, HTTPDigestAuth):
        return add_digest_auth(agent, auth_config)

    raise UnknownAuthConfig(auth_config)
