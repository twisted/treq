import mock

from twisted.trial.unittest import TestCase
from twisted.web.client import Agent
from twisted.web.http_headers import Headers

from treq.auth import _RequestHeaderSettingAgent, add_auth, \
    UnknownAuthConfig, HTTPDigestAuth, UnknownDigestAuthAlgorithm, add_digest_auth


class RequestHeaderSettingAgentTests(TestCase):
    def setUp(self):
        self.agent = mock.Mock(Agent)

    def test_sets_headers(self):
        agent = _RequestHeaderSettingAgent(
            self.agent,
            Headers({b'X-Test-Header': [b'Test-Header-Value']}))

        agent.request('method', 'uri')

        self.agent.request.assert_called_once_with(
            'method', 'uri',
            headers=Headers({b'X-Test-Header': [b'Test-Header-Value']}),
            bodyProducer=None
        )

    def test_overrides_per_request_headers(self):
        agent = _RequestHeaderSettingAgent(
            self.agent,
            Headers({b'X-Test-Header': [b'Test-Header-Value']})
        )

        agent.request(
            'method', 'uri',
            Headers({b'X-Test-Header': [b'Unwanted-Value']})
        )

        self.agent.request.assert_called_once_with(
            'method', 'uri',
            headers=Headers({b'X-Test-Header': [b'Test-Header-Value']}),
            bodyProducer=None
        )


class AddAuthTests(TestCase):
    def setUp(self):
        self.rhsa_patcher = mock.patch('treq.auth._RequestHeaderSettingAgent')
        self.rdaa_patcher = mock.patch(
            'treq.auth._RequestDigestAuthenticationAgent'
        )
        self._RequestDigestAuthenticationAgent = self.rdaa_patcher.start()
        self._RequestHeaderSettingAgent = self.rhsa_patcher.start()
        self.addCleanup(self.rhsa_patcher.stop)
        self.addCleanup(self.rdaa_patcher.stop)

    def test_add_basic_auth(self):
        agent = mock.Mock()

        add_auth(agent, ('username', 'password'))

        self._RequestHeaderSettingAgent.assert_called_once_with(
            agent,
            Headers({b'authorization': [b'Basic dXNlcm5hbWU6cGFzc3dvcmQ=']})
        )

    def test_add_basic_auth_huge(self):
        agent = mock.Mock()
        pwd = ('verylongpasswordthatextendsbeyondthepointwheremultiplel'
               'inesaregenerated')
        auth = (b'Basic dXNlcm5hbWU6dmVyeWxvbmdwYXNzd29yZHRoYXRleHRlbmRzY'
                b'mV5b25kdGhlcG9pbnR3aGVyZW11bHRpcGxlbGluZXNhcmVnZW5lcmF0ZWQ=')
        add_auth(agent, ('username', pwd))

        self._RequestHeaderSettingAgent.assert_called_once_with(
            agent,
            Headers({b'authorization': [auth]}))

    def test_add_digest_auth(self):
        agent = mock.Mock()
        username = 'spam'
        password = 'eggs'
        auth = HTTPDigestAuth(username, password)

        add_digest_auth(agent, auth)

        self._RequestDigestAuthenticationAgent.assert_called_once_with(
            agent, auth
        )

    def test_add_unknown_auth(self):
        agent = mock.Mock()
        self.assertRaises(UnknownAuthConfig, add_auth, agent, mock.Mock())



class HttpDigestAuthTests(TestCase):

    def setUp(self):
        self._auth = HTTPDigestAuth('spam', 'eggs')

    def test_build_authentication_header_unknown_alforythm(self):
        self.assertRaises(UnknownDigestAuthAlgorithm, self._auth.build_authentication_header,
            b'/spam/eggs', b'GET', False,
            b'b7f36bc385a662ed615f27bd9e94eecd',
            b'me@dragons', qop=None,
            algorithm=b'UNKNOWN')

    def test_build_authentication_header_md5_no_cache_no_qop(self):
        auth_header = self._auth.build_authentication_header(
            b'/spam/eggs', b'GET', False,
            b'b7f36bc385a662ed615f27bd9e94eecd',
            b'me@dragons', qop=None,
            algorithm=b'MD5'
        )
        self.assertEquals(
            auth_header,
            b'Digest username="spam", realm="me@dragons", ' +
            b'nonce="b7f36bc385a662ed615f27bd9e94eecd", ' +
            b'uri="/spam/eggs", ' +
            b'response="fc05d17c55156b278132a52dc0dca526", algorithm="MD5"',
        )

    def test_build_authentication_header_md5_sess_no_cache(self):
        auth_header = self._auth.build_authentication_header(
            b'/spam/eggs?ham=bacon', b'GET', False,
            b'b7f36bc385a662ed615f27bd9e94eecd',
            b'me@dragons', qop='auth',
            algorithm=b'MD5-SESS'
        )
        self.assertRegex(
            auth_header,
            b'Digest username="spam", realm="me@dragons", ' +
            b'nonce="b7f36bc385a662ed615f27bd9e94eecd", ' +
            b'uri="/spam/eggs\?ham=bacon", ' +
            b'response="([0-9a-f]{32})", ' +
            b'algorithm="MD5-SESS", qop="auth", ' +
            b'nc=00000001, cnonce="([0-9a-f]{16})"',
        )

    def test_build_authentication_header_sha_no_cache_no_qop(self):
        auth_header = self._auth.build_authentication_header(
            b'/spam/eggs', b'GET', False,
            b'b7f36bc385a662ed615f27bd9e94eecd',
            b'me@dragons', qop=None,
            algorithm=b'SHA'
        )

        self.assertEquals(
            auth_header,
            b'Digest username="spam", realm="me@dragons", ' +
            b'nonce="b7f36bc385a662ed615f27bd9e94eecd", ' +
            b'uri="/spam/eggs", ' +
            b'response="45420a4786287998bcb99dfde563c3a198109b31", ' +
            b'algorithm="SHA"'
        )


    def test_build_authentication_header_sha512_cache(self):
        # Emulate 1st request
        self._auth.build_authentication_header(
            b'/spam/eggs', b'GET', False,
            b'b7f36bc385a662ed615f27bd9e94eecd',
            b'me@dragons', qop='auth',
            algorithm=b'SHA-512'
        )
        # Get header after cached request
        auth_header = self._auth.build_authentication_header(
            b'/spam/eggs', b'GET', True,
            b'b7f36bc385a662ed615f27bd9e94eecd',
            b'me@dragons', qop='auth',
            algorithm=b'SHA-512'
        )

        # Make sure metadata was cached
        self.assertTrue(self._auth.cached_metadata_for(b'GET', b'/spam/eggs'))

        self.assertRegex(
            auth_header,
            b'Digest username="spam", realm="me@dragons", ' +
            b'nonce="b7f36bc385a662ed615f27bd9e94eecd", ' +
            b'uri="/spam/eggs", ' +
            b'response="([0-9a-f]{128})", ' +
            b'algorithm="SHA-512", qop="auth", ' +
            b'nc=00000002, cnonce="([0-9a-f]+?)"',
        )
