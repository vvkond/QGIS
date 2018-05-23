# -*- coding: utf-8 -*-

import os
import fnmatch
from struct import unpack_from
from qgis.core import *
from PyQt4 import QtGui, uic
from PyQt4.QtGui import *
from PyQt4.QtCore import *

from QgisPDS.db import Oracle
from QgisPDS.connections import create_connection
from utils import *

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'qgis_pds_templateList_base.ui'))

class QgisPDSTemplateListDialog(QtGui.QDialog, FORM_CLASS):
    """Constructor."""
    def __init__(self, _db, currentId, simple=True, parent=None):
        self.db = _db
        self.currentId = currentId

        if not simple:
            super(QgisPDSTemplateListDialog, self).__init__(parent)

            self.setupUi(self)

            headerState = QSettings().value('/PDS/TemplateList/HeaderState')
            if headerState:
                self.tableWidget.horizontalHeader().restoreState(headerState)

            self.fillTableWidget()

    def get_sql(self, value):
        plugin_dir = os.path.dirname(__file__)
        sql_file_path = os.path.join(plugin_dir, 'db', value)
        with open(sql_file_path, 'rb') as f:
            return f.read().decode('utf-8')


    def fillTableWidget(self):
        sql = self.get_sql('template.sql')
        records = self.db.execute(sql, app_name = 'brwwel')
        if not records:
            return

        row = 0
        self.tableWidget.setSortingEnabled(False)
        for input_row in records:
            self.tableWidget.insertRow(row)

            sldnid = int(input_row[0])
            item = QTableWidgetItem(input_row[1])
            item.setData(Qt.UserRole, sldnid)
            self.tableWidget.setItem(row, 0, item)

            item = QTableWidgetItem(input_row[2])
            self.tableWidget.setItem(row, 1, item)

            item = QTableWidgetItem(input_row[3])
            self.tableWidget.setItem(row, 2, item)

            dt = QDateTime.fromString(input_row[4], 'dd-MM-yyyy HH:mm:ss')
            item = QTableWidgetItem(QVariant.DateTime)
            item.setData(Qt.DisplayRole, dt)
            self.tableWidget.setItem(row, 3, item)

            if self.currentId == sldnid:
                self.tableWidget.setCurrentItem(item)

            row += 1

        self.tableWidget.setSortingEnabled(True)


    def hideEvent(self, event):
        QSettings().setValue('/PDS/TemplateList/HeaderState', self.tableWidget.horizontalHeader().saveState())
        super(QgisPDSTemplateListDialog, self).hideEvent(event)

    def getListId(self):
        result = -1
        row = self.tableWidget.currentRow()
        if row >= 0 and row < self.tableWidget.rowCount():
            item = self.tableWidget.item(row, 0)
            result = item.data(Qt.UserRole)

        return result

    def getWells(self, list_id):
        result = []
        sql = 'select DB_SLDNID, TIG_TEMPLATE_DATA from tig_template where DB_SLDNID = ' + str(list_id)
        records = self.db.execute(sql)
        if records:
            for input_row in records:
                if input_row[1]:
                    ids = self.parceCLob(input_row[1])
                    result = self.getWellNames(ids)
                    break

        return result

    def getWellNames(self, ids):
        result = []
        sql = self.get_sql('well.sql')
        for id in ids:
            records = self.db.execute(sql, well_id=id)
            if records:
                for rec in records:
                    well = []
                    well.append(int(rec[0]))
                    well.append(rec[1])
                    well.append(rec[2])
                    well.append(rec[3])
                    well.append(rec[4])
                    well.append(rec[5])
                    well.append(float(rec[6]))
                    well.append(float(rec[7]))
                    well.append(rec[8])
                    well.append(rec[9])
                    dt = QDateTime.fromString(rec[10], 'dd-MM-yyyy HH:mm:ss')
                    well.append(dt)
                    result.append(well)
                    break

        return result


    def parceCLob(self, lobObject):
        try:
            strToParce = lobObject.read()
            lines = strToParce.split('\n')

            #Version
            values = lines[0].split('\t')
            if len(values) < 2 or int(values[1]) != 2:
                QtGui.QMessageBox.critical(self, self.tr(u'Error'), self.tr(u'Version is not 2'), QtGui.QMessageBox.Ok)
                return []

            #Number in list
            values = lines[2].split('\t')
            numIds = int(values[1])

            #SLDNIDs
            ids = []
            for i in xrange(4, 4+numIds):
                ids.append(int(lines[i]))

            return ids

        except Exception as e:
            QgsMessageLog.logMessage('CLOB: ' + str(e), 'QGisPDS')

        return []