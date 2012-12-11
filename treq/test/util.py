import os
import platform

DEBUG = os.getenv("TREQ_DEBUG", False) == "true"

is_pypy = platform.python_implementation() == 'PyPy'


try:
    import OpenSSL
    has_ssl = OpenSSL is not None
except ImportError:
    has_ssl = False
