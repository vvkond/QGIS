from cStringIO import StringIO
import unittest

from tig_loader.test_tools import read_test_data
from tig_loader.tig_projection import get_tig_projection


class FakeLob(object):
    def __init__(self, data):
        self._data = data
        self._pos = 0

    def size(self):
        return len(self._data)

    def read(self, offset=1, amount=None):
        if amount is None:
            ret = self._data[offset - 1:]
        else:
            ret = self._data[offset - 1: offset - 1 + amount]
        self._pos += len(ret)
        return ret


class Test(unittest.TestCase):
    maxDiff = None

    def _check(self, dd):
        d = dd.copy()
        d['pj_ref'] = d.pop('cp.DB_CARTO_REFERENCE_CODE')
        d['units'] = d.pop('DB_CARTO_EXTERNAL_UNITS')
        d['p_type'] = d.pop('DB_CARTO_DEF_PARAMS_TYPE')
        d['p'] = FakeLob(d.pop('DB_CARTO_DEF_PARAMETERS'))
        prj = get_tig_projection(**d)
        self.assertIsNotNone(prj, 'empty prj {!r}'.format(dd))
        self.assertIsNotNone(prj.proj4_args, 'empty proj4_args {} {!r}'.format(prj.__class__.__name__, dd))
        self.assertIsNotNone(prj.proj4_string, 'empty proj4_string {} {!r}'.format(prj.__class__.__name__, dd))
        self.assertIsNotNone(prj.proj4_object, 'empty proj4_object {} {!r}'.format(prj.__class__.__name__, dd))
        self.assertIsNotNone(prj.esri_string, 'empty esri_string {} {!r}'.format(prj.__class__.__name__, prj.proj4_args))

    def test_tig_projections(self):
        errors = []
        data = read_test_data('used_projections')
        for line in StringIO(data):
            if line[0] == '#':
                continue
            dd = dict(eval(line))
            try:
                self._check(dd)
            except AssertionError as e:
                errors.append(e)
        if errors:
            raise Exception('{} {}'.format(len(errors), errors[0]))

    def test_g1(self):
        self._check({'!c': u'everest', 'DB_CARTO_DATUM_SLDNID': 0, 'DB_CARTO_DEF_PARAMETERS': 'AXT\xc1@\x00\x00\x00AX?\xdf\xc17K\xc7?\xf0\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00A(\xb8 \x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xc1\x1e\x84\x80\x00\x00\x00\x00\xc1X\xcb\xa8\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00', 'DB_CARTO_DEF_PARAMS_TYPE': 1, 'DB_CARTO_EXTERNAL_UNITS': 1, 'DB_CARTO_TYPE': 1, 'cp.DB_CARTO_REFERENCE_CODE': 11, 'DB_CARTO_USER_NAME': 'CRS 1,294,038,194', 'DB_CARTO_SPHEROID_SLDNID': 15000021, '!p': 'stolbovoe', 'DB_COMMENT': 'A new CRS', 'DB_CARTO_PROJECTN_SLDNID': 15000010, 'cp.DB_CARTO_PROJECTION_NAME': 'Transverse Mercator', 'DB_SLDNID': 10, 'cp.DB_SLDNID': 15000010, 'DB_CARTO_PARAMS_SLDNID': 0})


if __name__ == '__main__':
    unittest.main()
