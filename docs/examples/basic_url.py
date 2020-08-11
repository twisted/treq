# -*- encoding: utf-8 -*-
from hyperlink import DecodedURL
from twisted.internet.task import react
from _utils import print_response

import treq

def main(reactor):
    url = (
        DecodedURL.from_text(u"https://httpbin.org")
        .child(u"get")      # add path /get
        .add(u"foo", u"&")  # add query ?foo=%26
    )
    print(url.to_text())
    return treq.get(url).addCallback(print_response)

react(main, [])
