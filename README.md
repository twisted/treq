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

Contribute
==========

`treq` is hosted on [GitHub](http://www.github.com/dreid/treq).

Feel free to fork and send contributions over.
