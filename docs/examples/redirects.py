from twisted.internet.task import react
from _utils import print_response

import treq


def main(reactor, *args):
    http_client = treq
    d = http_client.get('http://httpbin.org/redirect/1')
    d.addCallback(print_response)
    return d

react(main, [])
