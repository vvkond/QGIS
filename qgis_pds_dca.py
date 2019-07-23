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
import pandas as pd
from type_well.autoDCA_new import get_config

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'qgis_pds_dca_base.ui'))


#===============================================================================
# 
#===============================================================================
class QgisPDSDCAForm(QtGui.QDialog, FORM_CLASS,WithSql):
    """Constructor."""
    def __init__(self, _project, _iface, parent=None):
        super(QgisPDSDCAForm, self).__init__(parent)
        self.setupUi(self)
        self._db = None
        self.conf = {}      # Dictionary of QTWidget with config parameters
        self.conf_setter={} # Dictionary of setter/gettervalue in self.conf
        self.conf_getter={} # Dictionary of setter/gettervalue in self.conf
        self._need_views=['view_V_PROD_RECORDS.sql','view_V_PROD_RESPART_M2.sql']
        
        self.iface = _iface
        self.project = _project
        self.reservoirsListWidget.setSelectionMode( QtGui.QAbstractItemView.SingleSelection )
        
        connection = create_connection(self.project)
        scheme = self.project['project']
        self.db = connection.get_db(scheme)
        self._create_views()
        
        res=[]
        #self.buttonBox.setEnabled(len(self.wells)>0)
        if len(self.wells)>0:
            self.setWindowTitle(u"Select reservoir for calculation")
            self.buttonBox.button( QtGui.QDialogButtonBox.Ok).setEnabled(True)
            reg = self._getReservoirGroups(wells=self.wells)            
            pass
        else:
            self.setWindowTitle(u"You must select wells")
            self.buttonBox.button( QtGui.QDialogButtonBox.Ok).setEnabled(False)
            reg = self._getReservoirGroups()
            pass
    
        if reg is not None:
            for reservoir_group_code in reg:
                reservoirName = to_unicode("".join(reservoir_group_code))
                item = QtGui.QListWidgetItem(reservoirName)
                if self.reservoirsListWidget.isEnabled():
                    self.reservoirsListWidget.addItem(item)
                    self.reservoirsListWidget.setItemSelected(item, False)
        self.init_gui_config()
    #===========================================================================
    # 
    #===========================================================================
    def init_gui_config(self):
        """
            
            
            ,perhour=1 #defaults is 24
            ,persecond=1 #default is 3600
            ,window_size=5 #size of Sample for calculkation        
        """
        conf={}
        conf_setter={} # Dictionary of setter/gettervalue in self.conf
        conf_getter={} # Dictionary of setter/gettervalue in self.conf
        
        hh=[]
        tableWidget = QtGui.QTableWidget()
        tableWidget.setColumnCount(1)
        tableWidget.setRowCount(0)
        tableWidget.setHorizontalHeaderLabels(["value"])
        col=0
        
        #--- forecast_end='2029'
        tableWidget.insertRow(tableWidget.rowCount())
        name='forecast_end'
        val = QtGui.QDateEdit()
        val.setMaximumDateTime(QtCore.QDateTime(QtCore.QDate(7999, 12, 28), QtCore.QTime(23, 59, 59)))
        val.setDate(QtCore.QDate(2029, 01,01) )
        val.setCalendarPopup(False)   
        val.setDisplayFormat("yyyy");
        setter=lambda widget,val:widget.setDate(QtCore.QDate(int(val), 01,01) )
        getter=lambda widget:int(widget.date().toString('yyyy'))
        hh.append(name)
        tableWidget.setCellWidget(tableWidget.rowCount()-1,col,val)
        conf[name]=val
        conf_setter[name]=setter
        conf_getter[name]=getter
        
        #--- MinRate=0.158988  #One barrel per day
        tableWidget.insertRow(tableWidget.rowCount())
        name='MinRate'
        val=QtGui.QDoubleSpinBox()
        val.setValue(0.158988)
        setter=lambda widget,val:widget.setValue(float(val) )
        getter=lambda widget:widget.value()
        hh.append(name)
        tableWidget.setCellWidget(tableWidget.rowCount()-1,col,val)
        conf[name]=val
        conf_setter[name]=setter
        conf_getter[name]=getter
        
        #--- MaxWC=0.99
        tableWidget.insertRow(tableWidget.rowCount())
        name='MaxWC'
        val=QtGui.QDoubleSpinBox()
        val.setValue(0.99)
        setter=lambda widget,val:widget.setValue(float(val) )
        getter=lambda widget:widget.value()
        hh.append(name)
        tableWidget.setCellWidget(tableWidget.rowCount()-1,col,val)
        conf[name]=val
        conf_setter[name]=setter
        conf_getter[name]=getter
        
                
        #--- threshold=0.1
        tableWidget.insertRow(tableWidget.rowCount())
        name='threshold'
        val=QtGui.QDoubleSpinBox()
        setter=lambda widget,val:widget.setValue(float(val) )
        getter=lambda widget:widget.value()
        val.setValue(0.1) 
        hh.append(name)
        tableWidget.setCellWidget(tableWidget.rowCount()-1,col,val)
        conf[name]=val  
        conf_setter[name]=setter
        conf_getter[name]=getter
        
        
        #--- window_size=5 #size of Sample for calculkation
        tableWidget.insertRow(tableWidget.rowCount())
        name='window_size'
        val=QtGui.QSpinBox()
        setter=lambda widget,val:widget.setValue(int(val) )
        getter=lambda widget:widget.value()
        val.setValue(5) 
        hh.append(name)
        tableWidget.setCellWidget(tableWidget.rowCount()-1,col,val)
        conf[name]=val      
        conf_setter[name]=setter
        conf_getter[name]=getter


        #--- LastPointFcst=True
        tableWidget.insertRow(tableWidget.rowCount())
        name='LastPointFcst'
        val=QtGui.QCheckBox()
        val.setCheckState(True)
        val.setTristate(False)
        setter=lambda widget,val:widget.setChecked(False if val in ['False',0,'0'] else True)
        getter=lambda widget:widget.isChecked()
        hh.append(name) 
        tableWidget.setCellWidget(tableWidget.rowCount()-1,col,val)   
        conf[name]=val     
        conf_setter[name]=setter
        conf_getter[name]=getter

        #--- LastDateFcst=False
        tableWidget.insertRow(tableWidget.rowCount())
        name='LastDateFcst'
        val=QtGui.QCheckBox()
        val.setCheckState(False)
        val.setTristate(False)
        setter=lambda widget,val:widget.setChecked(False if val in ['False',0,'0'] else True)
        getter=lambda widget:widget.isChecked()
        hh.append(name) 
        tableWidget.setCellWidget(tableWidget.rowCount()-1,col,val)   
        conf[name]=val     
        conf_setter[name]=setter
        conf_getter[name]=getter

        #--- EndFitFcst=False
        tableWidget.insertRow(tableWidget.rowCount())
        name='EndFitFcst'
        val=QtGui.QCheckBox()
        val.setCheckState(False)
        val.setTristate(False)
        setter=lambda widget,val:widget.setChecked(False if val in ['False',0,'0'] else True)
        getter=lambda widget:widget.isChecked()
        hh.append(name) 
        tableWidget.setCellWidget(tableWidget.rowCount()-1,col,val)   
        conf[name]=val     
        conf_setter[name]=setter
        conf_getter[name]=getter

        #--- perhour=1 #defaults is 24
        tableWidget.insertRow(tableWidget.rowCount())
        name='perhour'
        val=QtGui.QSpinBox()
        val.setValue(1) 
        setter=lambda widget,val:widget.setValue(int(val) )
        getter=lambda widget:widget.value()
        hh.append(name)
        tableWidget.setCellWidget(tableWidget.rowCount()-1,col,val)
        conf[name]=val        
        conf_setter[name]=setter
        conf_getter[name]=getter

        #--- persecond=1 #default is 3600
        tableWidget.insertRow(tableWidget.rowCount())
        name='persecond'
        val=QtGui.QSpinBox()
        val.setValue(1) 
        setter=lambda widget,val:widget.setValue(int(val) )
        getter=lambda widget:widget.value()
        hh.append(name)
        tableWidget.setCellWidget(tableWidget.rowCount()-1,col,val)
        conf[name]=val        
        conf_setter[name]=setter
        conf_getter[name]=getter

        #--- LastPointFcst=True
        tableWidget.insertRow(tableWidget.rowCount())
        name='UseTypeWell'
        val=QtGui.QCheckBox()
        val.setCheckState(True)
        val.setTristate(False)
        setter=lambda widget,val:widget.setChecked(False if val in ['False',0,'0'] else True)
        getter=lambda widget:widget.isChecked()
        hh.append(name) 
        tableWidget.setCellWidget(tableWidget.rowCount()-1,col,val)   
        conf[name]=val
        conf_setter[name]=setter
        conf_getter[name]=getter
             
        #---
        tableWidget.setVerticalHeaderLabels(hh)
        self.configPanel.addWidget(tableWidget)
        self.conf=conf
        self.conf_getter=conf_getter
        self.conf_setter=conf_setter
        
        self.readSettings()
                
    #===========================================================================
    # 
    #===========================================================================
    def parse_gui_config(self):
        return  get_config(
                        forecast_end=   str(self.conf['forecast_end'].date().toString('yyyy'))
                        ,MinRate=        self.conf['MinRate'].value()
                        ,MaxWC=          self.conf['MaxWC'].value()
                        ,threshold=      self.conf['threshold'].value()
                        ,LastPointFcst=  self.conf['LastPointFcst'].isChecked()
                        ,LastDateFcst=   self.conf['LastDateFcst'].isChecked()
                        ,EndFitFcst=     self.conf['EndFitFcst'].isChecked()
                        ,perhour=        self.conf['perhour'].value()
                        ,persecond=      self.conf['persecond'].value()
                        ,window_size=    self.conf['window_size'].value()
                        ,UseTypeWell=    self.conf['UseTypeWell'].isChecked()
                )        
        
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
    def _create_views(self):
        for view in self._need_views:
            QgsMessageLog.logMessage(u"Update view '{}'".format(view), tag="QgisPDS.DCA")
            sql = self.get_sql(view)
            pd.io.sql.execute(sql,self.db.connection)
        pass
    #===========================================================================
    # read reservoirs names from DB
    #===========================================================================
    def _getReservoirGroups(self,wells=None):
        try:           
            sql = self.get_sql('WellReservoirs.sql')
            SELECT=sql.format(
                WELL_FILTER='' if wells is None else "AND w.WELL_ID in ('{}')".format("','".join(map(str,wells)))
                ,RP_FILTER=''
                ,GRP_FILTER=''
                )
            res_df=pd.read_sql(SELECT,self.db.connection)
            return res_df[u'GRP_CODE'].sort_values(ascending=True).unique()
            
        except Exception as e:
            QgsMessageLog.logMessage(u"Project reservoir group read error {0}: {1}".format(scheme, str(e)), tag="QgisPDS.Error")
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
    #========================================================================
    # 
    #========================================================================
    def writeSettings(self):
        settings = QSettings()
        for name,widget in self.conf.items():
            settings.setValue("/PDS/dca/{}".format(name), str(self.conf_getter[name](widget)) )
        pass
    #========================================================================
    # 
    #========================================================================
    def readSettings(self):
        settings = QSettings()
        for name,widget in self.conf.items():
            val=settings.value("/PDS/dca/{}".format(name), None)
            if val is not None:
                self.conf_setter[name](widget,val)
        pass
    
    #===========================================================================
    # 
    #===========================================================================
    def accept(self):
        self.writeSettings()
        self.hide() # QDialog always modal,so hide it
        
        from QgisPDS.type_well.autoDCA_new import DCA
        for reg in self.reservoir_groups:
            QgsMessageLog.logMessage(u"Reservoir '{}'".format(reg), tag="QgisPDS.DCA")
            
            dca=DCA(reservoir_group=reg, well_names=self.wells, conn=self.db.connection, config=self.parse_gui_config())
            dca.process()
        pass




        