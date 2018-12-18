# -*- coding: utf-8 -*-

from os.path import basename, dirname
import tempfile
from datetime import timedelta

from qgis.core import *
from qgis.gui import QgsMessageBar
from PyQt4 import QtGui, uic
from PyQt4.QtGui import *
from PyQt4.QtCore import *
from qgis.analysis import QgsGeometryAnalyzer
from qgis.analysis import QgsZonalStatistics
import processing
from processing.tools.system import getTempFilename
import math

import os
from os.path import abspath
import numpy
from osgeo import gdal 
import ogr
import csv

from db import Oracle, Sqlite
from QgisPDS.connections import create_connection
from QgisPDS.utils import to_unicode, StrictInit, lonlat_add_list
from bblInit import *
from qgis_processing import *
from tig_projection import *
from qgis_pds_wellFilter import QgisWellFilterDialog

class Item(StrictInit):
    id = None
    begin = None
    end = None
    value = None


def split(times, items):
    items = iter(items)
    item = next(items, None)
    if item is None:
        return
    begin = None
    cur = []
    ids = []
    value_by_id = {}
    for end in times:
        if begin is not None:
            assert begin < end
            for i in xrange(len(cur) - 1, -1, -1):
                if cur[i].end <= begin:
                    del cur[i]
            while item is not None and item.begin == begin:
                assert end <= item.end
                cur.append(item)
                item = next(items, None)
            value_by_id.clear()
            del ids[:]
            for x in cur:
                value = x.value * (end - begin) / (x.end - x.begin)
                try:
                    value_by_id[x.id] += value
                except KeyError:
                    value_by_id[x.id] = value
                    ids.append(x.id)
            layer = [
                Item(
                    id=id,
                    begin=begin,
                    end=end,
                    value=value_by_id[id],
                )
                for id in ids
            ]
            yield layer
        begin = end


class Well(StrictInit):
    id = None
    name = None
    pos = None
    buffer = None

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'qgis_pds_residuals_base.ui'))

class QgisPDSResidualDialog(QtGui.QDialog, FORM_CLASS):

    def __init__(self, project, iface, parent=None):
        """Constructor."""
        super(QgisPDSResidualDialog, self).__init__(parent)       

        self.oilKindId = u'crude oil'
        self.gasKindId = u'free gas'

        self.iface = iface
        self.project = project
        self.plugin_dir = os.path.dirname(__file__)
        self.productionKind = self.oilKindId

        self.temp_path = tempfile.gettempdir()
        self.project_path = QgsProject.instance().homePath()
        
        self.reservoir_element_group = 0
        self.reservoir_name = ''
        self.currentZonation = 0
        self.currentZone = 0
        self.dateFormat = u'dd/MM/yyyy HH:mm:ss'

        self.wellFilter = []
        selectedParams = QSettings().value("/PDS/WellFilter/SelectedParameters", [])
        if selectedParams:
            self.wellFilter = [int(z) for z in selectedParams]

        self.connection = create_connection(self.project)
        scheme = self.project['project']
        try:           
            self.db = self.connection.get_db(scheme)
        except Exception as e:
            self.iface.messageBar().pushMessage(self.tr("Error"), 
                self.tr(u'Open project {0}: {1}').format(scheme, str(e)), level=QgsMessageBar.CRITICAL)
            return

        self.start_date = QDateTime().currentDateTime().toString(u'yyyy-MM-dd HH:mm:ss')
        self.endDate = QDateTime().currentDateTime().toString(u'yyyy-MM-dd HH:mm:ss')
        
        self.setupUi(self)

        self.proj4String = 'epsg:4326'
        try:
            self.tig_projections = TigProjections(db=self.db)
            proj = self.tig_projections.get_projection(self.tig_projections.default_projection_id)
            if proj is not None:
                self.proj4String = 'PROJ4:'+proj.qgis_string
                destSrc = QgsCoordinateReferenceSystem()
                destSrc.createFromProj4(proj.qgis_string)
                sourceCrs = QgsCoordinateReferenceSystem('epsg:4326')
                self.xform = QgsCoordinateTransform(sourceCrs, destSrc)
        except Exception as e:
            self.iface.messageBar().pushMessage(self.tr("Error"),
                                                self.tr(u'Project projection read error {0}: {1}').format(
                                                scheme, str(e)),
                                                level=QgsMessageBar.CRITICAL)
            return

        self.mWellCoordComboBox.addItem(self.tr(u'Well top'), u'well_top')
        self.mWellCoordComboBox.addItem(self.tr(u'Well bottom'), u'well_bottom')
        self.mWellCoordComboBox.addItem(self.tr(u'Zone intersection'), u'well_zone')
        self.mWellCoordComboBox.setCurrentIndex(0)



        validator = QDoubleValidator(self)
        validator.setRange(0, 1, 6)
        self.mMaxRadiusLineEdit.setValidator(validator)
        self.mPorosityLineEdit.setValidator(validator)
        self.mSaturationLineEdit.setValidator(validator)
        self.mShrinkageLineEdit.setValidator(validator)

        self.fillRasterLayers()

        self.restoreSettings()

        self.fillReservoirs()
        self.fillZonations()

        self.mStartDateComboBox.addItem(str(self.start_date), self.start_date)
        self.mEndDateComboBox.addItem(str(self.endDate), self.endDate)

        self.setZoneWidgetVisible()

        # self.setStartDate()
        # self.setEndDate()

    def setZoneWidgetVisible(self):
        self.mZoneLabel.setVisible(self.well_coords == 'well_zone')
        self.mZonationLabel.setVisible(self.well_coords == 'well_zone')
        self.mZoneComboBox.setVisible(self.well_coords == 'well_zone')
        self.mZonationComboBox.setVisible(self.well_coords == 'well_zone')




