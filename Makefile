
UTILNAME:=bws
PKGNAME:=ruamel.bws
VERSION:=$$(python setup.py --version)
REGEN:=/usr/local/bin/ruamel_util_new util --published --command bws --skip-hg

include ~/.config/ruamel_util_new/Makefile.inc

clean:
	rm -rf build .tox $(PKGNAME).egg-info/ README.pdf __pycache__
	find . -name "*.pyc" -exec rm {} +

updatereadme:
	updatereadme

layout:	pdf
	cp README.pdf /data0/tmp/pdf
