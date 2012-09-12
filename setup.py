#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup
from elseql import __version__

SETUP_OPTIONS = dict(
    name='elseql',
    version=__version__,
    description='SQL-like command line client for ElasticSearch',
    long_description = open("README.md").read(),
    author='Raffaele Sena',
    author_email='raff367@gmail.com',
    url='https://github.com/raff/elseql',
    license = "MIT",
    platforms = "Posix; MacOS X; Windows",

    packages=['elseql'
              ],

    data_files=[('.', ['README.md'])
               ],

    install_requires=['distribute',
                      'setuptools >= 0.6c11',
                      'pyparsing',
                      'rawes',
                      ],

    entry_points="""
    [console_scripts]
    elseql=elseql.elseql:run_command
    """
    )


def do_setup():
    setup(**SETUP_OPTIONS)

if __name__ == '__main__':
    do_setup()