#Residual calculaion
    @property
    def sql_args(self):
        ret = {}

        ret['bsasc_source'] = self.productionKind
        ret['reservoir_element_group_id'] = self.reservoir_element_group
        ret['start_date'] = self.mStartDateComboBox.itemData(self.mStartDateComboBox.currentIndex())
        ret['end_date'] = self.mEndDateComboBox.itemData(self.mEndDateComboBox.currentIndex())

        return ret

    @property
    def well_coords(self):
        return self.mWellCoordComboBox.itemData(self.mWellCoordComboBox.currentIndex())

    @property
    def zonationId(self):
        idx = self.mZonationComboBox.currentIndex()
        if idx < 0:
            return 0
        else:
            return int(self.mZonationComboBox.itemData(idx))

    @property
    def zoneId(self):
        idx = self.mZoneComboBox.currentIndex()
        if idx < 0:
            return 0
        else:
            return int(self.mZoneComboBox.itemData(idx)[0])

    @property
    def zoneOrder(self):
        idx = self.mZoneComboBox.currentIndex()
        if idx < 0:
            return 0
        else:
            return int(self.mZoneComboBox.itemData(idx)[2])


    @property
    def input_raster(self):
        layerName = self.mNPTSurfaceComboBox.itemData(self.mNPTSurfaceComboBox.currentIndex())
        lay = QgsMapLayerRegistry.instance().mapLayer(layerName)
        if lay is not None:
            return lay
        else:
            return None

    # @cached_property
    # def max_radius(self):
    #     return float(self.mMaxRadiusLineEdit.text())

    # @property
    # def porosity(self):
    #     return float(self.mPorosityLineEdit.text())

    # @property
    # def saturation(self):
    #     return float(self.mSaturationLineEdit.text())

    # @property
    # def shrinkage(self):
    #     return float(self.mShrinkageLineEdit.text())

    def get_value_multiplier_oil(self):
        return 1 / (self.shrinkage * self.porosity * self.saturation)

    def get_value_multiplier_gas(self):
        return self.shrinkage / (self.porosity * self.saturation)

    @property
    def value_multiplier_methods(self):
        return {
            self.oilKindId: self.get_value_multiplier_oil,
            self.gasKindId: self.get_value_multiplier_gas,
        }

    @property
    def value_multiplier(self):
        return self.value_multiplier_methods[self.productionKind]()

    @property
    def initial_multiplier(self):
        return self.porosity * self.saturation

    @property
    def wells_sql(self):
        return self.get_sql(u'Residual_wells.sql')

    def get_well_tops(self):
        for row in self.db.execute(self.wells_sql, **self.sql_args):
            pt = QgsPoint(row[2], row[3])
            if self.xform:
                pt = self.xform.transform(pt)
            yield Well(
                id=int(row[0]),
                name=row[1].decode('utf-8'),
                pos=(pt.x(), pt.y()),
            )

    @property
    def well_bottoms_sql(self):
        return self.get_sql(u'Residual_well_bottoms.sql')

    @property
    def well_zones_sql(self):
        return self.get_sql(u'Residual_ZonationCoords.sql')

    def get_well_bottoms(self):
        for row in self.db.execute(self.well_bottoms_sql, **self.sql_args):
            pt = QgsPoint(row[2], row[3])
            if self.xform:
                pt = self.xform.transform(pt)
            pos=(pt.x(), pt.y())
            blob_x = row[4]
            blob_y = row[5]
            if blob_x is not None and blob_y is not None:
                xx = numpy.fromstring(self.db.blobToString(blob_x), '>f').astype('d')
                yy = numpy.fromstring(self.db.blobToString(blob_y), '>f').astype('d')
                size_x = len(xx)
                size_y = len(yy)

                # size_x = blob_x.size()
                # size_y = blob_y.size()
                if size_x == size_y and size_x >= 0:
                    # delta_x = numpy.fromstring(self.db.blobToString(blob_x, size_x - 3), '>f').astype('d')[0]
                    # delta_y = numpy.fromstring(self.db.blobToString(blob_y, size_y - 3), '>f').astype('d')[0]
                    delta_x = xx[size_x-1]
                    delta_y = yy[size_y-1]
                    pos = (pos[0]+delta_x, pos[1]+delta_y)
            yield Well(
                id=int(row[0]),
                name=row[1].decode('utf-8'),
                pos=pos,
            )

    def _getCoords(self, lon, lat, idZonation, idZone, wellId):
        def read_floats(index):
            return numpy.fromstring(self.db.blobToString(input_row[index]), '>f').astype('d')


        sql = self.get_sql('ZonationCoords.sql')
        records = self.db.execute(sql
                                  , well_id=wellId
                                  , zonation_id=idZonation
                                  , zone_id=idZone
                                  , interval_order=None
                                  , only_pub_devi=None
                                  )

        newCoords = (lon, lat)

        if records:
            for input_row in records:
                devi_id=input_row[15]
                if devi_id is None:
                    self.no_devi_wells.append(wellId)
                else:
                    x = read_floats(16)
                    y = read_floats(17)
                    md = read_floats(18)
                    depth = input_row[3]
    
                    newCoords = self._calcOffset(lon, lat, x, y, md, depth)

        return newCoords


    def _calcOffset(self, lon, lat, x, y, md, depth):
        jp = None
        lastIdx = len(x) - 1
        for ip in xrange(len(x) - 1):
            if md[ip] <= depth <= md[ip + 1]:
                jp = ip

        xPosition = 0
        yPosition = 0
        if jp is not None:
            rinterp = (depth - md[jp]) / (md[jp + 1] - md[jp])
            xPosition = x[jp] + rinterp * (x[jp + 1] - x[jp])
            yPosition = y[jp] + rinterp * (y[jp + 1] - y[jp])
        elif depth >= md[lastIdx]:
            xPosition = x[lastIdx]
            yPosition = y[lastIdx]

        return (lon+xPosition, lat+yPosition)

    @property
    def well_coords_methods(self):
        return {
            'well_top': self.get_well_tops,
            'well_bottom': self.get_well_bottoms,
            'well_zone': self.get_well_tops
        }

    def get_all_wells(self):
        get_raw_wells = self.well_coords_methods[self.well_coords]
        wells = {}
        unique_positions = set()
        angle = 0
        for well in get_raw_wells():
            pos = well.pos
            if self.well_coords == 'well_zone':
                pos = self._getCoords(pos[0], pos[1], self.zonationId, self.zoneId, well.name)
            if pos in unique_positions:
                radius = 1e-5  # ~ 1m
                while True:
                    new_pos = (pos[0] + radius * math.cos(angle), pos[1] + radius * math.sin(angle))
                    angle = (angle + 1) % math.pi
                    if new_pos not in unique_positions:
                        pos = new_pos
                        break
            unique_positions.add(pos)
            wells[well.id] = Well(id=well.id, name=well.name, pos=pos)
        return wells

    @property 
    def query_sql(self):
        if type(self.db) is Sqlite:
            return self.get_sql('Residual_sqlite.sql')
        else:
            return self.get_sql('Residual.sql')

    @property
    def times_sql(self):
        if type(self.db) is Sqlite:
            return self.get_sql('Residual_times_sqlite.sql')
        else:
            return self.get_sql('Residual_times.sql')

    def get_times(self):
        times = []
        first_time = None
        sql = self.times_sql
        #     .format(self.db.fieldToDate('tt.PROD_START_TIME'),
        #                             self.db.fieldToDate('tt.PROD_END_TIME', '+1'))
        # print sql
        for time in self.db.execute_scalar(sql, **self.sql_args):
            if first_time is None:
                first_time = time
                times.append(0)
            else:
                times.append((time - first_time).total_seconds())
        return first_time, times

    def get_events(self, start_time):
        useFilter = self.mUseWellFilterCheckBox.isChecked()
        for row in self.db.execute(self.query_sql, **self.sql_args):
            useWell = True
            if useFilter:
                useWell = row[0] in self.wellFilter
            if useWell:
                yield Item(
                    id=int(row[0]),
                    begin=(row[1] - start_time).total_seconds(),
                    end=(row[2] - start_time).total_seconds(),
                    value=row[3],
                )

    @property
    def out_feature_path(self):
        return self.mOutFeatureClassLineEdit.text()

    @property
    def out_raster_path(self):
        result = '_raster.tif'
        fn = self.mOutFeatureClassLineEdit.text()
        if fn:
            result = os.path.splitext(fn)[0] + result

        return result

    @property
    def out_nfpt_path(self):
        if self.input_raster :
            fn = self.input_raster.source()
            if fn:
                return os.path.splitext(fn)[0]+'_residuals.shp'

        return 'Unknown_residuals.shp'

    @property
    def out_production_raster_path(self):
        result = '_production_raster.tif'
        fn = self.mOutFeatureClassLineEdit.text()
        if fn:
            result = os.path.splitext(fn)[0] + result

        return result

    @property
    def initial_raster_path(self):
        result = '_initial_raster.tif'
        fn = self.mOutFeatureClassLineEdit.text()
        if fn:
            result = os.path.splitext(fn)[0] + result

        return result

    @cached_property
    def temp_polygons_path(self):
        nn = getTempFilename('shp')
        return nn


    @property
    def temp_points_path(self):
        return self.temp_path + '/temp_points.shp'

    @property 
    def maxRadius(self):
        dist = QgsDistanceArea()
        dist.setEllipsoid('WGS84')
        dist.setEllipsoidalMode(True)

        val = float(self.mMaxRadiusLineEdit.text())

        mr = val*1000 # dist.convertLengthMeasurement(val*1000, 2) #km
        if self.mRaduisUnitComboBox.currentIndex() == 1: #m
            mr = val # dist.convertLengthMeasurement(val, 2)
        elif self.mRaduisUnitComboBox.currentIndex() == 1: #degrees
            mr = dist.convertLengthMeasurement(val, 2)
        return mr


    def create_temp_points(self):
        uri = "Point?crs={}".format(self.proj4String)
        uri += "&field=ID:integer"
        self.temp_points = QgsVectorLayer(uri, "temp_points", "memory")
        QgsMapLayerRegistry.instance().addMapLayer(self.temp_points)
        self.iface.legendInterface().setLayerVisible(self.temp_points, False)

    def create_temp_raster_polygons(self):
        uri = "Polygon?crs={}".format(self.proj4String)
        uri += "&field=ID:integer"
        self.temp_raster_polygons_path = QgsVectorLayer(uri, "temp_raster_polygons", "memory")
        # QgsMapLayerRegistry.instance().addMapLayer(self.temp_raster_polygons_path)

    def create_output_nfpt_class(self):
        uri = "Point?crs={}".format(self.proj4String)
        uri += "&field=ID:integer"
        uri += "&field=Well:string"
        self.nfpt_output_class = QgsVectorLayer(uri, "TEMP_NFPT", "memory")
        QgsMapLayerRegistry.instance().addMapLayer(self.nfpt_output_class)


    def DeleteRows_management(self, layer):
        with edit(layer):   
            for feat in layer.getFeatures():
                layer.deleteFeature(feat.id())

    def copy_wells_to_temp_points(self, wells):
        self.DeleteRows_management(self.temp_points)
        with edit(self.temp_points):
            f = QgsFeature(self.temp_points.fields())
            for well in wells:
                geom = QgsGeometry.fromPoint(QgsPoint(well.pos[0], well.pos[1]))
                f.setGeometry(geom)
                f.setAttribute('ID', well.id)
                self.temp_points.addFeatures([f])
        self.temp_points.removeSelection()


    def copy_wells_to_residual_points(self, wells):
        with edit(self.nfpt_output_class):
            f = QgsFeature(self.nfpt_output_class.fields())
            for wellId in wells:
                well = wells[wellId]
                geom = QgsGeometry.fromPoint(QgsPoint(well.pos[0], well.pos[1]))
                f.setGeometry(geom)
                f.setAttribute('ID', well.id)
                f.setAttribute('Well', well.name)
                self.nfpt_output_class.addFeatures([f])
        self.nfpt_output_class.removeSelection()


    def buffer_wells(self, wells, mr):
        for well in wells:
            geom = QgsGeometry.fromPoint(QgsPoint(well.pos[0], well.pos[1]))
            well.buffer = geom.buffer(mr, 50)
            

