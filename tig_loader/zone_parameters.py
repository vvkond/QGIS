from __future__ import division

from struct import unpack_from

import numpy

from tig_loader.projection_utils import lonlat_add_list
from tig_loader.utils import cached_property


class ZoneParameterCommon(object):

    @cached_property
    def zonation_id_column_index(self):
        return int(self.args['zonation_id_column'])

    @cached_property
    def zone_id_column_index(self):
        return int(self.args['zone_id_column'])

    @cached_property
    def zone_top_column_index(self):
        return int(self.args['zone_top_column'])

    @cached_property
    def zone_bottom_column_index(self):
        return int(self.args['zone_bottom_column'])

    @cached_property
    def well_id_column_index(self):
        return int(self.args['well_id_column'])

    @cached_property
    def well_name_column_index(self):
        return self.args['well_name_column']

    @cached_property
    def well_lng_column_index(self):
        return int(self.args['well_lng_column'])

    @cached_property
    def well_lat_column_index(self):
        return int(self.args['well_lat_column'])

    @cached_property
    def deviation_x_column_index(self):
        return int(self.args['deviation_x_column'])

    @cached_property
    def deviation_y_column_index(self):
        return int(self.args['deviation_y_column'])

    @cached_property
    def deviation_md_column_index(self):
        return int(self.args['deviation_md_column'])

    @cached_property
    def deviation_tvd_column_index(self):
        return int(self.args['deviation_tvd_column'])

    @cached_property
    def parameter_name_column_index(self):
        return int(self.args['parameter_name_column'])

    @cached_property
    def zonation_params_column_index(self):
        return int(self.args['zonation_params_column'])

    @cached_property
    def variable_short_name_column_index(self):
        return int(self.args['variable_short_name_column'])

    @cached_property
    def variable_dflt_column_index(self):
        return int(self.args['variable_dflt_column'])

    @cached_property
    def variable_min_column_index(self):
        return int(self.args['variable_min_column'])

    @cached_property
    def variable_max_column_index(self):
        return int(self.args['variable_max_column'])

    @cached_property
    def variable_null_column_index(self):
        return int(self.args['variable_null_column'])

    def read_zonation_params(self, params):
        d = params.read()
        if not d:
            return
        _pos = [0]

        def read_int():
            ret = unpack_from('>i', d, _pos[0])[0]
            _pos[0] += 4
            return ret

        def read_string(count):
            ret = unpack_from('>{}s'.format(count), d, _pos[0])[0]
            _pos[0] += count
            return ret

        def read_float():
            ret = unpack_from('>f', d, _pos[0])[0]
            _pos[0] += 4
            return ret

        zonation_id = read_int()
        TIG_VARIABLE_SHORT_NAME_LEN = 8
        TIG_VARIABLE_CHAR_DFLT_LEN = 80
        SQL_INTEGER = 1
        SQL_FLOAT = 2
        SQL_CHARACTER = 4

        well_count = read_int()
        for _i in xrange(well_count):
            well_id = read_int()
            wint_ct = read_int()
            for _j in xrange(wint_ct):
                zone_id = read_int()
                para_ct = read_int()
                for _k in xrange(para_ct):
                    type = read_int()
                    name = read_string(TIG_VARIABLE_SHORT_NAME_LEN).strip()
                    if type == SQL_FLOAT:
                        value = read_float()
                    elif type == SQL_INTEGER:
                        value = read_int()
                    elif type == SQL_CHARACTER:
                        value = read_string(TIG_VARIABLE_CHAR_DFLT_LEN)
                    else:
                        raise Exception('bad type {}'.format(type))
                    yield zonation_id, well_id, zone_id, name, type, value

    def get_zonation_param_value(self, input_row):
        zonation_params = input_row[self.zonation_params_column_index]
        _zonation_id = input_row[self.zonation_id_column_index]
        _well_id = input_row[self.well_id_column_index]
        _zone_id = input_row[self.zone_id_column_index]
        _name = input_row[self.parameter_name_column_index]
        for t in self.read_zonation_params(zonation_params):
            zonation_id, well_id, zone_id, name, type, value = t
            if (
                zonation_id == _zonation_id and
                well_id == _well_id and
                zone_id == _zone_id and
                name == _name
            ):
                return value

    def get_zone_coord_value(self, input_row, context):
        ZAV_INDT_LO = -1000.9
        ZAV_INDT_HI = -998.9

        parameter_name = input_row[self.parameter_name_column_index]
        zonation_param_value = self.get_zonation_param_value(input_row)

        zone_top = input_row[self.zone_top_column_index]
        zone_bottom = input_row[self.zone_bottom_column_index]

        value = None
        depth = None

        if parameter_name == 'TopTVD':
            depth = zone_top
            value = zone_top
        elif parameter_name == 'BotTVD':
            depth = zone_bottom
            value = zone_bottom
        else:
            if zonation_param_value is None:
                zonation_param_value = input_row[self.variable_dflt_column_index]
            if ZAV_INDT_LO < zonation_param_value < ZAV_INDT_HI:
                value = None
            else:
                value = zonation_param_value
            depth = (zone_bottom + zone_top) * 0.5

            if parameter_name in ['ISCtopMD', 'ISPtopMD', 'DIPZTOP']:
                depth = zone_top
            elif parameter_name in ['ISCbotMD', 'ISPbotMD', 'DIPZBOT']:
                depth = zone_bottom

        def read_floats(index):
            return numpy.fromstring(input_row[index].read(), '>f').astype('d')

        x = read_floats(self.deviation_x_column_index)
        y = read_floats(self.deviation_y_column_index)
        md = read_floats(self.deviation_md_column_index)
        tvd = read_floats(self.deviation_tvd_column_index)

        jp = None
        for ip in xrange(len(x) - 1):
            if md[ip] <= depth <= md[ip + 1]:
                jp = ip

        if jp is None:
            context.addWarningMessage('Can not find cdt for well {} at depth {}'.format(input_row[self.well_name_column_index], depth))
            return

        rinterp = (depth - md[jp]) / (md[jp + 1] - md[jp])
        xPosition = x[jp] + rinterp * (x[jp + 1] - x[jp])
        yPosition = y[jp] + rinterp * (y[jp + 1] - y[jp])

        if parameter_name in ['TopTVD', 'BotTVD']:
            value = tvd[jp] + rinterp * (tvd[jp + 1] - tvd[jp])

        lng = input_row[self.well_lng_column_index]
        lat = input_row[self.well_lat_column_index]
        ret_x, ret_y = lonlat_add_list(lng, lat, [xPosition], [yPosition])
        return (ret_x[0], ret_y[0], value)
