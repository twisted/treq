from setuptools import find_packages, setup
import os.path
import sys


with open(os.path.join(os.path.dirname(__file__), "treq", "_version")) as ver:
    __version__ = ver.readline().strip()

classifiers = [
    "Development Status :: 5 - Production/Stable",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Operating System :: OS Independent",
    "Framework :: Twisted",
    "Programming Language :: Python",
    "Programming Language :: Python :: 2.7",
    "Programming Language :: Python :: 3.3",
    "Programming Language :: Python :: 3.4",
    "Programming Language :: Python :: 3.5",
    "Programming Language :: Python :: Implementation :: CPython",
    "Programming Language :: Python :: Implementation :: PyPy",
]

with open('README.rst') as f:
    readme = f.read()

install_requires = [
    "pyOpenSSL >= 0.13",
    "requests >= 2.1.0",
    "service_identity >= 14.0.0",
    "six"
]

setup(
    name="treq",
    version=__version__,
    packages=find_packages(),
    install_requires=install_requires,
    extras_require={
        ':python_version<"3.0"': ["Twisted>=13.2.0"],
        ':python_version>"3.0"': ["Twisted>=15.5.0"],
    },
    package_data={"treq": ["_version"]},
    author="David Reid",
    author_email="dreid@dreid.org",
    classifiers=classifiers,
    description="A requests-like API built on top of twisted.web's Agent",
    license="MIT/X",
    url="http://github.com/twisted/treq",
    long_description=readme
)
