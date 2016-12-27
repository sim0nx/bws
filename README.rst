The Problem
===========

On Linux, after a crash, or a re-login, Firefox and Chrome can restore their
previous windows' contents and positions. However they do not normally
restore these windows in the different workspaces/desktops that you
may be using.

If the desktop manager implements workspaces by using offsets (wider or
higher than the desktop resolution) restoration works as offsets "push" the
window to the right workspace on restoration. Such a workspace setup often
implies you see a window that you moveover the edge of one workspace show up
on the next one. KDE seems to have used such a scheme in the period
2010-2013.

Browsers would need to be `EWMH
<https://en.wikipedia.org/wiki/Extended_Window_Manager_Hints>`_ aware, which
they currently aren't.

A partial solution
==================
But browser windows usually have the name of the page
visited in the title, which makes instances of the browser windows relatively
uniquely identifiable. Based on that you can save the state of the browser
windows in a file, and restore windows with matching titles to the original
workspace.

This program will not work correctly if a browser window has the same title
on multiple workspaces and only has differing secondary tabs. If two, single
tab windows have the same title, they probably point to the same URL, and in
that case which one gets restored to what workspace is less important (unless
the history makes a difference).

Installation
============

First, make sure your linux version has ``wmctrl`` installed.

You can use ``pip`` to install the program::

    pip install bws

You can also install the
`configobj <http://www.voidspace.org.uk/python/configobj.html>`_ library
(with ``pip``) and directly download and use the main Python file.

Usage
=====

Run ``bws save`` to save the current browser windows, ``bws restore`` to
restore the latest saved setup. Before restoring reopen the browser windows
and select [Restore] as necessary.

Chrome needs to be configured to allow restoring by selecting "Continue where
you left off", in the `settings menu
<chrome://settings/#startup-section-content>`_. Firefox always seems to ask
when a crash occured, but you can also explicitly `set the preferences
<about:preferences#general>`_ to "Show my windows and tabs from last time"

The program keeps configuration defaults and restore information in (by
default) ``~/.config/bws`` in ``bws.ini`` resp. ``*.bws`` files. Multiple
restore settings are kept (which might be a privacy issue for you), and ``bws list``
will show you which ones (with a date-time-stamp). ``bws restore`` can take
an argument to select a specific "save""

The config file allows to expand the patterns that are matched on where
``/proc/PID/exe`` points to, to identify the windows for which information
needs saving. A minimum number of windows can be specified that are necessary
for restoring (in the configuration file or on the commandline; the
commandline overrules the configuration file). This minimum prevents saves of
browser windows when a single window is open asking for confirmation to
restore previously opened windows.

Cron
====

I run ``bws`` from crontab file every five minutes like this::

  */5 *  *   *   *     DISPLAY=:0 /home/anthon/.venv/27/bin/bws save --check

the ``--check`` only works if the file specified with ``--unlock-file`` exists. This
defaults to ``/tmp/bws.restored`` (which is on a temporary filesystem).

Issuing ``bws restore`` removes this unlock file, unless you specify `--unlock`, which I do
on the last run, after Firefox has reloaded all pages, and restoring is complete..


ToDo
====

- check windows position for multiple occuring same strings (assuming positions
  differ, this gives additional info for workspace determination)

----

Firefox
-------
https://bugzilla.mozilla.org/show_bug.cgi?id=372650
https://bugs.launchpad.net/ubuntu/+source/firefox/+bug/684982

Chrome
------
https://code.google.com/p/chromium/issues/detail?id=18596
https://groups.google.com/a/chromium.org/forum/#!topic/chromium-discuss/h8tY-p-gXIE

KDE used to work
----------------
https://code.google.com/p/chromium/issues/detail?id=297864

