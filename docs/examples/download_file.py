import io
import functools

from twisted.internet.task import react
from twisted.internet import threads, defer

import treq


def deferToThread(reactor, f, *args, **kwargs):
    if reactor is None:
        from twisted.internet import reactor
    return threads.deferToThreadPool(
        reactor, reactor.getThreadPool(),
        f, *args, **kwargs
    )


@defer.inlineCallbacks
def download_file(reactor, url, dest):
    response = yield treq.get(url, reactor=reactor, unbuffered=True)
    f = yield deferToThread(reactor, io.open, dest, 'wb')
    try:
        yield treq.collect(
            response,
            functools.partial(deferToThread, reactor, f.write),
        )
    finally:
        yield deferToThread(reactor, f.close)

react(download_file, ['http://httpbin.org/get', 'download.txt'])
