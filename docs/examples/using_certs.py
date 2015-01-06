from twisted.internet import ssl, task
from twisted.python import filepath
from twisted.web import client

from _utils import print_response

import treq


def main(reactor, *args):
    pemFile = filepath.FilePath('server.pem').getContent()
    certificate = ssl.Certificate.loadPEM(pemFile)
    customPolicy = client.BrowserLikePolicyForHTTPS(certificate)

    d = treq.get('https://localhost:8443/', policy=customPolicy)
    d.addCallback(print_response)
    return d


task.react(main, [])
