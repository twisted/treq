from __future__ import print_function
from twisted.internet.task import react
from twisted.web.iweb import IAgent
from _utils import print_response
from zope.interface import implementer

import treq


@implementer(IAgent)
class CustomAuth(object):
    """
    I implement a custom authorization scheme.
    """

    def __init__(self, agent):
        self._agent = agent

    def request(self, method, uri, headers=None, bodyProducer=None):
        print("Some authorization occurs here")
        return self._agent.request(method, uri, headers, bodyProducer)


def main(reactor, *args):
    d = treq.get(
        'http://httpbin.org/get',
        auth=CustomAuth,
    )
    d.addCallback(print_response)
    return d

react(main, [])
