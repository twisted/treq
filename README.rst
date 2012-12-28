treq
====

|build|_

``treq`` is an HTTP library inspired by
`requests <http://www.python-requests.org>`_ but written on top of
`Twisted <http://www.twistedmatrix.com>`_'s
`Agents <http://twistedmatrix.com/documents/current/api/twisted.web.client.Agent.html>`_.

It provides a simple, higher level API for making HTTP requests when
using Twisted.

.. code-block:: python

    >>> from treq import get

    >>> def done(response):
    ...     print response.code
    ...     reactor.stop()

    >>> get("http://www.github.com").addCallback(done)

    >>> from twisted.internet import reactor
    >>> reactor.run()
    200

For more info `read the docs <http://treq.readthedocs.org>`_.

Contribute
==========

``treq`` is hosted on `GitHub <http://github.com/dreid/treq>`_.

Feel free to fork and send contributions over.

Developing
==========

Install dependencies:

::

    pip install -r requirements-dev.txt

Optionally install PyOpenSSL:

::

    pip install PyOpenSSL

Run Tests (unit & integration):

::

    trial treq

Lint:

::

    pep8 treq
    pyflakes treq

Build docs:

::

    cd docs; make html

.. |build| image:: https://secure.travis-ci.org/dreid/treq.png?branch=master
.. _build: http://travis-ci.org/dreid/treq
