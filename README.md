treq
====

[![Build Status](https://secure.travis-ci.org/dreid/treq.png?branch=master)](http://travis-ci.org/dreid/treq)

`treq` is an HTTP library inspired by [requests](http://www.python-requests.org)
but written on top of [Twisted](http://www.twistedmatrix.com)'s
[Agents](http://twistedmatrix.com/documents/current/api/twisted.web.client.Agent.html).

It provides a simple, higher level API for making HTTP requests when using
Twisted.

    >>> from treq import get

    >>> def done(response):
    ...     print response.code
    ...     reactor.stop()

    >>> get("http://www.github.com").addCallback(done)

    >>> from twisted.internet import reactor
    >>> reactor.run()
    200

For more info [read the docs](http://treq.readthedocs.org).

Contribute
==========

`treq` is hosted on [GitHub](http://www.github.com/dreid/treq).

Feel free to fork and send contributions over.

Developing
==========

Install dependencies:

    pip install -r requirements-dev.txt


Optionally install PyOpenSSL:

    pip install PyOpenSSL


Run Tests (unit & integration):

    trial treq


Lint:

    pep8 treq
    pyflakes treq


Build docs:

    cd docs; make html

