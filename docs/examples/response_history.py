from twisted.internet.task import react
from _utils import print_response

import treq


def main(reactor, *args):
    d = treq.get('http://httpbin.org/redirect/1')

    def cb(response):
        print 'Response history:', response.history()
        return print_response(response)

    d.addCallback(cb)
    return d

react(main, [])
