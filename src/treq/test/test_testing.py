"""
In-memory treq returns stubbed responses.
"""
from functools import partial
from inspect import getmembers, isfunction

from mock import ANY

from six import text_type, binary_type, PY3

from twisted.trial.unittest import TestCase
from twisted.web.client import ResponseFailed
from twisted.web.error import SchemeNotSupported
from twisted.web.resource import Resource
from twisted.web.server import NOT_DONE_YET

import treq

from treq.testing import (
    HasHeaders,
    RequestSequence,
    StringStubbingResource,
    StubTreq
)


class _StaticTestResource(Resource):
    """Resource that always returns 418 "I'm a teapot"""
    isLeaf = True

    def render(self, request):
        request.setResponseCode(418)
        request.setHeader(b"x-teapot", b"teapot!")
        return b"I'm a teapot"


class _NonResponsiveTestResource(Resource):
    """Resource that returns NOT_DONE_YET and never finishes the request"""
    isLeaf = True

    def render(self, request):
        return NOT_DONE_YET


class _EventuallyResponsiveTestResource(Resource):
    """
    Resource that returns NOT_DONE_YET and stores the request so that something
    else can finish the response later.
    """
    isLeaf = True

    def render(self, request):
        self.stored_request = request
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
            'http://this/has/a/path/and/invalid/domain/name',
            'https://supports-https.com:8080',
            'http://supports-http.com:8080',
        )
        params = (None, {}, {b'page': [1]})
        headers = (None, {}, {b'x-random-header': [b'value', b'value2']})
        data = (None, b"", b'some data', b'{"some": "json"}')

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
                self.assertEqual([b'teapot!'],
                                 resp.headers.getRawHeaders(b'x-teapot'))
                self.assertEqual(b"" if verb == "HEAD" else b"I'm a teapot",
                                 self.successResultOf(stub.content(resp)))

    def test_handles_invalid_schemes(self):
        """
        Invalid URLs errback with a :obj:`SchemeNotSupported` failure, and does
        so even after a successful request.
        """
        stub = StubTreq(_StaticTestResource())
        self.failureResultOf(stub.get("x-unknown-1:"), SchemeNotSupported)
        self.successResultOf(stub.get("http://url.com"))
        self.failureResultOf(stub.get("x-unknown-2:"), SchemeNotSupported)

    def test_files_are_rejected(self):
        """
        StubTreq does not handle files yet - it should reject requests which
        attempt to pass files.
        """
        stub = StubTreq(_StaticTestResource())
        self.assertRaises(
            AssertionError, stub.request,
            'method', 'http://url', files=b'some file')

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
            stub.request('method', 'http://url', data=binary_type(b"")))
        self.successResultOf(
            stub.request('method', 'http://url', data=text_type("")))

    def test_handles_failing_asynchronous_requests(self):
        """
        Handle a resource returning NOT_DONE_YET and then canceling the
        request.
        """
        stub = StubTreq(_NonResponsiveTestResource())
        d = stub.request('method', 'http://url', data=b"1234")
        self.assertNoResult(d)
        d.cancel()
        self.failureResultOf(d, ResponseFailed)

    def test_handles_successful_asynchronous_requests(self):
        """
        Handle a resource returning NOT_DONE_YET and then later finishing the
        response.
        """
        rsrc = _EventuallyResponsiveTestResource()
        stub = StubTreq(rsrc)
        d = stub.request('method', 'http://example.com/', data=b"1234")
        self.assertNoResult(d)
        rsrc.stored_request.finish()
        stub.flush()
        resp = self.successResultOf(d)
        self.assertEqual(resp.code, 200)

    def test_handles_successful_asynchronous_requests_with_response_data(self):
        """
        Handle a resource returning NOT_DONE_YET and then sending some data in
        the response.
        """
        rsrc = _EventuallyResponsiveTestResource()
        stub = StubTreq(rsrc)
        d = stub.request('method', 'http://example.com/', data=b"1234")
        self.assertNoResult(d)

        chunks = []
        rsrc.stored_request.write(b'spam ')
        rsrc.stored_request.write(b'eggs')
        stub.flush()
        resp = self.successResultOf(d)
        d = stub.collect(resp, chunks.append)
        self.assertNoResult(d)
        self.assertEqual(b''.join(chunks), b'spam eggs')

        rsrc.stored_request.finish()
        stub.flush()
        self.successResultOf(d)

    def test_handles_successful_asynchronous_requests_with_streaming(self):
        """
        Handle a resource returning NOT_DONE_YET and then streaming data back
        gradually over time.
        """
        rsrc = _EventuallyResponsiveTestResource()
        stub = StubTreq(rsrc)
        d = stub.request('method', 'http://example.com/', data="1234")
        self.assertNoResult(d)

        chunks = []
        rsrc.stored_request.write(b'spam ')
        rsrc.stored_request.write(b'eggs')
        stub.flush()
        resp = self.successResultOf(d)
        d = stub.collect(resp, chunks.append)
        self.assertNoResult(d)
        self.assertEqual(b''.join(chunks), b'spam eggs')

        del chunks[:]
        rsrc.stored_request.write(b'eggs\r\nspam\r\n')
        stub.flush()
        self.assertNoResult(d)
        self.assertEqual(b''.join(chunks), b'eggs\r\nspam\r\n')

        rsrc.stored_request.finish()
        stub.flush()
        self.successResultOf(d)


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
        self.assertEqual(HasHeaders({b'A': [b'1'], b'b': [b'2']}),
                         {b'a': [b'1'], b'B': [b'2']})

    def test_case_sensitive_values(self):
        """
        The :obj:`HasHeaders` equality function does care about the case of
        the header value.
        """
        self.assertNotEqual(HasHeaders({b'a': [b'a']}), {b'a': [b'A']})

    def test_bytes_encoded_forms(self):
        """
        The :obj:`HasHeaders` equality function compares the bytes-encoded
        forms of both sets of headers.
        """
        self.assertEqual(HasHeaders({b'a': [b'a']}), {u'a': [u'a']})

        self.assertEqual(HasHeaders({u'b': [u'b']}), {b'b': [b'b']})

    def test_repr(self):
        """
        :obj:`HasHeaders` returns a nice string repr.
        """
        if PY3:
            reprOutput = "HasHeaders({b'a': [b'b']})"
        else:
            reprOutput = "HasHeaders({'a': ['b']})"
        self.assertEqual(reprOutput, repr(HasHeaders({b'A': [b'b']})))


