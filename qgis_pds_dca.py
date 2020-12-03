#!/usr/local/bin/python2.7
# -*- coding: utf-8 -*-

'''
Created on 8 апр. 2019 г.

@author: Alexey Russkikh
'''


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
from type_well.autoDCA_new import get_config, get_reservoir_prop
import traceback

if sys.version_info[0] < 3: 
    from StringIO import StringIO
else:
    from io import StringIO


FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'qgis_pds_dca_base.ui'))


PROPS_TYPES=u"""
name;bsasc;desc
primary_product;primary product;Первичный продукт (oil/gas)"""
OIL_PROPS=u"""
name;bsasc;desc
propan_fraction;propan butan yield;Доля пропан-бутана, fr
GOR;GOR;Газовый фактор,sm3/m3 (70-130)
FF;shrinkage factor oil;Коэффициент усадки нефти, m3/m3"""
GAS_PROPS=u"""
name;bsasc;desc
cond_RFi;initial condensate yield factor;Начальный конденсатный фактор, sm2/MMsm3 (395-1200)
propan_fraction;propan butan yield;Доля пропан-бутана, fr
FF;expansion factor gas;Коэффициент расширения газа 1/Bg sm3/m3 (324-346)
WetGasShrink;wet gas shrinkage factor;Коэфф. усадки сырого газа, fr"""

PROPS={
    "gas":pd.read_csv(StringIO(GAS_PROPS),sep=";")
    ,"oil":pd.read_csv(StringIO(OIL_PROPS),sep=";")
    }
PROP_ID=pd.read_csv(StringIO(PROPS_TYPES),sep=";")["bsasc"][0]

def get_prop_desc(primary_product,prop_name):
    df=PROPS[primary_product]
    res=''
    try:
        res=df[df['name']==prop_name]['desc'].tolist()[0]
    except:
        pass
    return res

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
        
        self.conf_reservoir={}          # Dictionary of QTWidget with config parameters from table self.optTableWidget
        self.conf_reservoir_setter={}   # Dictionary of setter/gettervalue in self.conf_reservoir
        self.conf_reservoir_getter={}   # Dictionary of setter/gettervalue in self.conf_reservoir
        self.conf_reservoir_opt={}      # Dictionary of other reservoir static values
        
        self._need_views=['view_V_PROD_RECORDS.sql','view_V_PROD_RESPART_M2.sql']
        
        self.iface = _iface
        self.project = _project
        self.reservoirsListWidget.setSelectionMode( QtGui.QAbstractItemView.SingleSelection )
        self.optTableWidget=None
        
        connection = create_connection(self.project)
        scheme = self.project['project']
        self.db = connection.get_db(scheme)
        self._create_views()
        
        reg_df=[]
        #self.buttonBox.setEnabled(len(self.wells)>0)
        if len(self.wells)>0:
            self.setWindowTitle(u"Select reservoir for calculation")
            self.buttonBox.button( QtGui.QDialogButtonBox.Ok).setEnabled(True)
            reg_df = self._getReservoirGroups(wells=self.wells)            
            pass
        else:
            self.setWindowTitle(u"You must select wells")
            self.buttonBox.button( QtGui.QDialogButtonBox.Ok).setEnabled(False)
            reg_df = self._getReservoirGroups()
            pass
    
        if reg_df is not None:
            for _idx,row in reg_df.iterrows():
                reservoir_group_code=row[u'GRP_CODE']
                reservoir_group_id=row[u'GRP_ID']
                reservoirName = to_unicode("".join(reservoir_group_code))
                item = QtGui.QListWidgetItem(to_unicode(reservoirName))
                item.setData(Qt.UserRole, reservoir_group_id)
                if self.reservoirsListWidget.isEnabled():
                    self.reservoirsListWidget.addItem(item)
                    self.reservoirsListWidget.setItemSelected(item, False)
        self.reservoirsListWidget.itemSelectionChanged.connect(self.onRGSelectionChange)
        
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
        
        vh=[]
        tt=[]
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
        tt.append(u'Дата окончания прогноза')
        vh.append(name)
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
        tt.append(u'Ограничение минимального дебита')
        vh.append(name)
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
        tt.append(u'Ограничение максимальной обводненности')
        vh.append(name)
        tableWidget.setCellWidget(tableWidget.rowCount()-1,col,val)
        conf[name]=val
        conf_setter[name]=setter
        conf_getter[name]=getter
        
                
