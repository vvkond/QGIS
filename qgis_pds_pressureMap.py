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
from qgis_pds_production import QgisPDSProductionDialog
from bblInit import *
from tig_projection import *

class QgisPDSPressure(QgisPDSProductionDialog):
    def __init__(self, project, iface, isCP=True, _layer=None, parent=None):
        """Constructor."""
        super(QgisPDSPressure, self).__init__(project, iface, isCP, _layer, parent)

        self.attrWellId = u'well_id'
        self.attrPressure = u'pressure'
        self.setWindowTitle(self.tr(u'Pressure map'))

        self.mAddAllWells.setVisible(False)
        self.startDateEdit.setEnabled(True)
        self.firstDate.setEnabled(True)

        self.plugin_dir = os.path.dirname(__file__)

    #read reservoirs names from DB
    def _getReservoirs(self):
        connection = create_connection(self.project)
        scheme = self.project['project']
        try:           
            self.db = connection.get_db(scheme)
            result = self.db.execute("select distinct ACTIVITY_NAME from WTST_MEAS where BSASC_SOURCE='KVD' and CONTAINING_ACT_T='WTST_MEAS' and CONTAINING_ACT_S is not NULL and ACTIVITY_NAME is not NULL")
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
        self.uri += '&field={}:{}'.format("zonation", "string")
        self.uri += '&field={}:{}'.format("top_zone", "string")
        self.uri += '&field={}:{}'.format("base_zone", "string")
        self.uri += '&field={}:{}'.format("reservoir", "string")
        self.uri += '&field={}:{}'.format("LablX", "double")
        self.uri += '&field={}:{}'.format("LablY", "double")
        self.uri += '&field={}:{}'.format("LablOffX", "double")
        self.uri += '&field={}:{}'.format("LablOffY", "double")
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
        palyr.fieldName = self.attrWellId
        palyr.placement = QgsPalLayerSettings.OverPoint
        palyr.quadOffset = QgsPalLayerSettings.QuadrantAboveRight
        palyr.setDataDefinedProperty(QgsPalLayerSettings.OffsetXY, True, True,
                                     'format(\'%1,%2\', "LablOffX" , "LablOffY")', '')
        palyr.labelOffsetInMapUnits = False
        palyr.setDataDefinedProperty(QgsPalLayerSettings.Size, True, True, '8', '')
        palyr.setDataDefinedProperty(QgsPalLayerSettings.PositionX, True, False, '', 'LablX')
        palyr.setDataDefinedProperty(QgsPalLayerSettings.PositionY, True, False, '', 'LablY')
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

                    if pres != -9999:
                        f = QgsFeature(self.layer.fields())
                        pt = QgsPoint(lng, lat)
                        if self.xform:
                            pt = self.xform.transform(pt)

                        geom = QgsGeometry.fromPoint(pt)
                        f.setGeometry(geom)
                        f.setAttribute(self.attrWellId, well_name)
                        f.setAttribute(self.attrPressure, pres)
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