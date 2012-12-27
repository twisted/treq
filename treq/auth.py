from twisted.web.http_headers import Headers


class UnknownAuthConfig(Exception):
    def __init__(self, config):
        super(Exception, self).__init__(
            '{0!r} not of a known type.'.format(config))


class _RequestHeaderSettingAgent(object):
    def __init__(self, agent, request_headers):
        self._agent = agent
        self._request_headers = request_headers

    def request(self, method, uri, headers=None, bodyProducer=None):
        if headers is None:
            headers = self._request_headers
        else:
            for header, values in self._request_headers.getAllRawHeaders():
                headers.setRawHeaders(header, values)

        return self._agent.request(
            method, uri, headers=headers, bodyProducer=bodyProducer)


def add_basic_auth(agent, username, password):
    creds = '{0}:{1}'.format(username, password).encode('base64').strip()
    return _RequestHeaderSettingAgent(
        agent,
        Headers({'Authorization': ['Basic {0}'.format(creds)]}))


def add_auth(agent, auth_config):
    if isinstance(auth_config, tuple):
        return add_basic_auth(agent, auth_config[0], auth_config[1])

    raise UnknownAuthConfig(auth_config)
