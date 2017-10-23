import os
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
    os.path.dirname(__file__), 'qgis_pds_wellfilter_base.ui'))


class QgisWellFilterDialog(QtGui.QDialog, FORM_CLASS):
    def __init__(self, _iface, wells, parent=None):
        """Constructor."""
        super(QgisWellFilterDialog, self).__init__(parent)

        self.setupUi(self)

        self.plugin_dir = os.path.dirname(__file__)
        self.iface = _iface

        self.selectedParams = []
        selectedParams = QSettings().value("/PDS/WellFilter/SelectedParameters", [])
        if selectedParams:
            self.selectedParams = [int(z) for z in selectedParams]

        self.tabledata = []
        for well in wells:
            isSelected = well.id in self.selectedParams
            columns = [well.id, well.name, isSelected]
            self.tabledata.append(columns)

        header = [self.tr(u'ID'), self.tr(u'Name')]

        tm = WellTableModel(self.tabledata, header, self.selectedParams, self)
        self.proxy = WellFilterProxy()
        self.proxy.setSourceModel(tm)
        self.tableView.setModel(self.proxy)

        self.mFilterLineEdit.setText(QSettings().value('PDS/WellFilter/filter', ''))
        self.proxy.setFilter(QSettings().value('PDS/WellFilter/filter', ''))

    def on_mFilterLineEdit_textEdited(self, text):
        self.proxy.setFilter(text)
        QSettings().setValue('PDS/WellFilter/filter', text)

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

    def on_buttonBox_accepted(self):
        QSettings().setValue("/PDS/WellFilter/SelectedParameters", self.selectedParams)



class WellTableModel(QAbstractTableModel):
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
            if self.arraydata[index.row()][2]:
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
            self.arraydata[index.row()][2] = isChecked
            if isChecked:
                self.selectedParams.append(id)

            self.dataChanged.emit(index, index);

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

class WellFilterProxy(QSortFilterProxyModel):
    def __init__(self, parent=None):
        QSortFilterProxyModel.__init__(self, parent)
        self.filter = ''

    def setFilter(self, f):
        self.filter = f
        self.invalidateFilter()

    def filterAcceptsRow(self, sourceRow, sourceParent):
        index1 = self.sourceModel().index(sourceRow, 0, sourceParent)
        index2 = self.sourceModel().index(sourceRow, 1, sourceParent)

        str1 = str(self.sourceModel().data(index1, Qt.DisplayRole))
        str2 = str(self.sourceModel().data(index2, Qt.DisplayRole))
        return self.filter=='' or str1.find(self.filter)>=0 or str2.find(self.filter)>=0

    def lessThan(self, left, right):
        leftData = self.sourceModel().data(left, Qt.DisplayRole)
        rightData = self.sourceModel().data(right, Qt.DisplayRole)
        return leftData < rightData
