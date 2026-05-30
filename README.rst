treq: High-level Twisted HTTP Client API
========================================

.. |pypi| image:: https://img.shields.io/pypi/v/treq.svg
    :alt: PyPI
    :target: https://pypi.org/project/treq/

.. |calver| image:: https://img.shields.io/badge/calver-YY.MM.MICRO-22bfda.svg
    :alt: calver: YY.MM.MICRO
    :target: https://calver.org/

.. |coverage| image:: https://coveralls.io/repos/github/twisted/treq/badge.svg
    :alt: Coverage
    :target: https://coveralls.io/github/twisted/treq

.. |documentation| image:: https://readthedocs.org/projects/treq/badge/
    :alt: Documentation
    :target: https://treq.readthedocs.org

|pypi|
|calver|
|coverage|
|documentation|

``treq`` is an HTTP library inspired by
`requests <https://requests.readthedocs.io/>`_ but written on top of
`Twisted <https://twisted.org/>`_'s
`Agents <https://docs.twisted.org/en/stable/api/twisted.web.client.Agent.html>`_.

It provides a simple, higher level API for making HTTP requests when
using Twisted.

.. code-block:: python

    >>> import treq

    >>> async def main(reactor):
    ...     response = await treq.get("https://github.com")
    ...     print(response.code)
    ...     body = await response.text()
    ...     print("<!DOCTYPE html>" in body)

    >>> from twisted.internet.task import react
    >>> react(main)
    200
    True

For more info `read the docs <https://treq.readthedocs.org>`_.

Contributing
------------

``treq`` development is hosted on `GitHub <https://github.com/twisted/treq>`_.

We welcome contributions: feel free to fork and send contributions over.
See `CONTRIBUTING.rst <https://github.com/twisted/treq/blob/master/CONTRIBUTING.rst>`_ for more info.

Code of Conduct
---------------

Refer to the `Twisted code of conduct <https://github.com/twisted/twisted/blob/trunk/code_of_conduct.md>`_.

Copyright and License
---------------------

``treq`` is made available under the MIT license.
See `LICENSE <./LICENSE>`_ for legal details and copyright notices.


