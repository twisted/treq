# coding: utf-8
"""
This test suite tests against webzoo frameworks:

https://github.com/klizhentas/webzoo

"""
from os import path, environ
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


def with_baseurl(method):
    def _request(self, url, *args, **kwargs):
        return method(self.baseurl + url, *args, pool=self.pool, **kwargs)
    return _request


class TreqPostTests(TestCase):
    baseurl = "http://localhost:{}".format(environ.get("TREQ_PORT"))
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

    @inlineCallbacks
    def test_multipart_post_params_and_pics(self):
        """This test upload various files and pictures"""

        cartman_png = open(fixture_file("cartman.png"), "rb")
        cartman_jpg = open(fixture_file("cartman.jpg"), "rb")
        cartman_gif = open(fixture_file("cartman.gif"), "rb")

        body_1 = u"Текстовое содержимое\r\n\r"
        body_2 = "Текстовое содержимое2"

        response = yield self.post(
            '/',
            data={
                "param-1": body_1,
                "param-2": body_2
            },
            files=[
                ("attachment-png", cartman_png),
                ("attachment-jpg", cartman_jpg),
                ("attachment-gif", cartman_gif)
            ])

        self.assertEqual(response.code, 200)
        body = yield treq.json_content(response)

        attachment = body['files']['attachment-png'][0]
        self.assertEqual("cartman.png", attachment['name'])
        self.assertEqual(
            open(fixture_file("cartman.png"), "rb").read(),
            b64decode(attachment['data']))

        attachment = body['files']['attachment-jpg'][0]
        self.assertEqual("cartman.jpg", attachment['name'])
        self.assertEqual(
            open(fixture_file("cartman.jpg"), "rb").read(),
            b64decode(attachment['data']))

        attachment = body['files']['attachment-gif'][0]
        self.assertEqual("cartman.gif", attachment['name'])
        self.assertEqual(
            open(fixture_file("cartman.gif"), "rb").read(),
            b64decode(attachment['data']))

        self.assertEqual(body['form']['param-1'][0], body_1)
        self.assertEqual(
            body['form']['param-2'][0], unicode(body_2, "utf-8"))

        yield print_response(response)

    @inlineCallbacks
    def test_multipart_post_params_with_same_names(self):
        """This test upload various files and pictures"""

        response = yield self.post(
            '/',
            data=[
                ("param", "body1"),
                ("param", "body2")
            ],
            files=[
                ("attachment", FileLikeObject("name1", "file1")),
                ("attachment", FileLikeObject("name2", "file2")),
                ("attachment", FileLikeObject("name3", "file3"))
            ])

        self.assertEqual(response.code, 200)
        body = yield treq.json_content(response)

        self.assertEqual(["body1", "body2"], body['form']['param'])

        files = body['files']['attachment']
        self.assertEqual("name1", files[0]["name"])
        self.assertEqual("name2", files[1]["name"])
        self.assertEqual("name3", files[2]["name"])

        self.assertEqual("file1", b64decode(files[0]["data"]))
        self.assertEqual("file2", b64decode(files[1]["data"]))
        self.assertEqual("file3", b64decode(files[2]["data"]))

        yield print_response(response)

    @inlineCallbacks
    def test_multipart_params_pics_and_unicode(self):
        """This test upload various files and pictures"""

        cartman_png = open(fixture_file("cartman.png"), "rb")
        cartman_jpg = open(fixture_file("cartman.jpg"), "rb")
        cartman_gif = open(fixture_file("cartman.gif"), "rb")

        body_1 = u"Текстовое содержимое\r\n\r"
        body_2 = "Текстовое содержимое2"

        response = yield self.post(
            '/',
            data={
                "param-1": body_1,
                "param-2": body_2
            },
            files=[
                ("attachment-png", cartman_png),
                ("attachment-jpg", cartman_jpg),
                ("attachment-gif", cartman_gif)
            ])

        self.assertEqual(response.code, 200)
        body = yield treq.json_content(response)

        attachment = body['files']['attachment-png'][0]
        self.assertEqual("cartman.png", attachment['name'])
        self.assertEqual(
            open(fixture_file("cartman.png"), "rb").read(),
            b64decode(attachment['data']))

        attachment = body['files']['attachment-jpg'][0]
        self.assertEqual("cartman.jpg", attachment['name'])
        self.assertEqual(
            open(fixture_file("cartman.jpg"), "rb").read(),
            b64decode(attachment['data']))

        attachment = body['files']['attachment-gif'][0]
        self.assertEqual("cartman.gif", attachment['name'])
        self.assertEqual(
            open(fixture_file("cartman.gif"), "rb").read(),
            b64decode(attachment['data']))

        self.assertEqual(body['form']['param-1'][0], body_1)
        self.assertEqual(
            body['form']['param-2'][0], unicode(body_2, "utf-8"))

        yield print_response(response)


class FileLikeObject(StringIO):
    def __init__(self, name, val):
        StringIO.__init__(self, val)
        self.name = name

    def read(*args, **kwargs):
        return StringIO.read(*args, **kwargs)


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


def fixtures_path():
    return path.join(
        path.abspath(
            path.dirname(__file__)), "fixtures")


def fixture_file(name):
    return path.join(fixtures_path(), name)
