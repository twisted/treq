# Copyright 2012-2020 The treq Authors.
# See LICENSE for details.
from __future__ import absolute_import, division, print_function

import binascii
from typing import Union

from twisted.web.http_headers import Headers
from twisted.web.iweb import IAgent
from zope.interface import implementer


class UnknownAuthConfig(Exception):
    """
    The authentication config provided couldn't be interpreted.
    """
    def __init__(self, config):
        super(Exception, self).__init__(
            '{0!r} not of a known type.'.format(config))


@implementer(IAgent)
class _RequestHeaderSetterAgent(object):
    """
    Wrap an agent to set request headers

    :ivar _agent: The wrapped agent.

    :ivar _request_headers:
        Headers to set on each request before forwarding it to the wrapped
        agent.
    """
    def __init__(self, agent, headers):
        self._agent = agent
        self._headers = headers

    def request(self, method, uri, headers=None, bodyProducer=None):
        if headers is None:
            requestHeaders = self._headers
        else:
            requestHeaders = headers.copy()
            for header, values in self._headers.getAllRawHeaders():
                requestHeaders.setRawHeaders(header, values)

        return self._agent.request(
            method, uri, headers=requestHeaders, bodyProducer=bodyProducer)


def add_basic_auth(agent, username, password):
    # type: (IAgent, Union[str, bytes], Union[str, bytes]) -> IAgent
    """
    Wrap an agent to add HTTP basic authentication

    The returned agent sets the *Authorization* request header according to the
    basic authentication scheme described in :rfc:`7617`. This header contains
    the given *username* and *password* in plaintext, and thus should only be
    used over an encrypted transport (HTTPS).

    Note that the colon (``:``) is used as a delimiter between the *username*
    and *password*, so if either parameter includes a colon the interpretation
    of the *Authorization* header is server-defined.

    :param agent: Agent to wrap.
    :param username: The username.
    :param password: The password.

    :returns: :class:`~twisted.web.iweb.IAgent`
    """
    if not isinstance(username, bytes):
        username = username.encode('utf-8')
    if not isinstance(password, bytes):
        password = password.encode('utf-8')

    creds = binascii.b2a_base64(b'%s:%s' % (username, password)).rstrip(b'\n')
    return _RequestHeaderSetterAgent(
        agent,
        Headers({b'Authorization': [b'Basic ' + creds]}),
    )


def add_auth(agent, auth_config):
    """
    Wrap an agent to perform authentication

    :param agent: Agent to wrap.

    :param auth_config:
        A ``('username', 'password')`` tuple --- see :func:`add_basic_auth`.

    :returns: :class:`~twisted.web.iweb.IAgent`

    :raises UnknownAuthConfig:
        When the format *auth_config* isn't supported.
    """
    if isinstance(auth_config, tuple):
        return add_basic_auth(agent, auth_config[0], auth_config[1])

    raise UnknownAuthConfig(auth_config)
