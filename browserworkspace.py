#!/usr/bin/env python
# coding: utf-8

from __future__ import print_function

import sys
import os
import subprocess
import json
import glob
import datetime

# only necessary for ruamel_util_updateprogram
import argparse
from configobj import ConfigObj

PY3 = sys.version_info[0] == 3

if PY3:
    string_types = str,
else:
    string_types = basestring,


# < from ruamel.std.argparse import ProgramBase, option, sub_parser, version, SmartFormatter
class ProgramBase(object):
    """
    ToDo:
    - grouping
    - mutual exclusion
    Done:
    - Original order/sorted (by kw)
    - aliases

    """
    _methods_with_sub_parsers = []

    def __init__(self, *args, **kw):
        """
        the 'aliases' keyword does result in the 'aliases' keyword in
        @sub_parser  (as for Py3 in add_parser()) being available for 2.x
        """
        self._verbose = kw.pop('verbose', 0)
        aliases = kw.pop('aliases', 0)
        self._parser = argparse.ArgumentParser(*args, **kw)
        if aliases and sys.version_info < (3,):
            self._parser.register('action', 'parsers', SubParsersAction)  # NOQA
        self._program_base_initialising = True
        cls = self
        self._sub_parsers = None
        methods_with_sub_parsers = []  # list to process, multilevel
        all_methods_with_sub_parsers = []

        def add_subparsers(method_name_list, parser, level=0):
            if not method_name_list:
                return None
            ssp = parser.add_subparsers(
                dest="subparser_level_{0}".format(level),)
            for method_name in method_name_list:
                # print('method', '  ' * level, method_name)
                method = getattr(self, method_name)
                all_methods_with_sub_parsers.append(method)
                info = method._sub_parser
                info['level'] = level
                if level > 0:
                    method._sub_parser['parent'] = \
                        method._sub_parser['kw'].pop('_parent')
                arg = method._sub_parser['args']
                if not arg or not isinstance(arg[0], string_types):
                    arg = list(arg)
                    arg.insert(0, method.__name__)
                parser = ssp.add_parser(*arg, **method._sub_parser['kw'])
                info['parser'] = parser
                res = add_subparsers(info.get('ordering', []),
                                     parser, level=level+1)
                if res is None:
                    # only set default if there are no subparsers, otherwise
                    # defaults override
                    parser.set_defaults(func=method)
                for o in info['options']:
                    arg = list(o['args'])
                    fun_name = o.get('fun')
                    if arg:
                        # short option name only, add long option name
                        # based on function name
                        if len(arg[0]) == 2 and arg[0][0] == '-':
                            if (fun_name):
                                arg.insert(0, '--' + fun_name)
                    else:
                        # no option name
                        if o['kw'].get('nargs') == '+ ':
                            # file names etc, no leading dashes
                            arg.insert(0, fun_name)
                        else:
                            # add long option based on function name
                            arg.insert(0, '--' + fun_name)
                    parser.add_argument(*arg, **o['kw'])
            return ssp

        def dump(method_name_list, level=0):
            if not method_name_list:
                return None
            for method_name in method_name_list:
                print('method', '  ' * level, method_name)
                method = getattr(self, method_name)
                info = method._sub_parser
                for k in sorted(info):
                    if k == 'parser':
                        v = 'ArgumentParser()'
                    elif k == 'sp':
                            v = '_SubParserAction()'
                    else:
                        v = info[k]
                    print('       ' + '  ' * level, k, '->', v)
                dump(info.get('ordering', []), level=level+1)

        self._sub_parsers = add_subparsers(
            ProgramBase._methods_with_sub_parsers, self._parser)

        # this only does toplevel and global options
        for x in dir(self):
            if x.startswith('_') and x not in ['__init__', '_pb_init']:
                continue
            method = getattr(self, x)
            if hasattr(method, "_options"):  # not transfered to sub_parser
                for o in method._options:
                    arg = o['args']
                    kw = o['kw']
                    global_option = kw.pop('global_option', False)
                    try:
                        self._parser.add_argument(*arg, **kw)
                    except TypeError:
                        print('args, kw', arg, kw)
                    if global_option:
                        # print('global option', arg, len(all_methods_with_sub_parsers))
                        for m in all_methods_with_sub_parsers:
                            sp = m._sub_parser['parser']
                            # adding _globa_option to allow easy check e.g. in
                            # AppConfig._set_section_defaults
                            sp.add_argument(*arg, **kw)._global_option = True
        self._program_base_initialising = False

        # print('-------------------')
        # dump(ProgramBase._methods_with_sub_parsers)
        if False:
            # for x in ProgramBase._methods_with_sub_parsers:
            for x in dir(cls):
                if x.startswith('_'):
                    continue
                method = getattr(self, x)
                if hasattr(method, "_sub_parser"):
                    if self._sub_parsers is None:
                        # create the top level subparsers
                        self._sub_parsers = self._parser.add_subparsers(
                            dest="subparser_level_0", help=None)
                    methods_with_sub_parsers.append(method)
            max_depth = 10
            level = 0
            all_methods_with_sub_parsers = methods_with_sub_parsers[:]
            while methods_with_sub_parsers:
                level += 1
                if level > max_depth:
                    raise NotImplementedError
                for method in all_methods_with_sub_parsers:
                    if method not in methods_with_sub_parsers:
                        continue
                    parent = method._sub_parser['kw'].get('_parent', None)
                    sub_parsers = self._sub_parsers
                    if parent is None:
                        method._sub_parser['level'] = 0
                        # parent sub parser
                    elif 'level' not in parent._sub_parser:
                        # print('skipping', parent.__name__, method.__name__)
                        continue
                    else:  # have a parent
                        # make sure _parent is no longer in kw
                        method._sub_parser['parent'] = \
                            method._sub_parser['kw'].pop('_parent')
                        level = parent._sub_parser['level'] + 1
                        method._sub_parser['level'] = level
                        ssp = parent._sub_parser.get('sp')
                        if ssp is None:
                            pparser = parent._sub_parser['parser']
                            ssp = pparser.add_subparsers(
                                dest="subparser_level_{0}".format(level),
                            )
                            parent._sub_parser['sp'] = ssp
                        sub_parsers = ssp
                    arg = method._sub_parser['args']
                    if not arg or not isinstance(arg[0], basestring):
                        arg = list(arg)
                        arg.insert(0, method.__name__)
                    sp = sub_parsers.add_parser(*arg,
                                                **method._sub_parser['kw'])
                    # add parser primarily for being able to add subparsers
                    method._sub_parser['parser'] = sp
                    # and make self._args.func callable
                    sp.set_defaults(func=method)

                    # print(x, method._sub_parser)
                    for o in method._sub_parser['options']:
                        arg = list(o['args'])
                        fun_name = o.get('fun')
                        if arg:
                            # short option name only, add long option name
                            # based on function name
                            if len(arg[0]) == 2 and arg[0][0] == '-':
                                if (fun_name):
                                    arg.insert(0, '--' + fun_name)
                        else:
                            # no option name
                            if o['kw'].get('nargs') == '+ ':
                                # file names etc, no leading dashes
                                arg.insert(0, fun_name)
                            else:
                                # add long option based on function name
                                arg.insert(0, '--' + fun_name)
                        sp.add_argument(*arg, **o['kw'])
                    methods_with_sub_parsers.remove(method)
            for x in dir(self):
                if x.startswith('_') and x not in ['__init__', '_pb_init']:
                    continue
                method = getattr(self, x)
                if hasattr(method, "_options"):  # not transfered to sub_parser
                    for o in method._options:
                        arg = o['args']
                        kw = o['kw']
                        global_option = kw.pop('global_option', False)
                        try:
                            self._parser.add_argument(*arg, **kw)
                        except TypeError:
                            print('args, kw', arg, kw)
                        if global_option:
                            # print('global option', arg, len(all_methods_with_sub_parsers))
                            for m in all_methods_with_sub_parsers:
                                sp = m._sub_parser['parser']
                                sp.add_argument(*arg, **kw)

    def _parse_args(self, *args, **kw):
        self._args = self._parser.parse_args(*args, **kw)
        return self._args

    # def _parse_known_args(self, *args, **kw):
    #     self._args, self._unknown_args = \
    #         self._parser.parse_known_args(*args, **kw)
    #     return self._args

    @staticmethod
    def _pb_option(*args, **kw):
        def decorator(target):
            if not hasattr(target, '_options'):
                target._options = []
            # insert to reverse order of list
            target._options.insert(0, {'args': args, 'kw': kw})
            return target
        return decorator

    @staticmethod
    def _pb_sub_parser(*args, **kw):
        class Decorator(object):
            def __init__(self):
                self.target = None
                self._parent = None

            def __call__(self, target):
                self.target = target
                a = args
                k = kw.copy()
                if self._parent:
                    a = self._parent[1]
                    k = self._parent[2].copy()
                    k['_parent'] = self._parent[0]
                    pi = self._parent[0]._sub_parser
                    ordering = pi.setdefault('ordering', [])
                else:
                    ordering = ProgramBase._methods_with_sub_parsers
                ordering.append(target.__name__)
                # move options to sub_parser
                o = getattr(target, '_options', [])
                if o:
                    del target._options
                target._sub_parser = {'args': a, 'kw': k, 'options': o}
                # assign the name
                target.sub_parser = self.sub_parser
                return target

            def sub_parser(self, *a, **k):
                """ after a method xyz is decorated as sub_parser, you can add
                a sub parser by decorating another method with:
                  @xyz.sub_parser(*arguments, **keywords)
                  def force(self):
                     pass

                if arguments is not given the name will be the method name
                """
                decorator = Decorator()
                decorator._parent = (self.target, a, k, [])
                return decorator

        decorator = Decorator()
        return decorator


