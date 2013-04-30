from setuptools import find_packages, setup
import os.path


with open(os.path.join(os.path.dirname(__file__), "treq", "_version")) as ver:
    __version__ = ver.readline().strip()

classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Operating System :: OS Independent",
    "Programming Language :: Python",
    "Programming Language :: Python :: 2",
    "Programming Language :: Python :: 2.6",
    "Programming Language :: Python :: 2.7",
    "Programming Language :: Python :: Implementation :: CPython",
    "Programming Language :: Python :: Implementation :: PyPy",
]


setup(
    name="treq",
    version=__version__,
    packages=find_packages(),
    install_requires=["Twisted >= 12.1.0"],
    package_data={"treq": ["_version"]},
    author="David Reid",
    author_email="dreid@dreid.org",
    classifiers=classifiers,
    description="A requests-like API built on top of twisted.web's Agent",
    license="MIT/X",
    url="http://github.com/dreid/treq",
    long_description=file('README.rst').read()
)
