# -*- coding: utf-8 -*-

import os
import numpy
import fnmatch
import ast
from struct import unpack_from
from qgis.core import *
from qgis.gui import QgsMessageBar
from PyQt4 import QtGui, uic
from PyQt4.QtGui import *
from PyQt4.QtCore import *

from QgisPDS.db import Oracle
from QgisPDS.connections import create_connection
from utils import *
from QgisPDS.tig_projection import *
from qgis_pds_CoordFromZone import QgisPDSCoordFromZoneDialog
from qgis_pds_zoneparams import QgisPDSZoneparamsDialog
from qgis_pds_WellFilterSetup import QgisPDSWellFilterSetupDialog
from qgis_pds_templateList import QgisPDSTemplateListDialog
from qgis_pds_wellsModel import *

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'wellsBrowserForm_base.ui'))

class QgisPDSWellsBrowserForm(QtGui.QWidget, FORM_CLASS):
    """Constructor."""
    def __init__(self, _iface, _db, getWellsFunc, _project, parent=None, selectedIds=None, markedIdsCol=0 ,markedIds=None, isDisableUnmarkedItems=False, allowCheckRow=True ):
        super(QgisPDSWellsBrowserForm, self).__init__(parent)
        self.setupUi(self)

        self.project = _project
        self.db = _db
        self.iface = _iface
        self.wellFilter = {}
        self.wellListId = -1
        self.wellList = []
        self.selectedIds=selectedIds   # list of wellIds that must be Checked by default.
        self.mark=[[markedIdsCol,markedIds]] if markedIds is not None else []  # list of list '[column_id,[list wellIds]]' that must be marked.
        self.isDisableUnmarkedItems=isDisableUnmarkedItems
        # self.wellFilter = wellFilter
        # self.wellListId = wellListId
        self.getWellsFunc = getWellsFunc
        # self.wellList = []
        if _project:
            self.scheme = _project['project']

        self.restoreFilter()

        #Setup toolButton icons
        self.mWellFilterToolButton.setIcon(QIcon(':/plugins/QgisPDS/mActionFilter.png'))
        self.mWellListToolButton.setIcon(QIcon(':/plugins/QgisPDS/list.png'))
        self.mSelectAll.setIcon(QIcon(':/plugins/QgisPDS/checked_checkbox.png'))
        self.mUnselectAll.setIcon(QIcon(':/plugins/QgisPDS/unchecked_checkbox.png'))
        self.mToggleSelected.setIcon(QIcon(':/plugins/QgisPDS/toggle.png'))
        self.mSaveWellList.setIcon(QIcon(':/plugins/QgisPDS/mActionFileSave.png'))


        #Selectors menu
        filterMenu = QMenu(self)
        filterMenu.addAction(self.actionSetupFilter)
        self.actionSetupFilter.triggered.connect(self.selectWellFilter)
        self.mWellFilterToolButton.setMenu(filterMenu)

        listMenu = QMenu(self)
        listMenu.addAction(self.actionSelectList)
        self.actionSelectList.triggered.connect(self.selectWellList)
        self.mWellListToolButton.setMenu(listMenu)

        #Active toolButtons
        # self.mWellListToolButton.blockSignals(True)
        # self.mWellFilterToolButton.blockSignals(True)
        #
        # self.mWellListToolButton.setChecked(wellListActive)
        # self.mWellFilterToolButton.setChecked(wellFilterActive)
        #
        # self.mWellListToolButton.blockSignals(False)
        # self.mWellFilterToolButton.blockSignals(False)

        #Read wells data
        self.getWells()

        #Setup data model
        headerData = [self.tr('Well id'), self.tr('Well name'), self.tr('Full name'),
                      self.tr('Operator'), self.tr('API number'), self.tr('Location'),
                      self.tr('Latitude'), self.tr('Longitude'), self.tr('Slot number'),
                      self.tr('Created by'), self.tr('Updated')]
        self.wellItemModel = WellsItemsModel(headerData, 1, self, allowCheckRow=allowCheckRow)
        self.wellItemModel.setModelData(self.wellList)
        
        self.updateRowMarks()
        self.updateRowCheckStates()
        #Setup proxy model
        self.wellItemProxyModel = WellsItemsProxyModel(self)
        self.wellItemProxyModel.setSourceModel(self.wellItemModel)
        self.wellItemProxyModel.setFilter(self.wellFilter)
        self.wellItemProxyModel.setFilterActive(self.mWellFilterToolButton.isChecked())
        self.mWellsTreeView.setModel(self.wellItemProxyModel)
        
        if not self.wellItemModel.allowCheckRow:
            self.mSelectAll.setEnabled(False)
            self.mUnselectAll.setEnabled(False)
            self.mToggleSelected.setEnabled(False)


    def updateRowCheckStates(self):
        if self.selectedIds is not None:
            self.wellItemModel.setCheckstateAll(checked=Qt.Unchecked)
            rows=[self.wellItemModel.rowId(item) for item in self.wellItemModel.getDataFiltered(filter_func=lambda row:row[self.wellItemModel.id_col] in self.selectedIds)]
            self.wellItemModel.setCheckState(checked=Qt.Checked, rows=rows )
        else:
            self.wellItemModel.setCheckstateAll(checked=Qt.Checked)
            
    def updateRowMarks(self):
        if len(self.mark)>0:
            self.wellItemModel.markData(markValue=QBrush(QColor('red')) ,markRole=Qt.ForegroundRole )
            for mark_col,mark_ids in self.mark:
                self.wellItemModel.markData(markedLineIds=mark_ids, markedIdColumn=mark_col
                                            , markValue=QBrush(QColor('green')) ,markRole=Qt.ForegroundRole 
                                            , unMarkedItemFlag=Qt.ItemIsEnabled if self.isDisableUnmarkedItems else None# | Qt.ItemIsSelectable
                                            )

    def getWells(self):
        if self.mWellListToolButton.isChecked() and self.wellListId > 0:
            dlg = QgisPDSTemplateListDialog(self.db, self.wellListId)
            self.wellList = dlg.getWells(self.wellListId)
        else:
            self.wellList = self.getWellsFunc()
        return

    def applyFilter(self, sender, needSave, forceFilter = False):
        self.wellFilter = sender.getFilter()
        self.wellItemProxyModel.setFilter(self.wellFilter)
        if forceFilter:
            self.mWellFilterToolButton.setChecked(True)
            self.wellItemProxyModel.setFilterActive(True)

    def refreshWells(self):
        self.getWells()
        self.wellItemModel.setModelData(self.wellList)
        self.updateRowMarks()

    def getSelectedWells(self, id_col=None):
        '''
            @param id_col: id of column for return values 
        '''
        well_ids = []
        if id_col is not None:
            id_bckp=self.wellItemModel.id_col
            self.wellItemModel.id_col=id_col
        for numRow in xrange(self.wellItemProxyModel.rowCount()):
            index = self.wellItemProxyModel.index(numRow, 0)
            checked = self.wellItemProxyModel.data(index, Qt.CheckStateRole)
            if checked == Qt.Checked:
                id = self.wellItemProxyModel.data(index, Qt.UserRole)
                well_ids.append(id)
        if id_col is not None:
            self.wellItemModel.id_col=id_bckp
        return well_ids

    @property
    def currentFilter(self):
        return self.wellFilter

    @property
    def isWellFilterActive(self):
        return self.mWellFilterToolButton.isChecked()

    @property
    def currentWellListId(self):
        return self.wellListId

    @property
    def isWellListActive(self):
        return self.mWellListToolButton.isChecked()


    @pyqtSlot(bool)
    def on_mWellFilterToolButton_toggled(self, checked):
        self.wellItemProxyModel.setFilterActive(checked)
        self.updateRowMarks()
        self.updateRowCheckStates()

    @pyqtSlot(bool)
    def on_mWellListToolButton_toggled(self, checked):
        if self.wellListId > 0:
            self.getWells()
            self.wellItemModel.setModelData(self.wellList)
            self.updateRowMarks()
            self.updateRowCheckStates()
        elif checked:
            self.selectWellList()

    def selectWellFilter(self):
        dlg = QgisPDSWellFilterSetupDialog(self.iface, self)
        dlg.setFilter(self.wellFilter)
        if dlg.exec_():
            self.wellFilter = dlg.getFilter()
            self.wellItemProxyModel.setFilter(self.wellFilter)
            self.wellItemProxyModel.setFilterActive(True)
            self.mWellFilterToolButton.setChecked(True)
            self.updateRowMarks()
            self.updateRowCheckStates()
        del dlg

    def selectWellList(self):
        dlg = QgisPDSTemplateListDialog(self.db, self.wellListId, False, self)
        if dlg.exec_():
            self.wellListId = dlg.getListId()
            if self.wellListId:
                self.wellList = dlg.getWells(self.wellListId)
                self.mWellListToolButton.setChecked(True)
                self.wellItemModel.setModelData(self.wellList)
                self.updateRowMarks()
                self.updateRowCheckStates()
        del dlg

    @pyqtSlot()
    def on_mSelectAll_clicked(self):
        self.wellItemModel.setCheckstateAll(Qt.Checked)
        self.selectedIds=None

    @pyqtSlot()
    def on_mUnselectAll_clicked(self):
        self.wellItemModel.setCheckstateAll(Qt.Unchecked)
        self.selectedIds=None

    @pyqtSlot()
    def on_mToggleSelected_clicked(self):
        rows = self.mWellsTreeView.selectionModel().selectedRows(0)
        if rows:
            for r in rows:
                state = self.mWellsTreeView.model().data(r, Qt.CheckStateRole)
                if state == Qt.Checked:
                    self.mWellsTreeView.model().setData(r, Qt.Unchecked, Qt.CheckStateRole)
                else:
                    self.mWellsTreeView.model().setData(r, Qt.Checked, Qt.CheckStateRole)
                self.mWellsTreeView.model().dataChanged.emit(r, r)

    @pyqtSlot()
    def on_mSaveWellList_clicked(self):
        well_ids = []
        for numRow in xrange(self.wellItemProxyModel.rowCount()):
            index = self.wellItemProxyModel.index(numRow, 0)
            checked = self.wellItemProxyModel.data(index, Qt.CheckStateRole)
            if checked == Qt.Checked:
                id = self.wellItemProxyModel.data(index, Qt.UserRole)
                well_ids.append(id)

        if len(well_ids) < 1:
            return

        dlg = QgisPDSTemplateListDialog(self.db, self.wellListId, False, self)
        dlg.setReadOnly(False)
        if dlg.exec_():
            dlg.saveList(well_ids, self.project)

        del dlg

    def hideEvent(self, event):
        className = type(self).__name__
        QSettings().setValue('/PDS/{0}/HeaderState'.format(className), self.mWellsTreeView.header().saveState())

        self.saveFilter()

        super(QgisPDSWellsBrowserForm, self).hideEvent(event)

    def showEvent(self, event):
        super(QgisPDSWellsBrowserForm, self).showEvent(event)

        className = type(self).__name__
        state = QSettings().value('/PDS/{0}/HeaderState'.format(className))
        if state:
            self.mWellsTreeView.header().restoreState(state)

    def saveFilter(self):
        try:
            varName = '/PDS/Zonations/WellFilter/v' + self.scheme
            QSettings().setValue(varName, str(self.wellFilter))

            varName = '/PDS/Zonations/wellFilterActive/v' + self.scheme
            QSettings().setValue(varName, 'True' if self.isWellFilterActive else 'False')

            varName = '/PDS/Zonations/wellListActive/v' + self.scheme
            QSettings().setValue(varName, 'True' if self.isWellListActive else 'False')

            varName = '/PDS/Zonations/wellListId/v' + self.scheme
            QSettings().setValue(varName, self.currentWellListId)
        except Exception as e:
            QgsMessageLog.logMessage('Save WellFilter: ' + str(e), 'QGisPDS')


    def restoreFilter(self):
        try:
            varName = '/PDS/Zonations/WellFilter/v' + self.scheme
            filterStr = QSettings().value(varName, '{}')
            self.wellFilter = ast.literal_eval(filterStr)

            varName = '/PDS/Zonations/wellFilterActive/v' + self.scheme
            wellFilterActive = QSettings().value(varName, 'False') == 'True'

            varName = '/PDS/Zonations/wellListActive/v' + self.scheme
            wellListActive = QSettings().value(varName, 'False') == 'True'

            varName = '/PDS/Zonations/wellListId/v' + self.scheme
            self.wellListId = int(QSettings().value(varName, "0"))

            self.mWellListToolButton.blockSignals(True)
            self.mWellFilterToolButton.blockSignals(True)

            self.mWellListToolButton.setChecked(wellListActive)
            self.mWellFilterToolButton.setChecked(wellFilterActive)

            self.mWellListToolButton.blockSignals(False)
            self.mWellFilterToolButton.blockSignals(False)

        except Exception as e:
            QgsMessageLog.logMessage('Restore WellFilter: ' + str(e), 'QGisPDS')