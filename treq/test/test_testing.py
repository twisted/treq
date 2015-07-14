"""
In-memory treq returns stubbed responses.
"""
from inspect import getmembers, isfunction

from six import text_type, binary_type

from twisted.web.client import ResponseFailed
from twisted.web.error import SchemeNotSupported
from twisted.web.resource import Resource
from twisted.web.server import NOT_DONE_YET

from zope.interface import implementer
from zope.interface.verify import verifyObject

import treq

from treq.test.util import TestCase
from treq.testing import (
    HasHeaders,
    IStringResponseStubs,
    SequenceStringStubs,
    StringStubbingResource,
    StubTreq
)


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
        The resource provided to StubTreq responds to every request no
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

    def test_handles_invalid_schemes(self):
        """
        Invalid URLs errback with a :obj:`SchemeNotSupported` failure, and does
        so even after a successful request.
        """
        stub = StubTreq(_StaticTestResource())
        self.failureResultOf(stub.get(""), SchemeNotSupported)
        self.successResultOf(stub.get("http://url.com"))
        self.failureResultOf(stub.get(""), SchemeNotSupported)

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


class HasHeadersTests(TestCase):
    """
    Tests for :obj:`HasHeaders`.
    """
    def test_equality_and_strict_subsets_succeed(self):
        """
        The :obj:`HasHeaders` returns True if both sets of headers are
        equivalent, or the first is a strict subset of the second.
        """
        self.assertEqual(HasHeaders({'one': ['two', 'three']}),
                         {'one': ['two', 'three']},
                         "Equivalent headers do not match.")
        self.assertEqual(HasHeaders({'one': ['two', 'three']}),
                         {'one': ['two', 'three', 'four'],
                          'ten': ['six']},
                         "Strict subset headers do not match")

    def test_partial_or_zero_intersection_subsets_fail(self):
        """
        The :obj:`HasHeaders` returns False if both sets of headers overlap
        but the first is not a strict subset of the second.  It also returns
        False if there is no overlap.
        """
        self.assertNotEqual(HasHeaders({'one': ['two', 'three']}),
                            {'one': ['three', 'four']},
                            "Partial value overlap matches")
        self.assertNotEqual(HasHeaders({'one': ['two', 'three']}),
                            {'one': ['two']},
                            "Missing value matches")
        self.assertNotEqual(HasHeaders({'one': ['two', 'three']}),
                            {'ten': ['six']},
                            "Complete inequality matches")

    def test_case_insensitive_keys(self):
        """
        The :obj:`HasHeaders` equality function ignores the case of the header
        keys.
        """
        self.assertEqual(HasHeaders({'A': ['1'], 'b': ['2']}),
                         {'a': ['1'], 'B': ['2']})

    def test_case_sensitive_values(self):
        """
        The :obj:`HasHeaders` equality function does care about the case of
        the header value.
        """
        self.assertNotEqual(HasHeaders({'a': ['a']}), {'a': ['A']})

    def test_repr(self):
        """
        :obj:`HasHeaders` returns a nice string repr.
        """
        self.assertEqual("HasHeaders({'a': ['b']})",
                         repr(HasHeaders({'A': ['b']})))


class StringStubbingTests(TestCase):
    """
    Tests for :obj:`StringStubbingResource`.
    """
    def _get_response_stub(self, expected_args, response):
        """
        Make a :obj:`IStringResponseStubs` that checks the expected args and
        returns the given response.
        """
        method, url, params, headers, data = expected_args

        @implementer(IStringResponseStubs)
        class Stubber(object):
            def get_response_for(_, _method, _url, _params, _headers, _data):
                self.assertEqual((method, url, params, data),
                                 (_method, _url, _params, _data))
                self.assertEqual(HasHeaders(headers), _headers)
                return response

        return Stubber()

    def test_interacts_successfully_with_istub(self):
        """
        The :obj:`IStringResponseStubs` is passed the correct parameters with
        which to evaluate the response, and the response is returned.
        """
        resource = StringStubbingResource(self._get_response_stub(
            ('DELETE', 'http://what/a/thing', {'page': ['1']},
             {'x-header': ['eh']}, 'datastr'),
            (418, {'x-response': 'responseheader'}, 'response body')))

        stub = StubTreq(resource)

        d = stub.delete('http://what/a/thing', headers={'x-header': 'eh'},
                        params={'page': '1'}, data='datastr')
        resp = self.successResultOf(d)
        self.assertEqual(418, resp.code)
        self.assertEqual(['responseheader'],
                         resp.headers.getRawHeaders('x-response'))
        self.assertEqual('response body',
                         self.successResultOf(stub.content(resp)))


