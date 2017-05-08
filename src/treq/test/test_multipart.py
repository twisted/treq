# coding: utf-8
# Copyright (c) Twisted Matrix Laboratories.
# See LICENSE for details.

import cgi

from io import BytesIO

from twisted.trial import unittest
from zope.interface.verify import verifyObject

from twisted.python import compat
from twisted.internet import task
from twisted.web.client import FileBodyProducer
from twisted.web.iweb import UNKNOWN_LENGTH, IBodyProducer

from treq.multipart import MultiPartProducer, _LengthConsumer

if compat._PY3:
    long = int
    unicode = compat.unicode


class MultiPartProducerTestCase(unittest.TestCase):
    """
    Tests for the L{MultiPartProducer} which gets dictionary like object
    with post parameters, converts them to mutltipart/form-data format
    and feeds them to an L{IConsumer}.
    """
    def _termination(self):
        """
        This method can be used as the C{terminationPredicateFactory} for a
        L{Cooperator}.  It returns a predicate which immediately returns
        C{False}, indicating that no more work should be done this iteration.
        This has the result of only allowing one iteration of a cooperative
        task to be run per L{Cooperator} iteration.
        """
        return lambda: True

    def setUp(self):
        """
        Create a L{Cooperator} hooked up to an easily controlled, deterministic
        scheduler to use with L{MultiPartProducer}.
        """
        self._scheduled = []
        self.cooperator = task.Cooperator(
            self._termination, self._scheduled.append)

    def getOutput(self, producer, with_producer=False):
        """
        A convenience function to consume and return outpute.
        """
        consumer = output = BytesIO()

        producer.startProducing(consumer)

        while self._scheduled:
            self._scheduled.pop(0)()

        if with_producer:
            return (output.getvalue(), producer)
        else:
            return output.getvalue()

    def newLines(self, value):

        if isinstance(value, unicode):
            return value.replace(u"\n", u"\r\n")
        else:
            return value.replace(b"\n", b"\r\n")

    def test_interface(self):
        """
        L{MultiPartProducer} instances provide L{IBodyProducer}.
        """
        self.assertTrue(
            verifyObject(
                IBodyProducer, MultiPartProducer({})))

    def test_unknownLength(self):
        """
        If the L{MultiPartProducer} is constructed with a file-like object
        passed as a parameter without either a C{seek} or C{tell} method,
        its C{length} attribute is set to C{UNKNOWN_LENGTH}.
        """
        class HasSeek(object):
            def seek(self, offset, whence):
                pass

        class HasTell(object):
            def tell(self):
                pass

        producer = MultiPartProducer(
            {"f": ("name", None, FileBodyProducer(HasSeek()))})
        self.assertEqual(UNKNOWN_LENGTH, producer.length)

        producer = MultiPartProducer(
            {"f": ("name", None, FileBodyProducer(HasTell()))})
        self.assertEqual(UNKNOWN_LENGTH, producer.length)

    def test_knownLengthOnFile(self):
        """
        If the L{MultiPartProducer} is constructed with a file-like object with
        both C{seek} and C{tell} methods, its C{length} attribute is set to the
        size of the file as determined by those methods.
        """
        inputBytes = b"here are some bytes"
        inputFile = BytesIO(inputBytes)
        inputFile.seek(5)
        producer = MultiPartProducer({
            "field": ('file name', None, FileBodyProducer(
                      inputFile, cooperator=self.cooperator))})

        # Make sure we are generous enough not to alter seek position:
        self.assertEqual(inputFile.tell(), 5)

        # Total length is hard to calculate manually
        # as it contains a lot of headers parameters, newlines and boundaries
        # let's assert for now that it's no less than the input parameter
        self.assertTrue(producer.length > len(inputBytes))

        # Calculating length should not touch producers
        self.assertTrue(producer._currentProducer is None)

    def test_defaultCooperator(self):
        """
        If no L{Cooperator} instance is passed to L{MultiPartProducer}, the
        global cooperator is used.
        """
        producer = MultiPartProducer({
            "field": ('file name', None, FileBodyProducer(
                      BytesIO(b"yo"),
                      cooperator=self.cooperator))
        })
        self.assertEqual(task.cooperate, producer._cooperate)

    def test_startProducing(self):
        """
        L{MultiPartProducer.startProducing} starts writing bytes from the input
        file to the given L{IConsumer} and returns a L{Deferred} which fires
        when they have all been written.
        """
        consumer = output = BytesIO()

        producer = MultiPartProducer({
            b"field": ('file name', "text/hello-world", FileBodyProducer(
                BytesIO(b"Hello, World"),
                cooperator=self.cooperator))
        }, cooperator=self.cooperator, boundary=b"heyDavid")

        complete = producer.startProducing(consumer)

        iterations = 0
        while self._scheduled:
            iterations += 1
            self._scheduled.pop(0)()

        self.assertTrue(iterations > 1)
        self.assertEqual(self.newLines(b"""--heyDavid
Content-Disposition: form-data; name="field"; filename="file name"
Content-Type: text/hello-world
Content-Length: 12

Hello, World
--heyDavid--
"""), output.getvalue())
        self.assertEqual(None, self.successResultOf(complete))

    def test_inputClosedAtEOF(self):
        """
        When L{MultiPartProducer} reaches end-of-file on the input
        file given to it, the input file is closed.
        """
        inputFile = BytesIO(b"hello, world!")
        consumer = BytesIO()

        producer = MultiPartProducer({
            "field": (
                "file name",
                "text/hello-world",
                FileBodyProducer(
                    inputFile,
                    cooperator=self.cooperator))
        }, cooperator=self.cooperator, boundary=b"heyDavid")

        producer.startProducing(consumer)

        while self._scheduled:
            self._scheduled.pop(0)()

        self.assertTrue(inputFile.closed)

    def test_failedReadWhileProducing(self):
        """
        If a read from the input file fails while producing bytes to the
        consumer, the L{Deferred} returned by
        L{MultiPartProducer.startProducing} fires with a L{Failure} wrapping
        that exception.
        """
        class BrokenFile(object):
            def read(self, count):
                raise IOError("Simulated bad thing")

        producer = MultiPartProducer({
            "field": (
                "file name",
                "text/hello-world",
                FileBodyProducer(
                    BrokenFile(),
                    cooperator=self.cooperator))
        }, cooperator=self.cooperator, boundary=b"heyDavid")

        complete = producer.startProducing(BytesIO())

        while self._scheduled:
            self._scheduled.pop(0)()

        self.failureResultOf(complete).trap(IOError)

    def test_stopProducing(self):
        """
        L{MultiPartProducer.stopProducing} stops the underlying
        L{IPullProducer} and the cooperative task responsible for
        calling C{resumeProducing} and closes the input file but does
        not cause the L{Deferred} returned by C{startProducing} to fire.
        """
        inputFile = BytesIO(b"hello, world!")
        consumer = BytesIO()

        producer = MultiPartProducer({
            "field": (
                "file name",
                "text/hello-world",
                FileBodyProducer(
                    inputFile,
                    cooperator=self.cooperator))
        }, cooperator=self.cooperator, boundary=b"heyDavid")
        complete = producer.startProducing(consumer)
        self._scheduled.pop(0)()
        producer.stopProducing()
        self.assertTrue(inputFile.closed)
        self._scheduled.pop(0)()
        self.assertNoResult(complete)

    def test_pauseProducing(self):
        """
        L{MultiPartProducer.pauseProducing} temporarily suspends writing bytes
        from the input file to the given L{IConsumer}.
        """
        inputFile = BytesIO(b"hello, world!")
        consumer = output = BytesIO()

        producer = MultiPartProducer({
            "field": (
                "file name",
                "text/hello-world",
                FileBodyProducer(
                    inputFile,
                    cooperator=self.cooperator))
        }, cooperator=self.cooperator, boundary=b"heyDavid")
        complete = producer.startProducing(consumer)
        self._scheduled.pop(0)()

        currentValue = output.getvalue()
        self.assertTrue(currentValue)
        producer.pauseProducing()

        # Sort of depends on an implementation detail of Cooperator: even
        # though the only task is paused, there's still a scheduled call.  If
        # this were to go away because Cooperator became smart enough to cancel
        # this call in this case, that would be fine.
        self._scheduled.pop(0)()

        # Since the producer is paused, no new data should be here.
        self.assertEqual(output.getvalue(), currentValue)
        self.assertNoResult(complete)

    def test_resumeProducing(self):
        """
        L{MultoPartProducer.resumeProducing} re-commences writing bytes
        from the input file to the given L{IConsumer} after it was previously
        paused with L{MultiPartProducer.pauseProducing}.
        """
        inputFile = BytesIO(b"hello, world!")
        consumer = output = BytesIO()

        producer = MultiPartProducer({
            "field": (
                "file name",
                "text/hello-world",
                FileBodyProducer(
                    inputFile,
                    cooperator=self.cooperator))
        }, cooperator=self.cooperator, boundary=b"heyDavid")

        producer.startProducing(consumer)
        self._scheduled.pop(0)()
        currentValue = output.getvalue()
        self.assertTrue(currentValue)
        producer.pauseProducing()
        producer.resumeProducing()
        self._scheduled.pop(0)()
        # make sure we started producing new data after resume
        self.assertTrue(len(currentValue) < len(output.getvalue()))

    def test_unicodeString(self):
        """
        Make sure unicode string is passed properly
        """
        output, producer = self.getOutput(
            MultiPartProducer({
                "afield": u"Это моя строчечка\r\n",
            }, cooperator=self.cooperator, boundary=b"heyDavid"),
            with_producer=True)

        expected = self.newLines(u"""--heyDavid
Content-Disposition: form-data; name="afield"

Это моя строчечка

--heyDavid--
""".encode("utf-8"))
        self.assertEqual(producer.length, len(expected))
        self.assertEqual(expected, output)

    def test_failOnByteStrings(self):
        """
        If byte string is passed as a param and we don't know
        the encoding, fail early to prevent corrupted form posts
        """
        self.assertRaises(
            ValueError,
            MultiPartProducer, {
                "afield": u"это моя строчечка".encode("utf-32"),
            },
            cooperator=self.cooperator, boundary=b"heyDavid")

    def test_failOnUnknownParams(self):
        """
        If byte string is passed as a param and we don't know
        the encoding, fail early to prevent corrupted form posts
        """
        # unknown key
        self.assertRaises(
            ValueError,
            MultiPartProducer, {
                (1, 2): BytesIO(b"yo"),
            },
            cooperator=self.cooperator, boundary=b"heyDavid")

        # tuple length
        self.assertRaises(
            ValueError,
            MultiPartProducer, {
                "a": (1,),
            },
            cooperator=self.cooperator, boundary=b"heyDavid")

        # unknown value type
        self.assertRaises(
            ValueError,
            MultiPartProducer, {
                "a": {"a": "b"},
            },
            cooperator=self.cooperator, boundary=b"heyDavid")

    def test_twoFields(self):
        """
        Make sure multiple fields are rendered properly.
        """
        output = self.getOutput(
            MultiPartProducer({
                "afield": "just a string\r\n",
                "bfield": "another string"
            }, cooperator=self.cooperator, boundary=b"heyDavid"))

        self.assertEqual(self.newLines(b"""--heyDavid
Content-Disposition: form-data; name="afield"

just a string

--heyDavid
Content-Disposition: form-data; name="bfield"

another string
--heyDavid--
"""), output)

    def test_fieldsAndAttachment(self):
        """
        Make sure multiple fields are rendered properly.
        """
        output, producer = self.getOutput(
            MultiPartProducer({
                "bfield": "just a string\r\n",
                "cfield": "another string",
                "afield": (
                    "file name",
                    "text/hello-world",
                    FileBodyProducer(
                        inputFile=BytesIO(b"my lovely bytes"),
                        cooperator=self.cooperator))
            }, cooperator=self.cooperator, boundary=b"heyDavid"),
            with_producer=True)

        expected = self.newLines(b"""--heyDavid
Content-Disposition: form-data; name="bfield"

just a string

--heyDavid
Content-Disposition: form-data; name="cfield"

another string
--heyDavid
Content-Disposition: form-data; name="afield"; filename="file name"
Content-Type: text/hello-world
Content-Length: 15

my lovely bytes
--heyDavid--
""")
        self.assertEqual(producer.length, len(expected))
        self.assertEqual(output, expected)

    def test_multipleFieldsAndAttachments(self):
        """
        Make sure multiple fields, attachments etc are rendered properly.
        """
        output, producer = self.getOutput(
            MultiPartProducer({
                "cfield": "just a string\r\n",
                "bfield": "another string",
                "efield": (
                    "ef",
                    "text/html",
                    FileBodyProducer(
                        inputFile=BytesIO(b"my lovely bytes2"),
                        cooperator=self.cooperator)),
                "xfield": (
                    "xf",
                    "text/json",
                    FileBodyProducer(
                        inputFile=BytesIO(b"my lovely bytes219"),
                        cooperator=self.cooperator)),
                "afield": (
                    "af",
                    "text/xml",
                    FileBodyProducer(
                        inputFile=BytesIO(b"my lovely bytes22"),
                        cooperator=self.cooperator))
            }, cooperator=self.cooperator, boundary=b"heyDavid"),
            with_producer=True)

        expected = self.newLines(b"""--heyDavid
Content-Disposition: form-data; name="bfield"

another string
--heyDavid
Content-Disposition: form-data; name="cfield"

just a string

--heyDavid
Content-Disposition: form-data; name="afield"; filename="af"
Content-Type: text/xml
Content-Length: 17

my lovely bytes22
--heyDavid
Content-Disposition: form-data; name="efield"; filename="ef"
Content-Type: text/html
Content-Length: 16

my lovely bytes2
--heyDavid
Content-Disposition: form-data; name="xfield"; filename="xf"
Content-Type: text/json
Content-Length: 18

my lovely bytes219
--heyDavid--
""")
        self.assertEqual(producer.length, len(expected))
        self.assertEqual(output, expected)

    def test_unicodeAttachmentName(self):
        """
        Make sure unicode attachment names are supported.
        """
        output, producer = self.getOutput(
            MultiPartProducer({
                "field": (
                    u'Так себе имя.jpg',
                    "image/jpeg",
                    FileBodyProducer(
                        inputFile=BytesIO(b"my lovely bytes"),
                        cooperator=self.cooperator
                    )
                )
            }, cooperator=self.cooperator, boundary=b"heyDavid"),
            with_producer=True)

        expected = self.newLines(u"""--heyDavid
Content-Disposition: form-data; name="field"; filename="Так себе имя.jpg"
Content-Type: image/jpeg
Content-Length: 15

my lovely bytes
--heyDavid--
""".encode("utf-8"))
        self.assertEqual(len(expected), producer.length)
        self.assertEqual(expected, output)

    def test_missingAttachmentName(self):
        """
        Make sure attachments without names are supported
        """
        output, producer = self.getOutput(
            MultiPartProducer({
                "field": (
                    None,
                    "image/jpeg",
                    FileBodyProducer(
                        inputFile=BytesIO(b"my lovely bytes"),
                        cooperator=self.cooperator,
                    )
                )
            }, cooperator=self.cooperator,
                boundary=b"heyDavid"),
            with_producer=True)

        expected = self.newLines(b"""--heyDavid
Content-Disposition: form-data; name="field"
Content-Type: image/jpeg
Content-Length: 15

my lovely bytes
--heyDavid--
""")
        self.assertEqual(len(expected), producer.length)
        self.assertEqual(expected, output)

    def test_newLinesInParams(self):
        """
        Make sure we generate proper format even with newlines in attachments
        """
        output = self.getOutput(
            MultiPartProducer({
                "field": (
                    u'\r\noops.j\npg',
                    "image/jp\reg\n",
                    FileBodyProducer(
                        inputFile=BytesIO(b"my lovely bytes"),
                        cooperator=self.cooperator
                    )
                )
            }, cooperator=self.cooperator,
                boundary=b"heyDavid"
            )
        )

        self.assertEqual(self.newLines(u"""--heyDavid
Content-Disposition: form-data; name="field"; filename="oops.jpg"
Content-Type: image/jpeg
Content-Length: 15

my lovely bytes
--heyDavid--
""".encode("utf-8")), output)

    def test_worksWithCgi(self):
        """
        Make sure the stuff we generated actually parsed by python cgi
        """
        output = self.getOutput(
            MultiPartProducer([
                ("cfield", "just a string\r\n"),
                ("cfield", "another string"),
                ("efield", ('ef', "text/html", FileBodyProducer(
                            inputFile=BytesIO(b"my lovely bytes2"),
                            cooperator=self.cooperator,
                            ))),
                ("xfield", ('xf', "text/json", FileBodyProducer(
                            inputFile=BytesIO(b"my lovely bytes219"),
                            cooperator=self.cooperator,
                            ))),
                ("afield", ('af', "text/xml", FileBodyProducer(
                            inputFile=BytesIO(b"my lovely bytes22"),
                            cooperator=self.cooperator,
                            )))
            ], cooperator=self.cooperator, boundary=b"heyDavid"
            )
        )

        form = cgi.parse_multipart(BytesIO(output), {"boundary": b"heyDavid"})
        self.assertEqual(set([b'just a string\r\n', b'another string']),
                         set(form['cfield']))

        self.assertEqual(set([b'my lovely bytes2']), set(form['efield']))
        self.assertEqual(set([b'my lovely bytes219']), set(form['xfield']))
        self.assertEqual(set([b'my lovely bytes22']), set(form['afield']))


class LengthConsumerTestCase(unittest.TestCase):
    """
    Tests for the _LengthConsumer, an L{IConsumer} which is used to compute
    the length of a produced content.
    """

    def test_scalarsUpdateCounter(self):
        """
        When a long or an int are written, _LengthConsumer updates its internal
        counter.
        """
        consumer = _LengthConsumer()
        self.assertEqual(consumer.length, 0)
        consumer.write(long(1))
        self.assertEqual(consumer.length, 1)
        consumer.write(2147483647)
        self.assertEqual(consumer.length, long(2147483648))

    def test_stringUpdatesCounter(self):
        """
        Use the written string length to update the internal counter
        """
        a = (b"Cantami, o Diva, del Pelide Achille\n l'ira funesta che "
             b"infiniti addusse\n lutti agli Achei")

        consumer = _LengthConsumer()
        self.assertEqual(consumer.length, 0)
        consumer.write(a)
        self.assertEqual(consumer.length, 89)
