from __future__ import absolute_import, division, print_function

from twisted.web.http_headers import Headers
from six.moves.urllib.parse import urlparse
import base64


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


class _PinToFirstHostAgent(object):
    """
    An {twisted.web.iweb.IAgent} implementing object that takes two
    agents, using the first as when the current request's host name
    matches first request's host name, and the second when it does
    not.
    """

    def __init__(self, first_agent, second_agent):
        self._first_agent = first_agent
        self._second_agent = second_agent
        self._first_host = None

    def request(self, method, uri, headers=None, bodyProducer=None):
        hostname = urlparse(uri).hostname
        if self._first_host in (None, hostname):
            self._first_host = hostname
            agent = self._first_agent
        else:
            agent = self._second_agent

        return agent.request(
            method, uri, headers=headers, bodyProducer=bodyProducer)


def add_basic_auth(agent, username, password):
    creds = base64.b64encode(
        '{0}:{1}'.format(username, password).encode('ascii'))
    return _RequestHeaderSettingAgent(
        agent,
        Headers({b'Authorization': [b'Basic ' + creds]}))


def add_auth(agent, auth_config):
    if isinstance(auth_config, tuple):
        return add_basic_auth(agent, auth_config[0], auth_config[1])
    elif callable(auth_config):
        return auth_config(agent)

    raise UnknownAuthConfig(auth_config)
