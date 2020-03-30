from twisted.internet.task import react
from _utils import print_response

import treq


def main(reactor, *args):
    d = treq.get('https://httpbin.org/redirect/1', allow_redirects=False)
    d.addCallback(print_response)
    return d

react(main, [])
