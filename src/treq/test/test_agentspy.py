# Copyright (c) The treq Authors.
# See LICENSE for details.
from io import BytesIO

from twisted.trial.unittest import SynchronousTestCase
from twisted.web.client import FileBodyProducer
from twisted.web.http_headers import Headers
from twisted.web.iweb import IAgent

from treq._agentspy import RequestRecord, agent_spy


class APISpyTests(SynchronousTestCase):
    """
    The agent_spy API provides an agent that records each request made to it.
    """

    def test_provides_iagent(self):
        """
        The agent returned by agent_spy() provides the IAgent interface.
        """
        agent, _ = agent_spy()

        self.assertTrue(IAgent.providedBy(agent))

    def test_records(self):
        """
        Each request made with the agent is recorded.
        """
        agent, requests = agent_spy()

        body = FileBodyProducer(BytesIO(b"..."))
        d1 = agent.request(b"GET", b"https://foo")
        d2 = agent.request(b"POST", b"http://bar", Headers({}))
        d3 = agent.request(b"PUT", b"https://baz", None, bodyProducer=body)

        self.assertEqual(
            requests,
            [
                RequestRecord(b"GET", b"https://foo", None, None, d1),
                RequestRecord(b"POST", b"http://bar", Headers({}), None, d2),
                RequestRecord(b"PUT", b"https://baz", None, body, d3),
            ],
        )

    def test_record_attributes(self):
        """
        Each parameter passed to `request` is available as an attribute of the
        RequestRecord. Additionally, the deferred returned by the call is
        available.
        """
        agent, requests = agent_spy()
        headers = Headers()
        body = FileBodyProducer(BytesIO(b"..."))

        deferred = agent.request(b"method", b"uri", headers=headers, bodyProducer=body)

        [rr] = requests
        self.assertIs(rr.method, b"method")
        self.assertIs(rr.uri, b"uri")
        self.assertIs(rr.headers, headers)
        self.assertIs(rr.bodyProducer, body)
        self.assertIs(rr.deferred, deferred)

    def test_type_validation(self):
        """
        The request method enforces correctness by raising TypeError when
        passed parameters of the wrong type.
        """
        agent, _ = agent_spy()

        self.assertRaises(TypeError, agent.request, u"method not bytes", b"uri")
        self.assertRaises(TypeError, agent.request, b"method", u"uri not bytes")
        self.assertRaises(
            TypeError, agent.request, b"method", b"uri", {"not": "headers"}
        )
        self.assertRaises(
            TypeError, agent.request, b"method", b"uri", None, b"not ibodyproducer"
        )
