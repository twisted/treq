from OpenSSL import SSL

from twisted.internet import defer, endpoints, reactor, ssl, task
from twisted.python import filepath, log
from twisted.web import client

import sys
sys.path.append('.')

import treq


@defer.inlineCallbacks
def main(reactor, *args):
    pemFile = filepath.FilePath('cert.pem').getContent()
    certificate = ssl.Certificate.loadPEM(pemFile)
    customPolicy = client.BrowserLikePolicyForHTTPS(certificate)
    response = yield treq.get('https://127.0.0.1:8443/', policy=customPolicy)
    print response.code
    defer.returnValue(None)


def _error(failure):
    log.msg(str(failure), system='epicFail')
    if hasattr(failure.value, 'reasons'):
        reasons = failure.value.reasons
        response = failure.value.response
        log.msg(str(response), system='epicFail')
        for reason in reasons:
            log.msg(reason.getErrorMessage(), system='epicFail')


if __name__ == '__main__':
    log.startLogging(sys.stdout)
    d = task.react(main, [])
    d.addErrback(_error)
