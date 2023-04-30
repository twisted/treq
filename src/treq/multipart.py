# Copyright (c) Twisted Matrix Laboratories.
# See LICENSE for details.

from contextlib import closing
from io import BytesIO
from typing import Any, Iterable, List, Mapping, Optional, Tuple, Union, cast
from uuid import uuid4

from twisted.internet import task
from twisted.internet.defer import Deferred
from twisted.internet.interfaces import IConsumer
from twisted.python.failure import Failure
from twisted.web.iweb import UNKNOWN_LENGTH, IBodyProducer
from typing_extensions import TypeAlias, Literal
from zope.interface import implementer

from treq._types import _S, _FilesType, _FileValue

CRLF = b"\r\n"


_Consumer: TypeAlias = "Union[IConsumer, _LengthConsumer]"
_UnknownLength = Literal["'twisted.web.iweb.UNKNOWN_LENGTH'"]
_Length: TypeAlias = Union[int, _UnknownLength]
_FieldValue = Union[bytes, Tuple[str, str, IBodyProducer]]
_Field: TypeAlias = Tuple[str, _FieldValue]


@implementer(IBodyProducer)
class MultiPartProducer:
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
    """

    length: _Length
    boundary: bytes
    _currentProducer: Optional[IBodyProducer] = None
    _task: Optional[task.CooperativeTask] = None

    def __init__(
        self,
        fields: _FilesType,
        boundary: Optional[Union[str, bytes]] = None,
        cooperator: task.Cooperator = cast(task.Cooperator, task),
    ) -> None:
        self._fields = _sorted_by_type(_converted(fields))
        self._cooperate = cooperator.cooperate

        if not boundary:
            boundary = uuid4().hex.encode("ascii")
        if isinstance(boundary, str):
            boundary = boundary.encode("ascii")
        self.boundary = boundary

        self.length = self._calculateLength()

    def startProducing(self, consumer: IConsumer) -> "Deferred[None]":
        """
        Start a cooperative task which will read bytes from the input file and
        write them to `consumer`.  Return a `Deferred` which fires after all
        bytes have been written.

        :param consumer: Any `IConsumer` provider
        """
        self._task = self._cooperate(self._writeLoop(consumer))  # type: ignore
        # whenDone returns the iterator that was passed to cooperate, so who
        # cares what type it has? It's an edge signal; we ignore its value.
        d: "Deferred[Any]" = self._task.whenDone()

        def maybeStopped(reason: Failure) -> "Deferred[None]":
            reason.trap(task.TaskStopped)
            return Deferred()

        d = cast("Deferred[None]", d.addCallbacks(lambda ignored: None, maybeStopped))
        return d

    def stopProducing(self) -> None:
        """
        Permanently stop writing bytes from the file to the consumer by
        stopping the underlying `CooperativeTask`.
        """
        assert self._task is not None
        if self._currentProducer:
            self._currentProducer.stopProducing()
        self._task.stop()

    def pauseProducing(self) -> None:
        """
        Temporarily suspend copying bytes from the input file to the consumer
        by pausing the `CooperativeTask` which drives that activity.
        """
        assert self._task is not None
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

    def resumeProducing(self) -> None:
        """
        Undo the effects of a previous `pauseProducing` and resume copying
        bytes to the consumer by resuming the `CooperativeTask` which drives
        the write activity.
        """
        assert self._task is not None
        if self._currentProducer:
            self._currentProducer.resumeProducing()
        else:
            self._task.resume()

    def _calculateLength(self) -> _Length:
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

    def _getBoundary(self, final: bool = False) -> bytes:
        """
        Returns a boundary line, either final (the one that ends the
        form data request or a regular, the one that separates the boundaries)

        --this-is-my-boundary
        """
        f = b"--" if final else b""
        return b"--" + self.boundary + f

    def _writeLoop(self, consumer: _Consumer) -> Iterable[Optional[Deferred]]:
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
            # but with CRLF characters before it and after the line.
            # This is very important.
            # proper boundary is "CRLF--boundary-valueCRLF"
            consumer.write((CRLF if index != 0 else b"") + self._getBoundary() + CRLF)
            yield self._writeField(name, value, consumer)

        consumer.write(CRLF + self._getBoundary(final=True) + CRLF)

    def _writeField(
        self, name: str, value: _FieldValue, consumer: _Consumer
    ) -> Optional[Deferred]:
        if isinstance(value, bytes):
            self._writeString(name, value, consumer)
            return None
        else:
            filename, content_type, producer = value
            return self._writeFile(name, filename, content_type, producer, consumer)

    def _writeString(self, name: str, value: bytes, consumer: _Consumer) -> None:
        cdisp = _Header(b"Content-Disposition", b"form-data")
        cdisp.add_param(b"name", name)
        consumer.write(bytes(cdisp) + CRLF + CRLF)
        consumer.write(value)
        self._currentProducer = None

    def _writeFile(
        self,
        name: str,
        filename: str,
        content_type: str,
        producer: IBodyProducer,
        consumer: _Consumer,
    ) -> "Optional[Deferred[None]]":
        cdisp = _Header(b"Content-Disposition", b"form-data")
        cdisp.add_param(b"name", name)
        if filename:
            cdisp.add_param(b"filename", filename)

        consumer.write(bytes(cdisp) + CRLF)
        consumer.write(bytes(_Header(b"Content-Type", content_type)) + CRLF)
        if producer.length != UNKNOWN_LENGTH:
            consumer.write(
                bytes(_Header(b"Content-Length", str(producer.length))) + CRLF
            )
        consumer.write(CRLF)

        if isinstance(consumer, _LengthConsumer):
            consumer.write(producer.length)
            return None
        else:
            self._currentProducer = producer

            def unset(val):
                self._currentProducer = None
                return val

            d = producer.startProducing(consumer)
            return cast("Deferred[None]", d.addCallback(unset))


def _escape(value: Union[str, bytes]) -> str:
    """
    This function prevents header values from corrupting the request,
    a newline in the file name parameter makes form-data request unreadable
    for majority of parsers.
    """
    if isinstance(value, bytes):
        value = value.decode("utf-8")
    return value.replace("\r", "").replace("\n", "").replace('"', '\\"')


def _enforce_unicode(value: Any) -> str:
    """
    This function enforces the strings passed to be unicode, so we won't
    need to guess what's the encoding of the binary strings passed in.
    If someone needs to pass the binary string, use BytesIO and wrap it with
    `FileBodyProducer`.
    """
    if isinstance(value, str):
        return value

    elif isinstance(value, bytes):
        # we got a byte string, and we have no idea what's the encoding of it
        # we can only assume that it's something cool
        try:
            return value.decode("utf-8")
        except UnicodeDecodeError:
            raise ValueError(
                "Supplied raw bytes that are not ASCII/UTF-8."
                " When supplying raw string make sure it's ASCII or UTF-8"
                ", or work with unicode if you are not sure"
            )
    else:
        raise ValueError("Unsupported field type: %s" % (value.__class__.__name__,))


def _converted(fields: _FilesType) -> Iterable[_Field]:
    """
    Convert any of the multitude of formats we accept for the *fields*
    parameter into the form we work with internally.
    """
    fields_: Iterable[Tuple[str, _FileValue]]
    if hasattr(fields, "items"):
        assert isinstance(fields, Mapping)
        fields_ = fields.items()
    else:
        fields_ = fields

    for name, value in fields_:
        # NOTE: While `name` is typed as `str` we still support UTF-8 `bytes` here
        # for backward compatibility, thus this call to decode.
        name = _enforce_unicode(name)

        if isinstance(value, (tuple, list)):
            if len(value) != 3:
                raise ValueError("Expected tuple: (filename, content type, producer)")
            filename, content_type, producer = value
            filename = _enforce_unicode(filename) if filename else None
            yield name, (filename, content_type, producer)

        elif isinstance(value, str):
            yield name, value.encode("utf-8")

        elif isinstance(value, bytes):
            yield name, value

        else:
            raise ValueError(
                "Unsupported value, expected str, bytes, "
                "or tuple (filename, content type, IBodyProducer)"
            )


class _LengthConsumer:
    """
    `_LengthConsumer` is used to calculate the length of the multi-part
    request. The easiest way to do that is to consume all the fields,
    but instead writing them to the string just accumulate the request
    length.

    :ivar length: The length of the request. Can be `UNKNOWN_LENGTH`
        if consumer finds the field that has length that can not be calculated

    """

    length: _Length

    def __init__(self) -> None:
        self.length = 0

    def write(self, value: Union[bytes, _Length]) -> None:
        # this means that we have encountered
        # unknown length producer
        # so we need to stop attempts calculating
        if self.length == UNKNOWN_LENGTH:
            return
        assert isinstance(self.length, int)

        if value == UNKNOWN_LENGTH:
            self.length = cast(_UnknownLength, UNKNOWN_LENGTH)
        elif isinstance(value, int):
            self.length += value
        else:
            assert isinstance(value, bytes)
            self.length += len(value)


class _Header:
    """
    `_Header` This class is a tiny wrapper that produces
    request headers. We can't use standard python header
    class because it encodes unicode fields using =? bla bla ?=
    encoding, which is correct, but no one in HTTP world expects
    that, everyone wants utf-8 raw bytes.

    """

    def __init__(
        self,
        name: bytes,
        value: _S,
        params: Optional[List[Tuple[_S, _S]]] = None,
    ):
        self.name = name
        self.value = value
        self.params = params or []

    def add_param(self, name: _S, value: _S) -> None:
        self.params.append((name, value))

    def __bytes__(self) -> bytes:
        with closing(BytesIO()) as h:
            h.write(self.name + b": " + _escape(self.value).encode("us-ascii"))
            if self.params:
                for (name, val) in self.params:
                    h.write(b"; ")
                    h.write(_escape(name).encode("us-ascii"))
                    h.write(b"=")
                    h.write(b'"' + _escape(val).encode("utf-8") + b'"')
            h.seek(0)
            return h.read()


def _sorted_by_type(fields: Iterable[_Field]) -> List[_Field]:
    """Sorts params so that strings are placed before files.

    That makes a request more readable, as generally files are bigger.
    It also provides deterministic order of fields what is easier for testing.
    """

    def key(p):
        key, val = p
        if isinstance(val, (bytes, str)):
            return (0, key)
        else:
            return (1, key)

    return sorted(fields, key=key)
