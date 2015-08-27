## header
# coding: utf-8

from __future__ import print_function

if __name__ != '__main__':
    raise NotImplementedError('should never include setup.py')

## definitions

full_package_name = 'ruamel.bws'

exclude_files = [
    'setup.py',
]

## imports
import os
import sys

from setuptools import setup, find_packages
from setuptools.command import install_lib

## helper

def get_version():
    v_i = 'version_info = '
    #    for line in open(os.path.join(rel_dir, '__init__.py')):
    for line in open('__init__.py'):
        if not line.startswith(v_i):
            continue
        s_e = line[len(v_i):].strip()[1:-1].split(', ')
        els = [x.strip()[1:-1] if x[0] in '\'"' else int(x) for x in s_e]
        return els


def _check_convert_version(tup):
    """create a PEP 386 pseudo-format conformant string from tuple tup"""
    ret_val = str(tup[0])  # first is always digit
    next_sep = "."  # separator for next extension, can be "" or "."
    nr_digits = 0  # nr of adjacent digits in rest, to verify
    post_dev = False  # are we processig post/dev
    for x in tup[1:]:
        if isinstance(x, int):
            nr_digits += 1
            if nr_digits > 2:
                raise ValueError("too many consecutive digits " + ret_val)
            ret_val += next_sep + str(x)
            next_sep = '.'
            continue
        first_letter = x[0].lower()
        next_sep = ''
        if first_letter in 'abcr':
            if post_dev:
                raise ValueError("release level specified after "
                                 "post/dev:" + x)
            nr_digits = 0
            ret_val += 'rc' if first_letter == 'r' else first_letter
        elif first_letter in 'pd':
            nr_digits = 1  # only one can follow
            post_dev = True
            ret_val += '.post' if first_letter == 'p' else '.dev'
        else:
            raise ValueError('First letter of "' + x + '" not recognised')
    return ret_val


version_info = get_version()
version_str = _check_convert_version(version_info)

class MyInstallLib(install_lib.install_lib):
    def install(self):
        fpp = full_package_name.split('.')  # full package path
        full_exclude_files = [os.path.join(*(fpp + [x]))
                              for x in exclude_files]
        alt_files = []
        outfiles = install_lib.install_lib.install(self)
        for x in outfiles:
            for full_exclude_file in full_exclude_files:
                if full_exclude_file in x:
                    os.remove(x)
                    break
            else:
                alt_files.append(x)
        return alt_files


class NameSpacePackager(object):
    def __init__(self, full_package_name):
        self.fns = full_package_name
        self._split = None
        self.depth = self.fns.count('.')
        self.command = None
        if sys.argv[0] == 'setup.py' and sys.argv[1] == 'install' and \
           not '--single-version-externally-managed' in sys.argv:
            print('error: have to isntall with "pip install ."')
            sys.exit(1)
        for x in sys.argv:
            if x[0] == '-' or x == 'setup.py':
                continue
            self.command = x
            break

    @property
    def split(self):
        """split the full package name in list of compontents"""
        if self._split is None:
            fpn = self.fns.split('.')
            self._split = []
            while fpn:
                self._split.insert(0, '.'.join(fpn))
                fpn = fpn[:-1]
            for d in os.listdir('.'):
                if not os.path.isdir(d) or d == self._split[0] or d[0] == '_':
                    continue
                x = os.path.join(d, '__init__.py')
                if os.path.exists(x):
                    self._split.append(full_package_name + '.' + d)
        return self._split

    @property
    def namespace_packages(self):
        return self.split[:self.depth]

    @property
    def package_dir(self):
        return {
            self.fns: '',
            self.split[0]: self.split[0],
        }

    def create_dirs(self):
        """create the directories necessary for namespace packaging"""
        if not os.path.exists(self.split[0]):
            for d in self.split[:self.depth]:
                d = os.path.join(*d.split('.'))
                os.mkdir(d)
                with open(os.path.join(d, '__init__.py'), 'w') as fp:
                    fp.write('import pkg_resources\n'
                             'pkg_resources.declare_namespace(__name__)\n')
            os.symlink(
                # a.b gives a/b -> ..
                # a.b.c gives a/b/c  -> ../..
                os.path.join(*['..'] * self.depth),
                os.path.join(*self.split[self.depth].split('.'))
            )

    def check(self):
        try:
            from pip.exceptions import InstallationError
        except ImportError:
            return
        # arg is either develop (pip install -e) or install
        if self.command not in ['install', 'develop']:
            return

        # if hgi and hgi.base are both in namespace_packages matching
        # against the top (hgi.) it suffices to find minus-e and non-minus-e
        # installed packages. As we don't know the order in namespace_packages
        # do some magic
        prefix = self.split[0]
        prefixes = set([prefix, prefix.replace('_', '-')])
        for p in sys.path:
            if not p:
                continue  # directory with setup.py
            if os.path.exists(os.path.join(p, 'setup.py')) :
                continue  # some linked in stuff might not be hgi based
            if not os.path.isdir(p):
                continue
            if p.startswith('/tmp/'):
                continue
            for fn in os.listdir(p):
                for pre in prefixes:
                    if fn.startswith(pre):
                        break
                else:
                    continue
                full_name = os.path.join(p, fn)
                # not in prefixes the toplevel is never changed from _ to -
                if fn == prefix and os.path.isdir(full_name):
                    # directory -> other, non-minus-e, install
                    if self.command == 'develop':
                        raise InstallationError(
                            'Cannot mix develop (pip install -e),\nwith '
                            'non-develop installs for package name {0}'.format(
                                fn))
                elif fn == prefix:
                    raise InstallationError(
                        'non directory package {0} in {1}'.format(
                            fn, p))
                for pre in [x + '.' for x in prefixes]:
                    if fn.startswith(pre):
                        break
                else:
                    continue # hgiabc instead of hgi.
                if fn.endswith('-link') and self.command == 'install':
                    raise InstallationError(
                        'Cannot mix non-develop with develop\n(pip install -e) '
                        'installs for package name {0}'.format(fn))

    def entry_points(self, script_name=None, package_name=None):
        if package_name is None:
            package_name = self.fns
        if not script_name:
            script_name = package_name.split('.')[-1]
        return {'console_scripts': [
            '{} = {}:main'.format(script_name, package_name),
        ]}

    @property
    def url(self):
        return 'https://bitbucket.org/{0}/{1}'.format(*self.fns.split('.', 1))

    @property
    def author(self):
        return 'Anthon van der Neut'

    @property
    def author_email(self):
        return 'a.van.der.neut@ruamel.eu',


## call setup
def main():
    nsp = NameSpacePackager(full_package_name)
    nsp.check()
    nsp.create_dirs()
    kw = dict(
        name=full_package_name,
        namespace_packages=nsp.namespace_packages,
        version=version_str,
        packages=nsp.split,
        url=nsp.url,
        author=nsp.author,
        author_email=nsp.author_email,
        cmdclass={'install_lib': MyInstallLib},
        package_dir=nsp.package_dir,
        entry_points=nsp.entry_points(),
    )
    for k in kw:
        print(k, '->', kw[k])
    setup(**kw)


main()
