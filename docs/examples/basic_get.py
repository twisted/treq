from twisted.internet.task import react

import treq


async def basic_get(reactor):
    resp = await treq.get("https://httpbin.org/get")
    print(resp.code, resp.phrase)
    print(resp.headers)
    print(await resp.text())


react(basic_get)
