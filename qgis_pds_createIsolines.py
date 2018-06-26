# -*- coding: utf-8 -*-

from PyQt4 import QtGui, uic, QtCore
from PyQt4.QtGui import *
from qgis import core, gui
from qgis_pds_production import *
from processing.tools.system import getTempFilename
from processing.tools.vector import VectorWriter
import os


FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'qgis_pds_isolines_base.ui'))

class QgisPDSCreateIsolines(QtGui.QDialog, FORM_CLASS):
    def __init__(self, iface, parent=None):
        super(QgisPDSCreateIsolines, self).__init__(parent)

        self.setupUi(self)

        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)

        self.updateWidgets()


    def updateWidgets(self):
        self.fillComboboxRaster(self.mSurfaceComboBox,)
        self.fillComboboxVector(self.mFaultsComboBox, QGis.WKBLineString)

        if self.mSurfaceComboBox.count() > 0:
            self.mSurfaceComboBox.setCurrentIndex(0)

        self.mFaultsComboBox.insertItem(0, self.tr(u'[Not selected]'), '-1')
        self.mFaultsComboBox.setCurrentIndex(0)

    def fillComboboxVector(self, combo, geomType):
        combo.clear()

        layers = self.iface.legendInterface().layers()

        for layer in layers:
            lt = layer.type()
            try:
                provider = layer.dataProvider()
                if lt == QgsMapLayer.VectorLayer and provider.geometryType() == geomType:
                    combo.addItem(layer.name(), layer.id())
            except:
                pass

    def fillComboboxRaster(self, combo):
        combo.clear()

        layers = self.iface.legendInterface().layers()

        for layer in layers:
            lt = layer.type()
            if lt == QgsMapLayer.RasterLayer:
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
            QtGui.QMessageBox.critical(None, self.tr(u'Error'),
               self.tr(u'Raster layer is not selected'), QtGui.QMessageBox.Ok)
            return

        tmpGrid = getTempFilename('grd').replace('\\', '/')
        sourceRasterName = raster.source()
        sn,se = os.path.splitext(sourceRasterName)
        if se.lower() == '.grd':
            tmpGrid = sourceRasterName.replace('\\', '/')
        else:
            runStr = 'gdal_translate -of GSAG -a_srs "{0}" "{1}" "{2}"'.format(raster.crs().toProj4(), sourceRasterName, tmpGrid)
            self.runProcess(runStr)
            if not os. path.exists(tmpGrid):
                QtGui.QMessageBox.critical(None, self.tr(u'Error'),
                   self.tr(u'Raster layer conversion error'), QtGui.QMessageBox.Ok)
                return

        settings = QSettings()
        systemEncoding = settings.value('/UI/encoding', 'System')

        faultFileName = ''
        faultLayer = self.input_fault
        if faultLayer:
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

        prjPath = QgsProject.instance().homePath()
        sn,se = os.path.splitext(os.path.basename(sourceRasterName))
        isolinePath = prjPath + '/' + sn + '_iso.shp'
        contourPath = prjPath + '/' + sn + '_cntr.shp'
        isolinePrj = prjPath + '/' + sn + '_iso.prj'
        contourPrj = prjPath + '/' + sn + '_cntr.prj'

#Create projection files for new created SHP
        prjWkt = raster.crs().toWkt()
        with open(isolinePrj, "w") as text_file:
            text_file.write(prjWkt)
        with open(contourPrj, "w") as text_file:
            text_file.write(prjWkt)

        # tmpFields = [QgsField('Z', QVariant.Double)]
        # tmpWriter = VectorWriter(isolinePath, systemEncoding, tmpFields, QGis.WKBPolygon, raster.crs())
        # f = QgsFeature()
        # tmpWriter.addFeature(f)
        # del tmpWriter
        #
        # tmpWriter = VectorWriter(contourPath, systemEncoding, tmpFields, QGis.WKBPolygon, raster.crs())
        # f = QgsFeature()
        # tmpWriter.addFeature(f)
        # del tmpWriter

        ctlFileName = getTempFilename('ctl')
        with open(ctlFileName, "w") as text_file:
            text_file.write("grid={0}\n".format(tmpGrid))
            if faultFileName:
                text_file.write('faults={0}\n'.format(faultFileName))
            text_file.write('step={0}\n'.format(self.mStepSpinBox.value()))
            text_file.write('minimum={0}\n'.format(self.mMinSpinBox.value()))
            text_file.write('maximum={0}\n'.format(self.mMaxSpinBox.value()))
            text_file.write('Isolines={0}\n'.format(isolinePath))
            text_file.write('Contours={0}\n'.format(contourPath))

        runStr = os.path.join(self.plugin_dir, "bin/grid_contour ") + os.path.realpath(ctlFileName)
        self.runProcess(runStr)

        isolineName = self.mIsolinesLineEdit.text()
        if not isolineName:
            isolineName = self.mIsolinesLineEdit.placeholderText()
        contourName = self.mContoursLineEdit.text()
        if not contourName:
            contourName = self.mContoursLineEdit.placeholderText()

        contourLayer = QgsVectorLayer(contourPath, contourName, 'ogr')
        if contourLayer:
            myStyle = QgsStyleV2().defaultStyle()
            ramp = myStyle.colorRamp('Spectral')

            idx = contourLayer.fieldNameIndex('Z')
            uniqSymbols = contourLayer.uniqueValues(idx)
            count = len(uniqSymbols)
            categories = []
            num = 0.0
            for ss in uniqSymbols:
                symbol = QgsSymbolV2.defaultSymbol(contourLayer.geometryType())

                clr = ramp.color(num / count)
                num = num + 1.0
                symbol.setColor(clr)
                symbol.symbolLayer(0).setBorderColor(symbol.color())

                category = QgsRendererCategoryV2(ss, symbol, str(ss))
                categories.append(category)

            renderer = QgsCategorizedSymbolRendererV2('Z', categories)
            renderer.setSourceColorRamp(ramp)
            contourLayer.setRendererV2(renderer)
            contourLayer.commitChanges()
            QgsMapLayerRegistry.instance().addMapLayer(contourLayer)

        isolineLayer = QgsVectorLayer(isolinePath, isolineName, 'ogr')
        if isolineLayer:
            QgsMapLayerRegistry.instance().addMapLayer(isolineLayer)

    def updateMinMax(self):
        raster = self.input_raster
        if raster:
            rasterProvider = raster.dataProvider()
            stats = rasterProvider.bandStatistics(1, QgsRasterBandStats.All, raster.extent(), 0)
            self.mMinSpinBox.setValue(stats.minimumValue)
            self.mMaxSpinBox.setValue(stats.maximumValue)
        else:
            print 'No raster'

    def on_buttonBox_accepted(self):
        self.createIsolines()


    def on_mSurfaceComboBox_currentIndexChanged(self, item):
        if type(item) is int:
            return

        if self.mUpdateMinMax.isChecked():
            self.updateMinMax()

        if not self.mIsolinesLineEdit.text():
            self.mIsolinesLineEdit.setPlaceholderText(self.tr(u'isolines ') + item)
        if not self.mContoursLineEdit.text():
            self.mContoursLineEdit.setPlaceholderText(self.tr(u'contours ') + item)


    def on_mFaultsComboBox_activated(self, item):
        if type(item) is int:
            return

    def on_mUpdateMinMax_toggled(self, checked):
        if checked:
            self.updateMinMax()


    def runProcess(self, runStr):
        process = QProcess(self.iface)
        process.start(runStr)
        process.waitForFinished()
        # print process.readAllStandardOutput()
        process.kill()


