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


    def get_sql(self, value):
        plugin_dir = os.path.dirname(__file__)
        sql_file_path = os.path.join(plugin_dir, 'db', value)
        with open(sql_file_path, 'rb') as f:
            return f.read().decode('utf-8')


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

        if attr == QgisPDSWellFilterSetupDialog.WELLNAME_FILTER and self.mWellName.text():
            filter = [ x.strip() for x in self.mWellName.text().split(',')]

        elif attr == QgisPDSWellFilterSetupDialog.FULLNAME_FILTER and self.mFullName.text():
            filter = [x.strip() for x in self.mFullName.text().split(',')]

        elif attr == QgisPDSWellFilterSetupDialog.OPERATOR_FILTER and self.mOperator.text():
            filter = [x.strip() for x in self.mOperator.text().split(',')]

        elif attr == QgisPDSWellFilterSetupDialog.APINUMBER_FILTER and self.mApiNumber.text():
            filter = [x.strip() for x in self.mApiNumber.text().split(',')]

        elif attr == QgisPDSWellFilterSetupDialog.LOCATION_FILTER and self.mLocation.text():
            filter = [x.strip() for x in self.mLocation.text().split(',')]

        elif attr == QgisPDSWellFilterSetupDialog.LATITUDE_FILTER and self.mLatitude.text():
            filter = [x.strip() for x in self.mLatitude.text().split(',')]

        elif attr == QgisPDSWellFilterSetupDialog.LONGITUDE_FILTER and self.mLongitude.text():
            filter = [x.strip() for x in self.mLongitude.text().split(',')]

        elif attr == QgisPDSWellFilterSetupDialog.SLOT_FILTER and self.mSlotNumber.text():
            filter = [x.strip() for x in self.mSlotNumber.text().split(',')]

        elif attr == QgisPDSWellFilterSetupDialog.AUTHOR_FILTER and self.mAuthor.text():
            filter = [x.strip() for x in self.mAuthor.text().split(',')]

        elif attr == QgisPDSWellFilterSetupDialog.DATETIME_FILTER and self.mDateTime.text():
            filter = [x.strip() for x in self.mDateTime.text().split(',')]

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
            if row[0]:  # Well name
                wn = str(row[0])
                wellName = [row[0] for w in self.wellnameFilter if
                            fnmatch.fnmatchcase(wn, w) or (not caseSensitive and fnmatch.fnmatch(wn, w))]
                num = num + 1 if len(wellName) else num

        if logic == 'and':
            return num == numFilters
        else:
            return num > 0

    def on_buttonBox_accepted(self):
        self.prepareFilter()

    def on_buttonBox_clicked(self, button):
        if self.buttonBox.buttonRole(button) == QDialogButtonBox.ApplyRole and self.parentDlg != None:
            self.prepareFilter()
            self.parentDlg.applyFilter(self)