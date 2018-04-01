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

    .. automethod:: request
    .. automethod:: get
    .. automethod:: head
    .. automethod:: post
    .. automethod:: put
    .. automethod:: patch
    .. automethod:: delete

Augmented Response Objects
--------------------------

:func:`treq.request`, :func:`treq.get`, etc. return an object which provides :class:`twisted.web.iweb.IResponse`, plus a few additional convenience methods:

.. module:: treq.response

.. class:: _Response

    .. automethod:: collect
    .. automethod:: content
    .. automethod:: json
    .. automethod:: text
    .. automethod:: history
    .. automethod:: cookies

    Inherited from :class:`twisted.web.iweb.IResponse`:

    :ivar version: See :attr:`IResponse.version <twisted.web.iweb.IResponse.version>`
    :ivar code: See :attr:`IResponse.code <twisted.web.iweb.IResponse.code>`
    :ivar phrase: See :attr:`IResponse.phrase <twisted.web.iweb.IResponse.pharse>`
    :ivar headers: See :attr:`IResponse.headers <twisted.web.iweb.IResponse.headers>`
    :ivar length: See :attr:`IResponse.length <twisted.web.iweb.IResponse.length>`
    :ivar request: See :attr:`IResponse.request <twisted.web.iweb.IResponse.request>`
    :ivar previousResponse: See :attr:`IResponse.previousResponse <twisted.web.iweb.IResponse.previousResponse>`

    .. method:: deliverBody(protocol)

        See :meth:`IResponse.deliverBody() <twisted.web.iweb.IResponse.deliverBody>`

    .. method:: setPreviousResponse(response)

        See :meth:`IResponse.setPreviousResponse() <twisted.web.iweb.IResponse.setPreviousResponse>`


Test Helpers
------------

.. automodule:: treq.testing
    :members:

MultiPartProducer Objects
-------------------------

:class:`treq.multipart.MultiPartProducer` is used internally when making requests which involve files.

.. automodule:: treq.multipart
    :members:
