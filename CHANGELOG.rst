=========
Changelog
=========

.. currentmodule:: treq

.. default-role:: any

.. towncrier release notes start

20.3.0rc1 (2020-03-15)
======================

Features
--------

- Python 3.7 support. (`#228 <https://github.com/twisted/treq/issues/228>`__)


Bugfixes
--------

- `treq.testing.RequestTraversalAgent` now passes its memory reactor to the `twisted.web.server.Site` it creates, preventing the `Site` from polluting the global reactor. (`#225 <https://github.com/twisted/treq/issues/225>`__)
- `treq.testing` no longer generates deprecation warnings about `twisted.test.proto_helpers.MemoryReactor`. (`#253 <https://github.com/twisted/treq/issues/253>`__)


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