#         #--- threshold=0.1
#         tableWidget.insertRow(tableWidget.rowCount())
#         name='threshold'
#         val=QtGui.QDoubleSpinBox()
#         setter=lambda widget,val:widget.setValue(float(val) )
#         getter=lambda widget:widget.value()
#         val.setValue(0.1)
#         tt.append(u'Порог') 
#         vh.append(name)
#         tableWidget.setCellWidget(tableWidget.rowCount()-1,col,val)
#         conf[name]=val  
#         conf_setter[name]=setter
#         conf_getter[name]=getter
        
        
        #--- window_size=5 #size of Sample for calculkation
        tableWidget.insertRow(tableWidget.rowCount())
        name='window_size'
        val=QtGui.QSpinBox()
        setter=lambda widget,val:widget.setValue(int(val) )
        getter=lambda widget:widget.value()
        tt.append(u'Размер окна для расчета(минимальное кол-во скважин)')
        val.setValue(5) 
        vh.append(name)
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
        tt.append(u'Прогноз на последнюю точку')
        vh.append(name) 
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
        tt.append(u'Прогноз на последнюю дату')
        vh.append(name) 
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
        tt.append(u'EndFitFcst')
        vh.append(name) 
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
        tt.append(u'Коэффициент перевода в часы')
        vh.append(name)
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
        tt.append(u'Коэффициент перевода в секунды')
        vh.append(name)
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
        tt.append(u'Использовать алгоритм typewell')
        vh.append(name) 
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
        tt.append(u'Порог')
        vh.append(name)
        tableWidget.setCellWidget(tableWidget.rowCount()-1,col,val)
        conf[name]=val  
        conf_setter[name]=setter
        conf_getter[name]=getter
             
        #---
        tableWidget.setVerticalHeaderLabels(vh)
        for _idx,name in enumerate(vh):
            h=tableWidget.verticalHeaderItem(_idx)
            try:
                if h:
                    h.setToolTip(to_unicode(tt[_idx]))
                v=tableWidget.cellWidget(_idx,col)
                if v:
                    v.setToolTip(to_unicode(tt[_idx]))
            except Exception as e:
                QgsMessageLog.logMessage(u"Tooltip set error:{}".format( traceback.format_exc()), tag="QgisPDS.Error")
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
    #===========================================================================
    # 
    #===========================================================================
    def parse_gui_reservoir_config(self):
        return get_reservoir_prop(primary_product=self.conf_reservoir_opt['primary_product'],**dict([[key,item.value()] for key,item in self.conf_reservoir.items()]))
        
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
            return res_df[[u'GRP_CODE',u'GRP_ID']].sort_values(u'GRP_CODE',ascending=True).drop_duplicates()
            
        except Exception as e:
            QgsMessageLog.logMessage(u"Project reservoir group read error {0}".format( str(e)), tag="QgisPDS.Error")
            return None

    #===============================================================================
    # 
    #===============================================================================
    def _clear_reservoir_conf(self):
        if self.optTableWidget is not None:
            self.configPanel.removeWidget(self.optTableWidget)
            self.optTableWidget.setParent(None)
            self.optTableWidget=None
        self.conf_reservoir={}  
        self.conf_reservoir_setter={}
        self.conf_reservoir_getter={}
        self.conf_reservoir_opt={}
        
    #===============================================================================
    # 
    #===============================================================================
    def init_reservoir_conf(self,dict_of_values):
        conf_reservoir={}
        conf_reservoir_setter={}
        conf_reservoir_getter={}
        vh=[]
        col=0
        
        tableWidget = QtGui.QTableWidget()
        tableWidget.setColumnCount(1)
        tableWidget.setRowCount(0)
        tableWidget.setHorizontalHeaderLabels(["value"])
        self.optTableWidget=tableWidget
        
        #--- add labels for self.conf_reservoir_opt
        for name,value in self.conf_reservoir_opt.items():
            self.optTableWidget.insertRow(self.optTableWidget.rowCount())
            name=name
            val=QtGui.QLabel(str(value))
            setter=lambda widget,val:None
            getter=lambda widget:widget.text()
            val.setText(value) 
            #hh.append(name)
            self.optTableWidget.setCellWidget(self.optTableWidget.rowCount()-1,col,val)
            vh.append(name)
        
        #--- add configurable values for self.conf_reservoir
        for name,value in dict_of_values.items():
            self.optTableWidget.insertRow(self.optTableWidget.rowCount())
            name=name
            val=QtGui.QDoubleSpinBox()
            setter=lambda widget,val:widget.setValue(float(val) )
            getter=lambda widget:widget.value()
            val.setValue(value) 
            #hh.append(name)
            self.optTableWidget.setCellWidget(self.optTableWidget.rowCount()-1,col,val)
            #self.optTableWidget.setToolTip()
            conf_reservoir[name]=val  
            conf_reservoir_setter[name]=setter
            conf_reservoir_getter[name]=getter
            vh.append(name)
        
        tableWidget.setVerticalHeaderLabels(vh)
        for _idx,name in enumerate(vh):
            try:
                h=tableWidget.verticalHeaderItem(_idx)
                if h:
                    tt=get_prop_desc(primary_product=self.conf_reservoir_opt['primary_product'], prop_name=name)
                    h.setToolTip(to_unicode(tt))
                v=tableWidget.cellWidget(_idx,col)
                if v:
                    v.setToolTip(to_unicode(tt))
            except Exception as e:
                QgsMessageLog.logMessage(u"Tooltip set error:{}".format( traceback.format_exc()), tag="QgisPDS.Error")
                        
        self.configPanel.addWidget(tableWidget)
        self.conf_reservoir=conf_reservoir  
        self.conf_reservoir_setter=conf_reservoir_setter
        self.conf_reservoir_getter=conf_reservoir_getter
        
        
        
    #===============================================================================
    # 
    #===============================================================================
    def onRGSelectionChange(self):
        QgsMessageLog.logMessage(u"onRGSelectionChange", tag="QgisPDS.DCA")
        selectedRG=[]
        self._clear_reservoir_conf()
        for si in self.reservoirsListWidget.selectedItems():
            selectedRG.append(int(si.data(Qt.UserRole)))
        for rg in selectedRG:
            rg_prop_df=self._getReservoirGroupProperties(reservoir_group_s=rg)
            QgsMessageLog.logMessage(u"{}".format(str(rg_prop_df)), tag="QgisPDS.DCA")
        # --- Get df with properties for current primary_product
        primary_product='oil' 
        try:
            primary_product=rg_prop_df[rg_prop_df[u'PROPERY_NAME']==PROP_ID]["STRING_VALUE"].tolist()[0]
        except:
            pass
        product_prop_names=PROPS[primary_product]  # df with columns : name;bsasc;desc
        self.conf_reservoir_opt={'primary_product':primary_product}
        # --- Fill property values from rg_prop_df or from default values
        prop_dict={}
        for idx,row in product_prop_names.iterrows():
            try:
                prop_dict[row[u"name"]] = ( rg_prop_df[rg_prop_df[u'PROPERY_NAME']==row[u"bsasc"]][u"QUANTITY_VALUE"].tolist()[0] )
            except :
                prop_dict[row[u"name"]] =0                
        self.init_reservoir_conf(prop_dict)
        pass
    #===========================================================================
    # 
    #===========================================================================
    def _getReservoirGroupProperties(self,reservoir_group_s):
        try:           
            sql = self.get_sql('ReservoirGroupsProperty.sql')
            SELECT=sql.format(
                GRP_FILTER=" AND RP.RESERVOIR_PART_S={}".format(reservoir_group_s)
                )
            QgsMessageLog.logMessage(u"\n\nExecute:\n{}".format( str(SELECT)), tag="QgisPDS.sql")            
            res_df=pd.read_sql(SELECT,self.db.connection)
            return res_df
        except Exception as e:
            QgsMessageLog.logMessage(u"Project reservoir group read error: {}".format( str(traceback.format_exc())), tag="QgisPDS.Error")
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
            
            dca=DCA(reservoir_group=reg, well_names=self.wells, conn=self.db.connection, config=self.parse_gui_config(), reservoir_group_prop=self.parse_gui_reservoir_config())
            dca.process()
        pass




        