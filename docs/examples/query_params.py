from twisted.internet.task import react
from twisted.internet.defer import inlineCallbacks

import treq


@inlineCallbacks
def main(reactor):
    print 'List of tuples'
    resp = yield treq.get('http://httpbin.org/get',
                          params=[('foo', 'bar'), ('baz', 'bax')])
    content = yield treq.content(resp)
    print content

    print 'Single value dictionary'
    resp = yield treq.get('http://httpbin.org/get',
                          params={'foo': 'bar', 'baz': 'bax'})
    content = yield treq.content(resp)
    print content

    print 'Multi value dictionary'
    resp = yield treq.get('http://httpbin.org/get',
                          params={'foo': ['bar', 'baz', 'bax']})
    content = yield treq.content(resp)
    print content

    print 'Mixed value dictionary'
    resp = yield treq.get('http://httpbin.org/get',
                          params={'foo': ['bar', 'baz'], 'bax': 'quux'})
    content = yield treq.content(resp)
    print content

    print 'Preserved query parameters'
    resp = yield treq.get('http://httpbin.org/get?foo=bar',
                          params={'baz': 'bax'})
    content = yield treq.content(resp)
    print content

react(main, [])
