import os
import platform

DEBUG = os.getenv("TREQ_DEBUG", False) == "true"
HTTPBIN_URL = os.getenv("HTTPBIN_URL", "http://httpbin.org")
HTTPSBIN_URL = os.getenv("HTTPSBIN_URL", "https://httpbin.org")

is_pypy = platform.python_implementation() == 'PyPy'
