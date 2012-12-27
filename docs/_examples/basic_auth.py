from __future__ import print_function

from twisted.internet import reactor

import treq


def print_response(r):
    print(r.code, r.phrase)
    print(r.headers)

    d = treq.content(r)
    d.addCallback(print)
    return d


def do():
    d = treq.get(
        'http://httpbin.org/basic-auth/treq/treq',
        auth=('treq', 'treq')
    )
    d.addCallback(print_response)
    d.addCallback(lambda _: reactor.stop())


reactor.callWhenRunning(do)
reactor.run()
