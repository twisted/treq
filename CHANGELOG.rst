=========
Changelog
=========

.. currentmodule:: treq

.. default-role:: any

.. towncrier release notes start

24.9.0 (2024-09-17)
===================

Features
--------

- treq now ships type annotations. (`#366 <https://github.com/twisted/treq/issues/366>`__)
- The new :mod:`treq.cookies` module provides helper functions for working with `http.cookiejar.Cookie` and `CookieJar` objects. (`#384 <https://github.com/twisted/treq/issues/384>`__)
- Python 3.13 is now supported. (`#391 <https://github.com/twisted/treq/issues/391>`__)


Bugfixes
--------

- :mod:`treq.content.text_content()` no longer generates deprecation warnings due to use of the ``cgi`` module. (`#355 <https://github.com/twisted/treq/issues/355>`__)


Deprecations and Removals
-------------------------

- Mixing the *json* argument with *files* or *data* now raises `TypeError`. (`#297 <https://github.com/twisted/treq/issues/297>`__)
- Passing non-string (`str` or `bytes`) values as part of a dict to the *headers* argument now results in a `TypeError`, as does passing any collection other than a `dict` or `Headers` instance. (`#302 <https://github.com/twisted/treq/issues/302>`__)
- Support for Python 3.7 and PyPy 3.8, which have reached end of support, has been dropped. (`#378 <https://github.com/twisted/treq/issues/378>`__)


Misc
----

- `#336 <https://github.com/twisted/treq/issues/336>`__, `#382 <https://github.com/twisted/treq/issues/382>`__, `#395 <https://github.com/twisted/treq/issues/395>`__


23.11.0 (2023-11-03)
====================

Features
--------

- When the collector passed to ``treq.collect(response, collector)`` throws an exception, that error will now be returned to the caller of ``collect()`` via the result ``Deferred``, and the underlying HTTP transport will be closed. (`#347 <https://github.com/twisted/treq/issues/347>`__)
- Python 3.11 is now supported. (`#364 <https://github.com/twisted/treq/issues/364>`__)
- Python 3.12 is now supported. (`#375 <https://github.com/twisted/treq/issues/375>`__)
- PyPy 3.9 is now supported. (`#365 <https://github.com/twisted/treq/issues/365>`__)
- PyPy 3.10 is now supported. (`#374 <https://github.com/twisted/treq/issues/374>`__)


Deprecations and Removals
-------------------------

- The minimum supported Twisted version has increased to 22.10.0. Older versions are no longer tested in CI. (`#374 <https://github.com/twisted/treq/issues/374>`__)
- Support for Python 3.6, which has reached end of support, has been dropped. (`#363 <https://github.com/twisted/treq/issues/363>`__)
- Support for Python 3.7, which reaches end of support 2023-06-27, is deprecated. This is the last release with support for Python 3.7. (`#361 <https://github.com/twisted/treq/issues/361>`__)
- Support for PyPy 3.7, which has reached end of support, has been removed. (`#365 <https://github.com/twisted/treq/issues/365>`__)
- Support for PyPy 3.8, which has reached end of support, is deprecated. This is the last release with support for PyPy 3.8. (`#374 <https://github.com/twisted/treq/issues/374>`__)


Misc
----

- `#349 <https://github.com/twisted/treq/issues/349>`__, `#350 <https://github.com/twisted/treq/issues/350>`__, `#352 <https://github.com/twisted/treq/issues/352>`__


22.2.0 (2022-02-08)
===================

Features
--------

- Python 3.10 and PyPy 3.8 are now supported. (`#338 <https://github.com/twisted/treq/issues/338>`__)


Bugfixes
--------

- Address a regression introduced in Treq 22.1.0 that prevented transmission of cookies with requests to ports other than 80, including HTTPS (443). (`#343 <https://github.com/twisted/treq/issues/343>`__)


Deprecations and Removals
-------------------------

