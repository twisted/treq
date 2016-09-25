import mock

from twisted.web.client import Agent
from twisted.web.http_headers import Headers
from twisted.web.iweb import IAgent

from treq.test.util import TestCase
from treq.auth import _RequestHeaderSettingAgent, add_auth, UnknownAuthConfig

from zope.interface import implementer


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
        self._RequestHeaderSettingAgent = self.rhsa_patcher.start()
        self.addCleanup(self.rhsa_patcher.stop)

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

    def test_auth_callable(self):
        agent = mock.Mock()

        @implementer(IAgent)
        class AuthorizingAgent(object):

            def __init__(self, agent):
                self.wrapped_agent = agent

            def request(self, method, uri, headers=None, bodyProducer=None):
                """Not called by this test"""

        wrapping_agent = add_auth(agent, AuthorizingAgent)
        self.assertIsInstance(wrapping_agent, AuthorizingAgent)
        self.assertIs(wrapping_agent.wrapped_agent, agent)

    def test_add_unknown_auth(self):
        agent = mock.Mock()
        self.assertRaises(UnknownAuthConfig, add_auth, agent, object())
