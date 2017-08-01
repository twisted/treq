"""
Spawn and monitor an ``httpbin`` child process.
"""
import attr

import signal
import sys
import os


from twisted.protocols import basic, policies
from twisted.internet import protocol, endpoints, error
from twisted.internet.defer import Deferred, succeed

from .shared import _HTTPBinDescription


class _HTTPBinServerProcessProtocol(basic.LineOnlyReceiver):
    """
    Manage the lifecycle of an ``httpbin`` process.
    """
    delimiter = b'\n'

    def __init__(self, all_data_received, terminated):
        """
        Manage the lifecycle of an ``httpbin`` process.

        :param all_data_received: A Deferred that will be called back
            with an :py:class:`_HTTPBinDescription` object
        :type all_data_received: :py:class:`Deferred`

        :param terminated: A Deferred that will be called back when
            the process has ended.
        :type terminated: :py:class:`Deferred`
        """
        self._all_data_received = all_data_received
        self._received = False
        self._terminated = terminated

    def lineReceived(self, line):
        if self._received:
            raise RuntimeError("Unexpected line: {!r}".format(line))
        description = _HTTPBinDescription.from_json_bytes(line)

        self._received = True

        # Remove readers and writers that leave the reactor in a dirty
        # state after a test.
        self.transport.closeStdin()
        self.transport.closeStdout()
        self.transport.closeStderr()

        self._all_data_received.callback(description)

    def connectionLost(self, reason):
        if not self._received:
            self._all_data_received.errback(reason)
        self._terminated.errback(reason)


@attr.s
class _HTTPBinProcess(object):
    """
    Manage an ``httpbin`` server process.

    :ivar _all_data_received: See
        :py:attr:`_HTTPBinServerProcessProtocol.all_data_received`
    :ivar _terminated: See
        :py:attr:`_HTTPBinServerProcessProtocol.terminated`
    """
    _https = attr.ib()

    _error_log_path = attr.ib(default='httpbin-server-error.log')

    _all_data_received = attr.ib(init=False, default=attr.Factory(Deferred))
    _terminated = attr.ib(init=False, default=attr.Factory(Deferred))

    _process = attr.ib(init=False, default=None)
    _process_description = attr.ib(init=False, default=None)

    _open = staticmethod(open)

    def _spawn_httpbin_process(self, reactor):
        """
        Spawn an ``httpbin`` process, returning a :py:class:`Deferred`
        that fires with the process transport and result.
        """
        server = _HTTPBinServerProcessProtocol(
            all_data_received=self._all_data_received,
            terminated=self._terminated
        )

        argv = [
            sys.executable,
            '-m',
            'treq.test.local_httpbin.child',
        ]

        if self._https:
            argv.append('--https')

        with self._open(self._error_log_path, 'wb') as error_log:
            endpoint = endpoints.ProcessEndpoint(
                reactor,
                sys.executable,
                argv,
                env=os.environ,
                childFDs={
                    1: 'r',
                    2: error_log.fileno(),
                },
            )
            # Processes are spawned synchronously.
            spawned = endpoint.connect(
                # ProtocolWrapper, WrappingFactory's protocol, has a
                # disconnecting attribute.  See
                # https://twistedmatrix.com/trac/ticket/6606
                policies.WrappingFactory(
                    protocol.Factory.forProtocol(lambda: server),
                ),
            )

        def wait_for_protocol(connected_protocol):
            process = connected_protocol.transport
            return self._all_data_received.addCallback(
                return_result_and_process, process,
            )

        def return_result_and_process(description, process):
            return description, process

        return spawned.addCallback(wait_for_protocol)

    def server_description(self, reactor):
        """
        Return a :py:class:`Deferred` that fires with the the process'
        :py:class:`_HTTPBinDescription`, spawning the process if
        necessary.
        """
        if self._process is None:
            ready = self._spawn_httpbin_process(reactor)

            def store_and_schedule_termination(description_and_process):
                description, process = description_and_process

                self._process = process
                self._process_description = description

                reactor.addSystemEventTrigger("before", "shutdown", self.kill)

                return self._process_description

            return ready.addCallback(store_and_schedule_termination)
        else:
            return succeed(self._process_description)

    def kill(self):
        """
        Kill the ``httpbin`` process.
        """
        if not self._process:
            return

        self._process.signalProcess("KILL")

        def suppress_process_terminated(exit_failure):
            exit_failure.trap(error.ProcessTerminated)
            if exit_failure.value.signal != signal.SIGKILL:
                return exit_failure

        return self._terminated.addErrback(suppress_process_terminated)
