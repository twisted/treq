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

Release notes
-------------

We use `towncrier`_ to manage our release notes.
Basically, every pull request that has a user visible effect should add a short file to the `changelog.d/ <./changelog.d>`_ directory describing the change,
with a name like <ISSUE NUMBER>.<TYPE>.rst.
See `changelog.d/README.rst <changelog.d/README.rst>`_ for details.
This way we can keep a good list of changes as we go,
which makes the release manager happy,
which means we get more frequent releases,
which means your change gets into users’ hands faster.

.. _towncrier: https://pypi.org/project/towncrier/
