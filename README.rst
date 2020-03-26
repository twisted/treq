treq: High-level Twisted HTTP Client API
========================================

|pypi|_
|build|_
|coverage|_

``treq`` is an HTTP library inspired by
`requests <https://requests.readthedocs.io/>`_ but written on top of
`Twisted <https://www.twistedmatrix.com>`_'s
`Agents <https://twistedmatrix.com/documents/current/api/twisted.web.client.Agent.html>`_.

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

For more info `read the docs <https://treq.readthedocs.org>`_.

Contributing
------------

``treq`` development is hosted on `GitHub <https://github.com/twisted/treq>`_.

We welcome contributions: feel to fork and send contributions over.
See `CONTRIBUTING.rst <https://github.com/twisted/treq/blob/master/CONTRIBUTING.rst>`_ for more info.

Code of Conduct
---------------

Refer to the `Twisted code of conduct <https://github.com/twisted/twisted/blob/trunk/code_of_conduct.md>`_.

Copyright and License
---------------------

``treq`` is made available under the MIT license.
See `LICENSE <./LICENSE>`_ for legal details and copyright notices.


.. |build| image:: https://api.travis-ci.org/twisted/treq.svg?branch=master
.. _build: https://travis-ci.org/twisted/treq

.. |coverage| image:: https://coveralls.io/repos/github/twisted/treq/badge.svg
.. _coverage: https://coveralls.io/github/twisted/treq

.. |pypi| image:: https://img.shields.io/pypi/v/treq.svg
.. _pypi: https://pypi.org/project/treq/
