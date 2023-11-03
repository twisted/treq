from setuptools import find_packages, setup

classifiers = [
    "Development Status :: 5 - Production/Stable",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Operating System :: OS Independent",
    "Framework :: Twisted",
    "Programming Language :: Python",
    "Programming Language :: Python :: 3.8",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: Implementation :: CPython",
    "Programming Language :: Python :: Implementation :: PyPy",
]

if __name__ == "__main__":

    with open("README.rst") as f:
        readme = f.read()

    setup(
        name="treq",
        packages=find_packages("src"),
        package_dir={"": "src"},
        setup_requires=["incremental"],
        use_incremental=True,
        python_requires=">=3.6",
        install_requires=[
            "incremental",
            "requests >= 2.1.0",
            "hyperlink >= 21.0.0",
            "Twisted[tls] >= 22.10.0",
            "attrs",
        ],
        extras_require={
            "dev": [
                "pep8",
                "pyflakes",
                "httpbin==0.7.0",
                "werkzeug==2.0.3",
            ],
            "docs": [
                "sphinx<7.0.0",  # Removal of 'style' key breaks RTD.
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
        long_description_content_type="text/x-rst",
    )
