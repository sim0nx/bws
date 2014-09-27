
import subprocess

# default for tox stub is to Fail
def test_bws_help():
    data = subprocess.check_output(['bws', '--help'])
    for word in 'list save restore'.split():
        assert ' ' + word + ' ' in data
