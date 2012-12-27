from __future__ import print_function

import treq


def print_response(response):
    print(response.code, response.phrase)
    print(response.headers)

    return treq.text_content(response).addCallback(print)
