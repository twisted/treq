.. treq documentation master file, created by
   sphinx-quickstart on Mon Dec 10 22:32:11 2012.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

treq: High-level Twisted HTTP Client API
========================================

Release v\ |release|.

treq depends on ``Twisted>=12.1.0`` and optionally pyOpenSSL.

All example code depends on ``Twisted>=12.3.0``.

Why?
----

`requests`_ by `Kenneth Reitz`_ is a wonderful library.  I want the same
ease of use when writing Twisted applications.  treq is not of course a
perfect clone of `requests`.  I have tried to stay true to the do-what-i-mean
spirit of the `requests` API and also kept the API familiar to users of
`Twisted`_ and ``twisted.web.client.Agent`` on which treq is based.

.. _requests: http://python-requests.org/
.. _Kenneth Reitz: https://www.gittip.com/kennethreitz/
.. _Twisted: http://twistedmatrix.com/

Quick Start
-----------
Installation::

    pip install treq

GET
+++

.. literalinclude:: examples/basic_get.py
    :linenos:
    :lines: 7-11

Full example: :download:`basic_get.py <examples/basic_get.py>`

POST
++++

.. literalinclude:: examples/basic_post.py
    :linenos:
    :lines: 9-14

Full example: :download:`basic_post.py <examples/basic_post.py>`

Howto
-----

.. toctree::
    :maxdepth: 3

    howto

API Documentation
-----------------

.. toctree::
   :maxdepth: 2

   api

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

