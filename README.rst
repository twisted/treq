treq
====

|pypi|_
|build|_
|coverage|_

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

``treq`` is hosted on `GitHub <http://github.com/twisted/treq>`_.

Feel free to fork and send contributions over.

Developing
==========

Install dependencies:

::

    pip install treq[dev]

Run Tests (unit & integration):

::

    trial treq

Lint:

::

    pep8 treq
    pyflakes treq

Build docs::

    tox -e docs

.. |build| image:: https://api.travis-ci.org/twisted/treq.svg?branch=master
.. _build: https://travis-ci.org/twisted/treq

.. |coverage| image:: https://codecov.io/github/twisted/treq/coverage.svg?branch=master
.. _coverage: https://codecov.io/github/twisted/treq

.. |pypi| image:: https://img.shields.io/pypi/v/treq.svg
.. _pypi: https://pypi.python.org/pypi/treq
