from treq.client import HTTPClient


def head(url, **kwargs):
    return _client(**kwargs).head(url, **kwargs)


def get(url, headers=None, **kwargs):
    return _client(**kwargs).get(url, headers=headers, **kwargs)


def post(url, data=None, **kwargs):
    return _client(**kwargs).post(url, data=data, **kwargs)


def put(url, data=None, **kwargs):
    return _client(**kwargs).put(url, data=data, **kwargs)


def delete(url, **kwargs):
    return _client(**kwargs).delete(url, **kwargs)


def request(method, url, **kwargs):
    return _client(**kwargs).request(method, url, **kwargs)


#
# Private API
#

def _client(*args, **kwargs):
    return HTTPClient.with_config(**kwargs)
