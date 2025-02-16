from _utils import print_response
from twisted.internet.task import react

import treq


async def disable_redirects(reactor):
    resp = await treq.get(
        "https://httpbin.org/redirect/1",
        allow_redirects=False,
    )
    await print_response(resp)


react(disable_redirects)
