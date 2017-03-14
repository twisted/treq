from setuptools import find_packages, setup

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

if __name__ == "__main__":

    with open('README.rst') as f:
        readme = f.read()

    setup(
        name="treq",
        packages=find_packages('src'),
        package_dir={"": "src"},
        setup_requires=["incremental"],
        use_incremental=True,
        install_requires=[
            "incremental",
            "requests >= 2.1.0",
            "six",
            # 17.1.0 is currently not compatible with RequestTraversalAgent
            # See https://github.com/twisted/treq/issues/164
            # And http://twistedmatrix.com/trac/ticket/9032
            "Twisted[tls] >= 16.0.0, != 17.1.0",
            # Twisted[tls] 16.0.0 doesn't specify a version.
            "service_identity >= 14.0.0",
            # Twisted[tls] 16.0.0 requires 0.13, which doesn't work on Python 3.
            "pyOpenSSL >= 0.15.1",
            "attr"
        ],
        extras_require={
            "dev": [
                "pyflakes",
                "pep8",
                "sphinx",
                # Can be removed once Python 2.6 is dropped.
                "mock==1.0.1",
            ],
        },
        package_data={"treq": ["_version"]},
        author="David Reid",
        author_email="dreid@dreid.org",
        maintainer="Amber Brown",
        maintainer_email="hawkowl@twistedmatrix.com",
        classifiers=classifiers,
        description="A requests-like API built on top of twisted.web's Agent",
        license="MIT/X",
        url="https://github.com/twisted/treq",
        long_description=readme
    )
