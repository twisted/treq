Making Requests
===============

.. module:: treq

.. autofunction:: request
.. autofunction:: get
.. autofunction:: head
.. autofunction:: post
.. autofunction:: put
.. autofunction:: patch
.. autofunction:: delete

Accessing Content
=================

.. autofunction:: collect
.. autofunction:: content
.. autofunction:: text_content
.. autofunction:: json_content

Responses
=========

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
