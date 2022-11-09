Testing Helpers
===============

The :mod:`treq.testing` module provides some tools for testing both HTTP clients which use the treq API and implementations of the `Twisted Web resource model <https://twistedmatrix.com/documents/current/api/twisted.web.resource.IResource.html>`_.

Writing tests for HTTP clients
------------------------------

The :class:`~treq.testing.StubTreq` class implements the :mod:`treq` module interface (:func:`treq.get()`, :func:`treq.post()`, etc.) but runs all I/O via a :class:`~twisted.internet.testing.MemoryReactor`.
It wraps a :class:`twisted.web.resource.IResource` provider which handles each request.

You can wrap a pre-existing `IResource` provider, or write your own.
For example, the :class:`twisted.web.resource.ErrorPage` resource can produce an arbitrary HTTP status code.
:class:`twisted.web.static.File` can serve files or directories.
And you can easily achieve custom responses by writing trivial resources yourself:

.. literalinclude:: examples/iresource.py
    :linenos:
    :pyobject: JsonResource

However, those resources don't assert anything about the request.
The :class:`~treq.testing.RequestSequence` and :class:`~treq.testing.StringStubbingResource` classes make it easy to construct a resource which encodes the expected request and response pairs.
Do note that most parameters to these functions must be bytes—it's safest to use the ``b''`` string syntax, which works on both Python 2 and 3.

For example:

.. literalinclude:: examples/testing_seq.py
    :linenos:

This may be run with ``trial testing_seq.py``.
Download: :download:`testing_seq.py <examples/testing_seq.py>`.

Loosely matching the request
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you don't care about certain parts of the request, you can pass :data:`unittest.mock.ANY`, which compares equal to anything.
This sequence matches a single GET request with any parameters or headers:

.. code-block:: python

    from unittest.mock import ANY

    RequestSequence([
        ((b'get', ANY, ANY, b''), (200, {}, b'ok'))
    ])


If you care about headers, use :class:`~treq.testing.HasHeaders` to make assertions about the headers present in the request.
It compares equal to a superset of the headers specified, which helps make your test robust to changes in treq or Agent.
Right now treq adds the ``Accept-Encoding: gzip`` header, but as support for additional compression methods is added, this may change.

Writing tests for Twisted Web resources
---------------------------------------

Since :class:`~treq.testing.StubTreq` wraps any resource, you can use it to test your server-side code as well.
This is superior to calling your resource's methods directly or passing mock objects, since it uses a real :class:`~twisted.web.client.Agent` to generate the request and a real :class:`~twisted.web.server.Site` to process the response.
Thus, the ``request`` object your code interacts with is a *real* :class:`twisted.web.server.Request` and behaves the same as it would in production.

Note that if your resource returns :data:`~twisted.web.server.NOT_DONE_YET` you must keep a reference to the :class:`~treq.testing.RequestTraversalAgent` and call its :meth:`~treq.testing.RequestTraversalAgent.flush()` method to spin the memory reactor once the server writes additional data before the client will receive it.

