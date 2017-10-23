# -*- coding: utf-8 -*-

import tempfile
import os
from os.path import abspath
import numpy
from osgeo import gdal
import ogr
from qgis.core import *

class QgisProcessing:
    def __init__(self):
        self.temp_path = tempfile.gettempdir()


    def rasterizeLayer(self, raster_polygons_path, input_raster, rasterCrs, cols, rows):
        out_path = self.temp_path +'/temp_raster_polygons.shp'
        err = QgsVectorFileWriter.writeAsVectorFormat(raster_polygons_path, out_path, 'utf-8', rasterCrs, 'ESRI Shapefile')
        if err != 0:
            raise Exception("error saving layer: %s" % err)

        tifDriver = gdal.GetDriverByName( 'GTiff' )
        driver = ogr.GetDriverByName('ESRI Shapefile')

        vector_source = driver.Open(out_path,0)
        source_layer = vector_source.GetLayer(0)    
        target_ds = tifDriver.Create( self.temp_path + '/temp_raster.tif', cols, rows, 1, gdal.GDT_Int32)
        target_ds.SetGeoTransform(input_raster.GetGeoTransform())
        target_ds.SetProjection(input_raster.GetProjection())
        band = target_ds.GetRasterBand(1)
        band.SetNoDataValue(0)
        band.Fill(0)
        err = gdal.RasterizeLayer(target_ds, [1], source_layer, options=["ATTRIBUTE=ID" ])
        if err != 0:
            raise Exception("error rasterizing layer: %s" % err)

        return target_ds

    def saveRaster(self, raster_path, geoTransform, nodata, crsWkt, size_x, size_y, data):
        driver = gdal.GetDriverByName('GTiff')
        output_raster = driver.Create(raster_path, size_x, size_y, 1 ,gdal.GDT_Float32)
        band = output_raster.GetRasterBand(1)
        band.SetNoDataValue(nodata)
        band.WriteArray(data, 0, 0)
        output_raster.SetGeoTransform(geoTransform)
        output_raster.SetProjection( str(crsWkt) )
        output_raster = None