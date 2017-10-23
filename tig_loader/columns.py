import re

import numpy

from tig_loader.utils import Args, Exc, cached_property
from tig_loader.zone_parameters import ZoneParameterCommon


def check_field_name(name):
    if re.match(r'^[A-Z][A-Z_0-9]*$', name) and name not in ('SHAPE', 'SHAPE_LENGTH'):
        return
    raise Exc('bad field name {}'.format(name))


class BasicColumn(Args):
    query = None
    default_column_index = 0

    @cached_property
    def name(self):
        return unicode(self.args['name'])

    @cached_property
    def field_name(self):
        name = unicode(self.args['field_name'])
        check_field_name(name)
        return name


class Column(BasicColumn):

    @cached_property
    def column_index(self):
        return int(self.args.get('column_index', self.default_column_index))

    def create_get_value(self, _context):
        column_index = self.column_index

        def get_value(row):
            return row[column_index]

        return get_value


class IntColumn(Column):
    arc_type = 'LONG'


class TextColumn(Column):
    arc_type = 'TEXT'


class DoubleColumn(Column):
    arc_type = 'DOUBLE'


class BlobDoubleColumn(Column):
    arc_type = 'DOUBLE'

    def create_get_value(self, _context):
        column_index = self.column_index
        nodata = 0.95 * 1e20

        def get_value(row):
            blob = row[column_index]
            data = blob.read()
            values = numpy.fromstring(data, '>d').astype('d')
            assert len(values) == 1, len(values)
            value = values[0]
            if value < nodata:
                return value
            return None

        return get_value


class ZoneParameterValueColumn(BasicColumn, ZoneParameterCommon):
    arc_type = 'DOUBLE'

    def create_get_value(self, context):

        def get_value(row):
            _lng, _lat, value = self.get_zone_coord_value(row, context)
            return value

        return get_value


column_types = {
    'int': IntColumn,
    'text': TextColumn,
    'double': DoubleColumn,
    'blob_double': BlobDoubleColumn,
    'zone_parameter_value': ZoneParameterValueColumn,
}


def create_column(args, **kw):
    return column_types[args['type']](args=args, **kw)
