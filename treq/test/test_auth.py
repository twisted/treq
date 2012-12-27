import mock

from twisted.web.client import Agent
from twisted.web.http_headers import Headers

from treq.test.util import TestCase
from treq.auth import RequestHeaderSettingAgent, add_auth


class RequestHeaderSettingAgentTests(TestCase):
    def setUp(self):
        self.agent = mock.Mock(Agent)

    def test_sets_headers(self):
        agent = RequestHeaderSettingAgent(
            self.agent,
            Headers({'X-Test-Header': ['Test-Header-Value']}))

        agent.request('method', 'uri')

        self.agent.request.assert_called_once_with(
            'method', 'uri',
            headers=Headers({'X-Test-Header': ['Test-Header-Value']}),
            bodyProducer=None
        )

    def test_overrides_per_request_headers(self):
        agent = RequestHeaderSettingAgent(
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
        self.rhsa_patcher = mock.patch('treq.auth.RequestHeaderSettingAgent')
        self.RequestHeaderSettingAgent = self.rhsa_patcher.start()
        self.addCleanup(self.rhsa_patcher.stop)

    def test_add_basic_auth(self):
        agent = mock.Mock()

        add_auth(agent, ('username', 'password'))

        self.RequestHeaderSettingAgent.assert_called_once_with(
            agent,
            Headers({'authorization': ['Basic dXNlcm5hbWU6cGFzc3dvcmQ=']})
        )
