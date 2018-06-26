# -*- coding: utf-8 -*-

import os
import fnmatch
from qgis.core import *
from qgis.gui import QgsMapLayerComboBox, QgsFieldComboBox
from PyQt4 import QtGui, uic
from PyQt4.QtGui import *
from PyQt4.QtCore import *

from QgisPDS.db import Oracle
from QgisPDS.connections import create_connection
from utils import *

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'qgis_pds_wellFilterSetup_base.ui'))

class QgisPDSWellFilterSetupDialog(QtGui.QDialog, FORM_CLASS):

    WELLNAME_FILTER = 'wellname'
    FULLNAME_FILTER = 'fullname'
    OPERATOR_FILTER = 'operator'
    APINUMBER_FILTER = 'api'
    LOCATION_FILTER = 'location'
    LATITUDE_FILTER = 'latitude'
    LONGITUDE_FILTER = 'longitude'
    SLOT_FILTER = 'slotnumber'
    AUTHOR_FILTER = 'author'
    DATETIME_FILTER = 'date_time'
    LOGIC_FILTER = 'logic'
    METHOD_FILTER = 'method'
    CONTEXT_FILTER = 'context'


    def __init__(self, _iface, parent=None):
        """Constructor."""
        super(QgisPDSWellFilterSetupDialog, self).__init__(parent)

        self.setupUi(self)

        self.parentDlg = parent
        self.iface = _iface

        self.wellnameFilter = None

        self.editWidgets = {}
        self.editWidgets[QgisPDSWellFilterSetupDialog.WELLNAME_FILTER] = self.mWellName
        self.editWidgets[QgisPDSWellFilterSetupDialog.FULLNAME_FILTER] = self.mFullName
        self.editWidgets[QgisPDSWellFilterSetupDialog.OPERATOR_FILTER] = self.mOperator
        self.editWidgets[QgisPDSWellFilterSetupDialog.APINUMBER_FILTER] = self.mApiNumber
        self.editWidgets[QgisPDSWellFilterSetupDialog.LOCATION_FILTER] = self.mLocation
        self.editWidgets[QgisPDSWellFilterSetupDialog.LATITUDE_FILTER] = self.mLatitude
        self.editWidgets[QgisPDSWellFilterSetupDialog.LONGITUDE_FILTER] = self.mLongitude
        self.editWidgets[QgisPDSWellFilterSetupDialog.SLOT_FILTER] = self.mSlotNumber
        self.editWidgets[QgisPDSWellFilterSetupDialog.AUTHOR_FILTER] = self.mAuthor
        self.editWidgets[QgisPDSWellFilterSetupDialog.DATETIME_FILTER] = self.mDateTime

        self.fieldComboBox = QgsFieldComboBox(self)
        self.horizontalLayout.addWidget(self.fieldComboBox)
        self.horizontalLayout.setStretch(3, 1)

        self.fillLayersComboBox()


    def fillLayersComboBox(self):
        self.mLayerComboBox.clear()
        # self.mLayerComboBox.addItem('', '')
        layers = self.iface.legendInterface().layers()

        for layer in layers:
            layerType = layer.type()
            if layerType == QgsMapLayer.VectorLayer:
                if len(layer.selectedFeatures()) > 0:
                    self.mLayerComboBox.addItem(layer.name(), layer.id())

        currentLayer = QSettings().value('/PDS/QgisPDSWellFilterSetupDialog/CurrentLayer')
        self.mLayerComboBox.setCurrentIndex(self.mLayerComboBox.findText(currentLayer))


    def getFilter(self):
        filter = {}

        for k, w in self.editWidgets.items():
            filter[k] = w.text()

        filter[QgisPDSWellFilterSetupDialog.LOGIC_FILTER] = self.mLogicComboBox.currentIndex()
        filter[QgisPDSWellFilterSetupDialog.METHOD_FILTER] = self.mMethodComboBox.currentIndex()
        filter[QgisPDSWellFilterSetupDialog.CONTEXT_FILTER] = 1 if self.mUseRegistry.isChecked() else 0

        return filter

    def resetFilter(self):
        for k, w in self.editWidgets.items():
            w.setText('')

    def setFilter(self, filter):
        for k, v in filter.items():
            if k in self.editWidgets:
                widget = self.editWidgets[k]
                widget.setText(v)

        try:
            if QgisPDSWellFilterSetupDialog.LOGIC_FILTER in filter:
                self.mLogicComboBox.setCurrentIndex(int(filter[QgisPDSWellFilterSetupDialog.LOGIC_FILTER]))

            if QgisPDSWellFilterSetupDialog.METHOD_FILTER in filter:
                self.mMethodComboBox.setCurrentIndex(int(filter[QgisPDSWellFilterSetupDialog.METHOD_FILTER]))

            if QgisPDSWellFilterSetupDialog.CONTEXT_FILTER in filter:
                self.mUseRegistry.setChecked(int(filter[QgisPDSWellFilterSetupDialog.CONTEXT_FILTER]) == 1)
        except Exception as e:
            QgsMessageLog.logMessage('Set well filter: ' + str(e), 'QGisPDS')


    def saveState(self):
        QSettings().setValue('/PDS/QgisPDSWellFilterSetupDialog/CurrentField', self.fieldComboBox.currentField())
        QSettings().setValue('/PDS/QgisPDSWellFilterSetupDialog/CurrentLayer', self.mLayerComboBox.currentText())

    def restoreState(self):
        currentField = QSettings().value('/PDS/QgisPDSWellFilterSetupDialog/CurrentField')
        if currentField:
            self.fieldComboBox.setField(currentField)


    def on_buttonBox_clicked(self, button):
        role = self.buttonBox.buttonRole(button)
        if role == QDialogButtonBox.ApplyRole and self.parentDlg != None:
            self.parentDlg.applyFilter(self, True, True)
        elif role == QDialogButtonBox.ResetRole:
            self.resetFilter()
            self.parentDlg.applyFilter(self, True, True)

    @pyqtSlot(int)
    def on_mLayerComboBox_currentIndexChanged(self, index):
        layerId = self.mLayerComboBox.itemData(self.mLayerComboBox.currentIndex())
        lay = QgsMapLayerRegistry.instance().mapLayer(layerId)
        if lay is not None:
            self.fieldComboBox.setLayer(lay)
            self.restoreState()
        else:
            self.fieldComboBox.setLayer(None)

    def getSelection(self):
        lay = self.fieldComboBox.layer()
        field = self.fieldComboBox.currentField()
        result = set()
        if lay and field:
            for f in lay.selectedFeatures():
                result.add(f[field])
        return ','.join(str(s) for s in result)

    @pyqtSlot()
    def on_mWellsToolButton_clicked(self):
        sel = self.getSelection()
        if sel:
            self.mWellName.setText(sel)

    @pyqtSlot()
    def on_mFullNameToolButton_clicked(self):
        sel = self.getSelection()
        if sel:
            self.mFullName.setText(sel)

    @pyqtSlot()
    def on_mOperatorToolButton_clicked(self):
        sel = self.getSelection()
        if sel:
            self.mOperator.setText(sel)

    @pyqtSlot()
    def on_mApiNumberToolButton_clicked(self):
        sel = self.getSelection()
        if sel:
            self.mApiNumber.setText(sel)

    @pyqtSlot()
    def on_mLocationToolButton_clicked(self):
        sel = self.getSelection()
        if sel:
            self.mLocation.setText(sel)

    @pyqtSlot()
    def on_mLatitudeToolButton_clicked(self):
        sel = self.getSelection()
        if sel:
            self.mLatitude.setText(sel)

    @pyqtSlot()
    def on_mLongitudeToolButton_clicked(self):
        sel = self.getSelection()
        if sel:
            self.mLongitude.setText(sel)

    @pyqtSlot()
    def on_mSlotNumberToolButton_clicked(self):
        sel = self.getSelection()
        if sel:
            self.mSlotNumber.setText(sel)

    @pyqtSlot()
    def on_mAuthorToolButton_clicked(self):
        sel = self.getSelection()
        if sel:
            self.mAuthor.setText(sel)

    @pyqtSlot()
    def on_mDateToolButton_clicked(self):
        sel = self.getSelection()
        if sel:
            self.mDateTime.setText(sel)

    def hideEvent(self, event):
        self.saveState()
        super(QgisPDSWellFilterSetupDialog, self).hideEvent(event)