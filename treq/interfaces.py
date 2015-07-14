"""
Interfaces.
"""

from zope.interface import Interface


class IStringResponseStubs(Interface):
    """
    An interface that :class:`StringStubbingResource` expects to provide it
    with a response based on what the
    """
    def get_response_for(method, url, params, headers, data):
        """
        :param bytes method: An HTTP method
        :param bytes url: The full URL of the request
        :param dict params: A dictionary of query parameters mapping query keys
            lists of values (sorted alphabetically)
        :param dict headers: A dictionary of headers mapping header keys to
            a list of header values (sorted alphabetically)
        :param str data: The request body.

        :return: a ``tuple`` of (code, headers, body) where the code is
            the HTTP status code, the headers is a dictionary of bytes
            (unlike the `headers` parameter, which is a dictionary of lists),
            and body is a string that will be returned as the response body.

        If there is a stubbing error, the return value is undefined (if an
        exception is raised, :obj:`Resource` will just eat it and return 500
        in its place).  But the stubbing error should definitely be recorded
        in the failures attribute.
        """
