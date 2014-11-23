#!/usr/bin/env python
from __future__ import absolute_import, print_function

from itertools import product

basepythons = {'py26': 'python2.6', 'py27': 'python2.7'}

python_versions = ['pypy', 'py26', 'py27']

deps = {
    'twisted': [
        '12.1.0', '12.2.0', '13.0.0', '13.1.0', '13.2.0', '14.0.0',
        'git+git://github.com/twisted/twisted#egg=Twisted'
    ],
    'pyopenssl': [
        '0.13', '0.14', 'git+git://github.com/pyca/pyopenssl.git#egg=pyopenssl'
    ]
}

env_names = []
envs = []

axes = [python_versions]

for dep, versions in deps.items():
    elems = []
    for version in versions:
        elems.append((dep, version))

    axes.append(elems)

env_template = """\
[testenv:{env_name}]
basepython = {basepython}
deps =
    {{[testenv]deps}}
    {deps}
"""

for env in product(*axes):
    python = env[0]
    deps = env[1:]

    env_name = [python]
    dep_entries = []

    for (dep, version) in deps:
        dep_entry = '{0}=={1}'.format(dep, version)
        dep_name = '{0}_{1}'.format(dep, version)

        if version is None:
            dep_entry = None
            dep_name = 'no_{0}'.format(dep)
        elif 'git' in version:
            dep_entry = version
            dep_name = '{0}_trunk'.format(dep)

        if dep_entry is not None:
            dep_entries.append(dep_entry)

        env_name.append(dep_name)

    env_name = '-'.join(env_name)
    env_names.append(env_name)
    envs.append(env_template.format(
                    env_name=env_name,
                    basepython=basepythons.get(python, python),
                    deps='\n    '.join(dep_entries)
                ))

print('[tox]')
print('envlist = {0}'.format(', '.join(env_names)))
print('')

for env in envs:
    print(env)

print('[testenv]')
print('deps =')
print('    mock')
print('commands =')
print('    trial treq')
