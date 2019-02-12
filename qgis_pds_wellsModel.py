# -*- coding: utf-8 -*-

import os
import fnmatch
from struct import unpack_from
from qgis.core import *
from PyQt4 import QtGui, uic
from PyQt4.QtGui import *
from PyQt4.QtCore import *
from qgis_pds_WellFilterSetup import *

class WellsItemsProxyModel(QSortFilterProxyModel):
    def __init__(self, parent=None):
        QSortFilterProxyModel.__init__(self, parent)
        self.filter = {}
        self.filterActive = False
        self.wellnameFilter = []
        self.fullnameFilter = []
        self.operatorFilter = []
        self.apiFilter = []
        self.locationFilter = []
        self.latitudeFilter = []
        self.longitudeFilter = []
        self.slotFilter = []
        self.authorFilter = []
        self.dateTimeFilter = []
        self.logic = 'and'
        self.method = 'include'
        self.caseSensitive = 1
        self.numFilters = 0

    def setupFilterOptions(self):
        self.logic = 'and'
        if QgisPDSWellFilterSetupDialog.LOGIC_FILTER in self.filter:
            if int(self.filter[QgisPDSWellFilterSetupDialog.LOGIC_FILTER]) == 1:
                self.logic = 'or'

        self.method = 'include'
        if QgisPDSWellFilterSetupDialog.METHOD_FILTER in self.filter:
            if int(self.filter[QgisPDSWellFilterSetupDialog.METHOD_FILTER]) == 1:
                self.method = 'exclude'

        if QgisPDSWellFilterSetupDialog.CONTEXT_FILTER in self.filter:
            self.caseSensitive = int(self.filter[QgisPDSWellFilterSetupDialog.CONTEXT_FILTER])

    def setupNumFilters(self):
        self.numFilters = 0  # Общее количество фильтров

        self.numFilters = self.numFilters + 1 if len(self.wellnameFilter) else self.numFilters
        self.numFilters = self.numFilters + 1 if len(self.fullnameFilter) else self.numFilters
        self.numFilters = self.numFilters + 1 if len(self.operatorFilter) else self.numFilters
        self.numFilters = self.numFilters + 1 if len(self.apiFilter) else self.numFilters
        self.numFilters = self.numFilters + 1 if len(self.locationFilter) else self.numFilters
        self.numFilters = self.numFilters + 1 if len(self.latitudeFilter) else self.numFilters
        self.numFilters = self.numFilters + 1 if len(self.longitudeFilter) else self.numFilters
        self.numFilters = self.numFilters + 1 if len(self.slotFilter) else self.numFilters
        self.numFilters = self.numFilters + 1 if len(self.authorFilter) else self.numFilters
        self.numFilters = self.numFilters + 1 if len(self.dateTimeFilter) else self.numFilters

    def getFilterAttribute(self, attr):
        filter = []

        if attr in self.filter:
            text = self.filter[attr]
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

        self.setupFilterOptions()
        self.setupNumFilters()

    def setFilter(self, f):
        self.filter = f
        self.prepareFilter()
        self.invalidateFilter()

    def setFilterActive(self, active):
        if self.filterActive != active:
            self.filterActive = active
            self.invalidateFilter()

    def filterAcceptsRow(self, sourceRow, sourceParent):
        if not self.filterActive:
            return True

        index1 = self.sourceModel().index(sourceRow, 0, sourceParent)
        row = self.sourceModel().getRowArray(index1.row())

        num = 0

        # Well name
        wn = row[1] #unicode
        if wn:
            wells = [wn for w in self.wellnameFilter if
                     fnmatch.fnmatchcase(wn, w) or (not self.caseSensitive and fnmatch.fnmatch(wn, w))]
            num = num + 1 if len(wells) else num

        # Fullname
        wn = row[2] #unicode
        if wn:
            wells = [wn for w in self.fullnameFilter if
                     fnmatch.fnmatchcase(wn, w) or (not self.caseSensitive and fnmatch.fnmatch(wn, w))]
            num = num + 1 if len(wells) else num

        # Operator
        wn = row[3]  #unicode
        if wn:
            wells = [wn for w in self.operatorFilter if
                     fnmatch.fnmatchcase(wn, w) or (not self.caseSensitive and fnmatch.fnmatch(wn, w))]
            num = num + 1 if len(wells) else num

        # API number
        wn = str(row[4])
        if wn:
            wells = [wn for w in self.apiFilter if
                     fnmatch.fnmatchcase(wn, w) or (not self.caseSensitive and fnmatch.fnmatch(wn, w))]
            num = num + 1 if len(wells) else num

        # Location
        wn = row[5] #unicode
        if wn:
            wells = [wn for w in self.locationFilter if
                     fnmatch.fnmatchcase(wn, w) or (not self.caseSensitive and fnmatch.fnmatch(wn, w))]
            num = num + 1 if len(wells) else num

        # Latitude
        wn = str(row[6])
        if wn:
            wells = [wn for w in self.latitudeFilter if
                     fnmatch.fnmatchcase(wn, w) or (not self.caseSensitive and fnmatch.fnmatch(wn, w))]
            num = num + 1 if len(wells) else num

        # Longitude
        wn = str(row[7])
        if wn:
            wells = [wn for w in self.longitudeFilter if
                     fnmatch.fnmatchcase(wn, w) or (not self.caseSensitive and fnmatch.fnmatch(wn, w))]
            num = num + 1 if len(wells) else num

        # Slot number
        wn = str(row[8])
        if wn:
            wells = [wn for w in self.slotFilter if
                     fnmatch.fnmatchcase(wn, w) or (not self.caseSensitive and fnmatch.fnmatch(wn, w))]
            num = num + 1 if len(wells) else num

        # Author
        wn = row[9] #unicode
        if wn:
            wells = [wn for w in self.authorFilter if
                     fnmatch.fnmatchcase(wn, w) or (not self.caseSensitive and fnmatch.fnmatch(wn, w))]
            num = num + 1 if len(wells) else num

        # DateTime
        wn = str(row[10])
        if wn:
            wells = [wn for w in self.dateTimeFilter if
                     fnmatch.fnmatchcase(wn, w) or (not self.caseSensitive and fnmatch.fnmatch(wn, w))]
            num = num + 1 if len(wells) else num

        use = False
        if self.logic == 'and':
            use = num == self.numFilters
        else:
            use = num > 0

        if self.method == 'include':
            return use
        else:
            return not use

        return True

    def lessThan(self, left, right):
        leftData = self.sourceModel().data(left, Qt.DisplayRole)
        rightData = self.sourceModel().data(right, Qt.DisplayRole)
        return leftData < rightData


