import unittest

from tig_loader.config import Config
from tig_loader.fake_arcpy import execute_tool
from tig_loader.test_utils import DB_PATH, catch_stdout, read_test_data, write_test_data


def make_file_name(parameters):
    return '_'.join(str(p).replace('/', '_') for p in parameters)


class Test(unittest.TestCase):
    maxDiff = None

    def create_config(self):
        return Config(db_path=DB_PATH)

    def _run(self, tool_name, **kw):
        kw.setdefault('connection', 'everest')
        kw.setdefault('project', 'webtest1')
        kw.setdefault('out_feature_class', 'bla')
        kw.setdefault('out_raster_dataset', 'bla')
        config = self.create_config()
        tool = config.get_tool_by_name(tool_name)
        tool_instance = tool()
        parameters = []
        with catch_stdout():
            for p in tool_instance.getParameterInfo():
                parameters.append(kw.get(p.name))

        with catch_stdout() as stdout:
            execute_tool(tool, parameters)
            output = stdout.getvalue()

        my_file_name = '{}_{}.my'.format(tool_name, make_file_name(parameters))
        write_test_data(my_file_name, output)
        expected_file_name = '{}_{}.ref'.format(tool_name, make_file_name(parameters))
        expected = read_test_data(expected_file_name)
        self.assertEqual(output.split('\n'), expected.split('\n'))

    def test_wells(self):
        self._run(tool_name='Wells')

    def test_well_paths(self):
        self._run(tool_name='WellPaths')

    def test_well_bottoms(self):
        self._run(tool_name='WellBottoms')

    def test_contours(self):
        self._run(tool_name='Contours')

    def test_contours_custom_group(self):
        self._run(tool_name='Contours', group='BV10')

    def test_contours_custom_group_set(self):
        self._run(tool_name='Contours', group='BV10', set='BV10/BotTVD')

    def test_faults_parameters(self):
        with catch_stdout():
            config = self.create_config()
            tool = config.get_tool_by_name('Faults')
            tool_instance = tool()
            parameters = tool_instance.getParameterInfo()
            tool_instance.updateParameters(parameters)
            tool_instance.updateMessages(parameters)

    def test_faults(self):
        self._run(tool_name='Faults')

    def test_faults_custom_group(self):
        self._run(tool_name='Faults', group='Left')

    def test_control_points(self):
        self._run(tool_name='ControlPoints')

    def test_control_points_custom_group(self):
        self._run(tool_name='ControlPoints', group='BV10(4)')

    def test_control_points_custom_group_set(self):
        self._run(tool_name='ControlPoints', group='BV10(4)', set='BV10(4)/BotTVD')

    def test_polygons(self):
        self._run(tool_name='Polygons')

    def test_polygons_custom_group(self):
        self._run(tool_name='Polygons', group='BV10')

    def test_polygons_custom_group_2(self):
        self._run(tool_name='Polygons', group='Lithology')

    def test_polygons_custom_group_set(self):
        self._run(tool_name='Polygons', group='BV10', set='BV10/OWC_int')

    def test_surface(self):
        self._run(tool_name='Surface', group='BV10', set='BV10/BotTVD')

    def test_zonation_parameters_parameters(self):
        #with catch_stdout():
            config = self.create_config()
            tool = config.get_tool_by_name('ZonationParams')
            tool_instance = tool()
            parameters = tool_instance.getParameterInfo()
            parameters[0].value = 'everest'
            parameters[0].altered = True
            parameters[1].value = 'webtest1'
            parameters[1].altered = True
            tool_instance.updateParameters(parameters)
            tool_instance.updateMessages(parameters)

    def test_zonation_parameters(self):
        self._run(tool_name='ZonationParams', parameter='TopTVD (TVD at top of zone (m))')

    def test_zonation_parameters_custom_zonation(self):
        self._run(tool_name='ZonationParams', zonation='Production1 (petrophysical)', parameter='TopTVD (TVD at top of zone (m))')

    def test_zonation_parameters_custom_zone(self):
        self._run(tool_name='ZonationParams', zonation='All 4', zone='Production1/BV9', parameter='TopTVD (TVD at top of zone (m))')

    def test_zonation_parameters_custom_zone_2(self):
        self._run(project='demo2007', tool_name='ZonationParams', zonation='Multi level published (resrock)', zone='Multi level published/Sand', parameter='VCLart-S (Clay arithmetic average over Sand)')

    def test_production_properties_static_fluid_level(self):
        self._run(tool_name='ProdPropStaticFluidLevel')

    def test_production_properties_static_fluid_level_custom_range(self):
        self._run(tool_name='ProdPropStaticFluidLevel', start_date='01.01.1900', end_date='30.01.1900')

    def test_production_properties_dynamic_fluid_level(self):
        self._run(tool_name='ProdPropDynamicFluidLevel')

    def test_production_properties_dynamic_fluid_level_custom_range(self):
        self._run(tool_name='ProdPropDynamicFluidLevel', start_date='01.01.1900', end_date='30.01.1900')


if __name__ == '__main__':
    unittest.main()
