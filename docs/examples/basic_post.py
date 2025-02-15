from _utils import print_response
from twisted.internet.task import react

import treq


def basic_post(reactor):
    resp = await treq.post(
        "https://httpbin.org/post",
        data={"form": "data"},
    )
    await print_response(resp)


react(basic_post)