- Support for Python 3.6, which has reached end of support, is deprecated. This is the last release with support for Python 3.6. (`#338 <https://github.com/twisted/treq/issues/338>`__)


22.1.0 (2022-01-29)
===================

Bugfixes
--------

- Cookies specified as a dict were sent to every domain, not just the domain of the request, potentially exposing them on redirect. See `GHSA-fhpf-pp6p-55qc <https://github.com/twisted/treq/security/advisories/GHSA-fhpf-pp6p-55qc>`_. (`#339 <https://github.com/twisted/treq/issues/339>`__, CVE-2022-23607)


21.5.0 (2021-05-24)
===================

Features
--------

- PEP 517/518 ``build-system`` metadata is now provided in ``pyproject.toml``. (`#329 <https://github.com/twisted/treq/issues/329>`__)


Bugfixes
--------

- ``treq.testing.StubTreq`` now persists ``twisted.web.server.Session`` instances between requests. (`#327 <https://github.com/twisted/treq/issues/327>`__)


Improved Documentation
----------------------

- The dependency on Sphinx required to build the documentation has been moved from the ``dev`` extra to the new ``docs`` extra. (`#296 <https://github.com/twisted/treq/issues/296>`__)


Deprecations and Removals
-------------------------

- Support for Python 2.7 and 3.5 has been dropped. treq no longer depends on ``six`` or ``mock``. (`#318 <https://github.com/twisted/treq/issues/318>`__)


21.1.0 (2021-01-14)
===================

Features
--------

- Support for Python 3.9: treq is now tested with CPython 3.9. (`#305 <https://github.com/twisted/treq/issues/305>`__)
- The *auth* parameter now accepts arbitrary text and `bytes` for usernames and passwords. Text is encoded as UTF-8, per :rfc:`7617`. Previously only ASCII was allowed. (`#268 <https://github.com/twisted/treq/issues/268>`__)
- treq produces a more helpful exception when passed a tuple of the wrong size in the *files* parameter. (`#299 <https://github.com/twisted/treq/issues/299>`__)


Bugfixes
--------

- The *params* argument once more accepts non-ASCII ``bytes``, fixing a regression first introduced in treq 20.4.1. (`#303 <https://github.com/twisted/treq/issues/303>`__)
- treq request APIs no longer mutates a :class:`http_headers.Headers <twisted.web.http_headers.Headers>` passed as the *headers* parameter when the *auth* parameter is also passed. (`#314 <https://github.com/twisted/treq/issues/314>`__)
- The agent returned by :func:`treq.auth.add_auth()` and :func:`treq.auth.add_basic_auth()` is now marked to provide :class:`twisted.web.iweb.IAgent`. (`#312 <https://github.com/twisted/treq/issues/312>`__)
- treq's package metadata has been updated to require ``six >= 1.13``, noting a dependency introduced in treq 20.9.0. (`#295 <https://github.com/twisted/treq/issues/295>`__)


Improved Documentation
----------------------

- The documentation of the *params* argument has been updated to more accurately describe its type-coercion behavior. (`#281 <https://github.com/twisted/treq/issues/281>`__)
- The :mod:`treq.auth` module has been documented. (`#313 <https://github.com/twisted/treq/issues/313>`__)


Deprecations and Removals
-------------------------

- Support for Python 2.7, which has reached end of support, is deprecated. This is the last release with support for Python 2.7. (`#309 <https://github.com/twisted/treq/issues/309>`__)
- Support for Python 3.5, which has reached end of support, is deprecated. This is the last release with support for Python 3.5. (`#306 <https://github.com/twisted/treq/issues/306>`__)
- Deprecate tolerance of non-string values when passing headers as a dict. They have historically been silently dropped, but will raise TypeError in the next treq release. Also deprecate passing headers other than :class:`dict`, :class:`~twisted.web.http_headers.Headers`, or ``None``. Historically falsy values like ``[]`` or ``()`` were accepted. (`#294 <https://github.com/twisted/treq/issues/294>`__)
- treq request functions and methods like :func:`treq.get()` and :meth:`HTTPClient.post()` now issue a ``DeprecationWarning`` when passed unknown keyword arguments, rather than ignoring them.
  Mixing the *json* argument with *files* or *data* is also deprecated.
  These warnings will change to a ``TypeError`` in the next treq release. (`#297 <https://github.com/twisted/treq/issues/297>`__)
