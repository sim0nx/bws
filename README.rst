After a crash, or a re-login, Firefox and Chrome can restore their previous
windows' contents and positions. However they do not normally restore these
windows in the different workspaces, unless the Desktop manager implements this
workspaces by using offsets.

That the latter does work makes sense, as in that case the (large) x and y
offsets "push" the window to the right workspace on restoration. Such a
workspace setup often implies you see a window that you moveover the edge of
one workspace show up on the next one. KDE seems to have used such a scheme
in the period 2010-2013.

Browser windows usually have the name of the page visited in the title. which
makes instances of the browser relatively uniquely identifiable. This program
can save the state of the browser windows in a file, and restore Windows with
matching titles to the original desktop.

This program will not work correctly if a browser window has the same title
on multiple workspaces and has differing secondary tabs.

ToDo:
- check windows position for multiple occuring same strings (assuming positions
  differ, this gives additional info for workspace determination)

----
Firefox
https://bugzilla.mozilla.org/show_bug.cgi?id=372650
https://bugs.launchpad.net/ubuntu/+source/firefox/+bug/684982

Chrome
https://code.google.com/p/chromium/issues/detail?id=18596
https://groups.google.com/a/chromium.org/forum/#!topic/chromium-discuss/h8tY-p-gXIE

KDE used to work:
https://code.google.com/p/chromium/issues/detail?id=297864