#Execute
    def execute(self):
        #Set variables
        self.porosity = float(self.mPorosityLineEdit.text())
        self.saturation = float(self.mSaturationLineEdit.text())
        self.shrinkage = float(self.mShrinkageLineEdit.text())

        #Open input raster
        self.progress.setFormat('Loading input raster')
        raster_lay = self.input_raster
        if not raster_lay:
            self.iface.messageBar().pushMessage(self.tr("Error"),
                                                self.tr(u'Input NPT raster is not selected'),
                                                level=QgsMessageBar.CRITICAL)
            return
        extent = raster_lay.extent()
        gdal_input_raster = gdal.Open(raster_lay.source())
        rasterCrs=raster_lay.crs()

        csvFileName = os.path.splitext(self.out_feature_path)[0] + '.csv'
        out_pipe = open(csvFileName, "wb")
        self.csvWriter = csv.writer(out_pipe)
        self.csvWriter.writerow(['attribute', 'value'])

        input_raster = numpy.array(gdal_input_raster.GetRasterBand(1).ReadAsArray()) 
        assert len(input_raster.shape) == 2

        noDataValue = gdal_input_raster.GetRasterBand(1).GetNoDataValue()
        saved_input_raster = numpy.copy(input_raster)
        input_raster[input_raster == noDataValue] = 0
        # saved_input_raster = numpy.copy(input_raster)

        cols = gdal_input_raster.RasterXSize
        rows = gdal_input_raster.RasterYSize

        (min_x, step_x, x_rotation, min_y, y_rotation, step_y) = gdal_input_raster.GetGeoTransform()

        cell_area = step_x * step_y * -1
        # self.addMessage(self.tr('Input raster volume: m^3'), input_raster.sum() * cell_area * self.initial_multiplier)
        self.csvWriter.writerow([self.tr('Input raster volume: m^3'), input_raster.sum() * cell_area * self.initial_multiplier])
        self.progress.setValue(0)

        self.progress.setFormat( self.tr('Creating temp feature class for polygons...') )
        self.create_temp_raster_polygons()

        self.progress.setFormat( self.tr('Creating temp feature class...') )
        self.create_temp_points()

        self.progress.setFormat( self.tr('Loading wells...') )
        all_wells = self.get_all_wells()
        
        self.progress.setFormat( self.tr('Copying wells to temp feature class...') )
        self.copy_wells_to_temp_points(all_wells.itervalues())

        self.progress.setFormat( self.tr('Buffering wells...') )
        # QgsGeometryAnalyzer().buffer(self.temp_points_path, self.temp_polygons_path, 0.02, False, False, -1)
        self.buffer_wells(all_wells.itervalues(), self.maxRadius)

        self.progress.setFormat( self.tr('Creating output feature class...') )
        uri = "Polygon?crs={}".format(self.proj4String)
        uri += "&field=ID:integer&field=NAME:string&field=VALUE:double&field=START_DATE:date&field=END_DATE:date"
        self.out_path = QgsVectorLayer(uri, basename(self.out_feature_path), "memory")
        QgsMapLayerRegistry.instance().addMapLayer(self.out_path)
        self.iface.legendInterface().setLayerVisible(self.out_path, False)

        self.progress.setFormat( self.tr('Loading intervals...') )
        first_time, times = self.get_times()

        events = self.get_events(first_time)    

        self.progress.setFormat(self.tr('Processing intervals %p%'))

        wellWithProduction = {}
        production_volume = 0
        intervals_count = len(times) - 1
        for i, items in enumerate(split(times, events)):
            if items:
                # print  'Processing interval {} of {}...'.format(i + 1, intervals_count) 
                progr = float(i+1)/float(intervals_count) * 100
                self.progress.setValue(progr)
                QApplication.processEvents()

                items_by_id = {item.id: item for item in items}
                item_index_by_id = {item.id: i + 1 for i, item in enumerate(items)}
                for item in items:
                    production_volume += item.value

                self.DeleteRows_management(self.temp_points)
                with edit(self.temp_points):
                    f = QgsFeature(self.temp_points.fields())
                    for item in items:
                        well = all_wells[item.id]
                        pos = well.pos
                        geom = QgsGeometry.fromPoint(QgsPoint(pos[0], pos[1]))
                        f.setGeometry(geom)
                        f.setAttribute('ID', item.id)
                        self.temp_points.addFeatures([f])
                    self.temp_points.removeSelection()

                # processing.runalg("qgis:voronoipolygons", self.temp_points, 50, self.temp_polygons_path, progress=self)

                self.DeleteRows_management(self.temp_raster_polygons_path)
                if self.temp_points.featureCount() > 1:
                    extStr = '%f,%f,%f,%f' % (extent.xMinimum(), extent.xMaximum(), extent.yMinimum(), extent.yMaximum())
                    processing.runalg("grass7:v.voronoi", self.temp_points, 'False', 'False', extStr,
                                      -1, 0.000100, 3, self.temp_polygons_path, progress=self)

                    temp_polygons = QgsVectorLayer(self.temp_polygons_path, 'temp_polygons', 'ogr')
                    with edit(self.temp_raster_polygons_path):
                        f_raster = QgsFeature(self.temp_raster_polygons_path.fields())
                        with edit(self.out_path):
                            f_out = QgsFeature(self.out_path.fields())
                            for f_voronoy in temp_polygons.getFeatures():
                                well = all_wells[f_voronoy[0]]
                                wellWithProduction[f_voronoy[0]] = well
                                item = items_by_id[well.id]
                                voronoi_poly = f_voronoy.geometry()
                                buffer_poly = well.buffer
                                clipped_poly = voronoi_poly.intersection(buffer_poly)
                                # add output feature
                                f_out.setGeometry(clipped_poly)
                                f_out.setAttribute('ID', well.id)
                                f_out.setAttribute('NAME', well.name)
                                f_out.setAttribute('VALUE', item.value)
                                f_out.setAttribute('START_DATE', (first_time+timedelta(seconds=item.begin)).strftime('%Y-%m-%d') )
                                f_out.setAttribute('END_DATE', (first_time + timedelta(seconds=item.end) - timedelta(days=1)).strftime('%Y-%m-%d') )
                                self.out_path.addFeatures([f_out])
                                #add to raster polygon
                                f_raster.setGeometry(clipped_poly)
                                f_raster.setAttribute('ID', item_index_by_id[well.id])
                                self.temp_raster_polygons_path.addFeatures([f_raster])
                else:
                    with edit(self.temp_raster_polygons_path):
                        f_raster = QgsFeature(self.temp_raster_polygons_path.fields())
                        with edit(self.out_path):
                            f_out = QgsFeature(self.out_path.fields())
                            for item in items:
                                well = all_wells[item.id]
                                wellWithProduction[item.id] = well
                                clipped_poly = well.buffer
                                # add output feature
                                f_out.setGeometry(clipped_poly)
                                f_out.setAttribute('ID', well.id)
                                f_out.setAttribute('NAME', well.name)
                                f_out.setAttribute('VALUE', item.value)
                                f_out.setAttribute('START_DATE',
                                                   (first_time + timedelta(seconds=item.begin)).strftime('%Y-%m-%d'))
                                f_out.setAttribute('END_DATE',
                                                   (first_time + timedelta(seconds=item.end) - timedelta(days=1)).strftime(
                                                       '%Y-%m-%d'))
                                self.out_path.addFeatures([f_out])
                                # add to raster polygon
                                f_raster.setGeometry(clipped_poly)
                                f_raster.setAttribute('ID', item_index_by_id[well.id])
                                self.temp_raster_polygons_path.addFeatures([f_raster])


                self.temp_raster_polygons_path.removeSelection()
                temp_polygons = None

                r = QgisProcessing()
                r.rasterizeLayer(self.temp_raster_polygons_path, gdal_input_raster, rasterCrs, cols, rows)

                def process(input_raster):
                    gdal_layer_raster = gdal.Open(self.temp_path + '/temp_raster.tif')
                    band = gdal_layer_raster.GetRasterBand(1)
                    layer_raster = numpy.array(band.ReadAsArray()) 
                    noDataValue = band.GetNoDataValue()
                    layer_raster[layer_raster == noDataValue] = 0
                    assert len(layer_raster.shape) == 2
                    if layer_raster.shape[0] < input_raster.shape[0] or layer_raster.shape[1] < input_raster.shape[1]:
                        self.iface.messageBar().pushMessage(self.tr("Error"),
                                                self.tr(u'PolygonToRaster_conversion made raster of size {0} which is less than input raster of size {1}').format(
                                                layer_raster.shape, input_raster.shape),
                                                level=QgsMessageBar.CRITICAL)
                        return False
                    if layer_raster.shape != input_raster.shape:
                        layer_raster = layer_raster[-input_raster.shape[0]:, -input_raster.shape[1]:]
                    layer_raster[input_raster <= 0] = 0
                    flattened = layer_raster.ravel()
                    counts = numpy.bincount(flattened)
                    sums = numpy.bincount(flattened, input_raster.ravel())
                    values = numpy.zeros(counts.size, dtype='f')
                    for i in xrange(1, counts.size):
                        values[i] = items[i - 1].value
                    values *= (self.value_multiplier / cell_area)
                    multipliers = ((sums - values) / sums).astype('f')
                    multipliers[0] = 1
                    multipliers_raster = multipliers[layer_raster]
                    input_raster *= multipliers_raster
                    return True

                if not process(input_raster):
                    return
        
        self.csvWriter.writerow(['Subsurface production volume: m^3', production_volume * self.value_multiplier * self.initial_multiplier])
        self.csvWriter.writerow(['Surface production volume: m^3', production_volume])
        self.csvWriter.writerow(['Output raster volume: m^3', input_raster.sum() * cell_area * self.initial_multiplier])

        out_raster = input_raster * self.initial_multiplier

        r = QgisProcessing()
        r.saveRaster(self.out_raster_path, gdal_input_raster.GetGeoTransform(), 0, rasterCrs.toWkt(), cols, rows, out_raster)
        layer = QgsRasterLayer(self.out_raster_path, basename(self.out_raster_path))
        if layer is None:
            self.iface.messageBar().pushMessage(self.tr("Error"),
                                                self.tr(u'Raster layer add error'),
                                                level=QgsMessageBar.CRITICAL)
        else:
            QgsMapLayerRegistry.instance().addMapLayer(layer)

        out_raster = numpy.copy(saved_input_raster)
        for i in xrange(out_raster.shape[0]):
            for j in xrange(out_raster.shape[1]):
                if out_raster[i,j] != noDataValue:
                    out_raster[i, j] = (out_raster[i, j] - input_raster[i, j] )* self.initial_multiplier
        r.saveRaster(self.out_production_raster_path, gdal_input_raster.GetGeoTransform(), noDataValue, rasterCrs.toWkt(), cols, rows,
                     out_raster)
        layer = QgsRasterLayer(self.out_production_raster_path, basename(self.out_production_raster_path))
        if layer is None:
            self.iface.messageBar().pushMessage(self.tr("Error"),
                                                self.tr(u'Raster layer add error'),
                                                level=QgsMessageBar.CRITICAL)
        else:
            QgsMapLayerRegistry.instance().addMapLayer(layer)

        out_raster = numpy.copy(saved_input_raster)
        for i in xrange(out_raster.shape[0]):
            for j in xrange(out_raster.shape[1]):
                if out_raster[i, j] != noDataValue:
                    out_raster[i, j] = out_raster[i, j] * self.initial_multiplier
        r.saveRaster(self.initial_raster_path, gdal_input_raster.GetGeoTransform(), noDataValue, rasterCrs.toWkt(), cols, rows,
                     out_raster)
        layer = QgsRasterLayer(self.initial_raster_path, basename(self.initial_raster_path))
        if layer is None:
            self.iface.messageBar().pushMessage(self.tr("Error"),
                                                self.tr(u'Raster layer add error'),
                                                level=QgsMessageBar.CRITICAL)
        else:
            QgsMapLayerRegistry.instance().addMapLayer(layer)

        QgsMapLayerRegistry.instance().removeMapLayers( [self.temp_points.id()] )

        del gdal_input_raster

        out_pipe.close()

        #Create residual polygons
        self.progress.setFormat(self.tr('Creating residuals feature class...'))
        self.create_output_nfpt_class()
        self.progress.setFormat(self.tr('Copying wells to residuals feature class...'))
        self.copy_wells_to_residual_points(wellWithProduction)
        extStr = '%f,%f,%f,%f' % (extent.xMinimum(), extent.xMaximum(), extent.yMinimum(), extent.yMaximum())
        try:
            processing.runalg("grass7:v.voronoi", self.nfpt_output_class, 'False', 'False', extStr,
                              -1, 0.000100, 3, self.out_nfpt_path, progress=self)
            layer = QgsVectorLayer(self.out_nfpt_path, basename(self.out_nfpt_path), 'ogr')
            if layer:
                QgsMapLayerRegistry.instance().addMapLayer(layer)
                # usage - QgsZonalStatistics (QgsVectorLayer *polygonLayer, const QString &rasterFile, const QString &attributePrefix="", int rasterBand=1)
                zoneStat = QgsZonalStatistics(layer, self.out_production_raster_path, '', 1, QgsZonalStatistics.Sum)
                zoneStat.calculateStatistics(None)
            else:
                self.iface.messageBar().pushMessage(self.tr("Error"),
                                                    self.tr(u'Residuals layer add error'),
                                                    level=QgsMessageBar.CRITICAL)
            QgsMapLayerRegistry.instance().removeMapLayers([self.nfpt_output_class.id()])
        except Exception as e:
            self.iface.messageBar().pushMessage(self.tr("Error"),
                                                str(e), level=QgsMessageBar.CRITICAL)

        #add CSV layer
        fileparts = os.path.split(csvFileName)
        try:
            layerList = QgsMapLayerRegistry.instance().mapLayersByName(fileparts[1])
            QgsMapLayerRegistry.instance().removeMapLayers(layerList)

            uri = 'file:///%s?type=csv&geomType=none&subsetIndex=no&watchFile=no' % (csvFileName)
            bh = QgsVectorLayer(uri, fileparts[1], "delimitedtext")
            QgsMapLayerRegistry.instance().addMapLayer(bh)
        except Exception as e:
            self.iface.messageBar().pushMessage(self.tr("Error"),
                                                str(e), level=QgsMessageBar.CRITICAL)

        return

