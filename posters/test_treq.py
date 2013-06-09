"""
This test suite tests against webzoo frameworks:

https://github.com/klizhentas/webzoo

"""
# coding: utf-8
from StringIO import StringIO
from base64 import b64decode

from twisted.trial.unittest import TestCase
from twisted.internet.defer import inlineCallbacks
from twisted.internet.task import deferLater
from twisted.internet import reactor
from twisted.internet.tcp import Client

from twisted.web.client import HTTPConnectionPool

from treq.test.util import DEBUG

import treq

@inlineCallbacks
def print_response(response):
    if DEBUG:
        print
        print '---'
        print response.code
        print response.headers
        text = yield treq.text_content(response)
        print text
        print '---'

def with_baseurl(method):
    def _request(self, url, *args, **kwargs):
        return method(self.baseurl + url, *args, pool=self.pool, **kwargs)
    return _request


class TreqPostTests(TestCase):
    baseurl = "http://localhost:49160"
    post = with_baseurl(treq.post)

    def setUp(self):
        self.pool = HTTPConnectionPool(reactor, False)

    def tearDown(self):
        def _check_fds(_):
            # This appears to only be necessary for HTTPS tests.
            # For the normal HTTP tests then closeCachedConnections is
            # sufficient.
            fds = set(reactor.getReaders() + reactor.getReaders())
            if not [fd for fd in fds if isinstance(fd, Client)]:
                return

            return deferLater(reactor, 0, _check_fds, None)

        return self.pool.closeCachedConnections().addBoth(_check_fds)

    @inlineCallbacks
    def assert_data(self, response, expected_data):
        body = yield treq.json_content(response)
        self.assertIn('data', body)
        self.assertEqual(body['data'], expected_data)

    @inlineCallbacks
    def test_multipart_post_simple(self):

        response = yield self.post(
            '/',
            data={"a": "b"},
            files={"file1": FileLikeObject("david.txt", "file\r\n\r")})
        self.assertEqual(response.code, 200)

        body = yield treq.json_content(response)

        self.assertEqual(['b'], body['form']['a'])

        self.assertEqual('david.txt', body['files']['file1'][0]['name'])
        self.assertEqual(
            'file\r\n\r', b64decode(body['files']['file1'][0]['data']))
        yield print_response(response)

    @inlineCallbacks
    def test_multipart_post_unicode_filename(self):
        name = u"Имя файла.txt"
        file_body = u"Текстовое содержимое\r\n\r".encode("utf-8")
        response = yield self.post(
            '/',
            files={
                "file1": FileLikeObject(name, file_body)})

        self.assertEqual(response.code, 200)

        body = yield treq.json_content(response)

        self.assertEqual(name, body['files']['file1'][0]['name'])
        self.assertEqual(
            file_body,
            b64decode(body['files']['file1'][0]['data']))
        yield print_response(response)        


class FileLikeObject(StringIO):
    def __init__(self, name, val):
        StringIO.__init__(self, val)
        self.name = name

    def read(*args, **kwargs):
        return StringIO.read(*args, **kwargs)
