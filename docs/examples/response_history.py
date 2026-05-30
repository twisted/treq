from _utils import print_response
from twisted.internet.task import react

import treq


async def response_history(reactor):
    resp = await treq.get("https://httpbin.org/redirect/1")
    print("Response history:")
    print(resp.history())
    await print_response(resp)


react(response_history)
