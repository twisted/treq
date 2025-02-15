from _utils import print_response
from twisted.internet.task import react

import treq


async def redirects(reactor):
    resp = await treq.get("https://httpbin.org/redirect/1")
    await print_response(resp)


react(redirects)
