"""
Tests for :py:mod:`treq.test.local_httpbin.parent`
"""
import attr

import json

import signal

import sys

from twisted.internet import defer
from twisted.internet.interfaces import (IProcessTransport,
                                         IReactorCore,
                                         IReactorProcess)
from twisted.python.failure import Failure

from treq.test.util import skip_on_windows_because_of_199

from twisted.internet.error import ProcessTerminated, ConnectionDone

try:
    from twisted.internet.testing import MemoryReactor, StringTransport
except ImportError:
    from twisted.test.proto_helpers import MemoryReactor, StringTransport

from twisted.trial.unittest import SynchronousTestCase

from zope.interface import implementer, verify

from .. import parent, shared


skip = skip_on_windows_because_of_199()


@attr.s
class FakeProcessTransportState(object):
    """
    State for :py:class:`FakeProcessTransport`.
    """
    standard_in_closed = attr.ib(default=False)
    standard_out_closed = attr.ib(default=False)
    standard_error_closed = attr.ib(default=False)
    signals = attr.ib(default=attr.Factory(list))


@implementer(IProcessTransport)
@attr.s
class FakeProcessTransport(StringTransport, object):
    """
    A fake process transport.
    """
    pid = 1234

    _state = attr.ib()

    def closeStdin(self):
        """
        Close standard in.
        """
        self._state.standard_in_closed = True

    def closeStdout(self):
        """
        Close standard out.
        """
        self._state.standard_out_closed = True

    def closeStderr(self):
        """
        Close standard error.
        """
        self._state.standard_error_closed = True

    def closeChildFD(self, descriptor):
        """
        Close a child's file descriptor.

        :param descriptor: See
            :py:class:`IProcessProtocol.closeChildFD`
        """

    def writeToChild(self, childFD, data):
        """
        Write data to a child's file descriptor.

        :param childFD: See :py:class:`IProcessProtocol.writeToChild`
        :param data: See :py:class:`IProcessProtocol.writeToChild`
        """

    def signalProcess(self, signalID):
        """
        Send a signal.

        :param signalID: See
            :py:class:`IProcessProtocol.signalProcess`
        """
        self._state.signals.append(signalID)


class FakeProcessTransportTests(SynchronousTestCase):
    """
    Tests for :py:class:`FakeProcessTransport`.
    """

    def setUp(self):
        self.state = FakeProcessTransportState()
        self.transport = FakeProcessTransport(self.state)

    def test_provides_interface(self):
        """
        Instances provide :py:class:`IProcessTransport`.
        """
        verify.verifyObject(IProcessTransport, self.transport)

    def test_closeStdin(self):
        """
        Closing standard in updates the state instance.
        """
        self.assertFalse(self.state.standard_in_closed)
        self.transport.closeStdin()
        self.assertTrue(self.state.standard_in_closed)

    def test_closeStdout(self):
        """
        Closing standard out updates the state instance.
        """
        self.assertFalse(self.state.standard_out_closed)
        self.transport.closeStdout()
        self.assertTrue(self.state.standard_out_closed)

    def test_closeStderr(self):
        """
        Closing standard error updates the state instance.
        """
        self.assertFalse(self.state.standard_error_closed)
        self.transport.closeStderr()
        self.assertTrue(self.state.standard_error_closed)


class HTTPServerProcessProtocolTests(SynchronousTestCase):
    """
    Tests for :py:class:`parent._HTTPBinServerProcessProtocol`
    """

    def setUp(self):
        self.transport_state = FakeProcessTransportState()
        self.transport = FakeProcessTransport(self.transport_state)

        self.all_data_received = defer.Deferred()
        self.terminated = defer.Deferred()

        self.protocol = parent._HTTPBinServerProcessProtocol(
            all_data_received=self.all_data_received,
            terminated=self.terminated,
        )

        self.protocol.makeConnection(self.transport)

    def assertStandardInputAndOutputClosed(self):
        """
        The transport's standard in, out, and error are closed.
        """
        self.assertTrue(self.transport_state.standard_in_closed)
        self.assertTrue(self.transport_state.standard_out_closed)
        self.assertTrue(self.transport_state.standard_error_closed)

    def test_receive_http_description(self):
        """
        Receiving a serialized :py:class:`_HTTPBinDescription` fires the
        ``all_data_received`` :py:class:`Deferred`.
        """
        self.assertNoResult(self.all_data_received)

        description = shared._HTTPBinDescription("host", 1234, "cert")

        self.protocol.lineReceived(
            json.dumps(attr.asdict(description)).encode('ascii')
        )

        self.assertStandardInputAndOutputClosed()

        self.assertEqual(self.successResultOf(self.all_data_received),
                         description)

    def test_receive_unexpected_line(self):
        """
        Receiving a line after the description synchronously raises in
        :py:class:`RuntimeError`
        """
        self.test_receive_http_description()
        with self.assertRaises(RuntimeError):
            self.protocol.lineReceived(b"unexpected")

    def test_connection_lost_before_receiving_data(self):
        """
        If the process terminates before its data is received, both
        ``all_data_received`` and ``terminated`` errback.
        """
        self.assertNoResult(self.all_data_received)

        self.protocol.connectionLost(Failure(ConnectionDone("done")))

        self.assertIsInstance(
            self.failureResultOf(self.all_data_received).value,
            ConnectionDone,
        )

        self.assertIsInstance(
            self.failureResultOf(self.terminated).value,
            ConnectionDone,
        )

    def test_connection_lost(self):
        """
        ``terminated`` fires when the connection is lost.
        """
        self.test_receive_http_description()

        self.protocol.connectionLost(Failure(ConnectionDone("done")))

        self.assertIsInstance(
            self.failureResultOf(self.terminated).value,
            ConnectionDone,
        )


