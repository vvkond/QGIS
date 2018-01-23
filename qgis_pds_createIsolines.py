# -*- coding: utf-8 -*-

from PyQt4 import QtGui, uic, QtCore
from PyQt4.QtGui import *
from qgis import core, gui
from qgis.gui import QgsColorButtonV2
from collections import namedtuple
from qgis_pds_production import *
from processing.tools.system import getTempFilename
from processing.tools.vector import VectorWriter
import ast
import math
import re

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'qgis_pds_isolines_base.ui'))

class QgisPDSCreateIsolines(QtGui.QDialog, FORM_CLASS):
    def __init__(self, iface, parent=None):
        super(QgisPDSCreateIsolines, self).__init__(parent)

        self.setupUi(self)

        self.iface = iface

        self.updateWidgets()


    def updateWidgets(self):
        self.fillCombobox(self.mSurfaceComboBox, QgsMapLayer.RasterLayer)
        self.fillCombobox(self.mFaultsComboBox, QgsMapLayer.VectorLayer)

        self.mFaultsComboBox.insertItem(0, self.tr(u'[Not selected]'), '-1')
        self.mFaultsComboBox.setCurrentIndex(0)

    def fillCombobox(self, combo, layerType):
        combo.clear()

        layers = self.iface.legendInterface().layers()

        for layer in layers:
            lt = layer.type()
            if lt == layerType:
                combo.addItem(layer.name(), layer.id())

    @property
    def input_raster(self):
        layerId = self.mSurfaceComboBox.itemData(self.mSurfaceComboBox.currentIndex())
        lay = QgsMapLayerRegistry.instance().mapLayer(layerId)
        if lay is not None:
            return lay
        else:
            return None

    @property
    def input_fault(self):
        layerId = self.mFaultsComboBox.itemData(self.mFaultsComboBox.currentIndex())
        lay = QgsMapLayerRegistry.instance().mapLayer(layerId)
        if lay is not None:
            return lay
        else:
            return None


    def createIsolines(self):
        raster = self.input_raster
        if not raster:
            QtGui.QMessageBox.critical(None, self.tr(u'Error'), self.tr(
                u'Raster layer is not selected'), QtGui.QMessageBox.Ok)
            return
        tmpGrid = getTempFilename('grd').replace('\\', '/')
        sourceRasterName = raster.source()
        runStr = 'gdal_translate -of GS7BG -a_srs "{0}" "{1}" "{2}"'.format(raster.crs().toProj4(), sourceRasterName, tmpGrid)
        self.runProcess(runStr)
        if not os. path.exists(tmpGrid):
            QtGui.QMessageBox.critical(None, self.tr(u'Error'), self.tr(
                u'Raster layer conversion error'), QtGui.QMessageBox.Ok)
            return

        faultFileName = ''
        faultLayer = self.input_fault
        if faultLayer:
            settings = QSettings()
            systemEncoding = settings.value('/UI/encoding', 'System')
            faultFileName = getTempFilename('shp').replace('\\', '/')
            provider = faultLayer.dataProvider()
            fields = provider.fields()
            writer = VectorWriter(faultFileName, systemEncoding,
                                  fields,
                                  provider.geometryType(), provider.crs())

            features = faultLayer.getFeatures()
            for f in features:
                l = f.geometry()
                feat = QgsFeature(f)
                feat.setGeometry(l)
                writer.addFeature(feat)

            del writer

        ctlFileName = getTempFilename('ctl')
        print ctlFileName
        with open(ctlFileName, "w") as text_file:
            text_file.write("grid={0}\n".format(tmpGrid))
            if faultFileName:
                text_file.write('faults={0}\n'.format(faultFileName))
            text_file.write('step={0}\n'.format(self.mStepSpinBox.value()))
            text_file.write('Isolines={0}\n'.format(self.mIsolinesLineEdit.text()))
            text_file.write('Contours={0}\n'.format(self.mContoursLineEdit.text()))

    def on_buttonBox_accepted(self):
        self.createIsolines()

    def on_mSurfaceComboBox_activated(self, item):
        if type(item) is int:
            return


    def on_mFaultsComboBox_activated(self, item):
        if type(item) is int:
            return


    def runProcess(self, runStr):
        process = QProcess(self.iface)
        process.start(runStr)
        process.waitForFinished()
        print process.readAllStandardOutput()
        process.kill()