class _FakeTestCase(object):
    def __init__(self):
        self.cleanups = []

    def addCleanup(self, f, *args, **kwargs):
        self.cleanups.append((f, args, kwargs))

    def fail(self, msg=None):
        raise AssertionError(msg)

    def cleanUp(self):
        for f, args, kwargs in self.cleanups:
            f(*args, **kwargs)


class SequenceStringStubsTests(TestCase):
    """
    Tests for :obj:`SequenceStringStubs`.
    """
    def test_implements_interface(self):
        """
        :obj:`SequenceStringStubs` implements :obj:`IStringResponseStubs`.
        """
        verifyObject(IStringResponseStubs,
                     SequenceStringStubs([], _FakeTestCase()))

    def test_only_check_args_that_are_not_None(self):
        """
        `None` is used as a sentinel value to mean "anything for this value is
        valid".
        """
        testcase = _FakeTestCase()
        sequence = SequenceStringStubs(
            [(('get', None, None, None, None), (418, {}, 'body'))],
            testcase)
        stub = StubTreq(StringStubbingResource(sequence))
        d = stub.get('https://anything', data='what', headers={'1': '1'})
        resp = self.successResultOf(d)
        self.assertEqual(418, resp.code)
        self.assertEqual('body', self.successResultOf(stub.content(resp)))
        testcase.cleanUp()

        testcase = _FakeTestCase()
        sequence = SequenceStringStubs(
            [(('get', None, None, None, None), (418, {}, 'body'))],
            testcase)
        stub = StubTreq(StringStubbingResource(sequence))
        d = stub.delete('https://anything', data='what', headers={'1': '1'})
        resp = self.successResultOf(d)
        self.assertEqual(500, resp.code)
        self.assertRaises(AssertionError, testcase.cleanUp)

    def test_unexpected_next_request_causes_failure(self):
        """
        If a request is made that is not expected as the next request,
        causes a failure.
        """
        testcase = _FakeTestCase()
        sequence = SequenceStringStubs(
            [(('get', 'https://anything', {}, {'1': ['1']}, 'what'),
              (418, {}, 'body')),
             (('get', 'http://anything', {}, {'2': ['1']}, 'what'),
              (202, {}, 'deleted'))],
            testcase)
        stub = StubTreq(StringStubbingResource(sequence))

        d = stub.get('https://anything', data='what', headers={'1': '1'})
        resp = self.successResultOf(d)
        self.assertEqual(418, resp.code)
        self.assertEqual('body', self.successResultOf(stub.content(resp)))
        testcase.cleanUp()

        d = stub.get('https://anything', data='what', headers={'1': '1'})
        resp = self.successResultOf(d)
        self.assertEqual(500, resp.code)
        self.assertRaises(AssertionError, testcase.cleanUp)

    def test_no_more_expected_requests_causes_failure(self):
        """
        If there are no more expected requests, making a request causes a
        failure.
        """
        testcase = _FakeTestCase()
        sequence = SequenceStringStubs([], testcase)
        stub = StubTreq(StringStubbingResource(sequence))
        d = stub.get('https://anything', data='what', headers={'1': '1'})
        resp = self.successResultOf(d)
        self.assertEqual(500, resp.code)
        self.assertRaises(AssertionError, testcase.cleanUp)
