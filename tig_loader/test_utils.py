from cStringIO import StringIO
from contextlib import contextmanager
from errno import EEXIST
from os import mkdir
from os.path import abspath, join


TD = abspath(__file__ + '/../test_data')
TEMP_TD = abspath(__file__ + '/../_temp_test_data')

DB_PATH = abspath(__file__ + '/../../TigLoader.sqlite')


@contextmanager
def catch_stdout(print_to_stdout=False):
    import sys
    prev_stdout = sys.stdout
    if print_to_stdout:
        real_new_stdout = StringIO()

        class Stdout(object):
            def write(self, s):
                prev_stdout.write(s)
                real_new_stdout.write(s)

        new_stdout = Stdout()
        sys.stdout = new_stdout
        yield real_new_stdout
    else:
        new_stdout = StringIO()
        sys.stdout = new_stdout
        yield new_stdout

    sys.stdout = prev_stdout


def read_test_data(file_name):
    path = join(TD, file_name)
    with open(path, 'rb') as f:
        data = f.read()
    write_test_data(file_name, data)
    return data


def write_test_data(file_name, data):
    try:
        mkdir(TEMP_TD)
    except OSError as e:
        if e.errno != EEXIST:
            raise
    path = join(TEMP_TD, file_name)
    with open(path, 'wb') as f:
        f.write(data)
