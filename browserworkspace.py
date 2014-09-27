#!/usr/bin/env python
# coding: utf-8

from __future__ import print_function

import sys
import os
import subprocess
import json
import glob
import datetime

from ruamel.std.argparse import ProgramBase, option, sub_parser, version, \
    CountAction, SmartFormatter
from ruamel.appconfig import AppConfig
from . import __version__


class BrowserWorkspace:
    """"""
    # names of the fields returned by wmctrl -l -G -p
    _names = 'wid workspace pid x y w h hostname title'.split()

    def __init__(self, args, config):
        self._args = args
        self._config = config
        # firefox=True, chrome=True, safe='json'):
        # self._firefox = firefox
        # self._chrome = chrome
        self._browsers = {}
        self._nr_windows = 0
        self._format_version = 1
        x = self._path_pattern = os.path.join(
            os.path.dirname(self._config.get_file_name()),
            '{}.bws'
        )

    def ewmh(self):
        NR_PARTS = 8
        res = subprocess.check_output('wmctrl -l -G -p'.split())
        start = []
        start.extend(['firefox-trunk', 'firefox'])
        start.append('chromium-browser')
        self._browsers = {}
        self._nr_windows = 0
        for line in res.splitlines():
            parts = line.split(None, NR_PARTS)
            pids = parts[2]
            parts = [parts[0]] + [int(x) for x in parts[1:NR_PARTS-1]] + \
                [z.decode('utf-8') for z in parts[NR_PARTS-1:]]
            pid = parts[2]
            exe = '/proc/' + pids + '/exe'
            try:
                full_path = os.path.realpath(exe)
            except OSError, e:
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
        if not self._browsers:
            self.ewmh()
        _p = self._path_pattern.format('{:%Y%m%d-%H%M%S}')
        file_name = _p.format(datetime.datetime.now())
        # print(json.dumps(self._browsers, indent=2))
        with file(file_name, 'w') as fp:
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
        if keep is not None:
            for file_name in list_of_saves[keep:]:
                os.remove(file_name)
        if show:
            default = " (default)"
            print("index | date-time-stamp | nr windows")
            for i, saved in enumerate(list_of_saves):
                num_windows = ''
                with file(saved) as fp:
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
        return list_of_saves[spec]

    def restore(self, position):
        if not self._browsers:
            self.ewmh()
        file_name = self.read(position)
        # print ('filename', file_name)
        with file(file_name, 'r') as fp:
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

    @staticmethod
    def cmdlst_as_string(cmd):
        """return cmd list as cut-and-pasteable string with quotes"""
        return (' '.join([c if ' ' not in c else '"' + c + '"' for c in cmd]))


def to_stdout(*args):
    sys.stdout.write(' '.join(args) + '\n')


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
            type=int, default=100, global_option=True)
    @version('version: ' + __version__)
    def _pb_init(self):
        # special name for which attribs are included in help
        pass

    def run(self):
        if self._args.func:
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
            from ruamel.ext.configobj import ConfigObj
            to_stdout('Initialising', config_file_name)
            cfg = ConfigObj(config_file_name)
            cfg['global'] = dict(keep=10)
            cfg['br-firefox'] = dict(basenamestart=
                                     ['firefox-trunk', 'firefox'])
            cfg['br-chrome'] = dict(basenamestart=['chromium-browser'])
            cfg.write()
        self._config.set_defaults()
        self._parse_args()

    @sub_parser(help='''save the current setup, purging old versions
                     (based on --keep)''')
    def save(self):
        print('saving')
        bws = BrowserWorkspace(self._args, self._config)
        bws.save()

    @sub_parser(help='''list availabel workspace setups''')
    def list(self):
        print('saving')
        bws = BrowserWorkspace(self._args, self._config)
        bws.read(show=True)

    @sub_parser(help='restore workspace setup (defaults to most recent)')
    @option('position', nargs='?', type=int, default=0)
    def restore(self):
        bws = BrowserWorkspace(self._args, self._config)
        bws.restore(self._args.position)


def main():
    n = bws_cmd()
    n.parse_args()
    n.run()