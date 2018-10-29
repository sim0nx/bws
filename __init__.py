# coding: utf-8

from __future__ import print_function
from __future__ import absolute_import

_package_data = dict(
    full_package_name='ruamel.bws',
    version_info=(0, 3, 3),
    __version__='0.3.3',
    author='Anthon van der Neut',
    description='browser restore to workspace',
    keywords='browser multiple workspace restore',
    author_email='a.van.der.neut@ruamel.eu',
    install_requires=['configobj'],
    since=2014,
    classifiers=[
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: Implementation :: CPython',
        'Topic :: Internet :: WWW/HTTP :: Browsers',
    ],
)


version_info = _package_data['version_info']
__version__ = _package_data['__version__']


def main():
    # No direct import of bws in order not to pollute namespace.
    # If other utility 'bodies' exist in this directory a module level
    # import here, would get you all of its initialisations/imports as well
    from .browserworkspace import main as util_main

    util_main()
