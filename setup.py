#!/usr/bin/env python
# -*- coding: utf-8 -*-

from elseql import __version__
import sys

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

if sys.version_info <= (2, 5):
    error = "ERROR: elseql %s requires Python Version 2.6 or above...exiting." % __version__
    print >> sys.stderr, error
    sys.exit(1)

SETUP_OPTIONS = dict(
    name='elseql',
    version=__version__,
    description='SQL-like command line client for ElasticSearch',
    long_description=open("README.md").read(),
    author='Raffaele Sena',
    author_email='raff367@gmail.com',
    url='https://github.com/raff/elseql',
    license="MIT",
    platforms="Posix; MacOS X; Windows",
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Topic :: Internet',
        'Topic :: Utilities',
        'Topic :: Database :: Front-Ends',
        'Topic :: Internet :: WWW/HTTP :: Indexing/Search',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7'
    ],

    packages=['elseql'
              ],

    data_files=[('.', ['README.md'])
                ],

    install_requires=['pyparsing',
                      'rawes',
                      'cmd2',
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