class WellsItemsModel(QAbstractItemModel):
    def __init__(self, headerData, firstColumn = 0, parent=None, *args):
        super(WellsItemsModel, self).__init__(parent)
        self.arraydata = []
        self.checkStates = []
        self.headerdata = headerData
        self.firstColumn = firstColumn

    def setModelData(self, _arrayData):
        if len(_arrayData) > 0:
            if len(_arrayData[0]) != len(self.headerdata):
                QtGui.QMessageBox.critical(None, self.tr(u'Error'),
                                           self.tr(u'len(_arrayData) != len(self.headerdata) ({0} != {1})'.
                                                   format(len(_arrayData[0]), len(self.headerdata))),
                                           QtGui.QMessageBox.Ok)
                return

        self.beginResetModel()
        self.arraydata = _arrayData
        self.checkStates = [Qt.Checked for i in self.arraydata]
        self.endResetModel()

    def getRowArray(self, row):
        if row >= 0 and row < len(self.arraydata):
            return self.arraydata[row]
        else:
            return []

    def rowCount(self, parent=QModelIndex()):
        if parent.isValid():
            return 0
        return len(self.arraydata)

    def columnCount(self, parent=QModelIndex()):
        if parent.isValid():
            return 0
        return len(self.headerdata) - self.firstColumn

    def data(self, index, role):
        if not index.isValid():
            return None

        if role == Qt.DisplayRole or role == Qt.EditRole:
            return self.arraydata[index.row()][index.column() + self.firstColumn]
        elif role == Qt.CheckStateRole and index.column() == 0:
            return self.checkStates[index.row()]
        elif role == Qt.UserRole:
            return self.arraydata[index.row()][0]

        return None

    def setData(self, index, value, role):
        if not index.isValid():
            return False

        if role == Qt.CheckStateRole and index.column() == 0:
            self.checkStates[index.row()] = value
            return True

        return False

    def headerData(self, col, orientation, role):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.headerdata[col + self.firstColumn]
        return None

    def index(self, row, column, parent=QModelIndex()):
        if parent.isValid():
            return QModelIndex()

        if row < 0 or column < 0 or row >= self.rowCount(parent) or column >= self.columnCount(parent):
            return QModelIndex()

        return self.createIndex(row, column, None)

    def parent(self, index):
        return QModelIndex()

    def flags(self, index):
        if not index.isValid():
            return QtCore.Qt.NoItemFlags

        if index.column() > 0:
            return Qt.ItemIsEnabled | Qt.ItemIsSelectable
        else:
            return Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsUserCheckable

    def setCheckstateAll(self, checked):
        self.beginResetModel()
        self.checkStates = [checked for r in self.checkStates]
        self.endResetModel()
        # index1 = self.index(0, 0)
        # index2 = self.index(self.rowCount(), 0)
        # self.dataChanged.emit(index1, index2)
        
    def rowId(self,rowData):
        row=None
        try:
            row=self.arraydata.index(rowData)
        except:pass
        return row
        
    def getDataFiltered(self,filter_func=lambda row:True): 
        filterdata=filter(filter_func, self.arraydata)
        return filterdata
               
    def setCheckState(self, checked, row):
        if row >= 0 and row < len(self.arraydata):
            self.beginResetModel()
            self.checkStates[row]=checked
            self.endResetModel()
        
        
        
        
        
        