class StringStubbingTests(TestCase):
    """
    Tests for :obj:`StringStubbingResource`.
    """
    def _get_response_for(self, expected_args, response):
        """
        Make a :obj:`IStringResponseStubs` that checks the expected args and
        returns the given response.
        """
        method, url, params, headers, data = expected_args

        def get_response_for(_method, _url, _params, _headers, _data):
            self.assertEqual((method, url, params, data),
                             (_method, _url, _params, _data))
            self.assertEqual(HasHeaders(headers), _headers)
            return response

        return get_response_for

    def test_interacts_successfully_with_istub(self):
        """
        The :obj:`IStringResponseStubs` is passed the correct parameters with
        which to evaluate the response, and the response is returned.
        """
        resource = StringStubbingResource(self._get_response_for(
            (b'DELETE', 'http://what/a/thing', {b'page': [b'1']},
             {b'x-header': [b'eh']}, b'datastr'),
            (418, {b'x-response': b'responseheader'}, b'response body')))

        stub = StubTreq(resource)

        d = stub.delete('http://what/a/thing', headers={b'x-header': b'eh'},
                        params={b'page': b'1'}, data=b'datastr')
        resp = self.successResultOf(d)
        self.assertEqual(418, resp.code)
        self.assertEqual([b'responseheader'],
                         resp.headers.getRawHeaders(b'x-response'))
        self.assertEqual(b'response body',
                         self.successResultOf(stub.content(resp)))


