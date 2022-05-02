#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages
from pathlib import Path
from typing import Dict


PACKAGE_NAME = 'nucypher_ops'
BASE_DIR = Path(__file__).parent

ABOUT: Dict[str, str] = dict()
SOURCE_METADATA_PATH = BASE_DIR / PACKAGE_NAME / "__about__.py"
with open(str(SOURCE_METADATA_PATH.resolve())) as f:
    exec(f.read(), ABOUT)


PYPI_CLASSIFIERS = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: GNU Affero General Public License v3 or later (AGPLv3+)",
    "Natural Language :: English",
    "Operating System :: OS Independent",
    "Programming Language :: Python",
    "Programming Language :: Python :: 3 :: Only",
    "Programming Language :: Python :: 3.7",
    "Programming Language :: Python :: 3.8",
    "Programming Language :: Python :: 3.9",
    "Topic :: Security"
]

setup(
    packages=find_packages(),
    include_package_data=True,
    name=ABOUT['__title__'],
    url=ABOUT['__url__'],
    version=ABOUT['__version__'],
    author=ABOUT['__author__'],
    author_email=ABOUT['__email__'],
    description=ABOUT['__summary__'],
    license=ABOUT['__license__'],
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
        nucypher-ops=nucypher_ops.cli.main:index
    ''',
)
