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


    def __init__(self, _project, _iface, parent=None):
        """Constructor."""
        super(QgisPDSWellFilterSetupDialog, self).__init__(parent)

        self.setupUi(self)

        self.project = _project
        self.iface = _iface
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


    def get_sql(self, value):
        plugin_dir = os.path.dirname(__file__)
        sql_file_path = os.path.join(plugin_dir, 'db', value)
        with open(sql_file_path, 'rb') as f:
            return f.read().decode('utf-8')

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


    def getFilterOptions(self):
        logic = 'and'
        if self.mLogicComboBox.currentIndex() == 1:
            logic = 'or'

        method = 'include'
        if self.mMethodComboBox.currentIndex() == 1:
            method = 'exclude'

        caseSensitive = 1 if self.mUseRegistry.isChecked() else 0

        return (logic, method, caseSensitive)


    def getFilterAttribute(self, attr):
        filter = []

        if attr in self.editWidgets:
            widget = self.editWidgets[attr]
            text = widget.text()
            if text:
                filter = [x.strip() for x in text.split(',')]

        return filter


    def prepareFilter(self):
        self.wellnameFilter = self.getFilterAttribute(QgisPDSWellFilterSetupDialog.WELLNAME_FILTER)
        self.fullnameFilter = self.getFilterAttribute(QgisPDSWellFilterSetupDialog.FULLNAME_FILTER)
        self.operatorFilter = self.getFilterAttribute(QgisPDSWellFilterSetupDialog.OPERATOR_FILTER)
        self.apiFilter = self.getFilterAttribute(QgisPDSWellFilterSetupDialog.APINUMBER_FILTER)
        self.locationFilter = self.getFilterAttribute(QgisPDSWellFilterSetupDialog.LOCATION_FILTER)
        self.latitudeFilter = self.getFilterAttribute(QgisPDSWellFilterSetupDialog.LATITUDE_FILTER)
        self.longitudeFilter = self.getFilterAttribute(QgisPDSWellFilterSetupDialog.LONGITUDE_FILTER)
        self.slotFilter = self.getFilterAttribute(QgisPDSWellFilterSetupDialog.SLOT_FILTER)
        self.authorFilter = self.getFilterAttribute(QgisPDSWellFilterSetupDialog.AUTHOR_FILTER)
        self.dateTimeFilter = self.getFilterAttribute(QgisPDSWellFilterSetupDialog.DATETIME_FILTER)


    def getNumFilters(self):
        numFilters = 0  # Общее количество фильтров

        numFilters = numFilters + 1 if len(self.wellnameFilter) else numFilters
        numFilters = numFilters + 1 if len(self.fullnameFilter) else numFilters
        numFilters = numFilters + 1 if len(self.operatorFilter) else numFilters
        numFilters = numFilters + 1 if len(self.apiFilter) else numFilters
        numFilters = numFilters + 1 if len(self.locationFilter) else numFilters
        numFilters = numFilters + 1 if len(self.latitudeFilter) else numFilters
        numFilters = numFilters + 1 if len(self.longitudeFilter) else numFilters
        numFilters = numFilters + 1 if len(self.slotFilter) else numFilters
        numFilters = numFilters + 1 if len(self.authorFilter) else numFilters
        numFilters = numFilters + 1 if len(self.dateTimeFilter) else numFilters

        return numFilters

    def checkWell(self, db, well_sldnid):
        if not self.wellnameFilter:
            self.prepareFilter()

        logic, method, caseSensitive = self.getFilterOptions()
        numFilters = self.getNumFilters()

        if numFilters == 0:
            return True

        wellSql = self.get_sql('Well.sql')
        well_records = db.execute(wellSql, well_id=well_sldnid)
        num = 0
        for row in well_records:
            #Well name
            wn = str(row[0])
            if wn:
                wells = [wn for w in self.wellnameFilter if
                            fnmatch.fnmatchcase(wn, w) or (not caseSensitive and fnmatch.fnmatch(wn, w))]
                num = num + 1 if len(wells) else num

            # Fullname
            wn = str(row[22])
            if wn:
                wells = [wn for w in self.fullnameFilter if
                         fnmatch.fnmatchcase(wn, w) or (not caseSensitive and fnmatch.fnmatch(wn, w))]
                num = num + 1 if len(wells) else num

            #Operator
            wn = str(row[3])
            if wn:
                wells = [wn for w in self.operatorFilter if
                            fnmatch.fnmatchcase(wn, w) or (not caseSensitive and fnmatch.fnmatch(wn, w))]
                num = num + 1 if len(wells) else num

            #API number
            wn = str(row[2])
            if wn:
                wells = [wn for w in self.apiFilter if
                            fnmatch.fnmatchcase(wn, w) or (not caseSensitive and fnmatch.fnmatch(wn, w))]
                num = num + 1 if len(wells) else num

            # Location
            wn = str(row[11])
            if wn:
                wells = [wn for w in self.locationFilter if
                         fnmatch.fnmatchcase(wn, w) or (not caseSensitive and fnmatch.fnmatch(wn, w))]
                num = num + 1 if len(wells) else num

            # Latitude
            wn = str(row[5])
            if wn:
                wells = [wn for w in self.latitudeFilter if
                         fnmatch.fnmatchcase(wn, w) or (not caseSensitive and fnmatch.fnmatch(wn, w))]
                num = num + 1 if len(wells) else num

            # Longitude
            wn = str(row[6])
            if wn:
                wells = [wn for w in self.longitudeFilter if
                         fnmatch.fnmatchcase(wn, w) or (not caseSensitive and fnmatch.fnmatch(wn, w))]
                num = num + 1 if len(wells) else num

            # Slot number
            wn = str(row[21])
            if wn:
                wells = [wn for w in self.slotFilter if
                         fnmatch.fnmatchcase(wn, w) or (not caseSensitive and fnmatch.fnmatch(wn, w))]
                num = num + 1 if len(wells) else num

            # Author
            wn = str(row[16])
            if wn:
                wells = [wn for w in self.authorFilter if
                         fnmatch.fnmatchcase(wn, w) or (not caseSensitive and fnmatch.fnmatch(wn, w))]
                num = num + 1 if len(wells) else num

            # DateTime
            wn = str(row[17])
            if wn:
                wells = [wn for w in self.dateTimeFilter if
                         fnmatch.fnmatchcase(wn, w) or (not caseSensitive and fnmatch.fnmatch(wn, w))]
                num = num + 1 if len(wells) else num

        use = False
        if logic == 'and':
            use = num == numFilters
        else:
            use = num > 0

        if method == 'include':
            return use
        else:
            return not use

    def on_buttonBox_accepted(self):
        self.prepareFilter()

    def on_buttonBox_clicked(self, button):
        role = self.buttonBox.buttonRole(button)
        if role == QDialogButtonBox.ApplyRole and self.parentDlg != None:
            self.prepareFilter()
            self.parentDlg.applyFilter(self, True, True)
        elif role == QDialogButtonBox.ResetRole:
            self.resetFilter()