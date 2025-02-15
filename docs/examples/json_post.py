from pprint import pprint

from twisted.internet.task import react

import treq


async def main(reactor):
    response = await treq.post(
        "https://httpbin.org/post",
        json={"msg": "Hello!"},
    )
    data = await response.json()
    pprint(data)


react(main)
