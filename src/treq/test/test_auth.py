# Copyright (c) The treq Authors.
# See LICENSE for details.
from twisted.trial.unittest import SynchronousTestCase
from twisted.web.http_headers import Headers
from twisted.web.iweb import IAgent

from treq._agentspy import agent_spy
from treq.auth import _RequestHeaderSetterAgent, add_auth, \
    UnknownAuthConfig, HTTPDigestAuth, _DIGEST_ALGO


class RequestHeaderSetterAgentTests(SynchronousTestCase):
    def setUp(self):
        self.agent, self.requests = agent_spy()

    def test_sets_headers(self):
        agent = _RequestHeaderSetterAgent(
            self.agent,
            Headers({b'X-Test-Header': [b'Test-Header-Value']}),
        )

        agent.request(b'method', b'uri')

        self.assertEqual(
            self.requests[0].headers,
            Headers({b'X-Test-Header': [b'Test-Header-Value']}),
        )

    def test_overrides_per_request_headers(self):
        agent = _RequestHeaderSetterAgent(
            self.agent,
            Headers({b'X-Test-Header': [b'Test-Header-Value']})
        )

        agent.request(
            b'method', b'uri',
            Headers({b'X-Test-Header': [b'Unwanted-Value']})
        )

        self.assertEqual(
            self.requests[0].headers,
            Headers({b'X-Test-Header': [b'Test-Header-Value']}),
        )

    def test_no_mutation(self):
        """
        The agent never mutates the headers passed to its request method.

        This reproduces https://github.com/twisted/treq/issues/314
        """
        requestHeaders = Headers({})
        agent = _RequestHeaderSetterAgent(
            self.agent,
            Headers({b'Added': [b'1']}),
        )

        agent.request(b'method', b'uri', headers=requestHeaders)

        self.assertEqual(requestHeaders, Headers({}))


class AddAuthTests(SynchronousTestCase):
    def test_add_basic_auth(self):
        """
        add_auth() wraps the given agent with one that adds an ``Authorization:
        Basic ...`` HTTP header that contains the given credentials.
        """
        agent, requests = agent_spy()
        authAgent = add_auth(agent, ('username', 'password'))

        authAgent.request(b'method', b'uri')

        self.assertTrue(IAgent.providedBy(authAgent))
        self.assertEqual(
            requests[0].headers,
            Headers({b'authorization': [b'Basic dXNlcm5hbWU6cGFzc3dvcmQ=']})
        )

    def test_add_basic_auth_huge(self):
        """
        The Authorization header doesn't include linebreaks, even if the
        credentials are so long that Python's base64 implementation inserts
        them.
        """
        agent, requests = agent_spy()
        pwd = ('verylongpasswordthatextendsbeyondthepointwheremultiplel'
               'inesaregenerated')
        expectedAuth = (
            b'Basic dXNlcm5hbWU6dmVyeWxvbmdwYXNzd29yZHRoYXRleHRlbmRzY'
            b'mV5b25kdGhlcG9pbnR3aGVyZW11bHRpcGxlbGluZXNhcmVnZW5lcmF0ZWQ='
        )
        authAgent = add_auth(agent, ('username', pwd))

        authAgent.request(b'method', b'uri')

        self.assertEqual(
            requests[0].headers,
            Headers({b'authorization': [expectedAuth]}),
        )

    def test_add_basic_auth_utf8(self):
        """
        Basic auth username and passwords given as `str` are encoded as UTF-8.

        https://developer.mozilla.org/en-US/docs/Web/HTTP/Authentication#Character_encoding_of_HTTP_authentication
        """
        agent, requests = agent_spy()
        auth = (u'\u16d7', u'\u16b9')
        authAgent = add_auth(agent, auth)

        authAgent.request(b'method', b'uri')

        self.assertEqual(
            requests[0].headers,
            Headers({b'Authorization': [b'Basic 4ZuXOuGauQ==']}),
        )

    def test_add_basic_auth_bytes(self):
        """
        Basic auth can be passed as `bytes`, allowing the user full control
        over the encoding.
        """
        agent, requests = agent_spy()
        auth = (b'\x01\x0f\xff', b'\xff\xf0\x01')
        authAgent = add_auth(agent, auth)

        authAgent.request(b'method', b'uri')

        self.assertEqual(
            requests[0].headers,
            Headers({b'Authorization': [b'Basic AQ//Ov/wAQ==']}),
        )

    def test_add_digest_auth(self):
        """
        add_auth() wraps the given agent with one that adds a ``Authorization:
        Digest ...`` authentication handler.
        """
        agent, requests = agent_spy()
        username = 'spam'
        password = 'eggs'
        auth = HTTPDigestAuth(username, password)
        authAgent = add_auth(agent, auth)

        authAgent.request(b'method', b'uri')

        self.assertEqual(
            authAgent._auth,
            auth,
        )
        self.assertEqual(
            authAgent._auth._username,
            username,
        )
        self.assertEqual(
            authAgent._auth._password,
            password,
        )

    def test_add_digest_auth_bytes(self):
        """
        Digest auth can be passed as `bytes` which will be encoded as utf-8.
        """
        agent, requests = agent_spy()
        username = b'spam'
        password = b'eggs'
        auth = HTTPDigestAuth(username, password)
        authAgent = add_auth(agent, auth)

        authAgent.request(b'method', b'uri')

        self.assertEqual(
            authAgent._auth,
            auth,
        )
        self.assertEqual(
            authAgent._auth._username,
            username.decode('utf-8'),
        )
        self.assertEqual(
            authAgent._auth._password,
            password.decode('utf-8'),
        )

    def test_add_unknown_auth(self):
        """
        add_auth() raises UnknownAuthConfig when given anything other than
        a tuple.
        """
        agent, _ = agent_spy()
        invalidAuth = 1234

        self.assertRaises(UnknownAuthConfig, add_auth, agent, invalidAuth)


