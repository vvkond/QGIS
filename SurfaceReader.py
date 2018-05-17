# -*- coding: utf-8 -*-

from qgis.core import *
from PyQt4.QtCore import *

from QgisPDS.db import Oracle
from QgisPDS.connections import create_connection
from tig_projection import *
from ReaderBase import *

from osgeo import gdal, osr
import numpy
import os
import struct
import tempfile


class SurfaceReader(ReaderBase):
    def __init__(self):
        super(SurfaceReader, self).__init__()

        self.plugin_dir = os.path.dirname(__file__)
        self.tempdir = tempfile.gettempdir()
        self.groupFile = 'Surface_group.sql'
        self.setFile = 'Surface_set.sql'


    @cached_property
    def windowTitle(self):
        return self.tr('Surfaces')


    def createLayer(self, layerName, pdsProject, groupSetId, defaultValue):
        layer = None

        fileName, layerName = self.readData(groupSetId)

        if fileName is not None:
#            settings = QSettings()
#            oldProjValue = settings.value( "/Projections/defaultBehaviour", "prompt", type=str )
#            settings.setValue( "/Projections/defaultBehaviour", "useProject" )

            layer = QgsRasterLayer(fileName, layerName)
            layer.setCustomProperty("pds_project", str(pdsProject))
            layer.setCustomProperty("qgis_pds_type", 'qgis_surface')
            # if layer.isValid() is True:
            #     layer.setCrs( QgsCoordinateReferenceSystem(4326, QgsCoordinateReferenceSystem.EpsgCrsId) )
            # else:
            #     print "Unable to read basename and file path - Your string is probably invalid"

#            settings.setValue( "/Projections/defaultBehaviour", oldProjValue )

        return layer


    def readData(self, groupSetId):
        sourceCrs = None
        fileName = None
        layerName = None

        self.tig_projections = TigProjections(db=self.db)
        proj = self.tig_projections.get_projection(self.tig_projections.default_projection_id)
        proj4String = ''
        if proj is not None:
            # sourceCrs = QgsCoordinateReferenceSystem()
            # sourceCrs.createFromProj4(proj.qgis_string)
            # destSrc = QgsCoordinateReferenceSystem('epsg:4326')
            proj4String = proj.qgis_string

            # xform = QgsCoordinateTransform(sourceCrs, destSrc)
        else:
            self.iface.messageBar().pushMessage(self.tr('Error'),
                self.tr(u'Project projection read error'), level=QgsMessageBar.CRITICAL)        

        sqlFile = os.path.join(self.plugin_dir, 'db', 'Surface.sql')
        if os.path.exists(sqlFile):
            f = open(sqlFile, 'r')
            sql = f.read()
            f.close()

            

            groups = self.db.execute(sql, group_id=groupSetId[0], set_id=groupSetId[1])

            for (TIG_MAP_X,
                TIG_MAP_Y,
                TIG_MAP_Z,
                TIG_MAP_PARAM_VRSHRT,
                TIG_MAP_SET_NO,
                TIG_MAP_SET_PARAMETER_NO,
                TIG_MAP_SUBSET_NO,
                TIG_MAP_SET_NAME,
                TIG_PARAM_LONG_NAME,
                TIG_MAP_SUBSET_NAME,
                TIG_SUBSET_V_MIN,
                TIG_SUBSET_V_MAX,
                TIG_SUBSET_V_NULLS,
                TIG_MAP_SET_CP_SOURCE,
                TIG_MAP_SET_X_MIN,
                TIG_MAP_SET_X_MAX,
                TIG_MAP_SET_Y_MIN,
                TIG_MAP_SET_Y_MAX,
                TIG_MAP_SUBSET_X_MIN,
                TIG_MAP_SUBSET_X_MAX,
                TIG_MAP_SUBSET_Y_MIN,
                TIG_MAP_SUBSET_Y_MAX,
                TIG_MAP_SUBSET_Z_MIN,
                TIG_MAP_SUBSET_Z_MAX,
                TIG_MAP_SUBSET_GEOM,
                TIG_MAP_SUBSET_GEOM_DATA) in groups:

                x = numpy.fromstring(TIG_MAP_X.read(), '>d').astype('d')
                y = numpy.fromstring(TIG_MAP_Y.read(), '>d').astype('d')
                z = numpy.fromstring(TIG_MAP_Z.read(), '>d').astype('d')
                min_x, max_x, step_x = x
                min_y, max_y, step_y = y

                values = numpy.fromstring(TIG_MAP_PARAM_VRSHRT.read(), '>f').astype('d')

                size_x = int((max_x - min_x) / step_x + 1.005)
                size_y = int((max_y - min_y) / step_y + 1.005)

                data = values.reshape((size_x, size_y), order='F')
                data = numpy.rot90(data)
                nodata = 1E+10
                numpy.minimum(data, nodata, out=data)

                # geotransform=(min.x(), step_x, 0, max.y(), 0, -step_y)
                geotransform=(min_x, step_x, 0, max_y, 0, -step_y)
                driver = gdal.GetDriverByName('GTiff')
                driver.Register()

#                fileName = u'%d_%d.tif' % (groupSetId[0], groupSetId[1])
                fileName = u'%s_%s.tif' % (TIG_MAP_SET_NAME, TIG_PARAM_LONG_NAME)
                layerName = u'%s/%s' % (TIG_MAP_SET_NAME, TIG_PARAM_LONG_NAME)

                (prjPath, prjExt) = os.path.splitext(QgsProject.instance().fileName())
                if not os.path.exists(prjPath):
                    os.mkdir(prjPath)

                fileName = prjPath +'/' + fileName
                output_raster = driver.Create(fileName, size_x, size_y, 1 ,gdal.GDT_Float32)

                band = output_raster.GetRasterBand(1)
                band.SetNoDataValue(nodata)
                band.WriteArray(data)

                output_raster.SetGeoTransform(geotransform)
                srs = osr.SpatialReference()
                # srs.ImportFromEPSG(4326)
                srs.ImportFromProj4(proj4String)
                output_raster.SetProjection( srs.ExportToWkt() )

                output_raster = None
                driver = None

                break
         
            
            #end if

        return fileName, layerName
