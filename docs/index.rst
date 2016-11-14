treq: High-level Twisted HTTP Client API
========================================

treq depends on Twisted 12.3.0 or later and optionally pyOpenSSL.
Python 3 support requires at least Twisted 15.5.

Why?
----

`requests`_ by `Kenneth Reitz`_ is a wonderful library.
I want the same ease of use when writing Twisted applications.
treq is not of course a perfect clone of `requests`.
I have tried to stay true to the do-what-I-mean spirit of the `requests` API and also kept the API familiar to users of `Twisted`_ and ``twisted.web.client.Agent`` on which treq is based.

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


Why not 100% requests-alike?
----------------------------

Initially when I started off working on treq I thought the API should look exactly like `requests`_ except anything that would involve the network would return a ``Deferred``.

Over time while attempting to mimic the `requests`_ API it became clear that not enough code could be shared between `requests`_ and treq for it to be worth the effort to translate many of the usage patterns from `requests`_.

With the current version of treq I have tried to keep the API simple, yet remain familiar to users of Twisted and its lower-level HTTP libraries.


Feature Parity w/ Requests
--------------------------

Even though mimicing the `requests`_ API is not a goal, supporting most of it's features is.
Here is a list of `requests`_ features and their status in treq.

+----------------------------------+----------+----------+
|                                  | requests |   treq   |
+----------------------------------+----------+----------+
| International Domains and URLs   | yes      | yes      |
+----------------------------------+----------+----------+
| Keep-Alive & Connection Pooling  | yes      | yes      |
+----------------------------------+----------+----------+
| Sessions with Cookie Persistence | yes      | yes      |
+----------------------------------+----------+----------+
| Browser-style SSL Verification   | yes      | yes      |
+----------------------------------+----------+----------+
| Basic Authentication             | yes      | yes      |
+----------------------------------+----------+----------+
| Digest Authentication            | yes      | no       |
+----------------------------------+----------+----------+
| Elegant Key/Value Cookies        | yes      | yes      |
+----------------------------------+----------+----------+
| Automatic Decompression          | yes      | yes      |
+----------------------------------+----------+----------+
| Unicode Response Bodies          | yes      | yes      |
+----------------------------------+----------+----------+
| Multipart File Uploads           | yes      | yes      |
+----------------------------------+----------+----------+
| Connection Timeouts              | yes      | yes      |
+----------------------------------+----------+----------+
| .netrc support                   | yes      | no       |
+----------------------------------+----------+----------+
| Python 2.6                       | yes      | no       |
+----------------------------------+----------+----------+
| Python 2.7                       | yes      | yes      |
+----------------------------------+----------+----------+
| Python 3.x                       | yes      | yes      |
+----------------------------------+----------+----------+

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
