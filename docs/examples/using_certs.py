from OpenSSL import SSL

from twisted.internet import endpoints, reactor, ssl, task
from twisted.python import filepath
from twisted.web import client

import treq


def main(reactor, *args):
    pemFile = filepath.FilePath('your-trust-root.pem').getContent()
    certificate = ssl.Certificate.loadPEM(pemFile)
    customPolicy = client.BrowserLikePolicyForHTTPS(certificate)
    d = treq.get('https://httpbin.org/get', policy=customPolicy)

    def _get_jar(resp):
        jar = resp.cookies()

        print 'The server set our hello cookie to: {0}'.format(jar['hello'])

        return treq.get('http://httpbin.org/cookies', cookies=jar)

    d.addCallback(_get_jar)
    d.addCallback(print_response)

    return d


if __name__ == '__main__':
    task.react(main, [])
