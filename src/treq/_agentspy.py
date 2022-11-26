# Copyright (c) The treq Authors.
# See LICENSE for details.
from typing import Callable, List, Optional, Tuple

import attr
from twisted.internet.defer import Deferred
from twisted.web.http_headers import Headers
from twisted.web.iweb import IAgent, IBodyProducer
from zope.interface import implementer


@attr.s(frozen=True, order=False, slots=True)
class RequestRecord:
    """
    The details of a call to :meth:`_AgentSpy.request`

    :ivar method: The *method* argument to :meth:`IAgent.request`
    :ivar uri: The *uri* argument to :meth:`IAgent.request`
    :ivar headers: The *headers* argument to :meth:`IAgent.request`
    :ivar bodyProducer: The *bodyProducer* argument to :meth:`IAgent.request`
    :ivar deferred: The :class:`Deferred` returned by :meth:`IAgent.request`
    """

    method: bytes = attr.ib()
    uri: bytes = attr.ib()
    headers: Optional[Headers] = attr.ib()
    bodyProducer: Optional[IBodyProducer] = attr.ib()
    deferred: Deferred = attr.ib()


@implementer(IAgent)
@attr.s
class _AgentSpy:
    """
    An agent that records HTTP requests

    :ivar _callback:
        A function called with each :class:`RequestRecord`
    """

    _callback: Callable[[Tuple[RequestRecord]], None] = attr.ib()

    def request(self, method: bytes, uri: bytes,
                headers: Optional[Headers] = None,
                bodyProducer: Optional[IBodyProducer] = None
                ):
        if not isinstance(method, bytes):
            raise TypeError(
                "method must be bytes, not {!r} of type {}".format(method, type(method))
            )
        if not isinstance(uri, bytes):
            raise TypeError(
                "uri must be bytes, not {!r} of type {}".format(uri, type(uri))
            )
        if headers is not None and not isinstance(headers, Headers):
            raise TypeError(
                "headers must be {}, not {!r} of type {}".format(
                    type(Headers), headers, type(headers)
                )
            )
        if bodyProducer is not None and not IBodyProducer.providedBy(bodyProducer):
            raise TypeError(
                (
                    "bodyProducer must implement IBodyProducer, but {!r} does not."
                    " Is the implementation marked with @implementer(IBodyProducer)?"
                ).format(bodyProducer)
            )
        d = Deferred()
        record = RequestRecord(method, uri, headers, bodyProducer, d)
        self._callback(record)
        return d


def agent_spy() -> Tuple[IAgent, List[RequestRecord]]:
    """
    Record HTTP requests made with an agent

    This is suitable for low-level testing of wrapper agents. It validates
    the parameters of each call to :meth:`IAgent.request` (synchronously
    raising :exc:`TypeError`) and captures them as a :class:`RequestRecord`,
    which can then be used to inspect the request or generate a response by
    firing the :attr:`~RequestRecord.deferred`.

    :returns:
        A two-tuple of:

         - An :class:`twisted.web.iweb.IAgent`
         - A list of calls made to the agent's
           :meth:`~twisted.web.iweb.IAgent.request()` method
    """
    records = []
    agent = _AgentSpy(records.append)
    return agent, records
