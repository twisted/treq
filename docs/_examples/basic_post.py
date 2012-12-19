from __future__ import print_function

from twisted.internet import reactor

import treq


def print_response(r):
    print(r.code, r.phrase)
    print(r.headers)

    d = treq.content(r)
    d.addCallback(print)
    return d

d = treq.post("http://httpbin.org/post",
              '{"msg": "Hello!"}',
              headers={'Content-Type': ['application/json']})

d.addCallback(print_response)

d.addBoth(lambda _: reactor.stop())

reactor.run()
