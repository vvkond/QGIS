# -*- coding: utf-8 -*-

import os
import numpy
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
from QgisPDS.qgis_pds_CoordFromZone import QgisPDSCoordFromZoneDialog
from QgisPDS.qgis_pds_zoneparams import QgisPDSZoneparamsDialog

class QgisPDSZonationsDialog(QgisPDSCoordFromZoneDialog):
    def __init__(self, _project, _iface, parent=None):
        """Constructor."""
        super(QgisPDSZonationsDialog, self).__init__(_project, _iface, None, parent)

        self.setWindowTitle(self.tr(u'Zonation parameters'))
        if _project:
            scheme = _project['project']
            if scheme:
                self.setWindowTitle(self.windowTitle() + ' - ' + scheme)


        self.mParameterFrame.setVisible(True)
        self.mWellsListWidget.setVisible(True)
        self.mWellLabel.setVisible(True)

        settings = QSettings()
        self.mUseElevation.setChecked(settings.value("/PDS/Zonations/UseElevation", u'True') == u'True')
        self.mUseErosion.setChecked(settings.value("/PDS/Zonations/UseErosion", u'False') == u'True')

        selectedParameters = QSettings().value("/PDS/Zonations/SelectedParameters", [])
        self.selectedParameters = [int(z) for z in selectedParameters]

        self.fillParameters()

    def on_zoneListWidget_itemSelectionChanged(self):
        zonation_id = None
        zone_id = None
        for zones in self.zoneListWidget.selectedItems():
            zoneDef = zones.data(Qt.UserRole)
            zonation_id = zoneDef[1]
            zone_id = zoneDef[0]

        self.mWellsListWidget.clear()
        sql = self.get_sql('ZonationParams_well.sql')
        records = self.db.execute(sql, zonation_id=zonation_id, zone_id=zone_id)
        if records:
            for input_row in records:
                item = QListWidgetItem(input_row[0])
                item.setData(Qt.UserRole, input_row[1])
                self.mWellsListWidget.addItem(item)


    def process(self):
        selectedZonations = []
        selectedZones = []
        for si in self.zonationListWidget.selectedItems():
            selectedZonations.append(int(si.data(Qt.UserRole)))

        sel = None
        for zones in self.zoneListWidget.selectedItems():
            sel = zones.data(Qt.UserRole)
            selectedZones.append(sel[0])

        if sel is None:
            return

        paramId = self.mParamComboBox.itemData(self.mParamComboBox.currentIndex())
        layerName = self.mParamComboBox.currentText()
        parts = layerName.split('(')
        if len(parts) > 0:
            layerName = parts[0]

        if self.createLayer(layerName):
            with edit(self.layer):
                self.execute(sel, paramId)

            self.layer = memoryToShp(self.layer, self.project['project'], layerName)
            QgsMapLayerRegistry.instance().addMapLayer(self.layer)

        try:
            settings = QSettings()
            settings.setValue("/PDS/Zonations/SelectedZonations", selectedZonations)
            settings.setValue("/PDS/Zonations/selectedZones", selectedZones)
            settings.setValue("/PDS/Zonations/SelectedParameter", paramId)
            settings.setValue("/PDS/Zonations/UseElevation", u'True' if self.mUseElevation.isChecked() else u'False')
            settings.setValue("/PDS/Zonations/UseErosion", u'True' if self.mUseErosion.isChecked() else u'False')
        except:
            return


    def createLayer(self, name):
        try:
            uri = "Point?crs={}".format(self.proj4String)
            uri += '&field={}:{}'.format(u'well_id', "string")
            uri += '&field={}:{}'.format(name, "double")

            self.layer = QgsVectorLayer(uri, name, "memory")
            # if self.layer:
            #     QgsMapLayerRegistry.instance().addMapLayer(self.layer)

            return self.layer is not None
        except Exception as e:
            self.iface.messageBar().pushMessage(self.tr("Error"),
                                                self.tr(u'Layer create error {0}').format(str(e)),
                                                level=QgsMessageBar.CRITICAL)
            return False


    def execute(self, zoneDef, paramId):
        well_ids = []
        for wells in self.mWellsListWidget.selectedItems():
            well_ids.append(wells.data(Qt.UserRole))

        sql = self.get_sql('ZonationParams.sql')
        records = self.db.execute(sql, parameter_id=paramId, zonation_id=zoneDef[1], zone_id=zoneDef[0])
        if records:            
            for input_row in records:
                x,y,value = self.get_zone_coord_value(input_row, zoneDef[1], zoneDef[0])
                if x is not None and y is not None:
                    wellId = input_row[self.well_name_column_index]
                    sldnid = input_row[self.well_id_column_index]
                    if not len(well_ids) or sldnid in well_ids:
                        pt = QgsPoint(x, y)
                        l = QgsGeometry.fromPoint(pt)
                        feat = QgsFeature(self.layer.fields())
                        feat.setGeometry(l)
                        feat.setAttributes([wellId, float(value)])
                        self.layer.addFeatures([feat])

    def getNextZonationDepth(self, wellId, zonationId, zoneId):
        sql = self.get_sql('ZonationErosion.sql')
        records = self.db.execute(sql, well_id=wellId, zonation_id=zonationId, zone_id=zoneId)
        result = 0.0
        for input_row in records:
            val = float(input_row[0])
            if val > 0 and val < 1.0E+19:
                result = val
                break
        return result


    @cached_property
    def zonation_id_column_index(self):
        return 7

    @cached_property
    def zone_id_column_index(self):
        return 8

    @cached_property
    def zone_top_column_index(self):
        return 4

    @cached_property
    def zone_bottom_column_index(self):
        return 5

    @cached_property
    def well_id_column_index(self):
        return 6

    @cached_property
    def well_name_column_index(self):
        return 0

    @cached_property
    def well_lng_column_index(self):
        return 10

    @cached_property
    def well_lat_column_index(self):
        return 11

    @cached_property
    def deviation_x_column_index(self):
        return 12

    @cached_property
    def deviation_y_column_index(self):
        return 13

    @cached_property
    def deviation_md_column_index(self):
        return 14

    @cached_property
    def deviation_tvd_column_index(self):
        return 15

    @cached_property
    def parameter_name_column_index(self):
        return 3

    @cached_property
    def zonation_params_column_index(self):
        return 16

    @cached_property
    def variable_short_name_column_index(self):
        return 17

    @cached_property
    def variable_dflt_column_index(self):
        return 18

    @cached_property
    def variable_min_column_index(self):
        return 19

    @cached_property
    def variable_max_column_index(self):
        return 20

    @cached_property
    def variable_null_column_index(self):
        return 21

    def read_zonation_params(self, params):
        d = params.read()
        if not d:
            return
        _pos = [0]

        def read_int():
            ret = unpack_from('>i', d, _pos[0])[0]
            _pos[0] += 4
            return ret

        def read_string(count):
            ret = unpack_from('>{}s'.format(count), d, _pos[0])[0]
            _pos[0] += count
            return ret

        def read_float():
            ret = unpack_from('>f', d, _pos[0])[0]
            _pos[0] += 4
            return ret

        zonation_id = read_int()
        TIG_VARIABLE_SHORT_NAME_LEN = 8
        TIG_VARIABLE_CHAR_DFLT_LEN = 80
        SQL_INTEGER = 1
        SQL_FLOAT = 2
        SQL_CHARACTER = 4

        well_count = read_int()
        for _i in xrange(well_count):
            well_id = read_int()
            wint_ct = read_int()
            for _j in xrange(wint_ct):
                zone_id = read_int()
                para_ct = read_int()
                for _k in xrange(para_ct):
                    type = read_int()
                    name = read_string(TIG_VARIABLE_SHORT_NAME_LEN).strip()
                    if type == SQL_FLOAT:
                        value = read_float()
                    elif type == SQL_INTEGER:
                        value = read_int()
                    elif type == SQL_CHARACTER:
                        value = read_string(TIG_VARIABLE_CHAR_DFLT_LEN)
                    else:
                        raise Exception('bad type {}'.format(type))
                    yield zonation_id, well_id, zone_id, name, type, value

    def get_zonation_param_value(self, input_row):
        zonation_params = input_row[self.zonation_params_column_index]
        _zonation_id = input_row[self.zonation_id_column_index]
        _well_id = input_row[self.well_id_column_index]
        _zone_id = input_row[self.zone_id_column_index]
        _name = input_row[self.parameter_name_column_index]
        for t in self.read_zonation_params(zonation_params):
            zonation_id, well_id, zone_id, name, type, value = t
            if (
                zonation_id == _zonation_id and
                well_id == _well_id and
                zone_id == _zone_id and
                name == _name
            ):
                return value


    def get_zone_coord_value(self, input_row, zonationId, zoneId):
        ZAV_INDT_LO = -1000.9
        ZAV_INDT_HI = -998.9

        parameter_name = input_row[self.parameter_name_column_index]
        zonation_param_value = self.get_zonation_param_value(input_row)

        zone_top = float(input_row[self.zone_top_column_index])
        zone_bottom = float(input_row[self.zone_bottom_column_index])

        elevation = 0.0
        if self.mUseElevation.isChecked():
            elevation = input_row[22]

        value = None
        depth = None

        _well_id = input_row[self.well_id_column_index]

        useErosion = self.mUseErosion.isChecked()

        if parameter_name == 'TopTVD':
            if useErosion and (zone_top == 0 or zone_top > 1.0E+19):
                zone_top = self.getNextZonationDepth(_well_id, zonationId, zoneId)
            depth = zone_top
            value = zone_top
        elif parameter_name == 'BotTVD':
            if useErosion and (zone_bottom == 0 or zone_bottom > 1.0E+19):
                zone_bottom = self.getNextZonationDepth(_well_id, zonationId, zoneId)
            depth = zone_bottom
            value = zone_bottom
        else:
            if zonation_param_value is None:
                zonation_param_value = input_row[self.variable_dflt_column_index]
            if ZAV_INDT_LO < zonation_param_value < ZAV_INDT_HI:
                value = None
            else:
                value = zonation_param_value
            depth = (zone_bottom + zone_top) * 0.5

            if parameter_name in ['ISCtopMD', 'ISPtopMD', 'DIPZTOP']:
                depth = zone_top
            elif parameter_name in ['ISCbotMD', 'ISPbotMD', 'DIPZBOT']:
                depth = zone_bottom

        def read_floats(index):
            return numpy.fromstring(input_row[index].read(), '>f').astype('d')

        x = read_floats(self.deviation_x_column_index)
        y = read_floats(self.deviation_y_column_index)
        md = read_floats(self.deviation_md_column_index)
        tvd = read_floats(self.deviation_tvd_column_index)

        jp = None
        lastIdx = len(x) - 1
        for ip in xrange(lastIdx):
            if md[ip] <= depth <= md[ip + 1]:
                jp = ip

        xPosition = 0
        yPosition = 0
        if jp is not None:
            rinterp = (depth - md[jp]) / (md[jp + 1] - md[jp])
            xPosition = x[jp] + rinterp * (x[jp + 1] - x[jp])
            yPosition = y[jp] + rinterp * (y[jp + 1] - y[jp])

            if parameter_name in ['TopTVD', 'BotTVD']:
                value = tvd[jp] + rinterp * (tvd[jp + 1] - tvd[jp]) - elevation
        elif depth >= md[lastIdx]:
            xPosition = x[lastIdx]
            yPosition = y[lastIdx]
            if parameter_name in ['TopTVD', 'BotTVD']:
                value = tvd[lastIdx] - elevation

        lng = input_row[self.well_lng_column_index]
        lat = input_row[self.well_lat_column_index]
        pt = QgsPoint(lng, lat)
        if self.xform:
            pt = self.xform.transform(pt)

        ret_x = pt.x() + xPosition
        ret_y = pt.y() + yPosition
        return (ret_x, ret_y, value)


    def fillParameters(self):
        settings = QSettings()
        selectedParameter = int(settings.value("/PDS/Zonations/SelectedParameter", -1))

        self.mParamComboBox.clear()
        records = self.db.execute(self.get_sql('ZonationParams_parameter.sql'))
        if records is not None:
            for row in records:
                if len(self.selectedParameters) == 0 or row[0] in self.selectedParameters:
                    self.mParamComboBox.addItem(row[1], int(row[0]))
                    if selectedParameter == int(row[0]):
                        self.mParamComboBox.setCurrentIndex(self.mParamComboBox.count()-1)

    def mParamToolButton_clicked(self):
        zonation_id = None
        zone_id = None
        for zones in self.zoneListWidget.selectedItems():
            zoneDef = zones.data(Qt.UserRole)
            zonation_id = zoneDef[1]
            zone_id = zoneDef[0]

        well_ids = []
        for wells in self.mWellsListWidget.selectedItems():
            well_ids.append(wells.data(Qt.UserRole))

        dlg = QgisPDSZoneparamsDialog(self.project, self.iface, zonation_id, zone_id, well_ids, self)
        if dlg.exec_():
            self.selectedParameters = dlg.getSelected()
            QSettings().setValue("/PDS/Zonations/SelectedParameters", self.selectedParameters)
            self.fillParameters()

