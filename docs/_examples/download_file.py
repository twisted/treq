from twisted.internet import reactor

import treq

def download_file(url, destination):
    d = treq.get(url)
    d.addCallback(treq.collect, destination.write)
    d.addBoth(destination.close)
    return d

def _do():
    d = download_file('http://httpbin.org/get', file('get.txt', 'w'))
    d.addBoth(lambda _: reactor.stop())

reactor.callWhenRunning(_do)
reactor.run()
