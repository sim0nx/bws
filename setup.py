# -*- coding: utf-8 -*-
import os.path

import setuptools

f = open(os.path.join(os.path.dirname(__file__), 'README.rst'))
long_description = f.read().strip()
f.close()

setuptools.setup(name='bws2',
                 description='browser restore to workspace',
                 license='MIT',
                 long_description=long_description,
                 version='0.3.4',
                 author='Anthon van der Neut, Georges Toth',
                 author_email='georges@trypill.org',
                 url='https://github.com/sim0nx/bws2',
                 keywords='browser, multiple, workspace, restore',
                 packages=setuptools.find_packages(),
                 classifiers=['Development Status :: 4 - Beta',
                              'License :: OSI Approved :: MIT License',
                              'Intended Audience :: Developers',
                              'Operating System :: POSIX :: Linux',
                              'Programming Language :: Python :: 3.5',
                              'Programming Language :: Python :: 3.7',
                              'Programming Language :: Python :: Implementation :: CPython',
                              'Topic :: Internet :: WWW/HTTP :: Browsers  '
                              ],
                 install_requires=[],
                 entry_points={'console_scripts': ['bws2=bws2.browserworkspace:main']}
                 )
