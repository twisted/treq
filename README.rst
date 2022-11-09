treq: High-level Twisted HTTP Client API
========================================

|pypi|_
|calver|_
|coverage|_
|documentation|_

``treq`` is an HTTP library inspired by
`requests <https://requests.readthedocs.io/>`_ but written on top of
`Twisted <https://www.twistedmatrix.com>`_'s
`Agents <https://twistedmatrix.com/documents/current/api/twisted.web.client.Agent.html>`_.

It provides a simple, higher level API for making HTTP requests when
using Twisted.

.. code-block:: python

    >>> import treq

    >>> def done(response):
    ...     print(response.code)
    ...     reactor.stop()

    >>> treq.get("https://github.com").addCallback(done)

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


.. _pypi: https://pypi.org/project/treq/
.. |pypi| image:: https://img.shields.io/pypi/v/treq.svg
    :alt: PyPI

.. _calver: https://calver.org/
.. |calver| image:: https://img.shields.io/badge/calver-YY.MM.MICRO-22bfda.svg
    :alt: calver: YY.MM.MICRO

.. _coverage: https://coveralls.io/github/twisted/treq
.. |coverage| image:: https://coveralls.io/repos/github/twisted/treq/badge.svg
    :alt: Coverage

.. _documentation: https://treq.readthedocs.org
.. |documentation| image:: https://readthedocs.org/projects/treq/badge/
    :alt: Documentation
