Use Cases
=========

Handling Streaming Responses
----------------------------

In addition to `receiving responses <https://twistedmatrix.com/documents/current/web/howto/client.html#receiving-responses>`_
with :meth:`IResponse.deliverBody`, treq provides a helper function
:py:func:`treq.collect` which takes a
``response`` and a single argument function which will be called with all new
data available from the response.  Much like :meth:`IProtocol.dataReceived`,
:py:func:`treq.collect` knows nothing about the framing of your data and will
simply call your collector function with any data that is currently available.

Here is an example which simply a file object's write method to
:py:func:`treq.collect` to save the response body to a file.

.. literalinclude:: examples/download_file.py
    :linenos:
    :lines: 6-11

Full example: :download:`download_file.py <examples/download_file.py>`

Query Parameters
----------------

:py:func:`treq.HTTPClient.request` supports a ``params`` keyword argument which will
be URL-encoded and added to the ``url`` argument in addition to any query
parameters that may already exist.

The ``params`` argument may be either a ``dict`` or a ``list`` of
``(key, value)`` tuples.

If it is a ``dict`` then the values in the dict may either be a ``str`` value
or a ``list`` of ``str`` values.

.. literalinclude:: examples/query_params.py
    :linenos:
    :lines: 7-37

Full example: :download:`query_params.py <examples/query_params.py>`

Auth
----

HTTP Basic authentication as specified in :rfc:`2617` is easily supported by
passing an ``auth`` keyword argument to any of the request functions.

The ``auth`` argument should be a tuple of the form ``('username', 'password')``.

.. literalinclude:: examples/basic_auth.py
    :linenos:
    :lines: 7-15

Full example: :download:`basic_auth.py <examples/basic_auth.py>`

Redirects
---------

treq handles redirects by default.

The following will print a 200 OK response.

.. literalinclude:: examples/redirects.py
    :linenos:
    :lines: 7-12

Full example: :download:`redirects.py <examples/redirects.py>`

You can easily disable redirects by simply passing `allow_redirects=False` to
any of the request methods.

.. literalinclude:: examples/disable_redirects.py
    :linenos:
    :lines: 7-12

Full example: :download:`disable_redirects.py <examples/disable_redirects.py>`

You can even access the complete history of treq response objects by calling
the :meth:`~treq.response._Response.history()` method on the response.

.. literalinclude:: examples/response_history.py
    :linenos:
    :lines: 7-15

Full example: :download:`response_history.py <examples/response_history.py>`


Cookies
-------

Cookies can be set by passing a ``dict`` or ``cookielib.CookieJar`` instance
via the ``cookies`` keyword argument.  Later cookies set by the server can be
retrieved using the :py:meth:`~treq.response._Response.cookies()` method of the response.

The object returned by :py:meth:`~treq.response._Response.cookies()` supports the same key/value
access as `requests cookies <https://requests.readthedocs.io/en/latest/user/quickstart/#cookies>`_.

.. literalinclude:: examples/using_cookies.py
    :linenos:
    :lines: 7-20

Full example: :download:`using_cookies.py <examples/using_cookies.py>`

Customizing the Twisted Agent
-----------------------------

The main :py:mod:`treq` module has helper functions that automatically instantiate
an instance of :py:class:`treq.client.HTTPClient`.  You can create an instance
of :py:class:`~treq.client.HTTPClient` directly in order to customize the 
paramaters used to initialize it.
Internally, the :py:class:`~treq.client.HTTPClient` wraps an instance of 
:py:class:`twisted.web.client.Agent`.  When you create an instance of 
:py:class:`~treq.client.HTTPClient`, you must initialize it with an instance of
:py:class:`~twisted.web.client.Agent`.  This allows you to customize its
behavior.

.. literalinclude:: examples/custom_agent.py
    :linenos:
    :lines: 6-19

Full example: :download:`custom_agent.py <examples/custom_agent.py>`