#Methods
    def addMessage(self, fmt, *a, **kw):
        print fmt.format(*a, **kw)

    def setPercentage(self, val):
        return

    def setText(self, text):
        return

    def error(self, text):
        print text

    def setCommand(self, text):
        return

    def setConsoleInfo(self, text):
        return

    def toMeters(self, sourceCrs, lon, lat, dx, dy):
        meterCrs = QgsCoordinateReferenceSystem()
        meterCrs.createFromProj4('+proj=tmerc +lon_0={} +k=1 +x_0=0 +y_0=0 +ellps=WGS84 +datum=WGS84 +units=m +no_defs'.format(lon))

        toM = QgsCoordinateTransform(sourceCrs, meterCrs)
        geoPt = QgsPoint(dx, dy)
        mPt = toM.transform(geoPt)
        return mPt.x(), mPt.y()

    def get_sql(self, value):
        sql_file_path = os.path.join(self.plugin_dir, 'db', value)
        with open(sql_file_path, 'rb') as f:
            return f.read().decode('utf-8')

    def execSql(self, sqlFileName, **kwargs):
        records = []
        if self.db is None:
            return records

        sqlFile = os.path.join(self.plugin_dir, 'db', sqlFileName)
        if os.path.exists(sqlFile):
            f = open(sqlFile, 'r')
            sql = f.read().decode('utf-8')
            f.close()

            records = self.db.execute(sql, **kwargs)

        return records


    def fillReservoirs(self):
        self.mReservoirComboBox.clear()
 
        reservoirs = self.execSql('Residual_reservoir_element_group.sql', bsasc_source=self.productionKind)
        if reservoirs is not None:
            idx = 0
            for s, name in reservoirs:
                self.mReservoirComboBox.addItem(to_unicode("".join(name)), s)
                if s == self.reservoir_element_group:
                    idx = self.mReservoirComboBox.count()-1

            self.mReservoirComboBox.setCurrentIndex(idx)

    def setStartDate(self):
        self.mStartDateComboBox.clear()

        # sql = self.get_sql('Residual_start_date.sql').format(self.db.formatDateField('PROD_START_TIME'))
        # startDates = self.db.execute(sql, bsasc_source=self.productionKind,
        #                             reservoir_element_group_id=self.reservoir_element_group)
        startDates = self.execSql('Residual_start_date.sql', bsasc_source=self.productionKind,
                                    reservoir_element_group_id=self.reservoir_element_group)

        if startDates is not None:
            idx = 0
            for s, ss in startDates:
                name = s.strftime('%d.%m.%Y') #QDateTime.fromString(ss, self.dateFormat).toString('dd.MM.yyyy')
                self.mStartDateComboBox.addItem(name, s)
                if s == self.start_date:
                    idx = self.mStartDateComboBox.count()-1

            self.mStartDateComboBox.setCurrentIndex(idx)


    def setEndDate(self):
        self.mEndDateComboBox.clear()

        # sql = self.get_sql('Residual_end_date.sql').format(self.db.formatDateField('PROD_END_TIME'))
        # endDates = self.db.execute(sql, bsasc_source=self.productionKind,
        #                         reservoir_element_group_id=self.reservoir_element_group,
        #                         start_date=self.mStartDateComboBox.itemData(self.mStartDateComboBox.currentIndex()))
        endDates = self.execSql('Residual_end_date.sql', bsasc_source=self.productionKind,
                                    reservoir_element_group_id=self.reservoir_element_group,
                                    start_date=self.mStartDateComboBox.itemData(self.mStartDateComboBox.currentIndex()))

        if endDates is not None:
            idx = 0
            for s, ss in endDates:
                name = s.strftime('%d.%m.%Y') #QDateTime.fromString(ss, self.dateFormat).toString('dd.MM.yyyy')
                self.mEndDateComboBox.addItem(name, s)
                if s == self.endDate:
                    idx = self.mEndDateComboBox.count() - 1

            self.mEndDateComboBox.setCurrentIndex(idx)

            
    def fillRasterLayers(self):
        self.mNPTSurfaceComboBox.clear()

        layers = self.iface.legendInterface().layers()

        for layer in layers:
            layerType = layer.type()
            if layerType == QgsMapLayer.RasterLayer:
                self.mNPTSurfaceComboBox.addItem(layer.name(), layer.id())

    def fillZonations(self):
        self.mZonationComboBox.clear()
        records = self.db.execute(self.get_sql(u'ZonationParams_zonation.sql'))
        if records :
            for id, desc in records:
                self.mZonationComboBox.addItem(to_unicode("".join(desc)), id)
                if id == self.currentZonation:
                    self.mZonationComboBox.setCurrentIndex(self.mZonationComboBox.count()-1)

    def fillZones(self):
        self.mZoneComboBox.clear()
        records = self.db.execute(self.get_sql(u'ZonationParams_zone.sql'), zonation_id=self.zonationId)
        if records:
            for i_id, i_desc, i_name, i_order, i_level in records:
                item = QListWidgetItem(to_unicode(i_desc))
                item.setData(Qt.UserRole, [i_id, i_name, i_order, i_level])
                self.mZoneComboBox.addItem(item)
                #self.mZoneComboBox.addItem(to_unicode("".join(i_desc)), id)
                if i_id == self.currentZone:
                    self.mZoneComboBox.setCurrentIndex(self.mZoneComboBox.count() - 1)
            

    def saveSettings(self):
        settings = QSettings()

        settings.setValue('PDS/Residuals/productionKind', self.productionKind)
        settings.setValue('PDS/Residuals/currentComponent', self.mComponentComboBox.currentIndex())
        settings.setValue('PDS/Residuals/well_coords', self.mWellCoordComboBox.currentIndex())
        settings.setValue('PDS/Residuals/inputRasterName', self.mNPTSurfaceComboBox.currentText())

        settings.setValue('PDS/Residuals/outFeatureClass', self.mOutFeatureClassLineEdit.text())
        # settings.setValue('PDS/Residuals/outRaster', self.mOutRasterLineEdit.text())
        # settings.setValue('PDS/Residuals/initialRaster', self.mInitialRasterLineEdit.text())
        # settings.setValue('PDS/Residuals/productionRaster', self.mProductionRasterLineEdit.text())

        settings.setValue('PDS/Residuals/MaxRadius', self.mMaxRadiusLineEdit.text())
        settings.setValue('PDS/RaduisUnitComboBox', self.mRaduisUnitComboBox.currentIndex())
        settings.setValue('PDS/Residuals/Porosity', self.mPorosityLineEdit.text())
        settings.setValue('PDS/Residuals/Saturation', self.mSaturationLineEdit.text())
        settings.setValue('PDS/Residuals/Shrinkage', self.mShrinkageLineEdit.text())

        settings.setValue('PDS/Residuals/reservoir', self.reservoir_element_group)
        settings.setValue('PDS/Residuals/reservoir_name', self.reservoir_name)
        settings.setValue('PDS/Residuals/start_date', self.start_date)
        settings.setValue('PDS/Residuals/endDate', self.endDate)

        settings.setValue('PDS/zonation', self.zonationId )
        settings.setValue('PDS/zone', self.zoneId)

        settings.setValue('PDS/Residuals/useFilter', int(self.mUseWellFilterCheckBox.isChecked()))



    def restoreSettings(self):
        settings = QSettings()

        self.productionKind = settings.value('PDS/Residuals/productionKind', self.oilKindId )
        self.mComponentComboBox.setCurrentIndex( int(settings.value('PDS/Residuals/currentComponent', 0)) )
        self.mWellCoordComboBox.setCurrentIndex(int(settings.value('PDS/Residuals/well_coords', 0)))
        self.mNPTSurfaceComboBox.setCurrentIndex( self.mNPTSurfaceComboBox.findText( settings.value('PDS/Residuals/inputRasterName') ))

        self.mOutFeatureClassLineEdit.setText(settings.value('PDS/Residuals/outFeatureClass', ''))
        # self.mOutRasterLineEdit.setText(settings.value('PDS/Residuals/outRaster', ''))
        # self.mInitialRasterLineEdit.setText(settings.value('PDS/Residuals/initialRaster', ''))
        # self.mProductionRasterLineEdit.setText(settings.value('PDS/Residuals/productionRaster', ''))

        self.mMaxRadiusLineEdit.setText(settings.value('PDS/Residuals/MaxRadius', '1.0'))
        self.mRaduisUnitComboBox.setCurrentIndex( int(settings.value('PDS/RaduisUnitComboBox', 0)))
        self.mPorosityLineEdit.setText( settings.value('PDS/Residuals/Porosity', '1.0'))
        self.mSaturationLineEdit.setText(settings.value('PDS/Residuals/Saturation', '1.0'))
        self.mShrinkageLineEdit.setText(settings.value('PDS/Residuals/Shrinkage', '1.0'))

        self.reservoir_element_group = settings.value('PDS/Residuals/reservoir', 0)
        self.reservoir_name = settings.value('PDS/Residuals/reservoir_name', '')
        self.start_date = settings.value('PDS/Residuals/start_date', '')
        self.endDate = settings.value('PDS/Residuals/endDate', '')

        self.currentZonation = settings.value('PDS/zonation', 0)
        self.currentZone = settings.value('PDS/zone', 0)

        self.on_mNPTSurfaceComboBox_activated('-')

        self.mUseWellFilterCheckBox.setChecked(bool(settings.value('PDS/Residuals/useFilter', 0)))


    def to_oracle_date(self, qDate):
        # dateText = qDate.toString(u'dd/MM/yyyy HH:mm:ss')
        # return "TO_DATE('"+dateText+"', 'DD/MM/YYYY HH24:MI:SS')"
        try:
            return self.db.stringToSqlDate(qDate)
        except:
            return self.db.stringToSqlDate(QDateTime().currentDateTime())

    #SLOTS
    def on_buttonBox_accepted(self):
        
        self.no_devi_wells=[]
        
        self.iface.messageBar().clearWidgets() 
        progressMessageBar = self.iface.messageBar()
        self.progress = QProgressBar()
        self.progress.setMaximum(100) 
        progressMessageBar.pushWidget(self.progress)

        self.currentZonation = self.zonationId
        self.currentZone = self.zoneId
        self.saveSettings()

        self.execute()

        self.iface.messageBar().clearWidgets()
        QgsMessageLog.logMessage(self.tr(u"\t Deviation is private or no deviation in wells: {} ").format(",".join(self.no_devi_wells)), tag="QgisPDS.coordFromZone")
        

    def wellCoordComboBox_activated(self, index):
        self.setZoneWidgetVisible()

    def zonationComboBox_activated(self, index):
        self.fillZones()

    def on_mNPTSurfaceComboBox_activated(self, item):
        if type(item) is int or self.input_raster is None:
            return

        fn = self.input_raster.source()
        if fn:
            if not self.mOutFeatureClassLineEdit.text():
                self.mOutFeatureClassLineEdit.setText( os.path.splitext(fn)[0]+'.shp' )
            # if not self.mOutRasterLineEdit.text():
            #     self.mOutRasterLineEdit.setText( os.path.splitext(fn)[0]+'_raster.tif' )
            # if not self.mInitialRasterLineEdit.text():
            #     self.mInitialRasterLineEdit.setText( os.path.splitext(fn)[0]+'_initial_raster.tif' )
            # if not self.mProductionRasterLineEdit.text():
            #     self.mProductionRasterLineEdit.setText( os.path.splitext(fn)[0]+'_production_raster.tif' )

    def on_mComponentComboBox_activated(self, idx):
        if not type(idx) is int:
            return

        if idx == 0:
            self.productionKind = self.oilKindId
        else:
            self.productionKind = self.gasKindId

        self.fillReservoirs()

    def on_mReservoirComboBox_activated(self, idx):
        if not type(idx) is int:
            return

        self.reservoir_element_group = self.mReservoirComboBox.itemData(idx)
        self.reservoir_name = self.mReservoirComboBox.currentText()
        self.setStartDate()

    def on_mStartDateComboBox_activated(self, idx):
        if not type(idx) is int:
            return

        self.start_date = self.mStartDateComboBox.itemData(idx)
        self.setEndDate()

    def on_mEndDateComboBox_activated(self, idx):
        if not type(idx) is int:
            return

        self.endDate = self.mEndDateComboBox.itemData(idx)

    def on_mOutFeatureClassToolButton_pressed(self):
        fileName = QtGui.QFileDialog.getSaveFileName(self, self.tr("Save layer"), self.mOutFeatureClassLineEdit.text(),
                self.tr("Shape-file ESRI[OGR] (*.shp *.SHP);;All Files (*)"))

        if fileName:
            self.mOutFeatureClassLineEdit.setText(fileName)

    def on_mUseWellFilterCheckBox_toggled(self, toggle):
        self.mWellFilterPushButton.setEnabled(toggle)

    def wellFilterPushButton_clicked(self):
        wells = self.get_well_tops
        dialog = QgisWellFilterDialog(self.iface, wells(), self)
        if dialog.exec_():
            self.wellFilter = dialog.getSelected()

    # def on_mOutResidualToolButton_pressed(self):
    #     fileName = QtGui.QFileDialog.getSaveFileName(self, self.tr("Save layer"), self.mOutRasterLineEdit.text(),
    #             self.tr("GeoTiFF (*.tif *.tiff *.TIF *.TIFF);;All Files (*)"))
    #
    #     if fileName:
    #         self.mOutRasterLineEdit.setText(fileName)
        
   