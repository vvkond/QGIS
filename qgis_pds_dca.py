#!/usr/local/bin/python2.7
# -*- coding: utf-8 -*-

'''
Created on 8 апр. 2019 г.

@author: Alexey Russkikh
'''

# -*- coding: utf-8 -*-

import os
import numpy
import fnmatch
import ast
from struct import unpack_from
from qgis.core import *
from qgis.gui import QgsMessageBar
from qgis.PyQt import QtGui,QtCore, uic
from QgisPDS.db import Oracle
from QgisPDS.connections import create_connection
from utils import *
from bblInit import NAMES, Fields

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'qgis_pds_dca_base.ui'))



#===============================================================================
# 
#===============================================================================
class QgisPDSDCAForm(QtGui.QDialog, FORM_CLASS):
    """Constructor."""
    def __init__(self, _project, _iface, parent=None):
        super(QgisPDSDCAForm, self).__init__(parent)
        self.setupUi(self)
        self._db = None
        self.iface = _iface
        self.project = _project
        self.reservoirsListWidget.setSelectionMode( QtGui.QAbstractItemView.SingleSelection )
        
        reservoirs = self._getReservoirs()
        if reservoirs is not None:
            for reservoir_part_code,order_num in reservoirs:
                reservoirName = to_unicode("".join(reservoir_part_code))
                item = QtGui.QListWidgetItem(reservoirName)
                if self.reservoirsListWidget.isEnabled():
                    self.reservoirsListWidget.addItem(item)
                    self.reservoirsListWidget.setItemSelected(item, False)
        #self.buttonBox.setEnabled(len(self.wells)>0)
        if len(self.wells)>0:
            self.setWindowTitle(u"Select reservoir for calculation")
            self.buttonBox.button( QtGui.QDialogButtonBox.Ok).setEnabled(True)
            pass
        else:
            self.setWindowTitle(u"You must select wells")
            self.buttonBox.button( QtGui.QDialogButtonBox.Ok).setEnabled(False)
            pass
    #===========================================================
    # 
    #===========================================================
    @property
    def reservoir_groups(self):
        selectedReservoirs=[]
        for item in self.reservoirsListWidget.selectedItems():
            selectedReservoirs.append(item.text())
        return selectedReservoirs
    #===========================================================================
    # 
    #===========================================================================
    @property
    def db(self):
        if self._db is None:
            QtGui.QMessageBox.critical(None, self.tr(u'Error'), self.tr(u'No current PDS project'), QtGui.QMessageBox.Ok)            
        else:
            return self._db
    @db.setter
    def db(self,val):
        self._db=val

    #===========================================================================
    # read reservoirs names from DB
    #===========================================================================
    def _getReservoirs(self):
        connection = create_connection(self.project)
        scheme = self.project['project']
        try:           
            self.db = connection.get_db(scheme)
            sql = self.get_sql('ReservoirZones.sql')
            result = self.db.execute(sql)
            # db.disconnect()
            return result
            
        except Exception as e:
            QgsMessageLog.logMessage(u"Project production read error {0}: {1}".format(scheme, str(e)), tag="QgisPDS.Error")
            return None

    #=======================================================================
    # 
    #=======================================================================
    def get_sql(self, value):
        plugin_dir = os.path.dirname(__file__)
        sql_file_path = os.path.join(plugin_dir, 'db', value)
        with open(sql_file_path, 'rb') as f:
            return f.read().decode('utf-8')
    #===============================================================================
    # 
    #===============================================================================
    @property
    def wells(self):
        res=[]
        layer = self.iface.activeLayer()
        if layer is not None:
            selected_features = layer.selectedFeatures()
            for i in selected_features:
                try:
                    #i.fieldNameIndex('well_id')
                    val=i.attribute(Fields.WellId.name)
                    res.append(val)
                except:
                    QgsMessageLog.logMessage(u"Error get well_id for '{}'".format(str(i.attributes())), tag="QgisPDS.DCA")
        return res
       
    #===========================================================================
    # 
    #===========================================================================
    def accept(self):
        self.hide() # QDialog always modal,so hide it
        
        from QgisPDS.type_well.autoDCA_new import DCA
        for reg in self.reservoir_groups:
            QgsMessageLog.logMessage(u"Reservoir '{}'".format(reg), tag="QgisPDS.DCA")
            a=DCA(reservoir_group=reg, well_names=self.wells, conn=self.db.connection)
            a.process()
             
        pass




        