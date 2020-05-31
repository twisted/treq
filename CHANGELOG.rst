=========
Changelog
=========

.. currentmodule:: treq

.. default-role:: any

.. towncrier release notes start

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