def option(*args, **keywords):
    """\
 args:
    name or flags - Either a name or a list of option strings, e.g. foo or
                    -f, --foo.
 keywords:
    action   - The basic type of action to be taken when this argument is
               encountered at the command line.
    nargs    - The number of command-line arguments that should be consumed.
    const    - A constant value required by some action and nargs selections.
    default  - The value produced if the argument is absent from the command
               line.
    type     - The type to which the command-line argument should be converted.
    choices  - A container of the allowable values for the argument.
    required - Whether or not the command-line option may be omitted
               (optionals only).
    help     - A brief description of what the argument does.
    metavar  - A name for the argument in usage messages.
    dest     - The name of the attribute to be added to the object returned by
               parse_args().
    """
    return ProgramBase._pb_option(*args, **keywords)


def sub_parser(*args, **kw):
    return ProgramBase._pb_sub_parser(*args, **kw)


def version(version_string):
    return ProgramBase._pb_option(
        '--version', action='version', version=version_string)


class SmartFormatter(argparse.HelpFormatter):
    """
    you can only specify one formatter in standard argparse, so you cannot
    both have pre-formatted description (RawDescriptionHelpFormatter)
    and ArgumentDefaultsHelpFormatter.
    The SmartFormatter has sensible defaults (RawDescriptionFormatter) and
    the individual help text can be marked ( help="R|" ) for
    variations in formatting.
    version string is formatted using _split_lines and preserves any
    line breaks in the version string.
    """
    def __init__(self, *args, **kw):
        self._add_defaults = None
        super(SmartFormatter, self).__init__(*args, **kw)

    def _fill_text(self, text, width, indent):
        return ''.join([indent + line for line in text.splitlines(True)])

    def _split_lines(self, text, width):
        if text.startswith('D|'):
            self._add_defaults = True
            text = text[2:]
        elif text.startswith('*|'):
            text = text[2:]
        if text.startswith('R|'):
            return text[2:].splitlines()
        return argparse.HelpFormatter._split_lines(self, text, width)

    def _get_help_string(self, action):
        if self._add_defaults is None:
            return argparse.HelpFormatter._get_help_string(self, action)
        help = action.help
        if '%(default)' not in action.help:
            if action.default is not argparse.SUPPRESS:
                defaulting_nargs = [argparse.OPTIONAL, argparse.ZERO_OR_MORE]
                if action.option_strings or action.nargs in defaulting_nargs:
                    help += ' (default: %(default)s)'
        return help

    def _expand_help(self, action):
        """mark a password help with '*|' at the start, so that
        when global default adding is activated (e.g. through a helpstring
        starting with 'D|') no password is show by default.
        Orginal marking used in repo cannot be used because of decorators.
        """
        hs = self._get_help_string(action)
        if hs.startswith('*|'):
            params = dict(vars(action), prog=self._prog)
            if params.get('default') is not None:
                # you can update params, this will change the default, but we
                # are printing help only
                params['default'] = '*' * len(params['default'])
            return self._get_help_string(action) % params
        return super(SmartFormatter, self)._expand_help(action)


