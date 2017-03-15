import json

from zope.interface import implementer
from twisted.web.resource import IResource


@implementer(IResource)
class JsonResource(object):
    isLeaf = True  # NB: means getChildWithDefault will not be called

    def __init__(self, data):
        self.data = data

    def render(self, request):
        request.setHeader(b'Content-Type', b'application/json')
        return json.dumps(self.data).encode('utf-8')
