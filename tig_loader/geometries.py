from pyproj import Proj, transform
import numpy

from tig_loader.arcpy_wrap import arcpy
from tig_loader.projection_utils import lonlat_add_list
from tig_loader.utils import Args, cached_property
from tig_loader.zone_parameters import ZoneParameterCommon


class GeometryType(Args):
    query = None


class PointGeometry(GeometryType):
    arc_type = 'POINT'

    @cached_property
    def lng_column_index(self):
        return int(self.args['lng_column'])

    @cached_property
    def lat_column_index(self):
        return int(self.args['lat_column'])

    @cached_property
    def field_names(self):
        return ('SHAPE@X', 'SHAPE@Y')

    def create_get_values(self, _context):
        lng_column_index = self.lng_column_index
        lat_column_index = self.lat_column_index

        def get_values(input_row):
            return float(input_row[lng_column_index]), float(input_row[lat_column_index])

        return get_values


class DeviationGeometry(GeometryType):
    arc_type = 'POLYLINE'

    @cached_property
    def lng_column_index(self):
        return int(self.args['lng_column'])

    @cached_property
    def lat_column_index(self):
        return int(self.args['lat_column'])

    @cached_property
    def delta_x_column_index(self):
        return int(self.args['delta_x_column'])

    @cached_property
    def delta_y_column_index(self):
        return int(self.args['delta_y_column'])

    @cached_property
    def field_names(self):
        return ['SHAPE@']

    def create_get_values(self, _context):
        lng_column_index = self.lng_column_index
        lat_column_index = self.lat_column_index
        delta_x_column_index = self.delta_x_column_index
        delta_y_column_index = self.delta_y_column_index
        sr = arcpy.SpatialReference(4326)
        Polyline = arcpy.Polyline
        Point = arcpy.Point
        Array = arcpy.Array

        def get_values(input_row):
            lng = input_row[lng_column_index]
            lat = input_row[lat_column_index]
            delta_x = numpy.fromstring(input_row[delta_x_column_index].read(), '>f').astype('d')
            delta_y = numpy.fromstring(input_row[delta_y_column_index].read(), '>f').astype('d')
            x, y = lonlat_add_list(lng, lat, delta_x, delta_y)
            geometry = Polyline(
                Array([
                    Point(x[i], y[i])
                    for i in xrange(len(x))
                ]),
                sr,  # http://support.esri.com/en/bugs/nimbus/TklNMDU5ODQ1
            )
            return [geometry]

        return get_values


class WellBottomGeometry(GeometryType):
    arc_type = 'POINT'

    @cached_property
    def lng_column_index(self):
        return int(self.args['lng_column'])

    @cached_property
    def lat_column_index(self):
        return int(self.args['lat_column'])

    @cached_property
    def delta_x_column_index(self):
        return int(self.args['delta_x_column'])

    @cached_property
    def delta_y_column_index(self):
        return int(self.args['delta_y_column'])

    @cached_property
    def field_names(self):
        return ('SHAPE@X', 'SHAPE@Y')

    def create_get_values(self, _context):
        lng_column_index = self.lng_column_index
        lat_column_index = self.lat_column_index
        delta_x_column_index = self.delta_x_column_index
        delta_y_column_index = self.delta_y_column_index

        def get_values(input_row):
            lng = input_row[lng_column_index]
            lat = input_row[lat_column_index]
            blob_x = input_row[delta_x_column_index]
            blob_y = input_row[delta_y_column_index]
            size_x = blob_x.size()
            size_y = blob_y.size()
            delta_x = numpy.fromstring(blob_x.read(size_x - 3), '>f').astype('d')
            delta_y = numpy.fromstring(blob_y.read(size_y - 3), '>f').astype('d')
            x, y = lonlat_add_list(lng, lat, delta_x, delta_y)
            return [x[0], y[0]]

        return get_values


class BlobPointGeometry(GeometryType):
    arc_type = 'POINT'

    @cached_property
    def x_column_index(self):
        return int(self.args['x_column'])

    @cached_property
    def y_column_index(self):
        return int(self.args['y_column'])

    @cached_property
    def z_column_index(self):
        return int(self.args['z_column'])

    @cached_property
    def field_names(self):
        return ('SHAPE@X', 'SHAPE@Y')

    def create_get_values(self, context):
        x_column_index = self.x_column_index
        y_column_index = self.y_column_index
        p4326 = Proj(init='epsg:4326')
        prj = context.default_tig_projection.proj4_object

        def get_coord(input_row, column_index):
            blob = input_row[column_index]
            data = blob.read()
            coords = numpy.fromstring(data, '>d').astype('d')
            assert len(coords) == 1, len(coords)
            return coords[0]

        def get_values(input_row):
            x = get_coord(input_row, x_column_index)
            y = get_coord(input_row, y_column_index)
            x, y = transform(prj, p4326, x, y)
            return x, y

        return get_values


class BlobLineGeometry(GeometryType):
    arc_type = 'POLYLINE'

    @cached_property
    def x_column_index(self):
        return int(self.args['x_column'])

    @cached_property
    def y_column_index(self):
        return int(self.args['y_column'])

    @cached_property
    def z_column_index(self):
        return int(self.args['z_column'])

    @cached_property
    def field_names(self):
        return ['SHAPE@']

    def create_get_values(self, context):
        x_column_index = self.x_column_index
        y_column_index = self.y_column_index
        #z_column_index = self.z_column_index
        sr = arcpy.SpatialReference(4326)
        Polyline = arcpy.Polyline
        Point = arcpy.Point
        Array = arcpy.Array
        p4326 = Proj(init='epsg:4326')
        prj = context.default_tig_projection.proj4_object

        def get_values(input_row):
            blob_x = input_row[x_column_index]
            blob_y = input_row[y_column_index]
            data_x = blob_x.read()
            data_y = blob_y.read()
            x = numpy.fromstring(data_x, '>d').astype('d')
            y = numpy.fromstring(data_y, '>d').astype('d')
            x, y = transform(prj, p4326, x, y)
            if len(x) == 0:
                geometry = None
            else:
                geometry = Polyline(
                    Array([
                        Point(x[i], y[i])
                        for i in xrange(len(x))
                    ]),
                    sr,
                )
            return [geometry]

        return get_values


class BlobPolygonGeometry(GeometryType):
    arc_type = 'POLYGON'

    @cached_property
    def x_column_index(self):
        return int(self.args['x_column'])

    @cached_property
    def y_column_index(self):
        return int(self.args['y_column'])

    @cached_property
    def z_column_index(self):
        return int(self.args['z_column'])

    @cached_property
    def field_names(self):
        return ['SHAPE@']

    def create_get_values(self, context):
        x_column_index = self.x_column_index
        y_column_index = self.y_column_index
        #z_column_index = self.z_column_index
        sr = arcpy.SpatialReference(4326)
        Polygon = arcpy.Polygon
        Point = arcpy.Point
        Array = arcpy.Array
        p4326 = Proj(init='epsg:4326')

        def get_values(input_row):
            blob_x = input_row[x_column_index]
            blob_y = input_row[y_column_index]
            data_x = blob_x.read()
            data_y = blob_y.read()
            x = numpy.fromstring(data_x, '>d').astype('d')
            y = numpy.fromstring(data_y, '>d').astype('d')
            prj = context.default_tig_projection
            x, y = transform(prj, p4326, x, y)
            geometry = Polygon(
                Array([
                    Point(x[i], y[i])
                    for i in xrange(len(x))
                ]),
                sr,
            )
            return [geometry]

        return get_values


class ZoneParameterPointGeometry(GeometryType, ZoneParameterCommon):
    arc_type = 'POINT'

    @cached_property
    def field_names(self):
        return ('SHAPE@X', 'SHAPE@Y')

    def create_get_values(self, context):

        def get_values(input_row):
            values = self.get_zone_coord_value(input_row, context)
            if values is None:
                return
            lng, lat, _value = values
            return [lng, lat]

        return get_values


geometry_types = {
    'point': PointGeometry,
    'deviation': DeviationGeometry,
    'well_bottom': WellBottomGeometry,
    'blob_line': BlobLineGeometry,
    'blob_polygon': BlobPolygonGeometry,
    'blob_point': BlobPointGeometry,
    'zone_parameter_point': ZoneParameterPointGeometry,
}


def create_geometry(args, **kw):
    return geometry_types[args['type']](args=args, **kw)
