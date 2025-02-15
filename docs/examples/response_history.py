from _utils import print_response
from twisted.internet.task import react

import treq


async def main(reactor):
    response = await treq.get("https://httpbin.org/redirect/1")

    print("Response history:")
    print(response.history())
    await print_response(response)


react(main)
