# -*- coding: utf-8 -*-

import os

from qgis.core import *
from qgis.gui import QgsMessageBar
from PyQt4 import QtGui, uic
from PyQt4.QtGui import *
from PyQt4.QtCore import *
from collections import namedtuple

from os.path import abspath
import json
import ast

from QgisPDS.db import Oracle
from QgisPDS.connections import create_connection
from utils import *
from bblInit import *
from tig_projection import *




FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'qgis_pds_pressure_base.ui'))
class QgisPDSPressureDialog(QtGui.QDialog, FORM_CLASS):
    """
        @TODO: Its temporary revert of QgisPDSProductionDialog for pressure read. Need change pressure read dialog!!!
    """    
    @property
    def db(self):
        if self._db is None:
            QtGui.QMessageBox.critical(None, self.tr(u'Error'), self.tr(u'No current PDS project'), QtGui.QMessageBox.Ok)            
        else:
            return self._db
    @db.setter
    def db(self,val):
        self._db=val
    
    def createProductionLayer(self):
        pass
    def _getReservoirs(self):
        pass
    
    
    def __init__(self, project, iface, _layer=None, parent=None):
        """Constructor."""
        super(QgisPDSPressureDialog, self).__init__(parent)       
        
        self.setupUi(self)

        self.initialised = False
        self.layer = _layer
        self._db = None

        self.reservoirsListWidget.setEnabled(self.layer is None)
        
        self.attrWellId = u'well_id'
        self.attrLatitude = u'latitude'
        self.attrLongitude = u'longitude'
        self.attrDays = u'days'
        self.attrSymbolId = u'symbolid'
        self.attrSymbol = u'symbolcode'
        self.attrSymbolName = u'symbolname'
        self.attrLiftMethod = u'liftmethod'
        self.attr_lablx = "lablx"
        self.attr_lably = "lably"
        self.attr_labloffx = "labloffx"
        self.attr_labloffy = "labloffy"
        self.attr_labloffset = "labloffset"
        self.attr_lablwidth = "lablwidth"
        self.attr_bubblesize = "bubblesize"
        self.attr_bubblefields = OLD_NEW_FIELDNAMES[1] #"bubblefields"
        self.attr_scaletype = "scaletype"
        self.attr_movingres = "movingres"
        self.attr_resstate = "resstate"
        self.attr_multiprod = "multiprod"
        self.attr_labels = 'bbllabels'
        self.attr_startDate = 'startdate'

        self.dateFormat = u'dd/MM/yyyy HH:mm:ss'

        self.iface = iface
        self.project = project
        if self.project is None:
            QtGui.QMessageBox.critical(None, self.tr(u'Error'), self.tr(u'No current PDS project'), QtGui.QMessageBox.Ok)
            return
            
        self.mSelectedReservoirs = []
        self.mPhaseFilter = []
        self.mProductionWells = []
        self.mWells = {}
        self.reservoirNumbers = []
        self.reservoirIds = []
        
        self.readSettings()

        if self.layer:
            self.mSelectedReservoirs = ast.literal_eval(self.layer.customProperty("pds_prod_SelectedReservoirs"))
        
        self.endDateEdit.setDateTime(self.mEndDate)
        self.startDateEdit.setDateTime(self.mStartDate)

        self._getProjection()

        self.readReservoirOrders()

        reservoirs = self._getReservoirs()
        self.reservoirs = []
        if reservoirs is not None:
            for reservoir_part_code in reservoirs:
                reservoirName = to_unicode("".join(reservoir_part_code))
                self.reservoirs.append(NAMES(name=reservoirName, selected=True))
                item = QtGui.QListWidgetItem(reservoirName)
                isSelected = item.text() in self.mSelectedReservoirs
                if self.reservoirsListWidget.isEnabled():
                    self.reservoirsListWidget.addItem(item)
                    self.reservoirsListWidget.setItemSelected(item, isSelected)
                elif isSelected:
                    self.reservoirsListWidget.addItem(item)

        self.realEndDate = QDate()
        self.realStartDate = QDate()
        self.firstDate.setEnabled(False)
        self.lastDate.setEnabled(False)

        self.initialised = True
        
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


    def getReservoirOrder(self, reservoir):
        if reservoir in self.reservoirIds:
            idx = self.reservoirIds.index(reservoir)
            if idx is not None:
                return self.reservoirNumbers[idx]
        return 0


    def isLower(self, reservoirs1, reservoirs2):
        for name1 in reservoirs1:
            if name1.selected:
                for name2 in reservoirs2:
                    if name2.selected and self.getReservoirOrder(name1.name)<=self.getReservoirOrder(name2.name):
                        return False
        return True


    def isUpper(self, reservoirs1, reservoirs2):
        for name1 in reservoirs1:
            if name1.selected:
                for name2 in reservoirs2:
                    if name2.selected and self.getReservoirOrder(name1.name)>=self.getReservoirOrder(name2.name):
                        return False
        return True


    def intersectReservoirs(self, reservoirs1, reservoirs2):
        res = []
        for name1 in reservoirs1:
            if name1.selected:
                for name2 in reservoirs2:
                    if name2.selected and name1.name == name2.name:
                        res.append(NAMES(name=name1.name, selected=True))

        return res

    def subtractReservoirs(self, reservoirs1, reservoirs2):
        res = []
        for name1 in reservoirs1:
            if name1.selected:
                f = False
                for name2 in reservoirs2:
                    if name2.selected and name1.name == name2.name:
                        f = True
                        break

                if not f:
                    res.append(NAMES(name=name1.name, selected=True))

        return res

    def isEqualReservoirs(self, reservoirs1, reservoirs2):
        res1 = self.subtractReservoirs(reservoirs1, reservoirs2)
        res2 = self.subtractReservoirs(reservoirs2, reservoirs1)
        return len(res1) == 0 and len(res2) == 0


    def on_buttonBox_accepted(self):
        self.createProductionLayer()


    def isInitialised(self):
        return self.initialised


    def getLayer(self):
        return self.layer


    #Return TO_DATE oracle string 
    def to_oracle_date(self, qDate):
        # dateText = qDate.toString(self.dateFormat)
        # return "TO_DATE('"+dateText+"', 'DD/MM/YYYY HH24:MI:SS')"
        return self.db.stringToSqlDate(qDate)
        
    def to_oracle_char(self, field):
        return self.db.formatDateField(field)
        # return "TO_CHAR(" + field + ", 'DD/MM/YYYY HH24:MI:SS')"
        
    #return selected in reservoirsListWidget items
    def getSelectedReservoirs(self):
        selectedReservoirs = []
            
        for item in self.reservoirsListWidget.selectedItems():
            selectedReservoirs.append(item.text())
          
        return selectedReservoirs
        
    def lastDateClicked(self, checked):
        if checked:
            self.endDateEdit.setDateTime(self.realEndDate)
        else:
            self.endDateEdit.setDateTime(self.mEndDate)


    def firstDateClicked(self, checked):
        if checked:
            self.startDateEdit.setDateTime(self.realStartDate)
        else:
            self.startDateEdit.setDateTime(self.mStartDate)


    def readSettings(self):
        settings = QSettings()
        self.mStartDate = settings.value("/PDS/production/startDate", QDateTime().currentDateTime())
        self.mEndDate = settings.value("/PDS/production/endDate", QDateTime().currentDateTime())
        self.mSelectedReservoirs = settings.value("/PDS/production/selectedReservoirs")
        self.mPhaseFilter = settings.value("/PDS/production/selectedPhases")

        self.currentDiagramm = settings.value("/PDS/production/currentDiagramm", "1LIQUID_PRODUCTION")
        
        if self.mPhaseFilter is None:
            self.mPhaseFilter = []
        if self.mSelectedReservoirs is None:
            self.mSelectedReservoirs = []
        

    def writeSettings(self):
        settings = QSettings()
        settings.setValue("/PDS/production/startDate", self.mStartDate)
        settings.setValue("/PDS/production/endDate", self.mEndDate)
        settings.setValue("/PDS/production/selectedReservoirs", self.mSelectedReservoirs)
        settings.setValue("/PDS/production/selectedPhases", self.mPhaseFilter)

        settings.setValue("/PDS/production/currentDiagramm", self.currentDiagramm)


