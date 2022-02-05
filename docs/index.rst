treq: High-level Twisted HTTP Client API
========================================

Release v\ |release| (:doc:`What's new? <changelog>`).

`treq <https://pypi.org/project/treq>`_ depends on a recent Twisted and functions on Python 2.7 and Python 3.3+ (including PyPy).

Why?
----

`requests`_ by Kenneth Reitz is a wonderful library.
I want the same ease of use when writing Twisted applications.
treq is not of course a perfect clone of `requests`_.
I have tried to stay true to the do-what-I-mean spirit of the `requests`_ API and also kept the API familiar to users of `Twisted`_ and :class:`twisted.web.client.Agent` on which treq is based.

.. _requests: https://requests.readthedocs.io/en/master/
.. _Twisted: https://twistedmatrix.com/

Quick Start
-----------

Installation

.. code-block:: console

    $ pip install treq

GET
+++

.. literalinclude:: examples/basic_get.py
    :pyobject: main

Full example: :download:`basic_get.py <examples/basic_get.py>`

POST
++++

.. literalinclude:: examples/basic_post.py
    :pyobject: main

Full example: :download:`basic_post.py <examples/basic_post.py>`


Why not 100% requests-alike?
----------------------------

Initially when I started off working on treq I thought the API should look exactly like `requests`_ except anything that would involve the network would return a :class:`~twisted.internet.defer.Deferred`.

Over time while attempting to mimic the `requests`_ API it became clear that not enough code could be shared between `requests`_ and treq for it to be worth the effort to translate many of the usage patterns from `requests`_.

With the current version of treq I have tried to keep the API simple, yet remain familiar to users of Twisted and its lower-level HTTP libraries.


Feature Parity with Requests
----------------------------

Even though mimicking the `requests`_ API is not a goal, supporting most of its features is.
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
| HTTP(S) Proxy Support            | yes      | no       |
+----------------------------------+----------+----------+
| .netrc support                   | yes      | no       |
+----------------------------------+----------+----------+
| Python 3.x                       | yes      | yes      |
+----------------------------------+----------+----------+

Table of Contents
-----------------

.. toctree::
    :maxdepth: 3

    howto
    testing
    api
    changelog

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
