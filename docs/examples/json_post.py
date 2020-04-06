from pprint import pprint

from twisted.internet import defer
from twisted.internet.task import react

import treq


@defer.inlineCallbacks
def main(reactor):
    response = yield treq.post(
        'https://httpbin.org/post',
        json={"msg": "Hello!"},
    )
    data = yield response.json()
    pprint(data)

react(main, [])
