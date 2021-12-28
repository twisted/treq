API Reference
=============

This page lists all of the interfaces exposed by the `treq` package.

Making Requests
---------------

The :py:mod:`treq` module provides several convenience functions for making requests.
These functions all create a default :py:class:`treq.client.HTTPClient` instance and pass their arguments to the appropriate :py:class:`~treq.client.HTTPClient` method.

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

The HTTP Client
===============

.. module:: treq.client

:class:`treq.client.HTTPClient` has methods that match the signatures of the convenience request functions in the :mod:`treq` module.

.. autoclass:: HTTPClient(agent, cookiejar=None, data_to_body_producer=IBodyProducer)

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
    :ivar phrase: See :attr:`IResponse.phrase <twisted.web.iweb.IResponse.phrase>`
    :ivar headers: See :attr:`IResponse.headers <twisted.web.iweb.IResponse.headers>`
    :ivar length: See :attr:`IResponse.length <twisted.web.iweb.IResponse.length>`
    :ivar request: See :attr:`IResponse.request <twisted.web.iweb.IResponse.request>`
    :ivar previousResponse: See :attr:`IResponse.previousResponse <twisted.web.iweb.IResponse.previousResponse>`

    .. method:: deliverBody(protocol)

        See :meth:`IResponse.deliverBody() <twisted.web.iweb.IResponse.deliverBody>`

    .. method:: setPreviousResponse(response)

        See :meth:`IResponse.setPreviousResponse() <twisted.web.iweb.IResponse.setPreviousResponse>`

Authentication
--------------

.. module:: treq.auth

.. autofunction:: add_auth

.. autofunction:: add_basic_auth

.. autoexception:: UnknownAuthConfig

Test Helpers
------------

.. module:: treq.testing

The :mod:`treq.testing` module contains tools for in-memory testing of HTTP clients and servers.

StubTreq Objects
~~~~~~~~~~~~~~~~

.. class:: treq.testing.StubTreq(resource)

    :class:`StubTreq` implements the same interface as the :mod:`treq` module
    or the :class:`~treq.client.HTTPClient` class, with the limitation that it
    does not support the ``files`` argument.

    .. method:: flush()

        Flush all data between pending client/server pairs.

        This is only necessary if a :obj:`Resource` under test returns
        :obj:`NOT_DONE_YET` from its ``render`` method, making a response
        asynchronous. In that case, after each write from the server,
        :meth:`flush()` must be called so the client can see it.

    As the methods on :class:`treq.client.HTTPClient`:

    .. method:: request

        See :func:`treq.request()`.

    .. method:: get

        See :func:`treq.get()`.

    .. method:: head

        See :func:`treq.head()`.

    .. method:: post

        See :func:`treq.post()`.

    .. method:: put

        See :func:`treq.put()`.

    .. method:: patch

        See :func:`treq.patch()`.

    .. method:: delete

        See :func:`treq.delete()`.

RequestTraversalAgent Objects
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: treq.testing.RequestTraversalAgent
    :members:

RequestSequence Objects
~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: treq.testing.RequestSequence
    :members:

StringStubbingResource Objects
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: treq.testing.StringStubbingResource
    :members:

HasHeaders Objects
~~~~~~~~~~~~~~~~~~

.. autoclass:: treq.testing.HasHeaders
    :members:

MultiPartProducer Objects
-------------------------

:class:`treq.multipart.MultiPartProducer` is used internally when making requests which involve files.

.. automodule:: treq.multipart
    :members:
