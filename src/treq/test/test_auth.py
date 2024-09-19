# Copyright (c) The treq Authors.
# See LICENSE for details.
from twisted.trial.unittest import SynchronousTestCase
from twisted.web.http_headers import Headers
from twisted.web.iweb import IAgent

from treq._agentspy import agent_spy
from treq.auth import _RequestHeaderSetterAgent, add_auth, UnknownAuthConfig


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

    def test_add_unknown_auth(self):
        """
        add_auth() raises UnknownAuthConfig when given anything other than
        a tuple.
        """
        agent, _ = agent_spy()
        invalidAuth = 1234

        self.assertRaises(UnknownAuthConfig, add_auth, agent, invalidAuth)
