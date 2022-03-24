from setuptools import setup

setup(
    name='nucypher-ops',
    version='0.1',
    py_modules=['nucypher-ops'],
    install_requires=[
        'click',
        'colorama',
        'ansible',
        'hdwallet',
        'mako',
        'requests',
        'maya',
        'appdirs'
    ],
    entry_points='''
        [console_scripts]
        nucypher-ops=src.cli.main:index
    ''',
)