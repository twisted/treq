import re

import time
import base64
import hashlib
import urlparse

from twisted.web.http_headers import Headers
from twisted.python.randbytes import secureRandom
from requests.utils import parse_dict_header


_DIGEST_HEADER_PREFIX_REGEXP = re.compile(r'digest ', flags=re.IGNORECASE)


def generate_client_nonce(server_side_nonce):
    return hashlib.sha1(
        hashlib.sha1(server_side_nonce).digest() + secureRandom(16) + time.ctime()
    ).hexdigest()[:16]


def _md5_utf_digest(x):
    if isinstance(x, str):
        x = x.encode('utf-8')
    return hashlib.md5(x).hexdigest()


def _sha1_utf_digest(x):
    if isinstance(x, str):
        x = x.encode('utf-8')
    return hashlib.sha1(x).hexdigest()


def build_digest_authentication_header(agent, **kwargs):
    algo = kwargs.get('algorithm', 'MD5').upper()
    original_algo = kwargs.get('algorithm')
    qop = kwargs.get('qop', None)
    nonce = kwargs.get('nonce')
    opaque = kwargs.get('opaque', None)
    path_parsed = urlparse.urlparse(kwargs['path'])
    actual_path = path_parsed.path

    if path_parsed.query:
        actual_path += '?' + path_parsed.query

    a1 = '%s:%s:%s' % (
        agent.username,
        kwargs['realm'],
        agent.password
    )

    a2 = '%s:%s' % (
        kwargs['method'],
        actual_path
    )

    if algo == 'MD5' or algo == 'MD5-SESS':
        digest_hash_func = _md5_utf_digest
    elif algo == 'SHA':
        digest_hash_func = _sha1_utf_digest
    else:
        raise UnknownDigestAuthAlgorithm(algo)

    ha1 = digest_hash_func(a1)
    ha2 = digest_hash_func(a2)

    cnonce = generate_client_nonce(nonce)

    if algo == 'MD5-SESS':
        ha1 = digest_hash_func("%s:%s:%s" % (ha1, nonce, cnonce), algo)

    if kwargs['cached']:
        agent.digest_auth_cache[(kwargs['method'], kwargs['path'])]['c'] += 1
        nonce_count = agent.digest_auth_cache[(kwargs['method'], kwargs['path'])]['c']
    else:
        nonce_count = 1

    ncvalue = '%08x' % nonce_count
    if qop is None:
        response_digest = digest_hash_func("%s:%s" % (ha1, "%s:%s" % (ha2, nonce)))
    else:
        noncebit = "%s:%s:%s:%s:%s" % (nonce, ncvalue, cnonce.encode('utf-8'), 'auth', ha2)
        response_digest = digest_hash_func("%s:%s" % (ha1, noncebit))

    header_base = 'username="%s", realm="%s", nonce="%s", uri="%s", response="%s"' % (
        agent.username, kwargs['realm'], nonce, actual_path, response_digest
    )
    if opaque:
        header_base += ', opaque="%s"' % opaque
    if original_algo:
        header_base += ', algorithm="%s"' % original_algo
    if qop:
        header_base += ', qop="auth", nc=%s, cnonce="%s"' % (ncvalue, cnonce)
    if not kwargs['cached']:
        agent.digest_auth_cache[(kwargs['method'], kwargs['path'])] = {
            'p': kwargs,
            'c': 1
        }
    return 'Digest %s' % header_base


class HTTPDigestAuth(object):

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
            'Unsupported Quality Of Protection value passed: {qop}'.format(qop=qop)
        )


class UnknownDigestAuthAlgorithm(Exception):

    def __init__(self, algorithm):
        super(Exception, self).__init__(
            'Unsupported Digest Auth algorithm identifier passed: {algorithm}'.format(algorithm=algorithm)
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
        self.username = username
        self.password = password

    def _on_401_response(self, www_authenticate_response, method, uri, headers, bodyProducer):
        assert www_authenticate_response.code == 401, """Got invalid pre-authentication response code, probably URL
                                                        does not support Digest auth
                                                      """
        www_authenticate_header_string = www_authenticate_response.headers._rawHeaders.get('www-authenticate', [''])[0]
        digest_authentication_params = parse_dict_header(
            _DIGEST_HEADER_PREFIX_REGEXP.sub('', www_authenticate_header_string, count=1)
        )
        if digest_authentication_params.get('qop', None) is not None and \
            digest_authentication_params['qop'] != 'auth' and \
                'auth' not in digest_authentication_params['qop'].split(','):
            # We support only "auth" QoP as defined in rfc-2617 or rfc-2069
            raise UnknownQopForDigestAuth(digest_authentication_params['qop'])
        digest_authentication_header = build_digest_authentication_header(
            self,
            path=uri,
            method=method,
            cached=False,
            **digest_authentication_params
        )
        return self._perform_request(
            digest_authentication_header, method, uri, headers, bodyProducer
        )

    def _perform_request(self, digest_authentication_header, method, uri, headers, bodyProducer):
        if not headers:
            headers = Headers({'Authorization': digest_authentication_header})
        else:
            headers.addRawHeader('Authorization', digest_authentication_header)
        return self._agent.request(
            method, uri, headers=headers, bodyProducer=bodyProducer
        )

    def request(self, method, uri, headers=None, bodyProducer=None):
        if self.digest_auth_cache.get((method, uri), None) is None:
            # Perform first request for getting the realm; the client awaits for 401 response code here
            d = self._agent.request(method, uri, headers=headers, bodyProducer=None)
            d.addCallback(self._on_401_response, method, uri, headers, bodyProducer)
        else:
            digest_params_from_cache = self.digest_auth_cache.get((method, uri))['p']
            digest_params_from_cache['cached'] = True
            digest_authentication_header = build_digest_authentication_header(self, **digest_params_from_cache)
            d = self._perform_request(digest_authentication_header, method, uri, headers, bodyProducer)
        return d


def add_basic_auth(agent, username, password):
    creds = base64.b64encode('{0}:{1}'.format(username, password))
    return _RequestHeaderSettingAgent(
        agent,
        Headers({'Authorization': ['Basic {0}'.format(creds)]}))


def add_digest_auth(agent, http_digest_auth):
    return _RequestDigestAuthenticationAgent(agent, http_digest_auth.username, http_digest_auth.password)


def add_auth(agent, auth_config):
    if isinstance(auth_config, tuple):
        return add_basic_auth(agent, auth_config[0], auth_config[1])

    raise UnknownAuthConfig(auth_config)