class HttpDigestAuthTests(SynchronousTestCase):

    def setUp(self):
        self.maxDiff = None
        self._auth = HTTPDigestAuth('spam', 'eggs')

    def test_digest_unknown_algorithm(self):
        """
        _DIGEST_ALGO('UNKNOWN') raises ValueError when the algorithm is unknown.
        """
        with self.assertRaises(ValueError) as e:
            _DIGEST_ALGO('UNKNOWN')
        self.assertIn("'UNKNOWN' is not a valid _DIGEST_ALGO", str(e.exception))

    def test_build_authentication_header_md5_no_cache_no_qop(self):
        """
        _build_authentication_header test vectors using the MD5 algo and without
        qop parameter generate the expected digest header when cache is
        uninitialized.
        """
        auth_header = self._auth._build_authentication_header(
            b'/spam/eggs', b'GET', False,
            'b7f36bc385a662ed615f27bd9e94eecd',
            'me@dragons', qop=None,
            algorithm=_DIGEST_ALGO('MD5')
        )
        self.assertEquals(
            auth_header,
            'Digest username="spam", realm="me@dragons", ' +
            'nonce="b7f36bc385a662ed615f27bd9e94eecd", ' +
            'uri="/spam/eggs", ' +
            'response="fc05d17c55156b278132a52dc0dca526", algorithm="MD5"',
        )

    def test_build_authentication_header_md5_sess_no_cache(self):
        """
        _build_authentication_header test vectors using the MD5-SESS algo and
        with qop parameter generate the expected digest header when cache is
        uninitialized.
        """
        auth_header = self._auth._build_authentication_header(
            b'/spam/eggs?ham=bacon', b'GET', False,
            'b7f36bc385a662ed615f27bd9e94eecd',
            'me@dragons', qop='auth',
            algorithm=_DIGEST_ALGO('MD5-SESS')
        )
        self.assertRegex(
            auth_header,
            'Digest username="spam", realm="me@dragons", ' +
            'nonce="b7f36bc385a662ed615f27bd9e94eecd", ' +
            'uri="/spam/eggs\\?ham=bacon", ' +
            'response="([0-9a-f]{32})", ' +
            'algorithm="MD5-SESS", qop="auth", ' +
            'nc=00000001, cnonce="([0-9a-f]{16})"',
        )

    def test_build_authentication_header_sha_no_cache_no_qop(self):
        """
        _build_authentication_header test vectors using the SHA(SHA-1) algo and
        without the qop parameter generate the expected digest header when cache
        is uninitialized.
        """
        auth_header = self._auth._build_authentication_header(
            b'/spam/eggs', b'GET', False,
            'b7f36bc385a662ed615f27bd9e94eecd',
            'me@dragons', qop=None,
            algorithm=_DIGEST_ALGO('SHA')
        )

        self.assertEquals(
            auth_header,
            'Digest username="spam", realm="me@dragons", ' +
            'nonce="b7f36bc385a662ed615f27bd9e94eecd", ' +
            'uri="/spam/eggs", ' +
            'response="45420a4786287998bcb99dfde563c3a198109b31", ' +
            'algorithm="SHA"'
        )

    def test_build_authentication_header_sha512_cache(self):
        """
        _build_authentication_header test vectors using the SHA-512 algo and
        with the qop parameter generate the expected digest header when the
        digest cache is used for the second request.
        """
        # Emulate 1st request
        self._auth._build_authentication_header(
            b'/spam/eggs', b'GET', False,
            'b7f36bc385a662ed615f27bd9e94eecd',
            'me@dragons', qop='auth',
            algorithm=_DIGEST_ALGO('SHA-512')
        )
        # Get header after cached request
        auth_header = self._auth._build_authentication_header(
            b'/spam/eggs', b'GET', True,
            'b7f36bc385a662ed615f27bd9e94eecd',
            'me@dragons', qop='auth',
            algorithm=_DIGEST_ALGO('SHA-512')
        )

        # Make sure metadata was cached
        self.assertTrue(self._auth._cached_metadata_for(b'GET', b'/spam/eggs'))

        self.assertRegex(
            auth_header,
            'Digest username="spam", realm="me@dragons", ' +
            'nonce="b7f36bc385a662ed615f27bd9e94eecd", ' +
            'uri="/spam/eggs", ' +
            'response="([0-9a-f]{128})", ' +
            'algorithm="SHA-512", qop="auth", ' +
            'nc=00000002, cnonce="([0-9a-f]+?)"',
        )
