#!/usr/bin/env python3
# coding: utf-8

import argparse
import datetime
import glob
import json
import os
import pathlib
import subprocess

_default_minwin = 3
_default_keep = 10


class BrowserWorkspace:
  """"""
  # names of the fields returned by wmctrl -l -G -p
  _names = 'wid workspace pid x y w h hostname title'.split()

  def __init__(self, args, config, config_path):
    self._args = args
    self._config = config
    self._browsers = {}
    self._nr_windows = 0
    self._format_version = 1
    self._path_pattern = os.path.join(config_path, '{}.bws')

  def ewmh(self):
    NR_PARTS = 8

    start = []
    for key in self._config:
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
      raise SystemExit()

    try:
      res = subprocess.run(['wmctrl', '-l', '-G', '-p'], check=True, capture_output=True)
    except subprocess.CalledProcessError as exc:
      raise SystemExit('Error running wmctrl - {}'.format(str(exc)))

    self._browsers = {}
    self._nr_windows = 0

    for line in res.stdout.decode('utf-8').splitlines():
      parts = line.split(None, NR_PARTS)
      pids = parts[2]
      parts = (
        [parts[0]]
        + [int(x) for x in parts[1: NR_PARTS - 1]]
        + [z for z in parts[NR_PARTS - 1:]]
      )
      # pid = parts[2]
      exe = pathlib.Path('/proc/{}/exe'.format(pids))
      full_path = exe.resolve()
      binary = full_path.name

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
      raise SystemExit(1)

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
          cmd = ['wmctrl', '-i', '-r', k['wid'], '-t', str(instance['workspace'])]
          if self._args.verbose > 0:
            print(self.cmdlst_as_string(cmd))

          try:
            subprocess.run(cmd, check=True)
          except subprocess.CalledProcessError as exc:
            print('WARNING - Failed to move window - {}'.format(str(exc)))

          k['title'] = None  # don't move it again

    if self._args.unlock:
      with open(self._args.unlock_file, 'w') as fp:
        pass

  @staticmethod
  def cmdlst_as_string(cmd):
    """return cmd list as cut-and-pasteable string with quotes"""
    return (' '.join([c if ' ' not in c else '"' + c + '"' for c in cmd]))


def main():
  parser = argparse.ArgumentParser()

  parser.add_argument('--verbose', '-v', action='store_true',
                      help='increase verbosity level')
  parser.add_argument('--keep',
                      help='max number of old saves to keep (default: %(default)s)',
                      type=int, default=_default_keep)
  parser.add_argument('--unlock-file', default='/tmp/bws.restored', metavar='FILE',
                      help="file that has to exist for if doing bws save --check (default: %(default)s)")
  parser.add_argument('--config', default='~/.config/bws/bws2.json', metavar='FILE',
                      help="set FILE as configuration file [~/.config/bws/bws2.json]")

  subparser = parser.add_subparsers(dest='parser')

  subparser_save = subparser.add_parser('save', help='''save the current setup, purging old versions
                     (based on --keep)''')
  subparser_save.add_argument('--minwin', '-m', default=_default_minwin,
                              type=int, metavar='N',
                              help="minimum number of windows that needs to be open to create a "
                                   "new save file (default: %(default)s)")
  subparser_save.add_argument('--force', action='store_true', help="override (configured) minwin"
                                                                   " setting")
  subparser_save.add_argument('--check', action='store_true',
                              help="exit if file specified with --unlock-file doesn't exist")
  subparser_save.add_argument('--verbose', '-v', action='store_true',
                              help='increase verbosity level')
  subparser_save.add_argument('--keep',
                              help='max number of old saves to keep (default: %(default)s)',
                              type=int, default=_default_keep)

  subparser_list = subparser.add_parser('list', help='''list availabel workspace setups''')
  subparser_list.add_argument('--verbose', '-v', action='store_true',
                              help='increase verbosity level')

  subparser_restore = subparser.add_parser('restore', help='restore workspace setup (defaults to most recent)')
  subparser_restore.add_argument('position', nargs='?', type=int, default=0)
  subparser_restore.add_argument('--unlock', action='store_true',
                                 help="create file specified by --unlock-file")
  subparser_restore.add_argument('--verbose', '-v', action='store_true',
                                 help='increase verbosity level')
  subparser_restore.add_argument('--keep',
                                 help='max number of old saves to keep (default: %(default)s)',
                                 type=int, default=_default_keep)

  options = parser.parse_args()

  config_file_path = pathlib.Path(options.config).expanduser()

  if not config_file_path.parent.exists():
    config_file_path.parent.mkdir()

  if not config_file_path.exists():
    print('Initialising', str(config_file_path))

    config = {'global': {'keep': _default_keep},
              'save': {'minwin': _default_minwin},
              'br-firefox': {'basenamestart': ['firefox-trunk', 'firefox']},
              'br-chrome': {'basenamestart': ['chromium-browser', 'chrome']},
              }

    with open(config_file_path, 'w') as fhdl:
      json.dump(config, fhdl, indent=4)
  else:
    with open(config_file_path, 'r') as fhdl:
      config = json.load(fhdl)

  if options.parser == 'list':
    bws = BrowserWorkspace(options, config, str(config_file_path.parent))
    return bws.read(show=True)

  if options.parser == 'restore':
    bws = BrowserWorkspace(options, config, str(config_file_path.parent))
    return bws.restore(options.position)

  if options.parser == 'save':
    bws = BrowserWorkspace(options, config, str(config_file_path.parent))
    return bws.save()


if __name__ == '__main__':
  raise SystemExit(main())
