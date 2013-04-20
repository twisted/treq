# coding: utf-8
# Copyright (c) Twisted Matrix Laboratories.
# See LICENSE for details.
import cgi
from StringIO import StringIO

from twisted.trial import unittest
from zope.interface.verify import verifyObject

from twisted.internet import task
from twisted.web.client import FileBodyProducer
from twisted.web.iweb import UNKNOWN_LENGTH, IBodyProducer

from treq.multipart import MultiPartProducer

MP = MultiPartProducer


class StringConsumer(object):
    def __init__(self, outputFile):
        self.outputFile = outputFile

    def write(self, bytes):
        self.outputFile.write(bytes)


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

        output = StringIO()
        consumer = StringConsumer(output)

        producer.startProducing(consumer)

        while self._scheduled:
            self._scheduled.pop(0)()

        if with_producer:
            return (output.getvalue(), producer)
        else:
            return output.getvalue()

    def newLines(self, value):
        return value.replace("\n", "\r\n")

    def test_interface(self):
        """
        L{MultiPartProducer} instances provide L{IBodyProducer}.
        """
        self.assertTrue(verifyObject(IBodyProducer, MP({})))

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

        producer = MP({"f": ("name", None, FileBodyProducer(HasSeek()))})
        self.assertEqual(UNKNOWN_LENGTH, producer.length)

        producer = MP({"f": ("name", None, FileBodyProducer(HasTell()))})
        self.assertEqual(UNKNOWN_LENGTH, producer.length)

    def test_knownLengthOnFile(self):
        """
        If the L{MultiPartProducer} is constructed with a file-like object with
        both C{seek} and C{tell} methods, its C{length} attribute is set to the
        size of the file as determined by those methods.
        """
        inputBytes = "here are some bytes"
        inputFile = StringIO(inputBytes)
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
                      StringIO("yo"),
                      cooperator=self.cooperator))
        })
        self.assertEqual(task.cooperate, producer._cooperate)

    def test_startProducing(self):
        """
        L{MultiPartProducer.startProducing} starts writing bytes from the input
        file to the given L{IConsumer} and returns a L{Deferred} which fires
        when they have all been written.
        """

        output = StringIO()
        consumer = StringConsumer(output)

        producer = MultiPartProducer({
            "field": ('file name', "text/hello-world", FileBodyProducer(
                StringIO("Hello, World"),
                cooperator=self.cooperator))
        }, cooperator=self.cooperator, boundary="heyDavid")

        complete = producer.startProducing(consumer)

        iterations = 0
        while self._scheduled:
            iterations += 1
            self._scheduled.pop(0)()

        self.assertTrue(iterations > 1)
        self.assertEqual(self.newLines("""--heyDavid
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
        output = StringIO()
        inputFile = StringIO("hello, world!")
        consumer = StringConsumer(output)

        producer = MultiPartProducer({
            "field": (
                "file name",
                "text/hello-world",
                FileBodyProducer(
                    inputFile,
                    cooperator=self.cooperator))
        }, cooperator=self.cooperator, boundary="heyDavid")

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
        }, cooperator=self.cooperator, boundary="heyDavid")

        complete = producer.startProducing(
            StringConsumer(StringIO()))

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
        output = StringIO()
        inputFile = StringIO("hello, world!")
        consumer = StringConsumer(output)

        producer = MultiPartProducer({
            "field": (
                "file name",
                "text/hello-world",
                FileBodyProducer(
                    inputFile,
                    cooperator=self.cooperator))
        }, cooperator=self.cooperator, boundary="heyDavid")
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
        output = StringIO()
        inputFile = StringIO("hello, world!")
        consumer = StringConsumer(output)

        producer = MultiPartProducer({
            "field": (
                "file name",
                "text/hello-world",
                FileBodyProducer(
                    inputFile,
                    cooperator=self.cooperator))
        }, cooperator=self.cooperator, boundary="heyDavid")
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
        output = StringIO()
        inputFile = StringIO("hello, world!")
        consumer = StringConsumer(output)

        producer = MultiPartProducer({
            "field": (
                "file name",
                "text/hello-world",
                FileBodyProducer(
                    inputFile,
                    cooperator=self.cooperator))
        }, cooperator=self.cooperator, boundary="heyDavid")

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
            }, cooperator=self.cooperator, boundary="heyDavid"),
            with_producer=True)

        encoded = u"Это моя строчечка\r\n".encode("utf-8")

        expected = self.newLines(u"""--heyDavid
Content-Disposition: form-data; name="afield"
Content-Type: text/plain; charset="utf-8"
Content-Length: {}

Это моя строчечка

--heyDavid--
""".format(len(encoded)).encode("utf-8"))
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
            cooperator=self.cooperator, boundary="heyDavid")

    def test_failOnUnknownParams(self):
        """
        If byte string is passed as a param and we don't know
        the encoding, fail early to prevent corrupted form posts
        """
        # unknown key
        self.assertRaises(
            ValueError,
            MultiPartProducer, {
                (1, 2): StringIO("yo"),
            },
            cooperator=self.cooperator, boundary="heyDavid")

        # tuple length
        self.assertRaises(
            ValueError,
            MultiPartProducer, {
                "a": (1,),
            },
            cooperator=self.cooperator, boundary="heyDavid")

        # unknown value type
        self.assertRaises(
            ValueError,
            MultiPartProducer, {
                "a": {"a": "b"},
            },
            cooperator=self.cooperator, boundary="heyDavid")

    def test_twoFields(self):
        """
        Make sure multiple fields are rendered properly.
        """
        output = self.getOutput(
            MultiPartProducer({
                "afield": "just a string\r\n",
                "bfield": "another string"
            }, cooperator=self.cooperator, boundary="heyDavid"))

        self.assertEqual(self.newLines("""--heyDavid
Content-Disposition: form-data; name="afield"
Content-Type: text/plain; charset="utf-8"
Content-Length: 15

just a string

--heyDavid
Content-Disposition: form-data; name="bfield"
Content-Type: text/plain; charset="utf-8"
Content-Length: 14

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
                        inputFile=StringIO("my lovely bytes"),
                        cooperator=self.cooperator))
            }, cooperator=self.cooperator, boundary="heyDavid"),
            with_producer=True)

        expected = self.newLines("""--heyDavid
Content-Disposition: form-data; name="bfield"
Content-Type: text/plain; charset="utf-8"
Content-Length: 15

just a string

--heyDavid
Content-Disposition: form-data; name="cfield"
Content-Type: text/plain; charset="utf-8"
Content-Length: 14

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
                        inputFile=StringIO("my lovely bytes2"),
                        cooperator=self.cooperator)),
                "xfield": (
                    "xf",
                    "text/json",
                    FileBodyProducer(
                        inputFile=StringIO("my lovely bytes219"),
                        cooperator=self.cooperator)),
                "afield": (
                    "af",
                    "text/xml",
                    FileBodyProducer(
                        inputFile=StringIO("my lovely bytes22"),
                        cooperator=self.cooperator))
            }, cooperator=self.cooperator, boundary="heyDavid"),
            with_producer=True)

        expected = self.newLines("""--heyDavid
Content-Disposition: form-data; name="bfield"
Content-Type: text/plain; charset="utf-8"
Content-Length: 14

another string
--heyDavid
Content-Disposition: form-data; name="cfield"
Content-Type: text/plain; charset="utf-8"
Content-Length: 15

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
                        inputFile=StringIO("my lovely bytes"),
                        cooperator=self.cooperator
                    )
                )
            }, cooperator=self.cooperator, boundary="heyDavid"),
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
                        inputFile=StringIO("my lovely bytes"),
                        cooperator=self.cooperator,
                    )
                )
            }, cooperator=self.cooperator,
                boundary="heyDavid"),
            with_producer=True)

        expected = self.newLines("""--heyDavid
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
                        inputFile=StringIO("my lovely bytes"),
                        cooperator=self.cooperator
                    )
                )
            }, cooperator=self.cooperator,
                boundary="heyDavid"
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
                            inputFile=StringIO("my lovely bytes2"),
                            cooperator=self.cooperator,
                            ))),
                ("xfield", ('xf', "text/json", FileBodyProducer(
                            inputFile=StringIO("my lovely bytes219"),
                            cooperator=self.cooperator,
                            ))),
                ("afield", ('af', "text/xml", FileBodyProducer(
                            inputFile=StringIO("my lovely bytes22"),
                            cooperator=self.cooperator,
                            )))
            ], cooperator=self.cooperator, boundary="heyDavid"
            )
        )

        form = cgi.parse_multipart(StringIO(output), {"boundary": "heyDavid"})
        self.assertEqual(set(['just a string\r\n', 'another string']),
                         set(form['cfield']))

        self.assertEqual(set(['my lovely bytes2']), set(form['efield']))
        self.assertEqual(set(['my lovely bytes219']), set(form['xfield']))
        self.assertEqual(set(['my lovely bytes22']), set(form['afield']))
