# -*- coding: utf-8 -*-

import os

from qgis.core import *
from qgis.gui import QgsMessageBar
from PyQt4 import QtGui,QtCore, uic

from collections import namedtuple

from os.path import abspath
import json
import ast

from QgisPDS.db import Oracle
from QgisPDS.connections import create_connection
from utils import *
from bblInit import *
from tig_projection import *
import traceback
import pandas as pd
import datetime

IS_DEBUG=False
#===============================================================================
# https://stackoverflow.com/questions/23407295/default-kwarg-values-for-pythons-str-format-method
#===============================================================================
'''
    @info: Class for use like '{'a'} {'b'}'.format(**{'a':1,'b':2})
            Because str.format(**kwargs) not allowed we can use:
                fmt=UnseenFormatter()
                fmt.format(str,**kwargs)
'''
from string import Formatter
class UnseenFormatter(Formatter):
    def get_value(self, key, args, kwds):
        if isinstance(key, str) or isinstance(key, unicode) :
            try:
                return kwds[key]
            except KeyError:
                return key
        else:
            return Formatter.get_value(key, args, kwds)


#===============================================================================
# 
#===============================================================================
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'qgis_pds_pressure_base.ui'))

class QgisPDSPressure(QtGui.QDialog, FORM_CLASS):

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
    # fillReservoirsListWidget
    #===========================================================================
    def fillReservoirsListWidget(self):
        self.readReservoirOrders()
        reservoirs = self._getReservoirs()
        self.reservoirs = []
        if not len(self.mSelectedReservoirs)>0:
            self.mSelectedReservoirs = self.selected_reservoirs
        self.reservoirsListWidget.clear() 
        if reservoirs is not None:
            for reservoir_part_code in reservoirs:
                reservoirName = to_unicode(u"".join(reservoir_part_code))
                self.reservoirs.append(NAMES(name=reservoirName, selected=True))
                item = QtGui.QListWidgetItem(reservoirName)
                isSelected = item.text() in self.mSelectedReservoirs
                if self.reservoirsListWidget.isEnabled():
                    self.reservoirsListWidget.addItem(item)
                    self.reservoirsListWidget.setItemSelected(item, isSelected)
                elif isSelected:
                    self.reservoirsListWidget.addItem(item)
          
    #===========================================================================
    # 
    #===========================================================================
    def _getProjection(self):
        self.proj4String = QgisProjectionConfig.get_default_layer_prj_epsg()
        connection = create_connection(self.project)
        scheme = self.project['project']
        try:
            self.db = connection.get_db(scheme)
            self.tig_projections = TigProjections(db=self.db)
            proj = self.tig_projections.get_projection(self.tig_projections.default_projection_id)
            if proj is not None:
                self.proj4String = 'PROJ4:'+proj.qgis_string
                destSrc = QgsCoordinateReferenceSystem()
                destSrc.createFromProj4(proj.qgis_string)
                sourceCrs = QgsCoordinateReferenceSystem(QgisProjectionConfig.get_default_latlon_prj_epsg())
                #self.xform = QgsCoordinateTransform(sourceCrs, destSrc)
                self.xform=get_qgis_crs_transform(sourceCrs,destSrc,self.tig_projections.fix_id)
        except Exception as e:
            QgsMessageLog.logMessage(u"Project projection read error {0}: {1}".format(scheme, str(e)), tag="QgisPDS.Error")
