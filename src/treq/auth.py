from __future__ import absolute_import, division, print_function
import re
import time
import base64
import hashlib

from six.moves.urllib.parse import urlparse
from twisted.web.http_headers import Headers
from twisted.python.randbytes import secureRandom
from requests.utils import parse_dict_header


_DIGEST_HEADER_PREFIX_REGEXP = re.compile(b'digest ', flags=re.IGNORECASE)


def generate_client_nonce(server_side_nonce):
    return hashlib.sha1(
        hashlib.sha1(server_side_nonce).digest() +
        secureRandom(16) +
        time.ctime().encode('utf-8')
    ).hexdigest()[:16]


def _md5_utf_digest(x):
    return hashlib.md5(x).hexdigest()


def _sha1_utf_digest(x):
    return hashlib.sha1(x).hexdigest()


def _sha256_utf_digest(x):
    return hashlib.sha256(x).hexdigest()


def _sha512_utf_digest(x):
    return hashlib.sha512(x).hexdigest()


class HTTPDigestAuth(object):
    """
    The container for HTTP Digest authentication credentials
    """

    def __init__(self, username, password):
        self.username = username
        self.password = password


class UnknownAuthConfig(Exception):
    def __init__(self, config):
        super(Exception, self).__init__(
            '{0!r} not of a known type.'.format(config))


class UnknownQopForDigestAuth(Exception):

    def __init__(self, qop):
        super(Exception, self).__init__(
            'Unsupported Quality Of Protection value passed: {qop}'.format(
                qop=qop
            )
        )


class UnknownDigestAuthAlgorithm(Exception):

    def __init__(self, algorithm):
        super(Exception, self).__init__(
            'Unsupported Digest Auth algorithm identifier passed: {algorithm}'
            .format(algorithm=algorithm)
        )


class _RequestHeaderSettingAgent(object):
    def __init__(self, agent, request_headers):
        self._agent = agent
        self._request_headers = request_headers

    def request(self, method, uri, headers=None, bodyProducer=None):
        if headers is None:
            headers = self._request_headers
        else:
            for header, values in self._request_headers.getAllRawHeaders():
                headers.setRawHeaders(header, values)

        return self._agent.request(
            method, uri, headers=headers, bodyProducer=bodyProducer)


