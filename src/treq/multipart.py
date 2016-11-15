# Copyright (c) Twisted Matrix Laboratories.
# See LICENSE for details.

from __future__ import absolute_import, division, print_function

from uuid import uuid4
from io import BytesIO
from contextlib import closing

from twisted.internet import defer, task
from twisted.python.compat import unicode, _PY3
from twisted.web.iweb import UNKNOWN_LENGTH, IBodyProducer

from zope.interface import implementer

if _PY3:
    long = int

CRLF = b"\r\n"


@implementer(IBodyProducer)
class MultiPartProducer(object):
    """
    :class:`MultiPartProducer` takes parameters for a HTTP request and
    produces bytes in multipart/form-data format defined in :rfc:`2388` and
    :rfc:`2046`.

    The encoded request is produced incrementally and the bytes are
    written to a consumer.

    Fields should have form: ``[(parameter name, value), ...]``

    Accepted values:

    * Unicode strings (in this case parameter will be encoded with utf-8)
    * Tuples with (file name, content-type,
      :class:`~twisted.web.iweb.IBodyProducer` objects)

    Since :class:`MultiPartProducer` can accept objects like
    :class:`~twisted.web.iweb.IBodyProducer` which cannot be read from in an
    event-driven manner it uses uses a
    :class:`~twisted.internet.task.Cooperator` instance to schedule reads
    from the underlying producers. Reading is also paused and resumed based on
    notifications from the :class:`IConsumer` provider being written to.

    :ivar _fields: Sorted parameters, where all strings are enforced to be
        unicode and file objects stacked on bottom (to produce a human readable
        form-data request)

    :ivar _cooperate: A method like `Cooperator.cooperate` which is used to
        schedule all reads.

    :ivar boundary: The generated boundary used in form-data encoding
    :type boundary: `bytes`
    """

    def __init__(self, fields, boundary=None, cooperator=task):
        self._fields = list(_sorted_by_type(_converted(fields)))
        self._currentProducer = None
        self._cooperate = cooperator.cooperate

        self.boundary = boundary or uuid4().hex

        if isinstance(self.boundary, unicode):
            self.boundary = self.boundary.encode('ascii')

        self.length = self._calculateLength()

    def startProducing(self, consumer):
        """
        Start a cooperative task which will read bytes from the input file and
        write them to `consumer`.  Return a `Deferred` which fires after all
        bytes have been written.

        :param consumer: Any `IConsumer` provider
        """
        self._task = self._cooperate(self._writeLoop(consumer))
        d = self._task.whenDone()

        def maybeStopped(reason):
            reason.trap(task.TaskStopped)
            return defer.Deferred()
        d.addCallbacks(lambda ignored: None, maybeStopped)
        return d

    def stopProducing(self):
        """
        Permanently stop writing bytes from the file to the consumer by
        stopping the underlying `CooperativeTask`.
        """
        if self._currentProducer:
            self._currentProducer.stopProducing()
        self._task.stop()

    def pauseProducing(self):
        """
        Temporarily suspend copying bytes from the input file to the consumer
        by pausing the `CooperativeTask` which drives that activity.
        """
        if self._currentProducer:
            # Having a current producer means that we are in
            # the paused state because we've returned
            # the deferred of the current producer to the
            # the cooperator. So this request
            # for pausing us is actually a request to pause
            # our underlying current producer.
            self._currentProducer.pauseProducing()
        else:
            self._task.pause()

    def resumeProducing(self):
        """
        Undo the effects of a previous `pauseProducing` and resume copying
        bytes to the consumer by resuming the `CooperativeTask` which drives
        the write activity.
        """
        if self._currentProducer:
            self._currentProducer.resumeProducing()
        else:
            self._task.resume()

    def _calculateLength(self):
        """
        Determine how many bytes the overall form post would consume.
        The easiest way is to calculate is to generate of `fObj`
        (assuming it is not modified from this point on).
        If the determination cannot be made, return `UNKNOWN_LENGTH`.
        """
        consumer = _LengthConsumer()
        for i in list(self._writeLoop(consumer)):
            pass
        return consumer.length

    def _getBoundary(self, final=False):
        """
        Returns a boundary line, either final (the one that ends the
        form data request or a regular, the one that separates the boundaries)

        --this-is-my-boundary
        """
        f = b"--" if final else b""
        return b"--" + self.boundary + f

    def _writeLoop(self, consumer):
        """
        Return an iterator which generates the multipart/form-data
        request including the encoded objects
        and writes them to the consumer for each time it is iterated.
        """
        for index, (name, value) in enumerate(self._fields):
            # We don't write the CRLF of the first boundary:
            # HTTP request headers are already separated with CRLF
            # from the request body, another newline is possible
            # and should be considered as an empty preamble per rfc2046,
            # but is generally confusing, so we omit it when generating
            # the request. We don't write Content-Type: multipart/form-data
            # header here as well as it's defined in the context of the HTTP
            # request headers, not the producer, so we gust generate
            # the body.

            # It's also important to note that the boundary in the message
            # is defined not only by "--boundary-value" but
            # but with CRLF characers before it and after the line.
            # This is very important.
            # proper boundary is "CRLF--boundary-valueCRLF"
            consumer.write(
                (CRLF if index != 0 else b"") + self._getBoundary() + CRLF)
            yield self._writeField(name, value, consumer)

        consumer.write(CRLF + self._getBoundary(final=True) + CRLF)

    def _writeField(self, name, value, consumer):
        if isinstance(value, unicode):
            self._writeString(name, value, consumer)
        elif isinstance(value, tuple):
            filename, content_type, producer = value
            return self._writeFile(
                name, filename, content_type, producer, consumer)

    def _writeString(self, name, value, consumer):
        cdisp = _Header(b"Content-Disposition", b"form-data")
        cdisp.add_param(b"name", name)
        consumer.write(bytes(cdisp) + CRLF + CRLF)

        encoded = value.encode("utf-8")
        consumer.write(encoded)
        self._currentProducer = None

    def _writeFile(self, name, filename, content_type, producer, consumer):
        cdisp = _Header(b"Content-Disposition", b"form-data")
        cdisp.add_param(b"name", name)
        if filename:
            cdisp.add_param(b"filename", filename)

        consumer.write(bytes(cdisp) + CRLF)
        consumer.write(bytes(_Header(b"Content-Type", content_type)) + CRLF)
        if producer.length != UNKNOWN_LENGTH:
            consumer.write(
                bytes(_Header(b"Content-Length", producer.length)) + CRLF)
        consumer.write(CRLF)

        if isinstance(consumer, _LengthConsumer):
            consumer.write(producer.length)
        else:
            self._currentProducer = producer

            def unset(val):
                self._currentProducer = None
                return val

            d = producer.startProducing(consumer)
            d.addCallback(unset)
            return d