# < from ruamel.std.argparse._action.count import CountAction
class CountAction(argparse.Action):
    """argparse action for counting up and down

    parser = argparse.ArgumentParser()
    parser.add_argument('--verbose', '-v', action=CountAction, const=1, nargs=0)
    parser.add_argument('--quiet', '-q', action=CountAction, dest='verbose',
            const=-1, nargs=0)
    """
    def __call__(self, parser, namespace, values, option_string=None):
        try:
            val = getattr(namespace, self.dest) + self.const
        except TypeError:  # probably None
            val = self.const
        setattr(namespace, self.dest, val)


# < from ruamel.appconfig import AppConfig
class AppConfig(object):
    """ToDo: update

    derives configuration filename and location from package name

    package_name is also stored to find 'local' configurations based
    on passed in directory name.
    The Config object allows for more easy change to e.g. YAML config files
    """

    class Config(ConfigObj):
        """ Config should have a __getitem__,
        preserve comments when writing
        (write config if changed)
        """
        def __init__(self, file_name, **kw):
            ConfigObj.__init__(self, file_name, *kw)

    def __init__(self, package_name, **kw):
        """create a config file if no file_name given,
        complain if multiple found"""
        self._package_name = package_name
        self._file_name = None
        warning = kw.pop('warning', None)
        self._parser = parser = kw.pop('parser', None)
        # create = kw.pop('create', True)
        # if not create:
        #     return
        file_name = self.get_file_name(
            kw.pop('filename', None),
            warning=warning,
        )
        if kw.pop('add_save', None):
            self.add_save_defaults(parser)
            if parser._subparsers is not None:
                assert isinstance(parser._subparsers, argparse._ArgumentGroup)
                # subparsers = {}  # aliases filtered out
                for spa in parser._subparsers._group_actions:
                    if not isinstance(spa, argparse._SubParsersAction):
                        continue
                    # print ('spa ', type(spa), spa)
                    for key in spa.choices:
                        # print ('key ', key)
                        sp = spa.choices[key]
                        # print ('sp ', type(sp), sp)
                        self.add_save_defaults(sp)
        self._config = self.Config(file_name, **kw)
        argparse._SubParsersAction.__call__ = self.sp__call__
        # super(AppConfig, self).__init__(file_name, **kw)

    def get_file_name(self, file_name=None, warning=None, add_save=None):
        if self._file_name:
            return self._file_name
        if warning is None:
            warning = self.no_warning
        add_config_to_parser = False
        if file_name is self.check:
            file_name = None
            if self._parser:
                add_config_to_parser = True
            # check if --config was given on commandline
            for idx, arg in enumerate(sys.argv[1:]):
                if arg.startswith('--config'):
                    if len(arg) > 8 and arg[8] == '=':
                        file_name = arg[9:]
                    else:
                        try:
                            file_name = sys.argv[idx+2]
                        except IndexError:
                            print('--config needs an argument')
                            sys.exit(1)
        expanded_file_names = [os.path.expanduser(x) for x in
                               self.possible_config_file_names]
        # print(expanded_file_names)
        existing = [x for x in expanded_file_names if os.path.exists(x)]
        # possible check for existence of preferred directory and less
        # preferred existing file
        # e.g. empty ~/.config/repo and existing ~/.repo/repo.ini
        if file_name and existing:
            warning("Multiple configuration files", [file_name] + existing)
        elif len(existing) > 1:
            warning("Multiple configuration files", existing)
        if file_name:
            self._file_name = os.path.expanduser(file_name)
        else:
            self._file_name = expanded_file_names[0]
        try:
            dir_name = os.path.dirname(self._file_name)
            os.mkdir(dir_name)
            warning('created directory', dir_name)
        except OSError:
            # warning('did not create directory ', dir_name)
            pass
        if not self.has_config() and add_config_to_parser:
            if '/XXXtmp/' not in self._file_name:
                default_path = self._file_name.replace(
                    os.path.expanduser('~/'), '~/')
            else:
                default_path = self._file_name
            self._parser.add_argument(
                '--config',
                metavar='FILE',
                default=default_path,
                help="set %(metavar)s as configuration file [%(default)s]",
            )
        return self._file_name

    def __getitem__(self, key):
        return self._config[key]

    def set_defaults(self):
        _glbl = 'global'
        parser = self._parser
        self._set_section_defaults(self._parser, _glbl)
        if parser._subparsers is None:
            return
        assert isinstance(parser._subparsers, argparse._ArgumentGroup)
        progs = set()
        # subparsers = {}  # aliases filtered out
        for sp in parser._subparsers._group_actions:
            if not isinstance(sp, argparse._SubParsersAction):
                continue
            for k in sp.choices:
                action = sp.choices[k]
                if self.query_add(progs, action.prog):
                    self._set_section_defaults(action, k, glbl=_glbl)

    def _set_section_defaults(self, parser, section, glbl=None):
        defaults = {}
        for action in parser._get_optional_actions():
            if isinstance(action,
                          (argparse._HelpAction,
                           argparse._VersionAction,
                           # SubParsersAction._AliasesChoicesPseudoAction,
                           )):
                continue
            for x in action.option_strings:
                if not x.startswith('--'):
                    continue
                try:
                    # get value based on long-option (without --)
                    # store in .dest
                    defaults[action.dest] = self[section][x[2:]]
                except KeyError:  # not in config file
                    if glbl is not None and \
                       getattr(action, "_global_option", False):
                        try:
                            defaults[action.dest] = self[glbl][x[2:]]
                        except KeyError:  # not in config file
                            pass
                break  # only first --option
        parser.set_defaults(**defaults)

    def has_config(self):
        """check if self._parser has --config already added"""
        if self._parser is not None:
            for action in self._parser._get_optional_actions():
                if '--config' in action.option_strings:
                    return True
        return False

    def parse_args(self, *args, **kw):
        """call ArgumentParser.parse_args and handle --save-defaults"""
        parser = self._parser
        opt = parser._optionals
        print('paropt', self._parser._optionals, len(opt._actions),
              len(opt._group_actions))
        # for a in self._parser._optionals._group_actions:
        #     print('    ', a)
        pargs = self._parser.parse_args(*args, **kw)
        if hasattr(pargs, 'save_defaults') and pargs.save_defaults:
            self.extract_default(opt, pargs)
            # for elem in self._parser._optionals._defaults:
            #     print('elem ', elem)
            if hasattr(parser, '_sub_parser_sel'):
                name, sp = parser._sub_parser_sel
                print('====sp', sp)
                opt = sp._optionals
                self.extract_default(opt, pargs, name)
            self._config.write()
        return pargs

    def extract_default(self, opt, pargs, name='global'):
        for a in opt._group_actions:
            # print('+++++', name, a)
            if isinstance(a, (argparse._HelpAction,
                              argparse._VersionAction,
                              )):
                continue
            if a.option_strings[0] in ["--config", "--save-defaults"]:
                continue
            print('    -> ', name, a.dest, a)
            if hasattr(pargs, a.dest):
                sec = self._config.setdefault(name, {})
                sec[a.dest] = getattr(pargs, a.dest)

    @property
    def possible_config_file_names(self, ext=None):
        """return all the paths to check for configuration
        first is the one created if none found"""
        pn = self._package_name
        if ext is None:
            ext = '.ini'
        # ud = '~'
        if sys.platform.startswith('linux'):
            ud = os.environ['HOME']
            ret_val = [
                # ~/.config/repo/repo.ini
                os.path.join(AppConfig._config_dir(), pn, pn + ext),
                # ~/.repo/repo.ini
                os.path.join(ud, '.' + pn, pn + ext),
                # ~/.repo.ini
                os.path.join(ud, '.' + pn + ext),
            ]
        elif sys.platform.startswith('win32'):
            ud = AppConfig._config_dir()
            # dotini = self._package_name + '.ini'  # this should be last elem
            ret_val = [
                os.path.join(ud, pn, pn + ext),  # %APPDATA%/repo/repo.ini
                os.path.join(ud, pn + ext),  # %APPDATA%/repo.ini
            ]
        return ret_val

    @staticmethod
    def add_save_defaults(p):
        p.add_argument(
            '--save-defaults',
            action='store_true',
            help='save option values as defaults to config file',
        )

    @classmethod
    def _config_dir(self):
        if sys.platform.startswith('linux'):
            return os.path.join(os.environ['HOME'], '.config')
        elif sys.platform.startswith('win32'):
            return os.environ['APPDATA']

    @staticmethod
    def no_warning(*args, **kw):
        """sync for warnings"""
        pass

    @staticmethod
    def check():
        """to have an object to check against initing sys.argv parsing"""
        pass

    @staticmethod
    def query_add(s, value):
        """check if value in s(et) and add if not

        return True if added, False if already in.

        >>> x = set()
        >>> if query_add(x, 'a'):
        ...     print 'hello'
        hello
        >>> if query_add(x, 'a'):
        ...     print 'hello'
        >>>

        """
        if value not in s:
            s.add(value)
            return True
        return False

    @staticmethod
    def sp__call__(self, parser, namespace, values, option_string=None):
        from argparse import SUPPRESS
        parser_name = values[0]
        arg_strings = values[1:]

        # set the parser name if requested
        if self.dest is not SUPPRESS:
            setattr(namespace, self.dest, parser_name)

        # select the parser
        try:
            glob_parser = parser
            parser = self._name_parser_map[parser_name]
            glob_parser._sub_parser_sel = (parser_name, parser)
        except KeyError:
            tup = parser_name, ', '.join(self._name_parser_map)
            msg = ('unknown parser %r (choices: %s)') % tup
            raise argparse.ArgumentError(self, msg)

        # parse all the remaining options into the namespace
        # store any unrecognized options on the object, so that the top
        # level parser can decide what to do with them
        namespace, arg_strings = parser.parse_known_args(
            arg_strings, namespace)
        if arg_strings:
            vars(namespace).setdefault(argparse._UNRECOGNIZED_ARGS_ATTR, [])
            getattr(namespace, argparse._UNRECOGNIZED_ARGS_ATTR).extend(arg_strings)


