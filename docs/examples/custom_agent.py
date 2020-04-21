from treq.client import HTTPClient
from _utils import print_response
from twisted.internet.task import react
from twisted.web.client import Agent

def make_custom_agent(reactor):
    return Agent(reactor, connectTimeout=42)

def main(reactor, *args):
    agent = make_custom_agent(reactor)
    http_client = HTTPClient(agent)
    d = http_client.get(
        'https://secure.example.net/area51',
        auth=('admin', "you'll never guess!"))
    d.addCallback(print_response)
    return d

react(main, [])

