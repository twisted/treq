from _utils import print_response
from twisted.internet.task import react

import treq


async def main(reactor):
    response = await treq.get(
        "https://httpbin.org/basic-auth/treq/treq",
        auth=("treq", "treq"),
    )
    await print_response(response)


react(main)
