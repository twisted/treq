import mimetypes

from StringIO import StringIO
from io import BytesIO
from uuid import uuid4


from twisted.internet import defer, task
from twisted.web.iweb import UNKNOWN_LENGTH, IBodyProducer

from twisted.web.client import  FileBodyProducer

from zope.interface import implementer

CRLF = b"\r\n"

@implementer(IBodyProducer)
class MultiPartProducer(object):

    def __init__(self, fields, boundary=None, cooperator=task):
        self._fields = list(_sorted(_converted(fields)))
        self._currentProducer = None
        self._cooperate = cooperator.cooperate

        self.boundary = boundary or uuid4().hex
        self.length = self._calculateLength()

    def startProducing(self, consumer):
        self._task = self._cooperate(self._writeLoop(consumer))
        d = self._task.whenDone()
        def maybeStopped(reason):
            reason.trap(task.TaskStopped)
            return defer.Deferred()
        d.addCallbacks(lambda ignored: None, maybeStopped)
        return d

    def stopProducing(self):
        if self._currentProducer:
            self._currentProducer.stopProducing()
        self._task.stop()

    def pauseProducing(self):
        if self._currentProducer:
            self._currentProducer.pauseProducing()
        self._task.pause()

    def resumeProducing(self):
        if self._currentProducer:
            self._currentProducer.resumeProducing()
        self._task.resume()

    def _calculateLength(self):
        consumer = _LengthConsumer()
        for i in self._writeLoop(consumer):
            pass
        return consumer.length

    def _getBoundary(self, final=False):
        return b"--{}{}".format(
            self.boundary, b"--" if final else b"")

    def _writeLoop(self, consumer):
        for index, (name, value) in enumerate(self._fields):
            consumer.write(
                (CRLF if index != 0 else "") + self._getBoundary() + CRLF)
            yield self._writeField(name, value, consumer)

        consumer.write(CRLF + self._getBoundary(final=True) + CRLF)

    def _writeField(self, name, value, consumer):
        if isinstance(value, unicode):
            self._writeString(name, value, consumer)
        elif isinstance(value, tuple):
            filename, producer = value
            return self._writeFile(name, filename, producer, consumer)

    def _writeString(self, name, value, consumer):
        consumer.write(
            _h_content_disposition(name) + CRLF + CRLF)
        consumer.write(value.encode("utf-8"))
        self._currentProducer = None

    def _writeFile(self, name, filename, producer, consumer):
        consumer.write(
            _h_content_disposition(name, filename) + CRLF)
        if filename:
            consumer.write(
                _h_content_type(_content_type(filename)) + CRLF)
        consumer.write(b"Content-Length: %s" %(producer.length) + CRLF + CRLF)

        self._currentProducer = producer
        if isinstance(consumer, _LengthConsumer):
            consumer.write(producer.length)
        else:
            return producer.startProducing(consumer)


def _escape(value):
    return value.replace(u"\r", u"").replace(u"\n", u"").replace(u'"', u'\\"')

def _enforce_unicode(value):
    if isinstance(value, unicode):
        return value
    elif isinstance(value, str):
        # we got a byte string, and we have no ide what's the encoding of it
        # we can only assume that it's something cool
        try:
            return unicode(value, "utf-8")
        except UnicodeDecodeError:
            raise ValueError(
                "Supplied raw bytes that are not ascii/utf-8."
                " When supplying raw string make sure it's ascii or utf-8"
                ", or work with unicode if you are not sure")
    else:
        raise ValueError(
            "Unsupported field type: {}".format(value.__class__.__name__))


def _converted(fields):
    for name, value in fields.iteritems():
        name = _enforce_unicode(name)

        if isinstance(value, (tuple, list)):
            if len(value) != 2:
                raise ValueError("Please provide (filename, file like object)")

            filename, fobj = value
            yield name, (_enforce_unicode(filename), IBodyProducer(fobj))

        elif isinstance(value, (StringIO, BytesIO, file)):
            yield name, (None, IBodyProducer(value))

        elif isinstance(value, (str, unicode)):
            yield name, _enforce_unicode(value)

        else:
            raise ValueError(
                "Unsupported value, expected string, unicode, file like object, "
                " (filename, file object) or (filename, IBodyProducer)")


class _LengthConsumer(object):

    def __init__(self):
        self.length = 0

    def write(self, value):
        # this means that we have encountered
        # unknown length producer
        # so we need to stop attempts calculating
        if self.length == UNKNOWN_LENGTH:
            return

        if value == UNKNOWN_LENGTH:
            self.length = value
        elif isinstance(value, int):
            self.length += value
        else:
            self.length += len(value)


def _h_content_type(ctype="multipart/form-data", boundary=None):
    ctype = b'Content-Type: %s' % (ctype,)
    if boundary:
        return b'%s; boundary=%s' % (ctype, boundary, )
    else:
        return ctype

def _h_content_disposition(name, filename=None):
    disp = b'Content-Disposition: form-data; name="%s"' % (
        _escape(name).encode("utf-8"))

    if filename:
        return b'%s; filename=%s' % (disp, _escape(filename).encode("utf-8"), )
    else:
        return disp

def _sorted(fields):
    def key(key, value):
        if isinstance(value, (str, unicode)):
            return 0
        else:
            return 1
    return sorted(fields, key)


def _from_bytes(orig_bytes):
    return FileBodyProducer(StringIO(orig_bytes))

def _from_file(orig_file):
    return FileBodyProducer(orig_file)

def _content_type(filename):
    return mimetypes.guess_type(filename)[0] or 'application/octet-stream'
