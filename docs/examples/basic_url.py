from _utils import print_response
from hyperlink import DecodedURL
from twisted.internet.task import react

import treq


async def basic_url(reactor):
    url = (
        DecodedURL.from_text("https://httpbin.org")
        .child("get")  # add path /get
        .add("foo", "&")  # add query ?foo=%26
    )
    print(url.to_text())
    await print_response(await treq.get(url))


react(basic_url)
