"""
In-memory treq returns stubbed responses.
"""
from inspect import getmembers, isfunction

from twisted.web.resource import Resource

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

        for name, obj in treq_things:
            stub_thing = getattr(stub, name, None)
            self.assertTrue(  # sanity check
                isfunction(obj),
                "treq.{0} is not a function - StubTreq should be updated.")
            if obj.__module__ == "treq.api":
                self.assertTrue(
                    isfunction(stub_thing),
                    "StubTreq.{0} should be a function.".format(name))
            elif obj.__module__ == "treq.collect":
                self.assertEqual(
                    stub_thing, obj,
                    "StubTreq.{0} should just expose treq.{0}".format(
                        name))

    def test_providing_resource_to_stub_treq(self):
        """
        The resource provided to StubTreq is responds to every request no
        matter what the URI or parameters or data.
        """
        verbs = ('GET', 'PUT', 'HEAD', 'PATCH', 'DELETE', 'POST')
        urls = (
            'http://supports-http.com',
            'http://this/has/a/path/and/invalid/domain/name'
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