class _RequestDigestAuthenticationAgent(object):

    digest_auth_cache = {}

    def __init__(self, agent, username, password):
        self._agent = agent
        self._username = username.encode('utf-8')
        self._password = password.encode('utf-8')

    def _build_digest_authentication_header(
            self, path, method, cached, nonce, realm, qop=None,
            algorithm=b'MD5', opaque=None
            ):
        """
        Build the authorization header for credentials got from the server.
        Algorithm is accurately ported from http://python-requests.org
            with small adjustments.
        See
        https://github.com/kennethreitz/requests/blob/v2.5.1/requests/auth.py#L72
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
        :param path: the URI path where we are authenticating
        :param method: HTTP method to be used when requesting
        :return: HTTP Digest authentication string
        """
        algo = algorithm.upper()
        original_algo = algorithm
        path_parsed = urlparse(path)
        actual_path = path_parsed.path

        if path_parsed.query:
            actual_path += '?' + path_parsed.query

        a1 = self._username
        a1 += b':'
        a1 += realm
        a1 += b':'
        a1 += self._password

        a2 = method
        a2 += b':'
        a2 += actual_path

        if algo == b'MD5' or algo == b'MD5-SESS':
            digest_hash_func = _md5_utf_digest
        elif algo == b'SHA':
            digest_hash_func = _sha1_utf_digest
        elif algo == b'SHA-256':
            digest_hash_func = _sha256_utf_digest
        elif algo == b'SHA-512':
            digest_hash_func = _sha512_utf_digest
        else:
            raise UnknownDigestAuthAlgorithm(algo)

        ha1 = digest_hash_func(a1)
        ha2 = digest_hash_func(a2)

        cnonce = generate_client_nonce(nonce)

        if algo == b'MD5-SESS':
            sess = ha1.encode('utf-8')
            sess += b':'
            sess += nonce
            sess += b':'
            sess += cnonce.encode('utf-8')
            ha1 = digest_hash_func(sess)

        if cached:
            self.digest_auth_cache[(method, path)]['c'] += 1
            nonce_count = self.digest_auth_cache[
                (method, path)
            ]['c']
        else:
            nonce_count = 1

        ncvalue = '%08x' % nonce_count
        if qop is None:
            rd = ha1.encode('utf-8')
            rd += b':'
            rd += ha2
            rd += b':'
            rd += nonce
            response_digest = digest_hash_func(rd).encode('utf-8')
        else:
            rd = ha1.encode('utf-8')
            rd += b':'
            rd += nonce
            rd += b':'
            rd += ncvalue.encode('utf-8')
            rd += b':'
            rd += cnonce.encode('utf-8')
            rd += b':'
            rd += b'auth'
            rd += b':'
            rd += ha2.encode('utf-8')
            response_digest = digest_hash_func(rd).encode('utf-8')
        hb = b'username="'
        hb += self._username
        hb += b'", realm="'
        hb += realm
        hb += b'", nonce="'
        hb += nonce
        hb += b'", uri="'
        hb += actual_path
        hb += b'", response="'
        hb += response_digest
        hb += b'"'
        if opaque:
            hb += b', opaque="'
            hb += opaque
            hb += b'"'
        if original_algo:
            hb += b', algorithm="'
            hb += original_algo
            hb += b'"'
        if qop:
            hb += b', qop="auth", nc='
            hb += ncvalue.encode('utf-8')
            hb += b', cnonce="'
            hb += cnonce.encode('utf-8')
            hb += b'"'
        if not cached:
            cache_params = {
                'path': path,
                'method': method,
                'cached': cached,
                'nonce': nonce,
                'realm': realm,
                'qop': qop,
                'algorithm': algorithm,
                'opaque': opaque
            }
            self.digest_auth_cache[(method, path)] = {
                'p': cache_params,
                'c': 1
            }
        digest_res = b'Digest '
        digest_res += hb
        return digest_res

    def _on_401_response(self, www_authenticate_response, method, uri, headers,
                         bodyProducer):
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
        digest_authentication_params_str = parse_dict_header(
            digest_header.decode("utf-8")
        )
        digest_authentication_params = {
            k.encode('utf8'): v.encode('utf8')
            for k, v in digest_authentication_params_str.items()}
        if digest_authentication_params.get(b'qop', None) == b'auth':
            qop = digest_authentication_params[b'qop']
        elif b'auth' in digest_authentication_params.get(b'qop', None).\
                split(b','):
            qop = b'auth'
        else:
            # We support only "auth" QoP as defined in rfc-2617 or rfc-2069
            raise UnknownQopForDigestAuth(digest_authentication_params.
                                          get(b'qop', None))

        digest_authentication_header = \
            self._build_digest_authentication_header(
                uri,
                method,
                False,
                digest_authentication_params[b'nonce'],
                digest_authentication_params[b'realm'],
                qop=qop,
                algorithm=digest_authentication_params.get(b'algorithm',
                                                           b'MD5'),
                opaque=digest_authentication_params.get(b'opaque', None)
            )
        return self._perform_request(
            digest_authentication_header, method, uri, headers, bodyProducer
        )

    def _perform_request(self, digest_authentication_header, method, uri,
                         headers, bodyProducer):
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
            headers = Headers({b'Authorization': digest_authentication_header})
        else:
            headers.addRawHeader(b'Authorization',
                                 digest_authentication_header)
        return self._agent.request(
            method, uri, headers=headers, bodyProducer=bodyProducer
        )

    def request(self, method, uri, headers=None, bodyProducer=None):
        """
        Wrap the agent with HTTP Digest authentication.
        :param method: HTTP method to be used to perform the request
        :param uri: URI to be used
        :param headers: Headers to be sent with the request
        :param bodyProducer: IBodyProducer implementer instance that would be
            used to fetch the response body
        :return: t.i.defer.Deferred (holding the result of the request)
        """
        if self.digest_auth_cache.get((method, uri)) is None:
            # Perform first request for getting the realm;
            # the client awaits for 401 response code here
            d = self._agent.request(b'GET', uri,
                                    headers=headers, bodyProducer=None)
            d.addCallback(self._on_401_response, method, uri,
                          headers, bodyProducer)
        else:
            # We have performed authentication on that URI already
            digest_params_from_cache = self.digest_auth_cache.get(
                (method, uri)
            )['p']
            digest_params_from_cache['cached'] = True
            digest_authentication_header = \
                self._build_digest_authentication_header(
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
    creds = base64.b64encode(
        '{0}:{1}'.format(username, password).encode('ascii'))
    return _RequestHeaderSettingAgent(
        agent,
        Headers({b'Authorization': [b'Basic ' + creds]}))


def add_digest_auth(agent, http_digest_auth):
    return _RequestDigestAuthenticationAgent(
        agent, http_digest_auth.username, http_digest_auth.password
    )


def add_auth(agent, auth_config):
    if isinstance(auth_config, tuple):
        return add_basic_auth(agent, auth_config[0], auth_config[1])
    elif isinstance(auth_config, HTTPDigestAuth):
        return add_digest_auth(agent, auth_config)

    raise UnknownAuthConfig(auth_config)