@attr.s
class SpawnedProcess(object):
    """
    A call to :py:class:`MemoryProcessReactor.spawnProcess`.
    """
    process_protocol = attr.ib()
    executable = attr.ib()
    args = attr.ib()
    env = attr.ib()
    path = attr.ib()
    uid = attr.ib()
    gid = attr.ib()
    use_pty = attr.ib()
    child_fds = attr.ib()
    returned_process_transport = attr.ib()
    returned_process_transport_state = attr.ib()

    def send_stdout(self, data):
        """
        Send data from the process' standard out.

        :param data: The standard out data.
        """
        self.process_protocol.childDataReceived(1, data)

    def end_process(self, reason):
        """
        End the process.

        :param reason: The reason.
        :type reason: :py:class:`Failure`
        """
        self.process_protocol.processEnded(reason)


@implementer(IReactorCore, IReactorProcess)
class MemoryProcessReactor(MemoryReactor):
    """
    A fake :py:class:`IReactorProcess` and :py:class:`IReactorCore`
    provider to be used in tests.
    """
    def __init__(self):
        MemoryReactor.__init__(self)
        self.spawnedProcesses = []

    def spawnProcess(self, processProtocol, executable, args=(), env={},
                     path=None, uid=None, gid=None, usePTY=0, childFDs=None):
        """
        :ivar process_protocol: Stores the protocol passed to the reactor.
        :return: An L{IProcessTransport} provider.
        """
        transport_state = FakeProcessTransportState()
        transport = FakeProcessTransport(transport_state)

        self.spawnedProcesses.append(SpawnedProcess(
            process_protocol=processProtocol,
            executable=executable,
            args=args,
            env=env,
            path=path,
            uid=uid,
            gid=gid,
            use_pty=usePTY,
            child_fds=childFDs,
            returned_process_transport=transport,
            returned_process_transport_state=transport_state,
        ))

        processProtocol.makeConnection(transport)

        return transport


class MemoryProcessReactorTests(SynchronousTestCase):
    """
    Tests for :py:class:`MemoryProcessReactor`
    """

    def test_provides_interfaces(self):
        """
        :py:class:`MemoryProcessReactor` instances provide
        :py:class:`IReactorCore` and :py:class:`IReactorProcess`.
        """
        reactor = MemoryProcessReactor()
        verify.verifyObject(IReactorCore, reactor)
        verify.verifyObject(IReactorProcess, reactor)


