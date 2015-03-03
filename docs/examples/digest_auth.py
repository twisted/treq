from twisted.internet.task import react
from _utils import print_response

import treq
from treq.auth import HTTPDigestAuth


def main(reactor, *args):
    d = treq.get(
        'http://httpbin.org/digest-auth/auth/treq/treq',
        auth=HTTPDigestAuth('treq', 'treq')
    )
    d.addCallback(print_response)
    return d

react(main, [])
