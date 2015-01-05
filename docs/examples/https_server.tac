from twisted.application import internet, service
from twisted.internet import endpoints, reactor, task
from twisted.web import server, static


endpoint = endpoints.serverFromString(
    reactor, 'ssl:certKey=./cert.pem:port=8443:privateKey=./private-key.pem'
)
rootResource = static.File('.')
site = server.Site(rootResource, logPath='./http.log')
webService = internet.StreamServerEndpointService(endpoint, site)
application = service.Application('https_server')
serviceCollection = service.IServiceCollection(application)
webService.setServiceParent(serviceCollection)