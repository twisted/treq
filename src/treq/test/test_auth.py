from twisted.trial.unittest import SynchronousTestCase
from twisted.web.iweb import IAgent
from twisted.web.http_headers import Headers

from treq.auth import _RequestHeaderSettingAgent, add_auth, UnknownAuthConfig
from treq._recorder import recorder


class RequestHeaderSettingAgentTests(SynchronousTestCase):
    def setUp(self):
        self.agent, self.requests = recorder()

    def test_sets_headers(self):
        agent = _RequestHeaderSettingAgent(
            self.agent,
            Headers({b'X-Test-Header': [b'Test-Header-Value']}),
        )

        agent.request(b'method', b'uri')

        self.assertEqual(
            self.requests[0].headers,
            Headers({b'X-Test-Header': [b'Test-Header-Value']}),
        )

    def test_overrides_per_request_headers(self):
        agent = _RequestHeaderSettingAgent(
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


class AddAuthTests(SynchronousTestCase):
    def test_add_basic_auth(self):
        """
        add_auth() wraps the given agent with one that adds an ``Authorization:
        Basic ...`` HTTP header that contains the given credentials.
        """
        agent, requests = recorder()
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
        agent, requests = recorder()
        pwd = ('verylongpasswordthatextendsbeyondthepointwheremultiplel'
               'inesaregenerated')
        auth = (b'Basic dXNlcm5hbWU6dmVyeWxvbmdwYXNzd29yZHRoYXRleHRlbmRzY'
                b'mV5b25kdGhlcG9pbnR3aGVyZW11bHRpcGxlbGluZXNhcmVnZW5lcmF0ZWQ=')
        authAgent = add_auth(agent, ('username', pwd))

        authAgent.request(b'method', b'uri')

        self.assertEqual(
            requests[0].headers,
            Headers({b'authorization': [auth]}),
        )

    def test_add_unknown_auth(self):
        """
        add_auth() raises UnknownAuthConfig when given anything other than
        a tuple.
        """
        agent, _ = recorder()
        invalidAuth = 1234

        self.assertRaises(UnknownAuthConfig, add_auth, agent, invalidAuth)