#===============================================================================
# 
#===============================================================================
class QgisPDSPressure(QgisPDSPressureDialog):
    def __init__(self, project, iface, _layer=None, parent=None):
        """Constructor."""
        super(QgisPDSPressure, self).__init__(project, iface, _layer, parent)

        self.attrWellId = u'well_id'
        self.attrPressure = u'pressure'
        self.attrDate = u'date'
        self.attrDepth = u'depth'
        self.setWindowTitle(self.tr(u'Pressure map'))

        self.startDateEdit.setEnabled(True)

        self.plugin_dir = os.path.dirname(__file__)

    #read reservoirs names from DB
    def _getReservoirs(self):
        connection = create_connection(self.project)
        scheme = self.project['project']
        try:           
            self.db = connection.get_db(scheme)
            sql="select distinct ACTIVITY_NAME from WTST_MEAS where BSASC_SOURCE='KVD' and CONTAINING_ACT_T='WTST_MEAS' and CONTAINING_ACT_S is not NULL and ACTIVITY_NAME is not NULL"
            QgsMessageLog.logMessage(u"Execute _getReservoirs: {}\\n\n".format(sql), tag="QgisPDS.sql")
            result = self.db.execute(sql)
            # db.disconnect()
            return result
        except Exception as e:
            self.iface.messageBar().pushMessage(self.tr("Error"), 
                self.tr(u'Read production from project {0}: {1}').format(scheme, str(e)), level=QgsMessageBar.CRITICAL)
            return None

    def get_sql(self, value):
        sql_file_path = os.path.join(self.plugin_dir, 'db', value)
        with open(sql_file_path, 'rb') as f:
            return f.read().decode('utf-8')


    def createQgisLayer(self):
        layerName = 'Pressure'
        self.uri = "Point?crs={}".format(self.proj4String)
        self.uri += '&field={}:{}'.format(self.attrWellId, "string")
        self.uri += '&field={}:{}'.format(self.attrPressure, "double")
        self.uri += '&field={}:{}'.format(self.attrDate, "date")        
        self.uri += '&field={}:{}'.format(self.attrDepth, "double")
        self.uri += '&field={}:{}'.format("zonation", "string")
        self.uri += '&field={}:{}'.format("top_zone", "string")
        self.uri += '&field={}:{}'.format("base_zone", "string")
        self.uri += '&field={}:{}'.format("reservoir", "string")

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
        
        #palyr.setDataDefinedProperty(QgsPalLayerSettings.Size, True, True, '8', '')
        #palyr.setDataDefinedProperty(QgsPalLayerSettings.PositionX, True, False, '', 'LablX')
        #palyr.setDataDefinedProperty(QgsPalLayerSettings.PositionY, True, False, '', 'LablY')
        palyr.writeToLayer(self.layer)
        
        # self.layer.commitChanges()


    def createProductionLayer(self):
        self.createQgisLayer()

        self.mEndDate = self.endDateEdit.dateTime()
        self.mStartDate = self.startDateEdit.dateTime() 

        self.mSelectedReservoirs = self.getSelectedReservoirs()
        
        reservoirs = u"'" + u"','".join(self.mSelectedReservoirs) + u"'"
        pressureSql = self.get_sql('pressure.kvd.sql').format(
                                                              self.db.formatDateField('STUDY.START_TIME')
                                                              ,self.db.formatDateField('STUDY.END_TIME')
                                                              , reservoirs
                                                              )
        QgsMessageLog.logMessage(u"pressureMap.createProductionLayer: {}\n\n".format(pressureSql), tag="QgisPDS.sql")
        wells = self._readDbWells()
        if wells is None:
            return

        with edit(self.layer):
            for sldnid, well_name, lat, lng in wells:
                records = self.db.execute(pressureSql, wellsldnid=sldnid)
                if records is not None:
                    pres = -9999
                    zonation = ''
                    top_zone_key = ''
                    base_zone_key = ''
                    reservoir = ''
                    stadat=''
                    findat=''
                    depth=''
                    for raw in records:
                        stadat = QDateTime.fromString(raw[5], self.dateFormat)
                        findat = QDateTime.fromString(raw[6], self.dateFormat)
                        if ((stadat >= self.mStartDate and stadat <= self.mEndDate) or
                            (findat >= self.mStartDate and findat <= self.mEndDate)):

                            pres = raw[0]
                            zonation = raw[1]
                            top_zone_key = raw[2]
                            base_zone_key = raw[3]
                            reservoir = raw[4]
                            depth = raw[7]

                    if pres != -9999:
                        f = QgsFeature(self.layer.fields())
                        pt = QgsPoint(lng, lat)
                        if self.xform:
                            pt = self.xform.transform(pt)

                        geom = QgsGeometry.fromPoint(pt)
                        f.setGeometry(geom)
                        f.setAttribute(self.attrWellId, well_name)
                        f.setAttribute(self.attrPressure, pres)
                        f.setAttribute(self.attrDepth, depth)
                        f.setAttribute(self.attrDate, stadat)
                        f.setAttribute('zonation', zonation)
                        f.setAttribute('top_zone', top_zone_key)
                        f.setAttribute('base_zone', base_zone_key)
                        f.setAttribute('reservoir', reservoir)

                        self.layer.addFeatures([f])


        self.writeSettings()
        self.db.disconnect()

        QgsMapLayerRegistry.instance().addMapLayer(self.layer)
        

    def _readDbWells(self):
        try:
            result = self.db.execute(
                "select DB_SLDNID, tig_latest_well_name, tig_latitude, tig_longitude from tig_well_history")

            
            return result
        except Exception as e:
            self.iface.messageBar().pushMessage(self.tr(u'Error'), str(e), level=QgsMessageBar.CRITICAL)
            return None