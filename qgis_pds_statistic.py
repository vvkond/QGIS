# -*- coding: utf-8 -*-

import os
from qgis.core import *
from qgis.gui import QgsMessageBar
from PyQt4 import QtGui, uic
from PyQt4.QtGui import *
from PyQt4.QtCore import *
import csv
import imp

from QgisPDS.db import Oracle
from QgisPDS.connections import create_connection
from QgisPDS.utils import to_unicode
from QgisPDS.tig_projection import *
from calc_statistics import CalculateStatistics


FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'qgis_pds_stat_base.ui'))


class QgisPDSStatisticsDialog(QtGui.QDialog, FORM_CLASS):
    zval = []
    def __init__(self, project, iface, parent=None):
        """Constructor."""
        super(QgisPDSStatisticsDialog, self).__init__(parent)

        self.setupUi(self)

        self.iface = iface
        self.project = project
        self.currentLayer = None
        self.allowFileChange = True

        try:
            mp_info = imp.find_module('matplotlib')
            mp = imp.load_module('mp', *mp_info)
            imp.find_module('pyplot', mp.__path__) # __path__ is already a list
        except ImportError:
            self.in_show_graph.value=False
            self.in_show_graph.enabled=False

        self.fillLayersList()

        try:
            connection = create_connection(self.project)
            scheme = self.project['project']

            self.db = connection.get_db(scheme)
        except Exception as e:
            self.iface.messageBar().pushMessage(self.tr("Error"),
                self.tr(u'Project {0}: {1}').format(scheme, str(e)), level=QgsMessageBar.CRITICAL)
            return

    def fillLayersList(self):
        self.mMapLayerComboBox.clear()
        layers = self.iface.legendInterface().layers()

        for layer in layers:
            layerType = layer.type()
            if layerType == QgsMapLayer.VectorLayer and layer.geometryType() == QGis.Point:
                self.mMapLayerComboBox.addItem(layer.name(), layer.id())


    def on_mMapLayerComboBox_currentIndexChanged(self, index):
        if not isinstance(index, int):
            return

        self.mFieldComboBox.clear()

        layerName = self.mMapLayerComboBox.itemData(index)
        self.currentLayer = QgsMapLayerRegistry.instance().mapLayer(layerName)
        if self.currentLayer is None:
            return

        for f in self.currentLayer.fields():
            if f.type() == QVariant.Double:
                self.mFieldComboBox.addItem(f.name())


    def on_mFieldComboBox_currentIndexChanged(self, fieldName):
        if isinstance(fieldName, int):
            return

        if self.currentLayer is None:
            return

        provider = self.currentLayer.dataProvider()
        fieldIndex = provider.fieldNameIndex(fieldName)
        if fieldIndex < 0:
            return

        del self.zval[:]
        for f in provider.getFeatures():
            self.zval.append(f[fieldIndex])

        self.mMaxDataValue.setText(str(max(self.zval)))
        self.mMinDataValue.setText(str(min(self.zval)))

        if self.allowFileChange:
            fileName = os.path.join(QgsProject.instance().homePath() ,fieldName+'_stat.txt')
            self.mOutputLineEdit.setText(os.path.normpath(fileName))

    def on_mPredefinedIntervals_currentIndexChanged(self, index):
        if isinstance(index, int):
            return

        try:
            vals = index.split(':')
            if len(vals) > 0:
                self.mMinValue.setValue(float(vals[0]))
            if len(vals) > 1:
                self.mMaxValue.setValue(float(vals[1]))
            if len(vals) > 2:
                self.mNumIntervals.setValue(int(vals[2]))
        except:
            return

    def percentSpinBox_editingFinished(self):
        self.in_rnd_avg_prc.blockSignals(True)
        self.in_rnd_avg_prc.setValue(self.percentSpinBox.value())
        self.in_rnd_avg_prc.blockSignals(False)


    def on_mOutputLineEdit_editingFinished(self):
        self.allowFileChange = False

    def mOutputToolButton_clicked(self):
        dir = os.path.normpath(QgsProject.instance().homePath())
        filters = self.tr(u'Text files (*.csv *.txt);;All files (*.*)')
        filename = QFileDialog.getSaveFileName(self, self.tr('Select output file'), dir, filters)
        if filename:
            self.mOutputLineEdit.setText(os.path.normpath(filename))

    def exec_stat(self):
        v_lbl_min = float(self.mMinDataValue.text())
        v_lbl_max = float(self.mMaxDataValue.text())
        v_min = self.mMinValue.value()
        v_max = self.mMaxValue.value()
        if v_min >= v_max:
            v_min = v_lbl_min
            v_max = v_lbl_max

        v_is_graph_show = self.in_show_graph.isChecked()
        v_is_add_source = self.in_addsource.isChecked()
        v_is_show_grid = self.in_show_grid.isChecked()
        v_is_show_gridavg = self.in_show_gridavg.isChecked()

        v_nbin = self.mNumIntervals.value()
        v_nrnd = self.mNumPlanedWells.value()
        v_rnd_avg_prc = self.in_rnd_avg_prc.value()
        v_nrnd_grp = self.in_nrnd_grp.value()

        v_out_f = self.mOutputLineEdit.text()

        out_pipe = open(v_out_f, "wb")
        w = csv.writer(out_pipe)
        stat = CalculateStatistics()
        stat.N_BINS = v_nbin
        stat.N_RND = v_nrnd
        stat.AVG_SLICE = v_rnd_avg_prc

        stat.range = None if None in [v_min, v_max] else [v_min, v_max]
        stat.generate_random_grid(data=self.zval
                                  , num_grids=v_nrnd_grp
                                  , use_original_data=v_is_add_source
                                  )
        if v_is_show_grid:
            print "Generated grids:"
            for data in stat.data_result:
                print str(data)
        if v_is_show_gridavg:
            print "Generated grid after averaging: {}".format(str(stat.get_slice_avg()))

        key, val = zip(*stat.get_statistics().items())
        w.writerow(key)
        w.writerow(val)

        if v_is_graph_show:
            out_png = stat.show_hist2(f_name=v_out_f)
            os.system("start " + out_png)

        return v_out_f

    def on_buttonBox_accepted(self):
        v_out_f = self.exec_stat()
        name = os.path.basename(v_out_f)

        uri = u'file:///{0}?type=csv&geomType=none&subsetIndex=no&watchFile=no'.format(v_out_f)
        layer = QgsVectorLayer(uri, name, "delimitedtext")
        if layer:
            QgsMapLayerRegistry.instance().addMapLayer(layer)
        else:
            self.iface.messageBar().pushMessage(self.tr("Error"),
                                                self.tr(u'Text file layer create error'),
                                                level=QgsMessageBar.CRITICAL)