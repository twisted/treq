from setuptools import find_packages, setup

classifiers = [
    "Development Status :: 5 - Production/Stable",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Operating System :: OS Independent",
    "Framework :: Twisted",
    "Programming Language :: Python",
    "Programming Language :: Python :: 2.7",
    "Programming Language :: Python :: 3.5",
    "Programming Language :: Python :: 3.6",
    "Programming Language :: Python :: 3.7",
    "Programming Language :: Python :: 3.8",
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
            "hyperlink >= 19.0.0",
            "six",
            "Twisted[tls] >= 16.4.0 ; python_version < '3.7'",
            "Twisted[tls] >= 18.7.0 ; python_version >= '3.7'",
            "attrs",
        ],
        extras_require={
            "dev": [
                "mock",
                "pep8",
                "pyflakes",
                "sphinx",
                "httpbin==0.5.0",
            ],
        },
        package_data={"treq": ["_version"]},
        author="David Reid",
        author_email="dreid@dreid.org",
        maintainer="Tom Most",
        maintainer_email="twm@freecog.net",
        classifiers=classifiers,
        description="High-level Twisted HTTP Client API",
        license="MIT/X",
        url="https://github.com/twisted/treq",
        long_description=readme,
        long_description_content_type='text/x-rst',
    )
