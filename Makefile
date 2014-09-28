
UTILNAME:=bws
PKGNAME:=ruamel.bws
VERSION:=$$(python setup.py --version)
DIST:=dist/$(PKGNAME)-$(VERSION).tar.gz
REGEN:=/usr/local/bin/ruamel_util_new util --published --command bws --skip-hg

sdist:
	python setup.py sdist

wheel:
	python setup.py bdist_wheel

pypi-register:
	python setup.py register

pypi-upload:
	python setup.py sdist upload

clean:
	rm -rf build .tox $(PKGNAME).egg-info/
	find . -name "*.pyc" -exec rm {} +

tar:
	tar tf $(DIST)

devpi:
	devpi upload $(DIST)

regen_setup:
	rm -f ../bws/setup.py
	$(REGEN)
	pep8 setup.py

regen_makefile:
	rm -f ../$(UTILNAME)/Makefile
	$(REGEN)

updateprogram:
	ruamel_util_updateprogram browserworkspace.py
