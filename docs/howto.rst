Handling Streaming Responses
----------------------------

In addition to `receiving responses <http://twistedmatrix.com/documents/current/web/howto/client.html#auto4>`_
with ``IResponse.deliverBody``.

treq provides a helper function :py:func:`treq.collect` which takes a
``response``, and a single argument function which will be called with all new
data available from the response.  Much like ``IProtocol.dataReceived``,
:py:func:`treq.collect` knows nothing about the framing of your data and will
simply call your collector function with any data that is currently available.

Here is an example which simply a ``file`` object's write method to
:py:func:`treq.collect` to save the response body to a file.

.. literalinclude:: examples/download_file.py
    :linenos:
    :lines: 6-11

Full example: :download:`download_file.py <examples/download_file.py>`

Query Parameters
----------------

:py:func:`treq.request` supports a ``params`` keyword argument which will
be urlencoded and added to the ``url`` argument in addition to any query
parameters that may already exist.

The ``params`` argument may be either a ``dict`` or a ``list`` of
``(key, value)`` tuples.

If it is a ``dict`` then the values in the dict may either be a ``str`` value
or a ``list`` of ``str`` values.

.. literalinclude:: examples/query_params.py
    :linenos:
    :lines: 7-37

Full example: :download:`download_file.py <examples/download_file.py>`

Auth
----

HTTP Basic authentication as specified in `RFC 2617`_ is easily supported by
passing an ``auth`` keyword argument to any of the request functions.

The ``auth`` argument should be a tuple of the form ``('username', 'password')``.

.. literalinclude:: examples/basic_auth.py
    :linenos:
    :lines: 7-13

Full example: :download:`download_file.py <examples/download_file.py>`

.. _RFC 2617: http://www.ietf.org/rfc/rfc2617.txt

Redirects
---------

treq handles redirects by default.

The following will print a 200 OK response.

.. literalinclude:: examples/redirects.py
    :linenos:
    :lines: 7-13

Full example: :download:`redirects.py <examples/redirects.py>`

You can easily disable redirects by simply passing `allow_redirects=False` to
any of the request methods.

.. literalinclude:: examples/disable_redirects.py
    :linenos:
    :lines: 7-13

Full example: :download:`disable_redirects.py <examples/disable_redirects.py>`

You can even access the complete history of treq response objects by calling
the `history()` method on the the response.

.. literalinclude:: examples/response_history.py
    :linenos:
    :lines: 7-15

Full example: :download:`response_history.py <examples/response_history.py>`
