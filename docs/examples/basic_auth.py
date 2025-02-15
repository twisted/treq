from _utils import print_response
from twisted.internet.task import react

import treq


async def basic_auth(reactor):
    resp = await treq.get(
        "https://httpbin.org/basic-auth/treq/treq",
        auth=("treq", "treq"),
    )
    await print_response(resp)


react(basic_auth)
