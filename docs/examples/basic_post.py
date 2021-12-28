from twisted.internet.task import react
from _utils import print_response

import treq


def main(reactor):
    d = treq.post("https://httpbin.org/post",
                  data={"form": "data"})
    d.addCallback(print_response)
    return d

react(main, [])
