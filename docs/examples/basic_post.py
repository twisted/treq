import json

from twisted.internet.task import react
from _utils import print_response

import treq


def main(reactor, *args):
    d = treq.post('https://httpbin.org/post',
                  json.dumps({"msg": "Hello!"}).encode('ascii'),
                  headers={b'Content-Type': [b'application/json']})
    d.addCallback(print_response)
    return d

react(main, [])