def _escape(value):
    """
    This function prevents header values from corrupting the request,
    a newline in the file name parameter makes form-data request unreadable
    for majority of parsers.
    """
    if not isinstance(value, (bytes, unicode)):
        value = unicode(value)
    if isinstance(value, bytes):
        value = value.decode('utf-8')
    return value.replace(u"\r", u"").replace(u"\n", u"").replace(u'"', u'\\"')


def _enforce_unicode(value):
    """
    This function enforces the stings passed to be unicode, so we won't
    need to guess what's the encoding of the binary strings passed in.
    If someone needs to pass the binary string, use BytesIO and wrap it with
    `FileBodyProducer`.
    """
    if isinstance(value, unicode):
        return value

    elif isinstance(value, bytes):
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
            "Unsupported field type: %s" % (value.__class__.__name__,))


def _converted(fields):
    if hasattr(fields, "iteritems"):
        fields = fields.iteritems()
    elif hasattr(fields, "items"):
        fields = fields.items()

    for name, value in fields:
        name = _enforce_unicode(name)

        if isinstance(value, (tuple, list)):
            if len(value) != 3:
                raise ValueError(
                    "Expected tuple: (filename, content type, producer)")
            filename, content_type, producer = value
            filename = _enforce_unicode(filename) if filename else None
            yield name, (filename, content_type, producer)

        elif isinstance(value, (bytes, unicode)):
            yield name, _enforce_unicode(value)

        else:
            raise ValueError(
                "Unsupported value, expected string, unicode  "
                "or tuple (filename, content type, IBodyProducer)")


class _LengthConsumer(object):
    """
    `_LengthConsumer` is used to calculate the length of the multi-part
    request. The easiest way to do that is to consume all the fields,
    but instead writing them to the string just accumulate the request
    length.

    :ivar length: The length of the request. Can be `UNKNOWN_LENGTH`
        if consumer finds the field that has length that can not be calculated

    """

    def __init__(self):
        self.length = 0

    def write(self, value):
        # this means that we have encountered
        # unknown length producer
        # so we need to stop attempts calculating
        if self.length is UNKNOWN_LENGTH:
            return

        if value is UNKNOWN_LENGTH:
            self.length = value
        elif isinstance(value, (int, long)):
            self.length += value
        else:
            self.length += len(value)


class _Header(object):
    """
    `_Header` This class is a tiny wrapper that produces
    request headers. We can't use standard python header
    class because it encodes unicode fields using =? bla bla ?=
    encoding, which is correct, but no one in HTTP world expects
    that, everyone wants utf-8 raw bytes.

    """
    def __init__(self, name, value, params=None):
        self.name = name
        self.value = value
        self.params = params or []

    def add_param(self, name, value):
        self.params.append((name, value))

    def __bytes__(self):
        with closing(BytesIO()) as h:
            h.write(self.name + b": " + _escape(self.value).encode("us-ascii"))
            if self.params:
                for (name, val) in self.params:
                    h.write(b"; ")
                    h.write(_escape(name).encode("us-ascii"))
                    h.write(b"=")
                    h.write(b'"' + _escape(val).encode('utf-8') + b'"')
            h.seek(0)
            return h.read()

    def __str__(self):
        return self.__bytes__()


def _sorted_by_type(fields):
    """Sorts params so that strings are placed before files.

    That makes a request more readable, as generally files are bigger.
    It also provides deterministic order of fields what is easier for testing.
    """
    def key(p):
        key, val = p
        if isinstance(val, (bytes, unicode)):
            return (0, key)
        else:
            return (1, key)
    return sorted(fields, key=key)
