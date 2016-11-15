API Reference
=============

This page lists all of the interfaces exposed by the `treq` package.

Making Requests
---------------

.. module:: treq

.. autofunction:: request
.. autofunction:: get
.. autofunction:: head
.. autofunction:: post
.. autofunction:: put
.. autofunction:: patch
.. autofunction:: delete

Accessing Content
-----------------

.. autofunction:: collect
.. autofunction:: content
.. autofunction:: text_content
.. autofunction:: json_content

HTTPClient Objects
------------------

.. module:: treq.client

The :class:`treq.client.HTTPClient` class provides the same interface as the :mod:`treq` module itself.

.. autoclass:: HTTPClient
    :members:
    :undoc-members:

Augmented Response Objects
--------------------------

:func:`treq.request`, :func:`treq.get`, etc. return an object which implements :class:`twisted.web.iweb.IResponse`, plus a few additional convenience methods:

.. module:: treq.response

.. class:: _Response

    .. automethod:: collect
    .. automethod:: content
    .. automethod:: json
    .. automethod:: text
    .. automethod:: history
    .. automethod:: cookies

    Inherited from :class:`twisted.web.iweb.IResponse`:

    :ivar version:
    :ivar code:
    :ivar phrase:
    :ivar headers:
    :ivar length:
    :ivar request:
    :ivar previousResponse:

    .. method:: deliverBody(protocol)
    .. method:: setPreviousResponse(response)

Test Helpers
------------

.. automodule:: treq.testing
    :members:

MultiPartProducer Objects
-------------------------

:class:`treq.multipart.MultiPartProducer` is used internally when making requests which involve files.

.. automodule:: treq.multipart
    :members:
