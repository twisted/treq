from twisted.internet import defer
from twisted.trial.unittest import SynchronousTestCase
from twisted.web import http

from treq.testing import StubTreq, HasHeaders
from treq.testing import RequestSequence, StringStubbingResource


@defer.inlineCallbacks
def make_a_request(treq):
    """
    Make a request using treq.
    """
    response = yield treq.get('http://an.example/foo', params={'a': 'b'},
                              headers={b'Accept': b'application/json'})
    if response.code == http.OK:
        result = yield response.json()
    else:
        message = yield response.text()
        raise Exception("Got an error from the server: {}".format(message))
    defer.returnValue(result)


class MakeARequestTests(SynchronousTestCase):
    """
    Test :func:`make_a_request()` using :mod:`treq.testing.RequestSequence`.
    """

    def test_200_ok(self):
        """On a 200 response, return the response's JSON."""
        req_seq = RequestSequence([
            ((b'get', 'http://an.example/foo', {b'a': [b'b']},
              HasHeaders({'Accept': ['application/json']}), b''),
             (http.OK, {b'Content-Type': b'application/json'}, b'{"status": "ok"}'))
        ])
        treq = StubTreq(StringStubbingResource(req_seq))

        with req_seq.consume(self.fail):
            result = self.successResultOf(make_a_request(treq))

        self.assertEqual({"status": "ok"}, result)

    def test_418_teapot(self):
        """On an unexpected response code, raise an exception"""
        req_seq = RequestSequence([
            ((b'get', 'http://an.example/foo', {b'a': [b'b']},
              HasHeaders({'Accept': ['application/json']}), b''),
             (418, {b'Content-Type': b'text/plain'}, b"I'm a teapot!"))
        ])
        treq = StubTreq(StringStubbingResource(req_seq))

        with req_seq.consume(self.fail):
            failure = self.failureResultOf(make_a_request(treq))

        self.assertEqual(u"Got an error from the server: I'm a teapot!",
                         failure.getErrorMessage())
