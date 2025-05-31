from _utils import print_response
from twisted.internet.task import react
from twisted.web.client import Agent

from treq.client import HTTPClient


async def custom_agent(reactor):
    my_agent = Agent(reactor, connectTimeout=42)
    http_client = HTTPClient(my_agent)
    resp = await http_client.get(
        "https://secure.example.net/area51",
        auth=("admin", "you'll never guess!"),
    )
    await print_response(resp)


react(custom_agent)