from ruamel.bws import __version__  # NOQA


class BrowserWorkspace(object):
    """"""
    # names of the fields returned by wmctrl -l -G -p
    _names = 'wid workspace pid x y w h hostname title'.split()

    def __init__(self, args, config):
        self._args = args
        self._config = config
        self._browsers = {}
        self._nr_windows = 0
        self._format_version = 1
        self._path_pattern = os.path.join(
            os.path.dirname(self._config.get_file_name()),
            '{}.bws'
        )

    def ewmh(self):
        NR_PARTS = 8
        res = subprocess.check_output('wmctrl -l -G -p'.split()).decode('utf-8')
        start = []
        for key in self._config._config:
            if not key.startswith('br-'):
                continue
            val = self._config[key].get('basenamestart')
            if val is None:
                print("your config file ({}) doesn't have basenamestart\n"
                      "    defintions for key: {}".format(
                          self._config.get_file_name(), key))
                continue
            if not isinstance(val, list):
                val = [val]
            start.extend(val)
        if not start:
            print("your config file ({}) doesn't have any\n   "
                  "br-*/basenamestart defintions".format(
                      self._config.get_file_name()))
            sys.exit()
        self._browsers = {}
        self._nr_windows = 0
        for line in res.splitlines():
            parts = line.split(None, NR_PARTS)
            pids = parts[2]
            parts = [parts[0]] + [int(x) for x in parts[1:NR_PARTS-1]] + \
                [z for z in parts[NR_PARTS-1:]]
            # pid = parts[2]
            exe = '/proc/' + pids + '/exe'
            try:
                full_path = os.path.realpath(exe)
            except OSError as e:
                if e.errno == os.errno.EACCES:
                    continue
                raise
            binary = os.path.basename(full_path)
            for s in start:
                if not binary.startswith(s):
                    continue
                # print(parts, pids)
                # print(full_path, len(parts))
                if len(parts) == NR_PARTS - 1:
                    parts.append('')  # not very helpful for identifying
                self._browsers.setdefault(s, []).append(
                    dict(zip(self._names, parts)))
                self._nr_windows += 1

    def save(self):
        if self._args.check and not os.path.exists(self._args.unlock_file):
            if self._args.verbose > 0:
                print('no unlock file ({}) found'.format(self._args.unlock_file))
            return
        if not self._browsers:
            self.ewmh()
        if self._nr_windows < self._args.minwin and not self._args.force:
            if self._args.verbose > 0:
                print('not saving number of windows: {} < {}'.format(
                    self._nr_windows, self._args.minwin))
            return 1
        _p = self._path_pattern.format('{:%Y%m%d-%H%M%S}')
        file_name = _p.format(datetime.datetime.now())
        # print(json.dumps(self._browsers, indent=2))
        with open(file_name, 'w') as fp:
            json.dump([self._format_version, self._nr_windows, self._browsers],
                      fp, indent=2, separators=(',', ': '))
        self.read(keep=self._args.keep)

    def read(self, spec=None, show=False, keep=None):
        """
        file names are date-time-stamps which are lexicographically ordered
        if spec is None, 0: read back the lastest file if spec is None or 0
        if spec is a simple integer: offset in reversed list (based 0)
        else assume the spec is a date-time-stamp, use that
        """
        list_of_saves = sorted(glob.glob(self._path_pattern.format('*')),
                               reverse=True)
        nlos = []
        for file_name in list_of_saves:
            if os.path.getsize(file_name) == 0:
                os.remove(file_name)
            else:
                nlos.append(file_name)
            list_of_saves = nlos
        if keep is not None:
            for file_name in list_of_saves[keep:]:
                os.remove(file_name)
        if show:
            default = " (default)"
            print("index | date-time-stamp | nr windows")
            for i, saved in enumerate(list_of_saves):
                num_windows = ''
                with open(saved) as fp:
                    data = fp.read(20)
                    if data[0] == '[':
                        # second number, the one before dict
                        num_windows = ' ' + \
                            data.split('{', 1)[0].rsplit(',', 2)[1].strip()
                print(' {:>4s}   {} {:>4}{}'.format(
                    "[{}]".format(i),
                    os.path.basename(saved).rsplit('.')[0],
                    num_windows,
                    default,
                ))
                default = ""
            print("\nYou can specify an older saved workspace by index")
            return
        if spec is None:
            spec = 0
        if spec >= len(list_of_saves):
            print('You have not enough saved browser workspace data sets to restore by '
                  'index', spec)
            sys.exit(1)
        return list_of_saves[spec]

    def restore(self, position):
        if not self._args.unlock and os.path.exists(self._args.unlock_file):
            if self._args.verbose > 0:
                print('removing unlock file ({})'.format(self._args.unlock_file))
            os.remove(self._args.unlock_file)
            return
        if not self._browsers:
            self.ewmh()
        file_name = self.read(position)
        # print ('filename', file_name)
        with open(file_name, 'r') as fp:
            data = fp.read()
            # if data[0] == '[':
            data = json.loads(data)
            if data[0] == 1:
                data = data[2]
        for browser in data:
            instances = data[browser]
            for instance in instances:
                for k in self._browsers.get(browser, []):
                    if k['title'] != instance['title']:
                        # if the title differs never restore
                        continue
                    if k['pid'] == instance['pid'] and \
                       k['wid'] == instance['wid']:
                        # if the process id and window id is the same
                        # this instance was probably never away
                        continue
                    if k['workspace'] == instance['workspace']:
                        print('not moving', k['title'])
                        continue
                    # now move new window id to old workspace
                    cmd = ['wmctrl', '-i', '-r', k['wid'], '-t',
                           str(instance['workspace'])]
                    if self._args.verbose > 0:
                        print(self.cmdlst_as_string(cmd))
                    print(subprocess.check_output(cmd))
                    k['title'] = None  # don't move it again
        if self._args.unlock:
            with open(self._args.unlock_file, 'w') as fp:
                pass

    @staticmethod
    def cmdlst_as_string(cmd):
        """return cmd list as cut-and-pasteable string with quotes"""
        return (' '.join([c if ' ' not in c else '"' + c + '"' for c in cmd]))


