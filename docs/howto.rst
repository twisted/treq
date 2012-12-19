Handling Streaming Responses
----------------------------

In addition to `receiving responses <http://twistedmatrix.com/documents/current/web/howto/client.html#auto4>`_ with ``IResponse.deliverBody``.

treq provides a helper function :py:func:`treq.collect` which takes a
``response``, and a single argument function which will be called with all new
data available from the response.  Much like ``IProtocol.dataReceived``,
:py:func:`treq.collect` knows nothing about the framing of your data and will
simply call your collector function with any data that is currently available.

Here is an example which simply a ``file`` object's write method to
:py:func:`treq.collect` to save the response body to a file.

.. literalinclude:: _examples/download_file.py
    :linenos:
