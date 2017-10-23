from collections import OrderedDict
from os.path import join
import json

from tig_loader.columns import create_column
from tig_loader.geometries import create_geometry
from tig_loader.row_transformers import create_row_transformer
from tig_loader.tool_parameters import create_tool_parameter
from tig_loader.utils import Args, Exc, cached_property


class Query(Args):
    external_files_path = None

    @cached_property
    def id(self):
        return int(self.args['id'])

    @cached_property
    def tool_name(self):
        return str(self.args['tool_name'])

    @cached_property
    def name(self):
        return unicode(self.args['name'])

    @cached_property
    def category(self):
        return unicode(self.args.get('category', ''))

    @cached_property
    def description(self):
        return unicode(self.args.get('description', ''))

    @cached_property
    def tool_parameters(self):
        parameters = self.options['parameters']
        return [
            create_tool_parameter(
                args=args,
                query=self,
                default_index=index,
            )
            for index, args in enumerate(parameters)
        ]

    def get_computed_parameters(self, arcpy_parameters, config):
        computed_parameters = OrderedDict()
        for p in self.tool_parameters:
            computed_parameter = p.create_computed_parameter(
                arcpy_parameter=arcpy_parameters[p.index],
                config=config,
                computed_parameters=computed_parameters,
            )
            assert p.id not in computed_parameters
            computed_parameters[p.id] = computed_parameter
        return computed_parameters

    @cached_property
    def connection_parameter_id(self):
        return unicode(self.options.get('connection_parameter_id', 'connection'))

    @cached_property
    def project_parameter_id(self):
        return unicode(self.options.get('project_parameter_id', 'project'))

    @cached_property
    def out_feature_class_parameter_id(self):
        return unicode(self.options.get('out_feature_class_parameter_id', 'out_feature_class'))

    def create_column(self, args, index):
        return create_column(args, default_column_index=index, query=self)

    @cached_property
    def options(self):
        options = json.loads(self.args['options'])
        if self.external_files_path is not None and 'file' in options and len(options) == 1:
            options_path = join(self.external_files_path, options['file'])
            with open(options_path, 'rb') as f:
                return json.loads(f.read().decode('utf-8'))
        return options

    @cached_property
    def row_transformer(self):
        return create_row_transformer(self.options.get('row_transformer', {'type': 'identity'}))

    def enumerate_columns(self):
        field_names = set()
        for i, args in enumerate(self.options['columns']):
            column = self.create_column(args, i)
            if column.field_name in field_names:
                raise Exc('duplicate field_name {} at column {}'.format(column.name, column.name))
            yield column
            field_names.add(column.field_name)

    @cached_property
    def columns(self):
        return list(self.enumerate_columns())

    @cached_property
    def geometry_type(self):
        return create_geometry(self.options['geometry'], query=self)

    def enumerate_field_names(self):
        for field_name in self.geometry_type.field_names:
            yield field_name
        for column in self.columns:
            yield column.field_name

    @cached_property
    def field_names(self):
        return list(self.enumerate_field_names())

    def get_sql(self, value):
        if isinstance(value, basestring):
            return unicode(value)
        if isinstance(value, dict):
            if self.external_files_path is not None and 'file' in value:
                sql_file_path = join(self.external_files_path, value['file'])
                with open(sql_file_path, 'rb') as f:
                    return f.read().decode('utf-8')
        raise Exc('can not get sql from {} for {}'.format(value, self.id))

    @cached_property
    def sql(self):
        return self.get_sql(self.options.get('sql'))

    @cached_property
    def sql_args(self):
        return self.options.get('sql_args', {})

    def create_transform_row(self, context):
        return self.row_transformer.create_transform_row(context)

    def create_translate_row(self, context):
        get_geometry_values = self.geometry_type.create_get_values(context)
        columns_get_value = [column.create_get_value(context) for column in self.columns]

        def translate_row(input_row):
            out_row = []
            geometry_values = get_geometry_values(input_row)
            if geometry_values is None:
                return
            out_row.extend(geometry_values)
            for get_value in columns_get_value:
                out_row.append(get_value(input_row))
            return out_row

        return translate_row
