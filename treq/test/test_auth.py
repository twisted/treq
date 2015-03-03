import mock

from twisted.web.client import Agent
from twisted.web.http_headers import Headers

from treq.test.util import TestCase
from treq.auth import _RequestHeaderSettingAgent, add_auth, \
    UnknownAuthConfig, HTTPDigestAuth, add_digest_auth


class RequestHeaderSettingAgentTests(TestCase):
    def setUp(self):
        self.agent = mock.Mock(Agent)

    def test_sets_headers(self):
        agent = _RequestHeaderSettingAgent(
            self.agent,
            Headers({'X-Test-Header': ['Test-Header-Value']}))

        agent.request('method', 'uri')

        self.agent.request.assert_called_once_with(
            'method', 'uri',
            headers=Headers({'X-Test-Header': ['Test-Header-Value']}),
            bodyProducer=None
        )

    def test_overrides_per_request_headers(self):
        agent = _RequestHeaderSettingAgent(
            self.agent,
            Headers({'X-Test-Header': ['Test-Header-Value']})
        )

        agent.request(
            'method', 'uri',
            Headers({'X-Test-Header': ['Unwanted-Value']})
        )

        self.agent.request.assert_called_once_with(
            'method', 'uri',
            headers=Headers({'X-Test-Header': ['Test-Header-Value']}),
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
            Headers({'authorization': ['Basic dXNlcm5hbWU6cGFzc3dvcmQ=']})
        )

    def test_add_basic_auth_huge(self):
        agent = mock.Mock()
        pwd = ('verylongpasswordthatextendsbeyondthepointwheremultiplel'
               'inesaregenerated')
        auth = ('Basic dXNlcm5hbWU6dmVyeWxvbmdwYXNzd29yZHRoYXRleHRlbmRz'
                'YmV5b25kdGhlcG9pbnR3aGVyZW11bHRpcGxlbGluZXNhcmVnZW5lcmF0ZWQ=')
        add_auth(agent, ('username', pwd))

        self._RequestHeaderSettingAgent.assert_called_once_with(
            agent,
            Headers({'authorization': [auth]}))

    def test_add_digest_auth(self):
        agent = mock.Mock()
        username = 'spam'
        password = 'eggs'

        add_digest_auth(agent, HTTPDigestAuth(username, password))

        self._RequestDigestAuthenticationAgent.assert_called_once_with(
            agent, username, password
        )

    def test_add_unknown_auth(self):
        agent = mock.Mock()
        self.assertRaises(UnknownAuthConfig, add_auth, agent, mock.Mock())
