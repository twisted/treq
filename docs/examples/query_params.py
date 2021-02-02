from twisted.internet.task import react
from twisted.internet.defer import inlineCallbacks

import treq


@inlineCallbacks
def main(reactor):
    print('List of tuples')
    resp = yield treq.get('https://httpbin.org/get',
                          params=[('foo', 'bar'), ('baz', 'bax')])
    content = yield resp.text()
    print(content)

    print('Single value dictionary')
    resp = yield treq.get('https://httpbin.org/get',
                          params={'foo': 'bar', 'baz': 'bax'})
    content = yield resp.text()
    print(content)

    print('Multi value dictionary')
    resp = yield treq.get('https://httpbin.org/get',
                          params={b'foo': [b'bar', b'baz', b'bax']})
    content = yield resp.text()
    print(content)

    print('Mixed value dictionary')
    resp = yield treq.get('https://httpbin.org/get',
                          params={'foo': [1, 2, 3], 'bax': b'quux', b'bar': 'foo'})
    content = yield resp.text()
    print(content)

    print('Preserved query parameters')
    resp = yield treq.get('https://httpbin.org/get?foo=bar',
                          params={'baz': 'bax'})
    content = yield resp.text()
    print(content)

react(main, [])