class HTTPBinProcessTests(SynchronousTestCase):
    """
    Tests for :py:class:`_HTTPBinProcesss`.
    """

    def setUp(self):
        self.reactor = MemoryProcessReactor()
        self.opened_file_descriptors = []

    def fd_recording_open(self, *args, **kwargs):
        """
        Record the file descriptors of files opened by
        :py:func:`open`.

        :return: A file object.
        """
        fobj = open(*args, **kwargs)
        self.opened_file_descriptors.append(fobj.fileno())
        return fobj

    def spawned_process(self):
        """
        Assert that ``self.reactor`` has spawned only one process and
        return the :py:class:`SpawnedProcess` representing it.

        :return: The :py:class:`SpawnedProcess`.
        """
        self.assertEqual(len(self.reactor.spawnedProcesses), 1)
        return self.reactor.spawnedProcesses[0]

    def assertSpawnAndDescription(self, process, args, description):
        """
        Assert that spawning the given process invokes the command
        with the given args, that standard error is redirected, that
        it is killed at reactor shutdown, and that it returns a
        description that matches the provided one.

        :param process: :py:class:`_HTTPBinProcesss` instance.
        :param args: The arguments with which to execute the child
            process.
        :type args: :py:class:`tuple` of :py:class:`str`

        :param description: The expected
            :py:class:`_HTTPBinDescription`.

        :return: The returned :py:class:`_HTTPBinDescription`
        """
        process._open = self.fd_recording_open

        description_deferred = process.server_description(self.reactor)

        spawned_process = self.spawned_process()

        self.assertEqual(spawned_process.args, args)

        self.assertEqual(len(self.opened_file_descriptors), 1)
        [error_log_fd] = self.opened_file_descriptors

        self.assertEqual(spawned_process.child_fds.get(2), error_log_fd)

        self.assertNoResult(description_deferred)

        spawned_process.send_stdout(description.to_json_bytes() + b'\n')

        before_shutdown = self.reactor.triggers["before"]["shutdown"]
        self.assertEqual(len(before_shutdown), 1)
        [(before_shutdown_function, _, _)] = before_shutdown

        self.assertEqual(before_shutdown_function, process.kill)

        self.assertEqual(self.successResultOf(description_deferred),
                         description)

    def test_server_description_spawns_process(self):
        """
        :py:class:`_HTTPBinProcess.server_description` spawns an
        ``httpbin`` child process that it monitors with
        :py:class:`_HTTPBinServerProcessProtocol`, and redirects its
        standard error to a log file.
        """
        httpbin_process = parent._HTTPBinProcess(https=False)
        description = shared._HTTPBinDescription(host="host", port=1234)

        self.assertSpawnAndDescription(
            httpbin_process,
            [
                sys.executable,
                '-m',
                'treq.test.local_httpbin.child'
            ],
            description)

    def test_server_description_spawns_process_https(self):
        """
        :py:class:`_HTTPBinProcess.server_description` spawns an
        ``httpbin`` child process that listens over HTTPS, that it
        monitors with :py:class:`_HTTPBinServerProcessProtocol`, and
        redirects the process' standard error to a log file.
        """
        httpbin_process = parent._HTTPBinProcess(https=True)
        description = shared._HTTPBinDescription(host="host",
                                                 port=1234,
                                                 cacert="cert")

        self.assertSpawnAndDescription(
            httpbin_process,
            [
                sys.executable,
                '-m',
                'treq.test.local_httpbin.child',
                '--https',
            ],
            description)

    def test_server_description_caches_description(self):
        """
        :py:class:`_HTTPBinProcess.server_description` spawns an
        ``httpbin`` child process only once, after which it returns a
        cached :py:class:`_HTTPBinDescription`.
        """
        httpbin_process = parent._HTTPBinProcess(https=False)

        description_deferred = httpbin_process.server_description(self.reactor)

        self.spawned_process().send_stdout(
            shared._HTTPBinDescription(host="host", port=1234).to_json_bytes()
            + b'\n'
        )

        description = self.successResultOf(description_deferred)

        cached_description_deferred = httpbin_process.server_description(
            self.reactor,
        )

        cached_description = self.successResultOf(cached_description_deferred)

        self.assertIs(description, cached_description)

    def test_kill_before_spawn(self):
        """
        Killing a process before it has been spawned has no effect.
        """
        parent._HTTPBinProcess(https=False).kill()

    def test_kill(self):
        """
        Kill terminates the process as quickly as the platform allows,
        and the termination failure is suppressed.
        """
        httpbin_process = parent._HTTPBinProcess(https=False)

        httpbin_process.server_description(self.reactor)

        spawned_process = self.spawned_process()

        spawned_process.send_stdout(
            shared._HTTPBinDescription(host="host", port=1234).to_json_bytes()
            + b'\n'
        )

        termination_deferred = httpbin_process.kill()

        self.assertEqual(
            spawned_process.returned_process_transport_state.signals,
            ['KILL'],
        )

        spawned_process.end_process(
            Failure(ProcessTerminated(1, signal=signal.SIGKILL)),
        )

        self.successResultOf(termination_deferred)

    def test_kill_unexpected_exit(self):
        """
        The :py:class:`Deferred` returned by
        :py:meth:`_HTTPBinProcess.kill` errbacks with the failure when
        it is not :py:class:`ProcessTerminated`, or its signal does
        not match the expected signal.
        """
        for error in [ProcessTerminated(1, signal=signal.SIGIO),
                      ConnectionDone("Bye")]:
            httpbin_process = parent._HTTPBinProcess(https=False)

            httpbin_process.server_description(self.reactor)

            spawned_process = self.reactor.spawnedProcesses[-1]

            spawned_process.send_stdout(
                shared._HTTPBinDescription(host="host",
                                           port=1234).to_json_bytes()
                + b'\n'
            )

            termination_deferred = httpbin_process.kill()

            spawned_process.end_process(Failure(error))

            self.assertIs(self.failureResultOf(termination_deferred).value,
                          error)