class RequestSequenceTests(TestCase):
    """
    Tests for :obj:`RequestSequence`.
    """
    def setUp(self):
        """
        Set up a way to report failures asynchronously.
        """
        self.async_failures = []

    def test_mismatched_request_causes_failure(self):
        """
        If a request is made that is not expected as the next request,
        causes a failure.
        """
        sequence = RequestSequence(
            [((b'get', 'https://anything/', {b'1': [b'2']},
               HasHeaders({b'1': [b'1']}), b'what'),
              (418, {}, b'body')),
             ((b'get', 'http://anything', {},
               HasHeaders({b'2': [b'1']}), b'what'),
              (202, {}, b'deleted'))],
            async_failure_reporter=self.async_failures.append)

        stub = StubTreq(StringStubbingResource(sequence))
        get = partial(stub.get, 'https://anything?1=2', data=b'what',
                      headers={b'1': b'1'})

        resp = self.successResultOf(get())

        self.assertEqual(418, resp.code)
        self.assertEqual(b'body', self.successResultOf(stub.content(resp)))
        self.assertEqual([], self.async_failures)

        resp = self.successResultOf(get())
        self.assertEqual(500, resp.code)
        self.assertEqual(1, len(self.async_failures))
        self.assertIn("Expected the next request to be",
                      self.async_failures[0])

        self.assertFalse(sequence.consumed())

    def test_unexpected_number_of_request_causes_failure(self):
        """
        If there are no more expected requests, making a request causes a
        failure.
        """
        sequence = RequestSequence(
            [],
            async_failure_reporter=self.async_failures.append)
        stub = StubTreq(StringStubbingResource(sequence))
        d = stub.get('https://anything', data=b'what', headers={b'1': b'1'})
        resp = self.successResultOf(d)
        self.assertEqual(500, resp.code)
        self.assertEqual(b'StubbingError',
                         self.successResultOf(resp.content()))
        self.assertEqual(1, len(self.async_failures))
        self.assertIn("No more requests expected, but request",
                      self.async_failures[0])

        # the expected requests have all been made
        self.assertTrue(sequence.consumed())

    def test_works_with_mock_any(self):
        """
        :obj:`mock.ANY` can be used with the request parameters.
        """
        sequence = RequestSequence(
            [((ANY, ANY, ANY, ANY, ANY), (418, {}, b'body'))],
            async_failure_reporter=self.async_failures.append)
        stub = StubTreq(StringStubbingResource(sequence))

        with sequence.consume(sync_failure_reporter=self.fail):
            d = stub.get('https://anything', data=b'what',
                         headers={b'1': b'1'})
            resp = self.successResultOf(d)
            self.assertEqual(418, resp.code)
            self.assertEqual(b'body', self.successResultOf(stub.content(resp)))

        self.assertEqual([], self.async_failures)

        # the expected requests have all been made
        self.assertTrue(sequence.consumed())

    def test_consume_context_manager_fails_on_remaining_requests(self):
        """
        If the `consume` context manager is used, if there are any remaining
        expecting requests, the test case will be failed.
        """
        sequence = RequestSequence(
            [((ANY, ANY, ANY, ANY, ANY), (418, {}, b'body'))] * 2,
            async_failure_reporter=self.async_failures.append)
        stub = StubTreq(StringStubbingResource(sequence))

        consume_failures = []
        with sequence.consume(sync_failure_reporter=consume_failures.append):

            self.successResultOf(stub.get('https://anything', data=b'what',
                                          headers={b'1': b'1'}))

        self.assertEqual(1, len(consume_failures))
        self.assertIn(
            "Not all expected requests were made.  Still expecting:",
            consume_failures[0])
        self.assertIn(
            "{0}(url={0}, params={0}, headers={0}, data={0})".format(
                repr(ANY)),
            consume_failures[0])

        # no asynchronous failures (mismatches, etc.)
        self.assertEqual([], self.async_failures)

    def test_async_failures_logged(self):
        """
        When no `async_failure_reporter` is passed async failures are logged by
        default.
        """
        sequence = RequestSequence([])
        stub = StubTreq(StringStubbingResource(sequence))

        with sequence.consume(self.fail):
            self.successResultOf(stub.get('https://example.com'))

        [failure] = self.flushLoggedErrors()
        self.assertIsInstance(failure.value, AssertionError)
