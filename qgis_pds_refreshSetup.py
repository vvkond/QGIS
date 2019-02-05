# -*- coding: utf-8 -*-

from qgis.core import *
from qgis.gui import QgsMessageBar
from qgis.PyQt.QtCore import *
from qgis.PyQt import QtGui, uic
from qgis.PyQt.QtGui import *
from qgis_pds_wellsBrowserDialog import QgisPDSWellsBrowserDialog
from qgis_pds_wells import QgisPDSWells
import ast
import os

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'qgis_pds_refreshSetup_base.ui'))
#===============================================================================
# 
#===============================================================================
class QgisPDSRefreshSetup(QtGui.QDialog, FORM_CLASS):
    def __init__(self, _iface, _project, parent=None, filterWellIds=None ):
        super(QgisPDSRefreshSetup, self).__init__(parent)
        self.filterWellIds = filterWellIds # list of well ids for read from base. 
        self.isNeedFilterWellIds = False   # need or not use self.filterWellIds

        self.setupUi(self)

        if _project:
            scheme = _project['project']
            if scheme:
                self.setWindowTitle(self.windowTitle() + ' - ' + scheme)

        self.restoreSettings()

        self.project = _project
        self.iface = _iface
    #===========================================================================
    # 
    #===========================================================================
    def on_button_OpenBrowser(self):
        dlg = QgisPDSWellsBrowserDialog(self.iface, self.project, selectedIds=self.filterWellIds)
        dlg
        if dlg.exec_():
            self.filterWellIds=dlg.getWellIds()
            self.isNeedFilterWellIds=True
        del dlg

    #===========================================================================
    # 
    #===========================================================================
    def on_buttonBox_accepted(self):
        self.saveSettings()
    #===========================================================================
    # 
    #===========================================================================
    def saveSettings(self):
        sett = QSettings()

        if self.isRefreshKoords:
            sett.setValue('PDS/refreshSetup/mKoordsCheckBox', 'True')
        else:
            sett.setValue('PDS/refreshSetup/mKoordsCheckBox', 'False')
        if self.isRefreshData:
            sett.setValue('PDS/refreshSetup/mDataCheckBox', 'True')
        else:
            sett.setValue('PDS/refreshSetup/mDataCheckBox', 'False')
        if self.isSelectedOnly:
            sett.setValue('PDS/refreshSetup/mSelectedCheckBox', 'True')
        else:
            sett.setValue('PDS/refreshSetup/mSelectedCheckBox', 'False')
        if self.isAddMissing:
            sett.setValue('PDS/refreshSetup/mAddMissingCheckBox', 'True')
        else:
            sett.setValue('PDS/refreshSetup/mAddMissingCheckBox', 'False')
        if self.isDeleteMissing:
            sett.setValue('PDS/refreshSetup/mDeleteMissingCheckBox', 'True')
        else:
            sett.setValue('PDS/refreshSetup/mDeleteMissingCheckBox', 'False')
            
        if self.isNeedFilterWellIds:
            sett.setValue('PDS/refreshSetup/mFilterWellIds', str(self.filterWellIds))
        else:
            sett.setValue('PDS/refreshSetup/mFilterWellIds', str(None))

    def restoreSettings(self):
        sett = QSettings()
        self.mKoordsCheckBox.setChecked(sett.value('PDS/refreshSetup/mKoordsCheckBox', 'True') == 'True')
        self.mDataCheckBox.setChecked(sett.value('PDS/refreshSetup/mDataCheckBox', 'True') == 'True')
        self.mSelectedCheckBox.setChecked(sett.value('PDS/refreshSetup/mSelectedCheckBox', 'False') == 'True')
        self.mAddMissingCheckBox.setChecked(sett.value('PDS/refreshSetup/mAddMissingCheckBox', 'False') == 'True')
        self.mDeleteMissingCheckBox.setChecked(sett.value('PDS/refreshSetup/mDeleteMissingCheckBox', 'False') == 'True')
        #try:
        #    self.filterWellIds = ast.literal_eval(sett.value('PDS/refreshSetup/mFilterWellIds'))
        #except: 
        #    self.filterWellIds =None

    @property
    def isRefreshKoords(self):
        return self.mKoordsCheckBox.isChecked()

    @property
    def isRefreshData(self):
        return self.mDataCheckBox.isChecked()

    @property
    def isSelectedOnly(self):
        return self.mSelectedCheckBox.isChecked()

    @property
    def isAddMissing(self):
        return self.mAddMissingCheckBox.isChecked()

    @property
    def isDeleteMissing(self):
        return self.mDeleteMissingCheckBox.isChecked()