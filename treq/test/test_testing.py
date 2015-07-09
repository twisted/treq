"""
In-memory treq returns stubbed responses.
"""
from inspect import getmembers, isfunction

from six import text_type, binary_type

from twisted.web.client import ResponseFailed
from twisted.web.resource import Resource
from twisted.web.server import NOT_DONE_YET

import treq

from treq.test.util import TestCase
from treq.testing import StubTreq


class _StaticTestResource(Resource):
    """Resource that always returns 418 "I'm a teapot"""
    isLeaf = True

    def render(self, request):
        request.setResponseCode(418)
        request.setHeader("x-teapot", "teapot!")
        return "I'm a teapot"


class _NonResponsiveTestResource(Resource):
    """Resource that returns NOT_DONE_YET and never finishes the request"""
    isLeaf = True

    def render(self, request):
        return NOT_DONE_YET


class StubbingTests(TestCase):
    """
    Tests for :class:`StubTreq`.
    """
    def test_stubtreq_provides_all_functions_in_treq_all(self):
        """
        Every single function and attribute exposed by :obj:`treq.__all__` is
        provided by :obj:`StubTreq`.
        """
        treq_things = [(name, obj) for name, obj in getmembers(treq)
                       if name in treq.__all__]
        stub = StubTreq(_StaticTestResource())

        api_things = [(name, obj) for name, obj in treq_things
                      if obj.__module__ == "treq.api"]
        content_things = [(name, obj) for name, obj in treq_things
                          if obj.__module__ == "treq.content"]

        # sanity checks - this test should fail if treq exposes a new API
        # without changes being made to StubTreq and this test.
        msg = ("At the time this test was written, StubTreq only knew about "
               "treq exposing functions from treq.api and treq.content.  If "
               "this has changed, StubTreq will need to be updated, as will "
               "this test.")
        self.assertTrue(all(isfunction(obj) for name, obj in treq_things), msg)
        self.assertEqual(set(treq_things), set(api_things + content_things),
                         msg)

        for name, obj in api_things:
            self.assertTrue(
                isfunction(getattr(stub, name, None)),
                "StubTreq.{0} should be a function.".format(name))

        for name, obj in content_things:
            self.assertIs(
                getattr(stub, name, None), obj,
                "StubTreq.{0} should just expose treq.{0}".format(name))

    def test_providing_resource_to_stub_treq(self):
        """
        The resource provided to StubTreq is responds to every request no
        matter what the URI or parameters or data.
        """
        verbs = ('GET', 'PUT', 'HEAD', 'PATCH', 'DELETE', 'POST')
        urls = (
            'http://supports-http.com',
            'https://supports-https.com',
            'http://this/has/a/path/and/invalid/domain/name'
            'https://supports-https.com:8080',
            'http://supports-http.com:8080',
        )
        params = (None, {}, {'page': [1]})
        headers = (None, {}, {'x-random-header': ['value', 'value2']})
        data = (None, "", 'some data', '{"some": "json"}')

        stub = StubTreq(_StaticTestResource())

        combos = (
            (verb, {"url": url, "params": p, "headers": h, "data": d})
            for verb in verbs
            for url in urls
            for p in params
            for h in headers
            for d in data
        )
        for combo in combos:
            verb, kwargs = combo
            deferreds = (stub.request(verb, **kwargs),
                         getattr(stub, verb.lower())(**kwargs))
            for d in deferreds:
                resp = self.successResultOf(d)
                self.assertEqual(418, resp.code)
                self.assertEqual(['teapot!'],
                                 resp.headers.getRawHeaders('x-teapot'))
                self.assertEqual("" if verb == "HEAD" else "I'm a teapot",
                                 self.successResultOf(stub.content(resp)))

    def test_files_are_rejected(self):
        """
        StubTreq does not handle files yet - it should reject requests which
        attempt to pass files.
        """
        stub = StubTreq(_StaticTestResource())
        self.assertRaises(
            AssertionError, stub.request,
            'method', 'http://url', files='some file')

    def test_passing_in_strange_data_is_rejected(self):
        """
        StubTreq rejects data that isn't list/dictionary/tuple/bytes/unicode.
        """
        stub = StubTreq(_StaticTestResource())
        self.assertRaises(
            AssertionError, stub.request, 'method', 'http://url',
            data=object())
        self.successResultOf(stub.request('method', 'http://url', data={}))
        self.successResultOf(stub.request('method', 'http://url', data=[]))
        self.successResultOf(stub.request('method', 'http://url', data=()))
        self.successResultOf(
            stub.request('method', 'http://url', data=binary_type("")))
        self.successResultOf(
            stub.request('method', 'http://url', data=text_type("")))

    def test_handles_asynchronous_requests(self):
        """
        Handle a resource returning NOT_DONE_YET.
        """
        stub = StubTreq(_NonResponsiveTestResource())
        d = stub.request('method', 'http://url', data="1234")
        self.assertNoResult(d)
        d.cancel()
        self.failureResultOf(d, ResponseFailed)
