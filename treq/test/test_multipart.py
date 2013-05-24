import StringIO

from twisted.trial import unittest
from twisted.web.client import HTTPConnectionPool
from zope.interface.verify import verifyObject

from twisted.internet import defer,task
from twisted.python.failure import Failure
from twisted.python.components import proxyForInterface
from twisted.test.proto_helpers import StringTransport
from twisted.test.proto_helpers import MemoryReactor
from twisted.internet.task import Clock
from twisted.internet.error import ConnectionRefusedError, ConnectionDone
from twisted.internet.protocol import Protocol, Factory
from twisted.internet.defer import Deferred, succeed
from twisted.internet.endpoints import TCP4ClientEndpoint, SSL4ClientEndpoint
from twisted.web.client import FileBodyProducer, Request, HTTPConnectionPool
from twisted.web.client import _WebToNormalContextFactory
from twisted.web.client import WebClientContextFactory, _HTTP11ClientFactory
from twisted.web.iweb import UNKNOWN_LENGTH, IBodyProducer, IResponse
from twisted.web._newclient import HTTP11ClientProtocol, Response
from twisted.web.error import SchemeNotSupported

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
        inputFile = StringIO.StringIO(inputBytes)
        inputFile.seek(5)
        producer = MultiPartProducer({
                "field": ('file name', None, FileBodyProducer(
                        inputFile, cooperator=self.cooperator))
                })

        # Make sure we are generous enough not to alter seek position:
        self.assertEqual(inputFile.tell(), 5)

        # Total length is hard to calculate manually
        # as it contains a lot of headers parameters, newlines and boundaries
        # let's assert for now that it's no less than the input parameter
        self.assertTrue(producer.length > len(inputBytes) - 5)


    def test_defaultCooperator(self):
        """
        If no L{Cooperator} instance is passed to L{MultiPartProducer}, the
        global cooperator is used.
        """
        producer = MultiPartProducer({
                "field": ('file name', None, FileBodyProducer(
                        StringIO.StringIO("yo"),
                        cooperator=self.cooperator))
                })
        self.assertEqual(task.cooperate, producer._cooperate)


    def test_startProducing(self):
        """
        L{MultiPartProducer.startProducing} starts writing bytes from the input
        file to the given L{IConsumer} and returns a L{Deferred} which fires
        when they have all been written.
        """

        output = StringIO.StringIO()
        consumer = StringConsumer(output)

        producer = MultiPartProducer({
                "field": ('file name', "text/hello-world", FileBodyProducer(
                        StringIO.StringIO("Hello, World"),
                        cooperator=self.cooperator,
                        ))
                }, cooperator=self.cooperator,
                boundary="heyDavid")

        complete = producer.startProducing(consumer)

        while self._scheduled:
            self._scheduled.pop(0)()

        self.assertEqual(self.newLines("""--heyDavid
Content-Disposition: form-data; name="field", filename="file name"
Content-Type: text/hello-world
Content-Length: 12

Hello, World
--heyDavid--
"""), output.getvalue())
        self.assertEqual(None, self.successResultOf(complete))

