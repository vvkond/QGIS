# -*- coding: utf-8 -*-

import os
import fnmatch
from qgis.core import *
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


    def __init__(self, parent=None):
        """Constructor."""
        super(QgisPDSWellFilterSetupDialog, self).__init__(parent)

        self.setupUi(self)

        self.parentDlg = parent

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


    def on_buttonBox_clicked(self, button):
        role = self.buttonBox.buttonRole(button)
        if role == QDialogButtonBox.ApplyRole and self.parentDlg != None:
            self.parentDlg.applyFilter(self, True, True)
        elif role == QDialogButtonBox.ResetRole:
            self.resetFilter()
            self.parentDlg.applyFilter(self, True, True)