- The minimum supported Twisted version has increased to 18.7.0. Older versions are no longer tested in CI. (`#307 <https://github.com/twisted/treq/issues/307>`__)


20.9.0 (2020-09-27)
===================

Features
--------

- The *url* parameter of :meth:`HTTPClient.request()` (and shortcuts like :meth:`~HTTPClient.get()`) now accept :class:`hyperlink.DecodedURL` and :class:`hyperlink.URL` in addition to :class:`str` and :class:`bytes`. (`#212 <https://github.com/twisted/treq/issues/212>`__)
- Compatibility with the upcoming Twisted 20.9.0 release (`#290 <https://github.com/twisted/treq/issues/290>`__).


Improved Documentation
----------------------

- An example of sending and receiving JSON has been added. (`#278 <https://github.com/twisted/treq/issues/278>`__)


20.4.1 (2020-04-16)
===================

Bugfixes
--------

- Correct a typo in the treq 20.4.0 package metadata that prevented upload to PyPI (`pypa/twine#589 <https://github.com/pypa/twine/issues/589>`__)

20.4.0 (2020-04-16)
===================

Features
--------

- Support for Python 3.8 and PyPy3: treq is now tested with these interpreters. (`#271 <https://github.com/twisted/treq/issues/271>`__)


Bugfixes
--------

- `treq.client.HTTPClient.request()` and its aliases no longer raise `UnicodeEncodeError` when passed a Unicode *url* and non-empty *params*.
  Now the URL and query parameters are concatenated as documented. (`#264 <https://github.com/twisted/treq/issues/264>`__)
- In treq 20.3.0 the *params* argument didn't accept parameter names or values that contain the characters ``&`` or ``#``.
  Now these characters are properly escaped. (`#282 <https://github.com/twisted/treq/issues/282>`__)


Improved Documentation
----------------------

- The treq documentation has been revised to emphasize use of `treq.client.HTTPClient` over the module-level convenience functions in the `treq` module. (`#276 <https://github.com/twisted/treq/issues/276>`__)


20.3.0 (2020-03-15)
===================

Features
--------

- Python 3.7 support. (`#228 <https://github.com/twisted/treq/issues/228>`__)


Bugfixes
--------

- `treq.testing.RequestTraversalAgent` now passes its memory reactor to the `twisted.web.server.Site` it creates, preventing the ``Site`` from polluting the global reactor. (`#225 <https://github.com/twisted/treq/issues/225>`__)
- `treq.testing` no longer generates deprecation warnings about ``twisted.test.proto_helpers.MemoryReactor``. (`#253 <https://github.com/twisted/treq/issues/253>`__)


Improved Documentation
----------------------

- The ``download_file.py`` example has been updated to do a streaming download with *unbuffered=True*. (`#233 <https://github.com/twisted/treq/issues/233>`__)
- The *agent* parameter to `treq.request()` has been documented. (`#235 <https://github.com/twisted/treq/issues/235>`__)
- The type of the *headers* element of a response tuple passed to `treq.testing.RequestSequence` is now correctly documented as `str`. (`#237 <https://github.com/twisted/treq/issues/237>`__)


Deprecations and Removals
-------------------------

- Drop support for Python 3.4. (`#240 <https://github.com/twisted/treq/issues/240>`__)


Misc
----

- `#247 <https://github.com/twisted/treq/issues/247>`__, `#248 <https://github.com/twisted/treq/issues/248>`__, `#249 <https://github.com/twisted/treq/issues/249>`__
