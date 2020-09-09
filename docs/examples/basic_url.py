from hyperlink import DecodedURL
from twisted.internet.task import react
from _utils import print_response

import treq

def main(reactor):
    url = (
        DecodedURL.from_text("https://httpbin.org")
        .child("get")      # add path /get
        .add("foo", "&")  # add query ?foo=%26
    )
    print(url.to_text())
    return treq.get(url).addCallback(print_response)

react(main, [])
