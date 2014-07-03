#!/usr/bin/python

from __future__ import absolute_import, print_function

from ConfigParser import SafeConfigParser

travis_template = """\
language: python
python: 2.7

env:
    {envs}

install:
    - pip install tox

script:
    - tox -e $TOX_ENV

notifications:
    email: false
"""

parser = SafeConfigParser()
parser.read('tox.ini')

tox_envs = []

for section in parser.sections():
    if section.startswith('testenv:'):
        tox_envs.append(section.split(':')[1])

print(travis_template.format(
        envs='\n    '.join(
            '- TOX_ENV={0}'.format(env) for env in tox_envs)))
