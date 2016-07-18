#!/usr/bin/env python
# -*- coding: utf-8 -*-
import glob
from setuptools import setup, find_packages


setup(
	name='dglib',
	packages=find_packages(),
	version='0.1.1',
	description='Daemon glance lib',
	author='DDGG',
	author_email='990080@qq.com',
	url='https://github.com/ddcatgg/dglib',
	download_url='',
	keywords=['util', 'tool', 'ddgg'],
	classifiers=[
		'Programming Language :: Python',
		'Programming Language :: Python :: 2.6',
		'Programming Language :: Python :: 2.7',
		'Development Status :: 4 - Beta',
		'Environment :: Other Environment',
		'Intended Audience :: Developers',
		'License :: OSI Approved :: MIT License',
		'Operating System :: Microsoft :: Windows',
		'Topic :: Software Development :: Libraries :: Python Modules',
		'Topic :: Utilities'
	],
	long_description='''\
Daemon glance lib
-----------------

This library provides a number of commonly used functions and classes, but also
the integration of a number of third-party modules, to facilitate the development.

At present, for the Windows platform, is being ported to linux.
'''
)
