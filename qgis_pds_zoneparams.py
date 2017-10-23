# -*- coding: utf-8 -*-

import os
import numpy
from qgis.core import *
from qgis.gui import QgsMessageBar
from PyQt4 import QtGui, uic
from PyQt4.QtGui import *
from PyQt4.QtCore import *

from QgisPDS.db import Oracle
from QgisPDS.connections import create_connection
from QgisPDS.utils import to_unicode
from QgisPDS.tig_projection import *

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'qgis_pds_zoneparams_base.ui'))

class QgisPDSZoneparamsDialog(QtGui.QDialog, FORM_CLASS):
    def __init__(self, _project, _iface, zonation_id, zone_id, well_ids,  parent=None):
        """Constructor."""
        super(QgisPDSZoneparamsDialog, self).__init__(parent)

        self.setupUi(self)

        self.plugin_dir = os.path.dirname(__file__)
        self.iface = _iface
        self.project = _project

        try:
            connection = create_connection(self.project)
            scheme = self.project['project']

            self.db = connection.get_db(scheme)
        except Exception as e:
            self.errorMessage(self.tr(u'Project {0}: {1}').format(scheme, str(e)))
            return

        selectedParams = QSettings().value("/PDS/Zonations/SelectedParameters", [])
        self.selectedParams = [int(z) for z in selectedParams]

        self.fillParameters(zonation_id, zone_id, well_ids)

        header = [self.tr(u'ID'), self.tr(u'Short name'), self.tr(u'Long name')]
        tm = MyTableModel(self.tabledata, header, self.selectedParams, self)
        self.proxy = FilterProxy()
        self.proxy.setSourceModel(tm)
        self.tableView.setModel(self.proxy)

        self.mFilterLineEdit.setText(QSettings().value('PDS/zoneparams/filter', ''))
        self.proxy.setFilter(QSettings().value('PDS/zoneparams/filter', ''))


    def get_sql(self, value):
        sql_file_path = os.path.join(self.plugin_dir, 'db', value)
        with open(sql_file_path, 'rb') as f:
            return f.read().decode('utf-8')

    def fillParameters(self, _zonation_id, _zone_id, well_ids):
        self.tabledata = []
        sql = self.get_sql('ZonationParams_inWells.sql')
        if len(well_ids):
            where = u'AND wh.DB_SLDNID in (' + ','.join([str(p) for p in well_ids]) + ')'
            sql = sql.format(where)
        else:
            sql = sql.format(u'AND 1=1')

        records = self.db.execute(sql, zonation_id=_zonation_id, zone_id=_zone_id)
        if records is not None:
            for row in records:
                isSelected = row[0] in self.selectedParams
                columns = [row[0], row[1], row[2], isSelected]
                self.tabledata.append(columns)

    def on_mFilterLineEdit_textEdited(self, text):
        self.proxy.setFilter(text)
        QSettings().setValue('PDS/zoneparams/filter', text)

    def on_mSelectAll_pressed(self):
        for idx in xrange(self.proxy.rowCount()):
            index1 = self.proxy.index(idx, 0)
            self.proxy.setData(index1, Qt.Checked, Qt.CheckStateRole)

    def on_mDeselectAll_pressed(self):
        for idx in xrange(self.proxy.rowCount()):
            index1 = self.proxy.index(idx, 0)
            self.proxy.setData(index1, Qt.Unchecked, Qt.CheckStateRole)

    def getSelected(self):
        return self.selectedParams


class MyTableModel(QAbstractTableModel):
    def __init__(self, datain, headerdata, selectedParams, parent=None, *args):
        QAbstractTableModel.__init__(self, parent, *args)
        self.arraydata = datain
        self.headerdata = headerdata
        self.selectedParams = selectedParams

    def rowCount(self, parent=QModelIndex()):
        return len(self.arraydata)

    def columnCount(self, parent=QModelIndex()):
        return len(self.headerdata)

    def data(self, index, role):
        if not index.isValid():
            return None

        if role == Qt.DisplayRole:
            return self.arraydata[index.row()][index.column()]
        elif role == Qt.CheckStateRole and index.column() == 0:
            if self.arraydata[index.row()][3]:
                return Qt.Checked
            else:
                return Qt.Unchecked
        return None

    def setData(self, index, value, role):
        if not index.isValid():
            return False

        if index.column() == 0 and role == Qt.CheckStateRole:
            id = self.arraydata[index.row()][0]
            if id in self.selectedParams:
                self.selectedParams.remove(id)

            isChecked = value == Qt.Checked
            self.arraydata[index.row()][3] = isChecked
            if isChecked:
                self.selectedParams.append(id)

            self.dataChanged.emit(index, index)

        return False

    def headerData(self, col, orientation, role):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.headerdata[col]
        return None

    def flags(self, index):
        if not index.isValid():
            return Qt.NoItemFlags

        flags = Qt.ItemIsEnabled | Qt.ItemIsSelectable
        if index.column() == 0:
            flags = flags | Qt.ItemIsUserCheckable

        return flags

class FilterProxy(QSortFilterProxyModel):
    def __init__(self, parent=None):
        QSortFilterProxyModel.__init__(self, parent)
        self.filter = ''

    def setFilter(self, f):
        self.filter = f
        self.invalidateFilter()

    def filterAcceptsRow(self, sourceRow, sourceParent):
        index1 = self.sourceModel().index(sourceRow, 1, sourceParent)
        index2 = self.sourceModel().index(sourceRow, 2, sourceParent)

        str1 = str(self.sourceModel().data(index1, Qt.DisplayRole))
        str2 = str(self.sourceModel().data(index2, Qt.DisplayRole))
        return self.filter=='' or str1.find(self.filter)>=0 or str2.find(self.filter)>=0