#             self.progressMessageBar.pushCritical(self.tr("Error"),
#                                                 self.tr(u'Project projection read error {0}: {1}').format(
#                                                 scheme, str(e))
#                                                 )
            return

        

    #===========================================================================
    # readReservoirOrders
    #===========================================================================
    def readReservoirOrders(self):
        sql = ("select reservoir_part.reservoir_part_code, "
            " p_equipment_fcl.string_value "
            " from p_equipment_fcl, equipment_insl, "
            " reservoir_part "
            "where reservoir_part.entity_type_nm = 'RESERVOIR_ZONE' "
            " and equipment_insl.equipment_item_s = p_equipment_fcl.object_s "
            " and reservoir_part.reservoir_part_s = equipment_insl.facility_s "
            " and p_equipment_fcl.bsasc_source = 'order no'")

        QgsMessageLog.logMessage(u"Execute readReservoirOrders: {}\\n\n".format(sql), tag="QgisPDS.sql")
        result = self.db.execute(sql)
        if result is not None:
            for reservoirId, reservoirNumber in result:
                self.reservoirNumbers.append(reservoirNumber)
                self.reservoirIds.append(reservoirId)

    #===========================================================================
    # on_buttonBox_accepted
    #===========================================================================
    def on_buttonBox_accepted(self):
        try:
            self.createDataLayer()
        except Exception as e:
            QgsMessageLog.logMessage(u"error: {}\n\n".format(traceback.format_exc()), tag="QgisPDS.erro")
            raise e
        
    def isInitialised(self):
        return self.initialised

    #===========================================================================
    # lastDateClicked
    #===========================================================================
    def lastDateClicked(self, checked):
        sql=self._getPressureSQL(reservoirs_lst=self.selected_reservoirs, pressure_load_types=self.selected_pressure)
        if len(sql)>0:        
            sql="select max(start_time) as start_time from ({})".format(sql)
            tmp_df = pd.read_sql(sql
                                 ,self.db.connection
                                 ,params={
                                 'start_limit':datetime.datetime.strptime(QtCore.QDateTime().fromString('19000101 00:00', 'yyyyMd h:m').toString(u'dd.MM.yyyy HH:mm:ss'),'%d.%m.%Y %H:%M:%S')
                                 ,'end_limit':datetime.datetime.strptime( QtCore.QDateTime().currentDateTime().toString(u'dd.MM.yyyy HH:mm:ss'),'%d.%m.%Y %H:%M:%S'  )
                                 }
                                 )   
            
            if len(tmp_df.index)>0:
                dt=QtCore.QDateTime().fromString( tmp_df['START_TIME'].max().strftime('%Y%m%d %H:%M') , 'yyyyMd h:m')
                self.endDateEdit.setDateTime(dt.addDays(1))
        self.lastDate.setChecked(False)

    #===========================================================================
    # firstDateClicked
    #===========================================================================
    def firstDateClicked(self, checked):
        sql=self._getPressureSQL(reservoirs_lst=self.selected_reservoirs, pressure_load_types=self.selected_pressure)
        if len(sql)>0:
            sql="select min(start_time) as start_time from ({})".format(sql)
            tmp_df = pd.read_sql(sql
                                 ,self.db.connection
                                 ,params={
                                 'start_limit':datetime.datetime.strptime(QtCore.QDateTime().fromString('19000101 00:00', 'yyyyMd h:m').toString(u'dd.MM.yyyy HH:mm:ss'),'%d.%m.%Y %H:%M:%S')
                                 ,'end_limit':datetime.datetime.strptime( QtCore.QDateTime().currentDateTime().toString(u'dd.MM.yyyy HH:mm:ss'),'%d.%m.%Y %H:%M:%S'  )
                                 }
                                 )   
            if len(tmp_df.index)>0:
                dt=QtCore.QDateTime().fromString( tmp_df['START_TIME'].min().strftime('%Y%m%d %H:%M') , 'yyyyMd h:m')
                self.startDateEdit.setDateTime(dt)
        self.firstDate.setChecked(False)
    #===========================================================================
    # __init__
    #===========================================================================
    def __init__(self, project, iface, _layer=None, parent=None):
        """Constructor."""
        super(QgisPDSPressure, self).__init__(parent)
        
        self.setupUi(self)
        self.initialised = False
        self.layer = _layer
        self._db = None
        self.reservoirsListWidget.setEnabled(self.layer is None)
        self.iface = iface
        self.project = project
        if self.project is None:
            QtGui.QMessageBox.critical(None, self.tr(u'Error'), self.tr(u'No current PDS project'), QtGui.QMessageBox.Ok)
            return
            
        self.mSelectedReservoirs = []
        self.reservoirNumbers = []
        self.reservoirIds = []

        self._getProjection()

        self.realEndDate = QtCore.QDate()
        self.realStartDate = QtCore.QDate()
        self.firstDate.setEnabled(True)
        self.lastDate.setEnabled(True)

        ########################
        self.attrWellId = u'well_id'
        self.attrPressure = u'pressure'
        self.attrDate = u'date'
        self.attrDepth = u'depth'
        self.setWindowTitle(self.tr(u'Pressure map'))

        self.startDateEdit.setEnabled(True)

        self.plugin_dir = os.path.dirname(__file__)
        
        '''Pressure variants'''
        self.SQL_Reservoirs=""
        self.init_gui_config()
        
        self.initialised = True

    #===========================================================================
    # 
    #===========================================================================
    def init_gui_config(self):
        """
        """
        conf={}
        conf_setter={} # Dictionary of setter/gettervalue in self.conf
        conf_getter={} # Dictionary of setter/gettervalue in self.conf
        
        hh=[]
        #tableWidget = QtGui.QTableWidget(self.pressurePanel)
        tableWidget=self.configWidget
        tableWidget.setColumnCount(1)
        tableWidget.setRowCount(0)
        tableWidget.setHorizontalHeaderLabels([""])
        col=0
        
        self.C_KVD=   self.tr('KVD')
        self.C_DynP=  self.tr('Dynamic BottomHole')
        self.C_DynCP= self.tr('Dynamic Calculated BottomHole')
        self.C_StP=   self.tr('Static BottomHole')
        self.C_StCP=  self.tr('Static Calculated BottomHole')
        
        #--- KVD
        tableWidget.insertRow(tableWidget.rowCount())
        name=self.C_KVD
        val=QtGui.QCheckBox()
        val.setCheckState(False)
        val.setTristate(False)
        val.stateChanged.connect(self.on_pressure_stateChanged)
        setter=lambda widget,val:widget.setChecked(False if val in ['False',0,'0'] else True)
        getter=lambda widget:widget.isChecked()
        hh.append(name) 
        tableWidget.setCellWidget(tableWidget.rowCount()-1,col,val)   
        conf[name]=val     
        conf_setter[name]=setter
        conf_getter[name]=getter

        #--- Dynamic BottomHole
        tableWidget.insertRow(tableWidget.rowCount())
        name=self.C_DynP
        val=QtGui.QCheckBox()
        val.setCheckState(False)
        val.setTristate(False)
        val.stateChanged.connect(self.on_pressure_stateChanged)
        setter=lambda widget,val:widget.setChecked(False if val in ['False',0,'0'] else True)
        getter=lambda widget:widget.isChecked()
        hh.append(name) 
        tableWidget.setCellWidget(tableWidget.rowCount()-1,col,val)   
        conf[name]=val     
        conf_setter[name]=setter
        conf_getter[name]=getter

        #--- DynamicCalculatedBottomHole
        tableWidget.insertRow(tableWidget.rowCount())
        name=self.C_DynCP
        val=QtGui.QCheckBox()
        val.setCheckState(False)
        val.setTristate(False)
        val.stateChanged.connect(self.on_pressure_stateChanged)
        setter=lambda widget,val:widget.setChecked(False if val in ['False',0,'0'] else True)
        getter=lambda widget:widget.isChecked()
        hh.append(name) 
        tableWidget.setCellWidget(tableWidget.rowCount()-1,col,val)   
        conf[name]=val     
        conf_setter[name]=setter
        conf_getter[name]=getter
   
        #--- Static BottomHole
        tableWidget.insertRow(tableWidget.rowCount())
        name=self.C_StP
        val=QtGui.QCheckBox()
        val.setCheckState(False)
        val.setTristate(False)
        val.stateChanged.connect(self.on_pressure_stateChanged)
        setter=lambda widget,val:widget.setChecked(False if val in ['False',0,'0'] else True)
        getter=lambda widget:widget.isChecked()
        hh.append(name) 
        tableWidget.setCellWidget(tableWidget.rowCount()-1,col,val)   
        conf[name]=val     
        conf_setter[name]=setter
        conf_getter[name]=getter

        #--- Static Calculated BottomHole
        tableWidget.insertRow(tableWidget.rowCount())
        name=self.C_StCP
        val=QtGui.QCheckBox()
        val.setCheckState(False)
        val.setTristate(False)
        val.stateChanged.connect(self.on_pressure_stateChanged)
        setter=lambda widget,val:widget.setChecked(False if val in ['False',0,'0'] else True)
        getter=lambda widget:widget.isChecked()
        hh.append(name) 
        tableWidget.setCellWidget(tableWidget.rowCount()-1,col,val)   
        conf[name]=val     
        conf_setter[name]=setter
        conf_getter[name]=getter

        #---
        tableWidget.setVerticalHeaderLabels(hh)
        #self.pressurePanel.addWidget(tableWidget)
        self.conf=conf
        self.conf_getter=conf_getter
        self.conf_setter=conf_setter
        
        self.readSettings()
    
    #===========================================================================
    # on_pressure_stateChanged
    #===========================================================================
    def on_pressure_stateChanged(self,state):
        QgsMessageLog.logMessage(u"on_pressure_stateChanged", tag="QgisPDS.debug")
        sqls=[]
        for name,subSql in [
                    [self.C_KVD     ,  "select distinct ACTIVITY_NAME from WTST_MEAS where BSASC_SOURCE='KVD' and CONTAINING_ACT_T='WTST_MEAS' and CONTAINING_ACT_S is not NULL and ACTIVITY_NAME is not NULL"]
                    ,[self.C_DynP   ,  "select distinct ACTIVITY_NAME from WTST_MEAS where BSASC_SOURCE='Pressure' and CONTAINING_ACT_T='WTST_MEAS' and TYPICAL_ACT_NAME='dyn'  and R_EXISTENCE_KD_NM='actual'     and CONTAINING_ACT_S is not NULL and ACTIVITY_NAME is not NULL"]
                    ,[self.C_StP    ,  "select distinct ACTIVITY_NAME from WTST_MEAS where BSASC_SOURCE='Pressure' and CONTAINING_ACT_T='WTST_MEAS' and TYPICAL_ACT_NAME='stat' and R_EXISTENCE_KD_NM='actual'     and CONTAINING_ACT_S is not NULL and ACTIVITY_NAME is not NULL"]
                    ,[self.C_DynCP  ,  "select distinct ACTIVITY_NAME from WTST_MEAS where BSASC_SOURCE='Pressure' and CONTAINING_ACT_T='WTST_MEAS' and TYPICAL_ACT_NAME='dyn'  and R_EXISTENCE_KD_NM='calculated' and CONTAINING_ACT_S is not NULL and ACTIVITY_NAME is not NULL"]
                    ,[self.C_StCP   ,  "select distinct ACTIVITY_NAME from WTST_MEAS where BSASC_SOURCE='Pressure' and CONTAINING_ACT_T='WTST_MEAS' and TYPICAL_ACT_NAME='stat' and R_EXISTENCE_KD_NM='calculated' and CONTAINING_ACT_S is not NULL and ACTIVITY_NAME is not NULL"]
            ]:
            if self.conf[name].isChecked():
                sqls.append(subSql)
        sql=''
        if len(sqls)>0:
            sql="SELECT distinct ACTIVITY_NAME from ({}) ORDER BY ACTIVITY_NAME".format(" UNION ALL ".join(sqls))
        self.SQL_Reservoirs=sql
        QgsMessageLog.logMessage(u"sql={}".format(sql), tag="QgisPDS.debug")
        self.fillReservoirsListWidget()
        
        pass

    #===========================================================================
    # #read reservoirs names from DB
    #===========================================================================
    def _getReservoirs(self):
        connection = create_connection(self.project)
        scheme = self.project['project']
        try:           
            self.db = connection.get_db(scheme)
            sql=self.SQL_Reservoirs
            QgsMessageLog.logMessage(u"Execute _getReservoirs: {}\\n\n".format(sql), tag="QgisPDS.sql")
            if len(sql)>0 and sql is not None:
                result = self.db.execute(sql)
                # db.disconnect()
                return result
            else:
                return None
        except Exception as e:
            self.iface.messageBar().pushMessage(self.tr("Error"), 
                self.tr(u'Read production from project {0}: {1}').format(scheme, str(e)), level=QgsMessageBar.CRITICAL)
            return None
    #===============================================================================
    # 
    #===============================================================================
    def get_sql(self, value):
        sql_file_path = os.path.join(self.plugin_dir, 'db', value)
        with open(sql_file_path, 'rb') as f:
            return f.read().decode('utf-8')


    #===========================================================================
    # createQgisLayer
    #===========================================================================
    def createQgisLayer(self):
        layerName = 'Pressure'
        self.uri = "Point?crs={}".format(self.proj4String)
        self.uri += '&field={}:{}'.format(self.attrWellId, "string")
        self.uri += '&field={}:{}'.format(self.attrPressure, "double")
        self.uri += '&field={}:{}'.format(self.attrDate, "date")        
        self.uri += '&field={}:{}'.format(self.attrDepth, "double")
        self.uri += '&field={}:{}'.format("type", "string")
        self.uri += '&field={}:{}'.format("reservoir", "string")
        self.uri += '&field={}:{}'.format("desc", "string")

        for field in FieldsForLabels:
            self.uri += field.memoryfield
        
        self.layer = QgsVectorLayer(self.uri, layerName, "memory")

        if self.layer is None:
            QtGui.QMessageBox.critical(None, self.tr(u'Error'), self.tr(
                u'Error create pressure layer'), QtGui.QMessageBox.Ok)
            return

        self.layer = memoryToShp(self.layer, self.project['project'], layerName)

        # self.layer.startEditing()

        self.layer.setCustomProperty("qgis_pds_type", "pds_wells")
        self.layer.setCustomProperty("pds_project", str(self.project))

        palyr = QgsPalLayerSettings()
        palyr.readFromLayer(self.layer)
        palyr.enabled = True
        palyr.fieldName = self.attrPressure
        palyr.placement = QgsPalLayerSettings.OverPoint
        palyr.quadOffset = QgsPalLayerSettings.QuadrantAboveRight
        palyr.setDataDefinedProperty(QgsPalLayerSettings.OffsetXY, True, True,
                                     'format(\'%1,%2\', "LablOffX" , "LablOffY")', '')
        palyr.labelOffsetInMapUnits = False
        palyr.distInMapUnits = True
        palyr.displayAll = True
        palyr.fontSizeInMapUnits = False
        palyr=layer_to_labeled(palyr)  #---enable EasyLabel             
        
        palyr.writeToLayer(self.layer)
        
    #===========================================================================
    # getPressureDf
    #===========================================================================
    def _getPressureSQL(self,reservoirs_lst,pressure_load_types=None):
        '''
            @param pressure_load_types: List of pressure type for load
        '''
        if pressure_load_types is None:
            pressure_load_types=[self.C_KVD,self.C_DynP,self.C_StP,self.C_DynCP,self.C_StCP]
        reservoirs = u"'" + u"','".join(reservoirs_lst) + u"'"
        wells_df = self._readDbWells()
        if wells_df is None:
            return
        #wellsldnid="({})".format(','.join(map(str,wells_df['DB_SLDNID'].unique().tolist())))
        wellsldnid=NULL
        st_t='STUDY.START_TIME'
        en_t='STUDY.END_TIME'
        fmt = UnseenFormatter()
        sqls=[]
        for (name,query_id,query_params) in [ 
                 [self.C_KVD    , 'pressure.kvd.sql' , {'st_t':st_t,'en_t':en_t,'reservoirs':reservoirs                      ,'wellsldnid':wellsldnid        }]
                ,[self.C_DynP   , 'pressure.BH.sql'  , {'st_t':st_t,'en_t':en_t,'reservoirs':reservoirs ,'name':self.C_DynP  ,'wellsldnid':wellsldnid , 'stat_dyn':'dyn',  'calc_meas':'actual' }]
                ,[self.C_StP    , 'pressure.BH.sql'  , {'st_t':st_t,'en_t':en_t,'reservoirs':reservoirs ,'name':self.C_StP   ,'wellsldnid':wellsldnid , 'stat_dyn':'stat', 'calc_meas':'actual' }]
                ,[self.C_DynCP  , 'pressure.BH.sql'  , {'st_t':st_t,'en_t':en_t,'reservoirs':reservoirs ,'name':self.C_DynCP ,'wellsldnid':wellsldnid , 'stat_dyn':'dyn',  'calc_meas':'calculated' }]
                ,[self.C_StCP   , 'pressure.BH.sql'  , {'st_t':st_t,'en_t':en_t,'reservoirs':reservoirs ,'name':self.C_StCP  ,'wellsldnid':wellsldnid , 'stat_dyn':'stat', 'calc_meas':'calculated' }]
                ]: 
            if name in pressure_load_types:
                sql = fmt.format(self.get_sql(query_id),**query_params)
                sqls.append(sql)
        sql=''
        if len(sqls)>0:
            sql="""SELECT
                        v_pressure
                        ,v_meas_depth
                        ,press_name
                        ,start_time
                        ,end_time
                        ,well_name
                        ,reservoir
                        ,description
                    FROM ({})
                    where 
                        start_time>= :start_limit
                        and start_time< :end_limit
                    """.format(" \nUNION ALL\n  ".join(sqls))
        IS_DEBUG and QgsMessageLog.logMessage(u"FULL SQL: {}\n\n".format(sql), tag="QgisPDS.sql")
        return sql
