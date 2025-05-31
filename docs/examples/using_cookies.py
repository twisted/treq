from _utils import print_response
from twisted.internet.task import react

import treq


async def using_cookies(reactor):
    resp = await treq.get("https://httpbin.org/cookies/set?hello=world")

    jar = resp.cookies()
    [cookie] = treq.cookies.search(jar, domain="httpbin.org", name="hello")
    print("The server set our hello cookie to: {}".format(cookie.value))

    await treq.get("https://httpbin.org/cookies", cookies=jar).addCallback(
        print_response
    )


react(using_cookies)