def to_stdout(*args):
    sys.stdout.write(' '.join(args) + '\n')


_default_minwin = 3
_default_keep = 10


class bws_cmd(ProgramBase):
    """handle commmandline options for BrowserWorkspace"""

    def __init__(self):
        super(bws_cmd, self).__init__(
            formatter_class=SmartFormatter
        )

    # you can put these on __init__, but subclassing bws will
    # cause that to break
    @option('--verbose', '-v',
            help='increase verbosity level', action=CountAction,
            const=1, nargs=0, default=0, global_option=True)
    @option('--keep',
            help='max number of old saves to keep (default: %(default)s)',
            type=int, default=_default_keep, global_option=True)
    @option('--unlock-file', default='/tmp/bws.restored', metavar='FILE',
            help="file that has to exist for if doing bws save --check (default: %(default)s)")
    @version('version: ' + __version__)
    def _pb_init(self):
        # special name for which attribs are included in help
        pass

    def run(self):
        if hasattr(self._args, 'func') and self._args.func:
            return self._args.func()

    def parse_args(self):
        self._config = AppConfig(
            'bws',
            filename=AppConfig.check,
            parser=self._parser,  # sets --config option
            warning=to_stdout,
        )
        # self._config._file_name can be handed to objects that need
        # to get other information from the configuration directory
        config_file_name = self._config.get_file_name()
        if not os.path.exists(config_file_name):
            # write new file with defaults
            to_stdout('Initialising', config_file_name)
            cfg = self._config._config
            cfg['global'] = dict(keep=_default_keep)
            cfg['save'] = dict(minwin=_default_minwin)
            cfg['br-firefox'] = dict(basenamestart=['firefox-trunk', 'firefox'])
            cfg['br-chrome'] = dict(basenamestart=['chromium-browser'])
            cfg.write()
        self._config.set_defaults()
        self._parse_args()

    @sub_parser(help='''save the current setup, purging old versions
                     (based on --keep)''')
    @option('--minwin', '-m', default=_default_minwin,
            type=int, metavar='N',
            help="minimum number of windows that needs to be open to create a "
            "new save file (default: %(default)s)")
    @option('--force', action='store_true', help="override (configured) minwin"
            " setting")
    @option('--check', action='store_true',
            help="exit if file specified with --unlock-file doesn't exist")
    def save(self):
        bws = BrowserWorkspace(self._args, self._config)
        return bws.save()

    @sub_parser(help='''list availabel workspace setups''')
    def list(self):
        bws = BrowserWorkspace(self._args, self._config)
        return bws.read(show=True)

    @sub_parser(help='restore workspace setup (defaults to most recent)')
    @option('position', nargs='?', type=int, default=0)
    @option('--unlock', action='store_true',
            help="create file specified by --unlock-file")
    def restore(self):
        bws = BrowserWorkspace(self._args, self._config)
        return bws.restore(self._args.position)


def main():
    n = bws_cmd()
    n.parse_args()
    res = n.run()
    sys.exit(res)  # if res is None -> 0 as exit


if __name__ == '__main__':
    main()