#         result_df = pd.read_sql(sql
#                              ,self.db.connection
#                              ,params={
#                              'start_limit':datetime.datetime.strptime(minQDt.toString(u'dd.MM.yyyy HH:mm:ss'),'%d.%m.%Y %H:%M:%S')
#                              ,'end_limit':datetime.datetime.strptime( maxQDt.toString(u'dd.MM.yyyy HH:mm:ss'),'%d.%m.%Y %H:%M:%S'  )
#                              }
#                              )   
#         return result_df
    #=========================================================================
    # 
    #=========================================================================
    @property
    def selected_pressure(self):
        return [name for name in [ self.C_KVD ,self.C_DynP ,self.C_StP ,self.C_DynCP ,self.C_StCP] if self.conf[name].isChecked()]      
    #===========================================================================
    # selected_reservoirs
    #===========================================================================
    '''
    return selected in reservoirsListWidget items
    '''
    @property
    def selected_reservoirs(self):
        selectedReservoirs = []
            
        for item in self.reservoirsListWidget.selectedItems():
            selectedReservoirs.append(item.text())
        return selectedReservoirs
    #===========================================================================
    # createDataLayer
    #===========================================================================
    def createDataLayer(self):
        self.createQgisLayer()

        self.mStartDate = self.startDateEdit.dateTime() 
        self.mEndDate =   self.endDateEdit.dateTime()
        self.mSelectedReservoirs = self.selected_reservoirs
        
        wells_df = self._readDbWells()
        if wells_df is None:
            return
         
        sql= self._getPressureSQL(reservoirs_lst=self.mSelectedReservoirs, pressure_load_types=self.selected_pressure)
        if len(sql)>0:
            result_df = pd.read_sql(sql
                                 ,self.db.connection
                                 ,params={
                                 'start_limit':datetime.datetime.strptime(self.mStartDate.toString(u'dd.MM.yyyy HH:mm:ss'),'%d.%m.%Y %H:%M:%S')
                                 ,'end_limit':datetime.datetime.strptime( self.mEndDate.toString(u'dd.MM.yyyy HH:mm:ss'),'%d.%m.%Y %H:%M:%S'  )
                                 }
                                 )   
            
            if self.isOnlyLast.isChecked():   
                IS_DEBUG and QgsMessageLog.logMessage(u"result_df: {}\n\n".format(result_df), tag="QgisPDS.debug")
                maxdt_df=result_df[result_df.groupby(['WELL_NAME'])['START_TIME'].transform(max) == result_df['START_TIME']]
                wellpress_df=wells_df.merge(maxdt_df, left_on='TIG_LATEST_WELL_NAME', right_on='WELL_NAME')
            else:
                wellpress_df=wells_df.merge(result_df, left_on='TIG_LATEST_WELL_NAME', right_on='WELL_NAME')
            with edit(self.layer):
                for idx,row in wellpress_df.iterrows():
                    f = QgsFeature(self.layer.fields())
                    pt = QgsPoint(row['TIG_LONGITUDE'], row['TIG_LATITUDE'])
                    if self.xform:
                        pt = self.xform.transform(pt)
                    geom = QgsGeometry.fromPoint(pt)
                    f.setGeometry(geom)
                    f.setAttribute(self.attrWellId   , row['TIG_LATEST_WELL_NAME'])
                    f.setAttribute(self.attrPressure , row['V_PRESSURE'])
                    f.setAttribute(self.attrDepth    , row['V_MEAS_DEPTH'])
                    f.setAttribute(self.attrDate     , QtCore.QDateTime().fromString(row['START_TIME'].strftime('%Y-%m-%d %H:%M'), 'yyyy-M-d h:m'))
                    f.setAttribute('reservoir'       , row['RESERVOIR'])
                    f.setAttribute('type'            , row['PRESS_NAME'])
                    f.setAttribute('desc'            , row['DESCRIPTION'])
                
                    self.layer.addFeatures([f])
            self.writeSettings()
            self.db.disconnect()
            QgsMapLayerRegistry.instance().addMapLayer(self.layer)
         

    #===========================================================================
    # _readDbWells
    #===========================================================================
    def _readDbWells(self):
        try:
            result = pd.read_sql("select DB_SLDNID, tig_latest_well_name, tig_latitude, tig_longitude from tig_well_history"
                                 ,self.db.connection
                                 )                
            return result
        except Exception as e:
            self.iface.messageBar().pushMessage(self.tr(u'Error'), str(e), level=QgsMessageBar.CRITICAL)
            return None
        
        
    #===========================================================================
    # readSettings
    #===========================================================================
    def readSettings(self):
        settings = QtCore.QSettings()
        self.mStartDate =          settings.value("/PDS/pressure/startDate", QtCore.QDateTime().currentDateTime())
        self.mEndDate =            settings.value("/PDS/pressure/endDate",   QtCore.QDateTime().currentDateTime())
        self.mSelectedReservoirs = settings.value("/PDS/pressure/selectedReservoirs")

        if self.mSelectedReservoirs is None:
            self.mSelectedReservoirs = []

        for name,widget in self.conf.items():
            val=settings.value("/PDS/pressure/{}".format(name), None)
            if val is not None:
                self.conf_setter[name](widget,val)
                
        self.on_pressure_stateChanged(False)
        self.firstDateClicked(False)
        self.lastDateClicked(False)
        
    #===========================================================================
    # writeSettings
    #===========================================================================
    def writeSettings(self):
        settings = QtCore.QSettings()
        settings.setValue("/PDS/pressure/startDate"         , self.mStartDate)
        settings.setValue("/PDS/pressure/endDate"           , self.mEndDate)
        settings.setValue("/PDS/pressure/selectedReservoirs", self.mSelectedReservoirs)

        for name,widget in self.conf.items():
            settings.setValue("/PDS/pressure/{}".format(name), str(self.conf_getter[name](widget)) )        
            
            
            
            
            
            
            