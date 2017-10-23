from __future__ import division

from os.path import abspath
from pprint import pformat
from types import ModuleType
import __builtin__
import functools
import itertools
import logging
import time


_log = None


def _get_log():
    global _log
    if _log is not None:
        return _log

    CWD = abspath(__file__ + '/..')

    _log = logging.getLogger('dbg')
    _log.setLevel(logging.DEBUG)
    h = logging.FileHandler(CWD + '/_temp_dbg.log')
    f = logging.Formatter('%(asctime)s %(message)s')
    h.setFormatter(f)
    _log.addHandler(h)

    return _log


def dmp(a):
    s = pformat(a)
    _get_log().debug(s)
    try:
        print s
    except IOError:
        pass


def log(fmt, *a, **kw):
    s = fmt.format(*a, **kw)
    _get_log().debug(s)
    try:
        print s
    except IOError:
        pass


def reload(module):
    #return
    __builtin__.reload(module)


def rreload(module):
    """Recursively reload modules."""
    __builtin__.reload(module)
    for attribute_name in dir(module):
        attribute = getattr(module, attribute_name)
        if type(attribute) is ModuleType:
            rreload(attribute)


def log_method(*fields, **kw):
    enabled = kw.get('enabled', False)
    log_args = kw.get('log_args', False)
    measure_time = kw.get('measure_time', False)

    def dwr(fn):
        if not enabled:
            return fn

        def get_attr(object, name):
            try:
                return getattr(object, name)
            except AttributeError as e:
                raise Exception(e)

        def wr(self, *a, **kw):
            s = '!!! {0}.{1}'.format(self.__class__.__name__, fn.__name__)
            if log_args:
                s += '({0})'.format(
                    ', '.join(itertools.chain(
                        ('self',),
                        ('{0!r}'.format(arg) for arg in a),
                        ('{0}={1!r}'.format(k, v) for k, v in kw.iteritems()),
                    ))
                )
            if fields:
                s += ' ' + ' '.join(('{0}={1!r}'.format(name, get_attr(self, name)) for name in fields))
            print s
            if measure_time:
                start_time = time.time()
                ret = fn(self, *a, **kw)
                print '{0}'.format(time.time() - start_time)
                return ret
            else:
                return fn(self, *a, **kw)

        return functools.update_wrapper(wr, fn)

    return dwr


def profile(fn, own_time=False):
    from cProfile import runctx
    #from profile import runctx
    sort = 'time' if own_time else 'cumulative'
    runctx('fn()', globals(), locals(), sort=sort)


def timeit(stmt, repeat=10, number=1, setup=lambda: None):
    import timeit
    timer = timeit.Timer(stmt, setup)
    times = timer.repeat(repeat, number)
    print 'min, avg, max:', min(times), sum(times) / len(times), max(times)
