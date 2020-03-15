from twisted.internet.task import react

import treq


def download_file(reactor, url, destination_filename):
    destination = open(destination_filename, 'wb')
    d = treq.get(url, unbuffered=True)
    d.addCallback(treq.collect, destination.write)
    d.addBoth(lambda _: destination.close())
    return d

react(download_file, ['https://httpbin.org/get', 'download.txt'])
