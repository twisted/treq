from twisted.application import internet, service
from twisted.internet import endpoints, reactor
from twisted.web import server, static


endpoint = endpoints.serverFromString(reactor, 'ssl:port=8443')
rootResource = static.File('.')
site = server.Site(rootResource)
webService = internet.StreamServerEndpointService(endpoint, site)
application = service.Application('https_server')
serviceCollection = service.IServiceCollection(application)
webService.setServiceParent(serviceCollection)