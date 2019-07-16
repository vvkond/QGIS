# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QgisPDS
                                 A QGIS plugin
 PDS link
                              -------------------
        begin                : 2016-11-05
        git sha              : $Format:%H$
        copyright            : (C) 2016 by Viktor Kondrashov
        email                : viktor@gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
from qgis.gui import QgsVertexMarker
# Initialize Qt resources from file resources.py
import resources
# Import the code for the dialog
from qgis_pds_dialog import QgisPDSDialog
from qgis_pds_production import QgisPDSProductionDialog
from qgis_pds_cpoints import QgisPDSCPointsDialog
from qgis_pds_wells import *
from qgis_pds_prodRenderer import *
from qgis_pds_prod_layer_type import *
from qgis_pds_prodSetup import *
from qgis_pds_bubbleSetup import *
from ControlPointReader import ControlPointReader
from ContoursReader import ContoursReader
from SurfaceReader import SurfaceReader
from qgis_pds_CoordFromZone import QgisPDSCoordFromZoneDialog
from qgis_pds_zonations import QgisPDSZonationsDialog
from qgis_pds_residual import QgisPDSResidualDialog
from qgis_pds_pressureMap import QgisPDSPressure
from qgis_pds_deviation import QgisPDSDeviation
from qgis_pds_statistic import QgisPDSStatisticsDialog
from qgis_pds_refreshSetup import QgisPDSRefreshSetup
from qgis_pds_SaveMapsetToPDS import QgisSaveMapsetToPDS
from qgis_pds_oracleSql import QgisOracleSql
from qgis_pds_createIsolines import QgisPDSCreateIsolines
from qgis_pds_transite import QgisPDSTransitionsDialog
from qgis_pds_SelectMapTool import QgisPDSSelectMapTool
from qgis_pds_dca import QgisPDSDCAForm
from qgis_pds_wellsMarkDialog import QgisPDSWellsMarkDialog
from qgis_pds_wellsBrowserDialog import *
# Import both Processing and CommanderWindow 
#   classes from the Processing framework. 
from processing.core.Processing import Processing
from processing.gui.CommanderWindow import CommanderWindow

import os
import os.path
import ast
import json




#===============================================================================
# --- REGISTER USER FUNCTIONS.CALL @qgsfunction MUST BE IN 1st level,not in def/class
#===============================================================================
from qgis.core import QgsMapLayerRegistry
from qgis.utils import qgsfunction
from qgis.core import QgsExpression
from utils import getenv_system


@qgsfunction(args='auto', group='PumaPlus')
def activeLayerCustomProperty(value1,feature, parent):
    """
    <h4>Return</h4>Read custom property of active layer. Most useful variants:qgis_pds_type, pds_prod_SelectedReservoirs, pds_project
    <p><h4>Syntax</h4>activeLayerCustomProperty(%property_name%)</p>
    <p><h4>Argument</h4>-</p>
    <p><h4>Example</h4>activeLayerCustomProperty('qgis_pds_type')</p><p>Return: String with selected reservoir names</p>
    """
    import qgis
    #get iface
    i =qgis.utils.iface
    # get legend
    layer=i.activeLayer()
    return layer.customProperty(value1)

@qgsfunction(args='auto', group='PumaPlus')
def makeMultilineFormatedLabel(label,label_row,row_count,feature, parent):
    """
    <h4>Return</h4>Make formated label for multiline labeled
    <p><h4>Syntax</h4>makeMultilineFormatedLabel(%label%,%row_number%, %row_count%)</p>
    <p><h4>Argument</h4> %row_number%-position start from 0</p>
    <p><h4>Argument</h4> %row_count%-count of rows</p>
    <p><h4>Example</h4>makeMultilineFormatedLabel("well_id",2,10)</p><p>Return: String with inserted new line symbols before and after field value</p>
    """
    res="\n"*(label_row)+'{}\n'.format(label)+"\n"*(row_count-label_row-1)
    return res

@qgsfunction(args='auto', group='PumaPlus')
def isValueInInterval(value, limit_min, limit_max, step, feature, parent):
    """
    <h4>Return</h4>Return True if value in interval
    <p><h4>Syntax</h4>isValueInInterval( %value%, %limit_min%, %limit_max%, %step% )</p>
    <p><h4>Argument</h4> %value% - field with values           </p>
    <p><h4>Argument</h4> %limit_min% - left interval limit     </p>
    <p><h4>Argument</h4> %limit_max% - right interval limit    </p>
    <p><h4>Argument</h4> %step% - step from left to right      </p>
    """
    if limit_min<value<limit_max:
        if (value-limit_min) % step>0:
            return False
        else:
            return True
    else:
        return False
@qgsfunction(args='auto', group='PumaPlus')
def isValueInIntervalWithSkeep(value, limit_min, limit_max, step, skeep_each, feature, parent):
    """
    <h4>Return</h4>Return True if value in interval
    <p><h4>Syntax</h4>isValueInInterval( %value%, %limit_min%, %limit_max%, %step%, %skeep_each% )</p>
    <p><h4>Argument</h4> %value% - field with values           </p>
    <p><h4>Argument</h4> %limit_min% - left interval limit     </p>
    <p><h4>Argument</h4> %limit_max% - right interval limit    </p>
    <p><h4>Argument</h4> %step% - step from left to right      </p>
    <p><h4>Argument</h4> %skeep_each% - return False for each %skeep_each% value </p>
    """
    if limit_min<value<limit_max:
        if (value-limit_min) % step>0:
            return False
        else:
            if skeep_each>0 and (value-limit_min) / step % skeep_each>0:
                return True
            elif (not skeep_each>0) and (not (value-limit_min) % step>0):
                return True
            else:
                return False
    else:
        return False

    
@qgsfunction(args='auto', group='PumaPlus')
def activeLayerReservoirs(feature, parent):
    """
    <h4>Return</h4>Get list of reservoirs in checked pds production layers
    <p><h4>Syntax</h4>activeLayerReservoirs()</p>
    <p><h4>Argument</h4>-</p>
    <p><h4>Example</h4>activeLayerReservoirs()</p><p>Return: String with selected reservoir names</p>
    """
    import qgis
    #get iface
    i =qgis.utils.iface
    # get legend
    legend = i.legendInterface()
    result=[]
    for layer in QgsMapLayerRegistry.instance().mapLayers().values():
        # check current visibility
        if legend.isLayerVisible(layer):
            if layer.customProperty("qgis_pds_type") == "pds_current_production" or layer.customProperty("qgis_pds_type") == "pds_cumulative_production":
                reservoir=layer.customProperty("pds_prod_SelectedReservoirs")
                result.extend(ast.literal_eval(reservoir))
            else:
                continue
    return u','.join(set(result))

@qgsfunction(args='auto', group='PumaPlus')
def activeLayerProductionType(feature, parent):
    """
    <h4>Return</h4>Get list of production type of selected pds layers
    <p><h4>Warning!!! When add it from qgis python console it take incorrect encoding. After reopen qgis it loaded correct</h4>-</p>
    <p><h4>Syntax</h4>activeLayerProductionType()</p>
    <p><h4>Argument</h4>-</p>
    <p><h4>Example</h4>activeLayerProductionType()</p><p>Return: String with selected production types</p>
    """
    import qgis
    #get iface
    i = qgis.utils.iface
    # get legend
    legend = i.legendInterface()
    result=[]
    for layer in QgsMapLayerRegistry.instance().mapLayers().values():
        # check current visibility
        if legend.isLayerVisible(layer):
            if layer.customProperty("qgis_pds_type") == "pds_current_production":
                #result.append("�������".decode('utf-8',errors='replace')) 
                result.append("текуших".decode('utf-8',errors='replace'))
                pass
            elif layer.customProperty("qgis_pds_type") == "pds_cumulative_production":
                #result.append("�����������".decode('utf-8',errors='replace'))
                result.append("накопленных".decode('utf-8',errors='replace'))
                pass
            else:
                continue
    return " и ".decode('utf-8',errors='replace').join(set(result))





#===============================================================================
# 
#===============================================================================
class QgisPDS(QObject):
    """QGIS Plugin Implementation."""
    @property
    def currentProject(self):
        if self._currentProject is None:
            QtGui.QMessageBox.critical(None, self.tr(u'Error'), self.tr(u'No current PDS project'), QtGui.QMessageBox.Ok)
            #try:
            #    projStr = currentLayer.customProperty("pds_project", str(self.currentProject))
            #    proj = ast.literal_eval(projStr)
            #    if proj is not None:
            #        return self.currentProject
            #    else:
            #        QtGui.QMessageBox.critical(None, self.tr(u'Error'), self.tr(u'No current PDS project'), QtGui.QMessageBox.Ok)
            #except:
            #    QtGui.QMessageBox.critical(None, self.tr(u'Error'), self.tr(u'No current PDS project'), QtGui.QMessageBox.Ok)
        else:
            return self._currentProject
    @currentProject.setter
    def currentProject(self,value):
        self._currentProject=value

    def __init__(self, _iface):
        """Constructor. """
        QObject.__init__(self)
        # Save reference to the QGIS interface
        self.iface = _iface
        
        self._currentProject = None

        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'QgisPDS_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)


        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&PDS')
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'QgisPDS')
        self.toolbar.setObjectName(u'QgisPDS')
        
        #Restore settings
        self.currentProject = QSettings().value('currentProject')

        #Connect signals
        self.connectToProject()

        self.labelPositions = []

        self.timer = QTimer()
        self.timer.timeout.connect(self.onTimer)
        # QObject.connect(self.timer, SIGNAL("timeout()"), self.onTimer)

        self.selectMapTool = None
        

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        return QCoreApplication.translate('QgisPDS', message)


    def connectToProject(self):
        proj = QgsProject.instance()
        proj.readProject.connect(self.loadData)
        QObject.connect(self.iface.legendInterface(), SIGNAL("currentLayerChanged(QgsMapLayer *)"), self.layerSelected)
        # QObject.connect(self.iface.mapCanvas(), SIGNAL("mapCanvasRefreshed ()"), self.renderComplete)


    def disconnectFromProject(self):
        proj = QgsProject.instance()
        proj.readProject.disconnect(self.loadData)
        self.disconnectFromLayers()
        QObject.disconnect(self.iface.legendInterface(), SIGNAL("currentLayerChanged(QgsMapLayer *)"), self.layerSelected)

        # QObject.disconnect(self.iface.mapCanvas(), SIGNAL("mapCanvasRefreshed ()"), self.renderComplete)

        
    
    def loadData(self):
        layers = self.iface.legendInterface().layers()

        for layer in layers:
            if not layer.type() == 0:
                continue

            if bblInit.isProductionLayer(layer) or bblInit.isWellLayer(layer):
                layer.attributeValueChanged.connect(self.pdsLayerModified)


    def disconnectFromLayers(self):
        layers = self.iface.legendInterface().layers()

        for layer in layers:
            if not layer.type() == 0:
                continue

            try:
                if bblInit.isProductionLayer(layer) or bblInit.isWellLayer(layer):
                    layer.attributeValueChanged.disconnect(self.pdsLayerModified)
            except:
                pass

    def pdsLayerModified(self, FeatureId, idx, variant):
        sender = self.sender()
        if not sender or not sender.type() == 0 or sender == self:
            return

        # print 'start pdsLayerModified', sender

        editedLayer = sender
        mc = self.iface.mapCanvas()
        tr = mc.getCoordinateTransform()
        xMm = mc.mapSettings().outputDpi() / 25.4

        dp = editedLayer.dataProvider()
        editFeature = QgsFeature()
        if editedLayer == None or editedLayer.getFeatures(QgsFeatureRequest().setFilterFid(FeatureId)).nextFeature(
                editFeature) is False:
            return
        else:
            # print 'traitement signal'
            editGeom = editFeature.geometry()
            editLayerProvider = editedLayer.dataProvider()
            fields = editLayerProvider.fields()

            fieldname = ''
            try:
                fieldname = fields[idx].name()
            except:
                pass
            originX = editGeom.asPoint().x()
            originY = editGeom.asPoint().y()
            pixelOrig = tr.transform(QgsPoint(originX, originY))

            idxOffX = editLayerProvider.fieldNameIndex('labloffx')
            idxOffY = editLayerProvider.fieldNameIndex('labloffy')
            if idxOffX < 0 or idxOffY < 0:
                editLayerProvider.addAttributes(
                    [QgsField("labloffx", QVariant.Double),
                     QgsField("labloffy", QVariant.Double)])
                idxOffX = editLayerProvider.fieldNameIndex('labloffx')
                idxOffY = editLayerProvider.fieldNameIndex('labloffy')

            if editLayerProvider.fieldNameIndex('labloffset') < 0:
                editLayerProvider.addAttributes([QgsField("labloffset", QVariant.Double)])

            if idxOffX < 0 or idxOffY < 0:
                return


            if fieldname.lower() == 'lablx':
                if variant == NULL:  # case when user unpins the label > sets arrow back to arrow based on point location
                    return
                if isinstance(variant, basestring):  # test case, when editing from attribute table, variant is sent as text! converts to float
                    variant = float(variant)
                newFinalX = variant

                pixelOffset = tr.transform(QgsPoint(newFinalX, originY))
                mmOffset = (pixelOffset.x() - pixelOrig.x()) / xMm

                editedLayer.changeAttributeValue(FeatureId, editLayerProvider.fieldNameIndex('LablX'), None)
                editedLayer.changeAttributeValue(FeatureId, idxOffX, mmOffset)
                editedLayer.changeAttributeValue(FeatureId, editLayerProvider.fieldNameIndex('labloffset'), 1)

            if fieldname.lower() == 'lably':
                if variant == NULL:  # case when user unpins the label > sets arrow back to arrow based on point location
                    return
                if isinstance(variant, basestring):  # test case, when editing from attribute table, variant is sent as text! converts to float
                    variant = float(variant)
                newFinalY = variant

                pixelOffset = tr.transform(QgsPoint(originX, newFinalY))
                mmOffset = (pixelOffset.y() - pixelOrig.y()) / xMm

                editedLayer.changeAttributeValue(FeatureId, editLayerProvider.fieldNameIndex('LablY'), None)
                editedLayer.changeAttributeValue(FeatureId, idxOffY, mmOffset)
                editedLayer.changeAttributeValue(FeatureId, editLayerProvider.fieldNameIndex('labloffset'), 1)


    @property
    def sldnidFieldName(self):
        return 'sldnid'

    def layerSelected(self, layer):
        """Change action enable"""
        enabled = False
        enabledWell = False
        enabledFond = False
        runAppEnabled = False
        try:
            if layer is not None:
                enabled = bblInit.isProductionLayer(layer)
                enabledWell = bblInit.isWellLayer(layer)
                enabledFond= bblInit.isFondLayer(layer)
                runAppEnabled = layer.fieldNameIndex(self.sldnidFieldName) >= 0

                if self.iface.mapCanvas().mapTool() == self.selectMapTool:
                    if self.selectMapTool:
                        if runAppEnabled:
                            self.selectMapTool.setLayer(layer)
                        else:
                            self.selectMapTool.reset()
                            
                field_names = [field.name() for field in layer.dataProvider().fields()]
                self.actionMarkWells.setEnabled(Fields.WellId.name in field_names)                              
        except:
            pass

        self.actionProductionSetup.setEnabled(enabled)
        self.actionCoordsFromZone.setEnabled(enabled or enabledWell or enabledFond)
        self.actionTransiteWells.setEnabled(enabled or enabledWell or enabledFond)

        self.runAppAction.setEnabled(runAppEnabled)

    
    #Save label positions
    def onTimer(self):
        self.timer.stop()

        mc = self.iface.mapCanvas()
        lr = mc.labelingResults()

        layers = mc.layers()
        ll = {}
        commitLayers = []
        if layers is not None:
            for lay in layers:
                if bblInit.isProductionLayer(lay):
                    ll[lay.id()] = lay
                    if not lay.isEditable():
                        lay.startEditing()
                        commitLayers.append(lay)

            for l in self.labelPositions:
                curLayer = ll[l.layerID]  
                if curLayer is not None:
                    curLayer.changeAttributeValue(l.featureId, curLayer.fieldNameIndex('LablWidth'), l.width)  
                    curLayer.changeAttributeValue(l.featureId, curLayer.fieldNameIndex('LablOffX'), l.labelRect.xMinimum())      
                    curLayer.changeAttributeValue(l.featureId, curLayer.fieldNameIndex('LablOffY'), l.labelRect.yMinimum())                       
                        
                
        for lay in commitLayers:
            lay.commitChanges()

        self.labelPositions = []

    def getLabelLayerName(self, name):
        return name + ' - outline'

    def createLabelLayer(self, lay, name):
        crs = lay.crs()
        if crs:
            crsString = crs.toProj4()
            self.uri = "LineString?crs=PROJ4:{}".format(crsString)
            self.uri += '&field={}:{}'.format("SLDNID", "int")
            layer = QgsVectorLayer(self.uri, name, "memory")
            if layer:
                QgsMapLayerRegistry.instance().addMapLayer(layer)
            return layer
        return None

    def checkLabellingLayer(self, lay):
        labelLayerName = self.getLabelLayerName(lay.name())
        layers = self.iface.legendInterface().layers()

        for layer in layers:
            if layer.name() == labelLayerName:
                return layer

        return self.createLabelLayer(lay, labelLayerName)


    #Collect label positions
    def renderComplete(self):
        mc = self.iface.mapCanvas()
        lr = mc.labelingResults()

        layers = mc.layers()
        ll = {}
        ll1 = {}
        if layers is None:
            return

        for lay in layers:
            if bblInit.isProductionLayer(lay):
                labelLayer = self.checkLabellingLayer(lay)
                if labelLayer:
                    ll[lay.id()] = lay
                    ll1[lay.id()] = labelLayer

        if len(ll) < 1:
            return

        # self.timer.stop()
        self.labelPositions = []

        tr = mc.getCoordinateTransform()
        xMm = mc.mapSettings().outputDpi() / 25.4

        commitLayers = []
        if lr is not None:
            labels = lr.labelsWithinRect(mc.extent())
            if labels is not None:
                for l in labels:
                    if not l.layerID in ll:
                        continue

                    curLayer = ll[l.layerID]
                    curLabLayer = ll1[l.layerID]
                    rect = l.labelRect
                    if curLayer is not None:

                        ff = curLayer.getFeatures(QgsFeatureRequest(l.featureId))
                        if ff is not None:
                            if not curLabLayer.isEditable():
                                curLabLayer.startEditing()
                                commitLayers.append(curLabLayer)
                            for f in ff:
                                editGeom = f.geometry()
                                geom = QgsGeometry.fromPolyline([editGeom.asPoint(), QgsPoint(rect.xMinimum(), rect.yMinimum())])

                                expr = QgsExpression('\"{0}\"={1}'.format("SLDNID", l.featureId))
                                searchRes = curLabLayer.getFeatures(QgsFeatureRequest(expr))
                                num = 0
                                for f1 in searchRes:
                                    curLabLayer.changeGeometry(f1.id(), geom)
                                    num = num + 1

                                if num == 0:
                                    fea = QgsFeature(curLabLayer.fields())
                                    fea.setAttribute("SLDNID", l.featureId)
                                    fea.setGeometry(geom)
                                    curLabLayer.addFeatures([fea])

                                # originX = editGeom.asPoint().x()
                                # originY = editGeom.asPoint().y()
                                # pixelOrig = tr.transform(editGeom.asPoint())
                                # pixelOffset = tr.transform(QgsPoint( rect.xMinimum(), rect.yMinimum()))
                                # mmOffsetX = (pixelOffset.x() - pixelOrig.x()) / xMm
                                # mmOffsetY = (pixelOffset.y() - pixelOrig.y()) / xMm
                                # curLayer.changeAttributeValue(l.featureId, curLayer.fieldNameIndex('LablWidth'), l.width)
                                # curLayer.changeAttributeValue(l.featureId, curLayer.fieldNameIndex('LablOffX'), mmOffsetX)
                                # curLayer.changeAttributeValue(l.featureId, curLayer.fieldNameIndex('LablOffY'), mmOffsetY)


        for lay in commitLayers:
            lay.commitChanges()
        mc.refresh()
        # if len(self.labelPositions) > 0:
        #     self.timer.start(100)
        

    def add_action(
        self,
        icon_path,
        text,
        callback=None,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None,
        menu=None):
        

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        if callback is not None:
            action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if menu is not None:
            action.setMenu(menu)

        if add_to_toolbar:
            self.toolbar.addAction(action)

        if add_to_menu:
            self.iface.addPluginToDatabaseMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action


    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        toolTipText = self.tr(u'Select PDS project')
        if self.currentProject:
            toolTipText += ' ({0})'.format(self.currentProject['project'])

        icon_path = ':/plugins/QgisPDS/database.png'
        self.selectProjectAction = self.add_action(
            icon_path,
            text=toolTipText,
            callback=self.selectProject,
            status_tip=self.tr(u'Select project'),
            parent=self.iface.mainWindow())

        icon_path = ':/plugins/QgisPDS/DR028.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Load control points'),
            callback=self.createCPointsLayer,
            parent=self.iface.mainWindow())

        icon_path = ':/plugins/QgisPDS/DR029.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Load faults'),
            callback=self.createFaultsLayer,
            parent=self.iface.mainWindow())

        icon_path = ':/plugins/QgisPDS/DR014.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Load contours'),
            callback=self.createContoursLayer,
            parent=self.iface.mainWindow())

        icon_path = ':/plugins/QgisPDS/DR030.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Load polygons'),
            callback=self.createPolygonsLayer,
            parent=self.iface.mainWindow())

        icon_path = ':/plugins/QgisPDS/DR012.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Load surface'),
            callback=self.createSurfaceLayer,
            parent=self.iface.mainWindow())

        icon_path = ':/plugins/QgisPDS/ME002.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Load wells'),
            callback=self.createWellLayer,
            parent=self.iface.mainWindow())

        icon_path = ':/plugins/QgisPDS/mark_item.png'
        self.actionMarkWells=self.add_action(
            icon_path,
            text=self.tr(u'Mark wells'),
            callback=self.markLayers,
            parent=self.iface.mainWindow())

        icon_path = ':/plugins/QgisPDS/deviations.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Load well deviations'),
            callback=self.createWellDeviationLayer,
            parent=self.iface.mainWindow())

        icon_path = ':/plugins/QgisPDS/pump-jack.png'
        self.actionRefreshLayer = self.add_action(
            icon_path,
            text=self.tr(u'Load wells status'),
            callback=self.createFondlayer,
            parent=self.iface.mainWindow())

        icon_path = ':/plugins/QgisPDS/GeoPROD24a.png'
        self.actionCurrentProduction = self.add_action(
            icon_path,
            text=self.tr(u'Load current production'),
            callback=self.createProductionlayer,
            parent=self.iface.mainWindow())

        icon_path = ':/plugins/QgisPDS/GeoPROD24Sum.png'
        self.actionProduction = self.add_action(
            icon_path,
            text=self.tr(u'Load production'),
            callback=self.createSummProductionlayer,
            parent=self.iface.mainWindow())

        icon_path = ':/plugins/QgisPDS/Refresh.png'
        self.actionRefreshLayer = self.add_action(
            icon_path,
            text=self.tr(u'Update layer'),
            callback=self.refreshLayer,
            parent=self.iface.mainWindow())

        icon_path = ':/plugins/QgisPDS/Pressure-50.png'
        self.actionLoadPressure = self.add_action(
            icon_path,
            text=u'Загрузить давления',
            callback=self.loadPressure,
            parent=self.iface.mainWindow())

        icon_path = ':/plugins/QgisPDS/zonation.png'
        self.actionLoadPressure = self.add_action(
            icon_path,
            text=self.tr(u'Zonation parameters'),
            callback=self.loadZonations,
            parent=self.iface.mainWindow())

        icon_path = ':/plugins/QgisPDS/piechart1.png'
        self.actionProductionSetup = self.add_action(
            icon_path,
            text=self.tr(u'Production setup'),
            callback=self.productionSetup,
            enabled_flag=False,
            parent=self.iface.mainWindow())

        icon_path = ':/plugins/QgisPDS/piechart2.png'
        self.actionBubblesSetup = self.add_action(
            icon_path,
            text=self.tr(u'Bubbles setup'),
            callback=self.bubblesSetup,
            enabled_flag=True,
            parent=self.iface.mainWindow())

        icon_path = ':/plugins/QgisPDS/point_to_zonation.png'
        self.actionCoordsFromZone = self.add_action(
            icon_path,
            text=self.tr(u'Well coordinate from zone'),
            callback=self.wellCoordFromZone,
            enabled_flag=False,
            parent=self.iface.mainWindow())

        icon_path = ':/plugins/QgisPDS/filter.png'
        self.actionTransiteWells = self.add_action(
            icon_path,
            text=self.tr(u'Mark transite wells'),
            callback=self.transiteWells,
            enabled_flag=False,
            parent=self.iface.mainWindow())

        icon_path = ':/plugins/QgisPDS/water-drop.png'
        self.actionRefreshLayer = self.add_action(
            icon_path,
            text=self.tr(u'Residuals'),
            callback=self.residuals,
            parent=self.iface.mainWindow())

        icon_path = ':/plugins/QgisPDS/statistics.png'
        self.actionRefreshLayer = self.add_action(
            icon_path,
            text=self.tr(u'Calculate statistics'),
            callback=self.calcStatistics,
            parent=self.iface.mainWindow())

        icon_path = ':/plugins/QgisPDS/type_well.png'
        self.actionRefreshLayer = self.add_action(
            icon_path,
            text=self.tr(u'DCA'),
            callback=self.calcDCA,
            parent=self.iface.mainWindow())

        icon_path = ':/plugins/QgisPDS/mActionFileSave.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Save to PDS'),
            callback=self.saveLayerToPDS,
            parent=self.iface.mainWindow())

        icon_path = ':/plugins/QgisPDS/new_sql_query.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Layer from Oracle SQL'),
            callback=self.dataFromOracleSql,
            parent=self.iface.mainWindow())

        icon_path = ':/plugins/QgisPDS/contours.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Create isolines'),
            callback=self.createIsolines,
            parent=self.iface.mainWindow())


        #--- button for processing functions
        # Instantiate the commander window and open the algorithm's interface 
        cw = CommanderWindow(self.iface.mainWindow(), self.iface.mapCanvas())
        # Then get the algorithm you're interested in (for instance, Join Attributes):
        alg_mesh = Processing.getAlgorithm("pumaplus:creategridwithfaults")
        if alg_mesh is not None:
            icon_path = ':/plugins/QgisPDS/surface.png'
            self.add_action(
                icon_path,
                text=self.tr(u'Create mesh'),
                callback=lambda :cw.runAlgorithm(alg_mesh),
                parent=self.iface.mainWindow())
        # Then get the algorithm you're interested in (for instance, Join Attributes):
        alg_mp = Processing.getAlgorithm("pumaplus:updatewelllocation")
        if alg_mp is not None:
            icon_path = ':/plugins/QgisPDS/move_point.png'
            self.add_action(
                icon_path,
                text=self.tr(u'Move point'),
                callback=lambda :cw.runAlgorithm(alg_mp),
                parent=self.iface.mainWindow())
        # Then get the algorithm you're interested in (for instance, Join Attributes):
        alg_ml = Processing.getAlgorithm("pumaplus:updatelabellocation")
        if alg_ml is not None:
            icon_path = ':/plugins/QgisPDS/move_label.png'
            self.add_action(
                icon_path,
                text=self.tr(u'Move label'),
                callback=lambda :cw.runAlgorithm(alg_ml),
                parent=self.iface.mainWindow())
        # Then get the algorithm you're interested in (for instance, Join Attributes):
        alg_ml = Processing.getAlgorithm("pumaplus:setmapvariable")
        if alg_ml is not None:
            icon_path = ':/plugins/QgisPDS/text_edit.png'
            self.add_action(
                icon_path,
                text=self.tr(u'Update variables'),
                callback=lambda :cw.runAlgorithm(alg_ml),
                parent=self.iface.mainWindow())


        applicationMenu = QMenu(self.iface.mainWindow())
        action = QAction(self.tr(u'Well Correlation && Zonation'), applicationMenu)
        applicationMenu.addAction(action)
        action.triggered.connect(self.startWcorr)
        action = QAction(self.tr(u'Well view'), applicationMenu)
        applicationMenu.addAction(action)
        action.triggered.connect(self.startWellView)
        action = QAction(self.tr(u'Well Log Processing'), applicationMenu)
        applicationMenu.addAction(action)
        action.triggered.connect(self.startWellLogProcessing)
        action = QAction(self.tr(u'Deviation Survey'), applicationMenu)
        applicationMenu.addAction(action)
        action.triggered.connect(self.startDevSurvey)
        action = QAction(self.tr(u'Log Plot'), applicationMenu)
        applicationMenu.addAction(action)
        action.triggered.connect(self.startLogPlot)
        applicationMenu.addSeparator()
        action = QAction(self.tr(u'Seismic Interpretation 2D'), applicationMenu)
        applicationMenu.addAction(action)
        action.triggered.connect(self.seis2D)
        action = QAction(self.tr(u'Seismic Interpretation 3D'), applicationMenu)
        applicationMenu.addAction(action)
        action.triggered.connect(self.seis3D)

        icon_path = ':/plugins/QgisPDS/play_24x24.png'
        self.runAppAction = self.add_action(
            icon_path,
            text=self.tr(u'Run application'),
            parent=self.iface.mainWindow(),
            enabled_flag=False,
            menu=applicationMenu)

        self._metadata = BabbleSymbolLayerMetadata()
        QgsSymbolLayerV2Registry.instance().addSymbolLayerType(self._metadata)
        #---REGISTER USER EXPRESSIONS
        QgsExpression.registerFunction(activeLayerCustomProperty)        
        QgsExpression.registerFunction(activeLayerReservoirs)
        QgsExpression.registerFunction(activeLayerProductionType)
        QgsExpression.registerFunction(makeMultilineFormatedLabel)
        QgsExpression.registerFunction(isValueInInterval)
        QgsExpression.registerFunction(isValueInIntervalWithSkeep)

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginDatabaseMenu( self.tr(u'&PDS'), action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar
        #---UNREGISTER USER EXPRESSIONS
        QgsExpression.unregisterFunction('activeLayerCustomProperty')        
        QgsExpression.unregisterFunction('activeLayerReservoirs')
        QgsExpression.unregisterFunction('activeLayerProductionType')
        QgsExpression.unregisterFunction('makeMultilineFormatedLabel')
        QgsExpression.unregisterFunction('isValueInInterval')
        QgsExpression.unregisterFunction('isValueInIntervalWithSkeep')
        
        

        # QgsPluginLayerRegistry.instance().removePluginLayerType(QgisPDSProductionLayer.LAYER_TYPE)

        #remove SIGNALS
        self.disconnectFromProject()


    def setReferenceLayer(self, layer):
        self.layer = layer


    def selectProject(self):
        try:
            dlg = QgisPDSDialog(self.iface)
            if self.currentProject is not None:
                dlg.setCurrentProject(self.currentProject)
            
            result = dlg.exec_()
            if result:
                self.currentProject = dlg.selectedProject()           
                self.saveSettings()
                toolTipText = self.tr(u'Select PDS project')
                if self.currentProject:
                    toolTipText += ' ({0})'.format(self.currentProject['project'])
                self.selectProjectAction.setToolTip(toolTipText)
        except Exception as e:
            QgsMessageLog.logMessage(u"{}".format(str(e)), tag="QgisPDS.error")  
                
      
            
    def createProductionlayer(self):
        try:
            if not QgsProject.instance().homePath():
                self.iface.messageBar().pushMessage(self.tr("Error"),
                            self.tr(u'Save project before load'), level=QgsMessageBar.CRITICAL)
                return
    
            dlg = QgisPDSProductionDialog(self.currentProject, self.iface)
            if dlg.isInitialised():
                result = dlg.exec_()
                if dlg.getLayer() is not None:
                    dlg.getLayer().attributeValueChanged.connect(self.pdsLayerModified)
        except Exception as e:
            QgsMessageLog.logMessage(u"{}".format(str(e)), tag="QgisPDS.error")  
                    

    def createFondlayer(self):
        try:
            if not QgsProject.instance().homePath():
                self.iface.messageBar().pushMessage(self.tr("Error"),
                            self.tr(u'Save project before load'), level=QgsMessageBar.CRITICAL)
                return
            currentLayer = self.iface.activeLayer()
            dlg = QgisPDSProductionDialog(self.currentProject, self.iface, isOnlyFond=True)
            if dlg.isInitialised():
                result = dlg.exec_()
                if dlg.getLayer() is not None:
                    dlg.getLayer().attributeValueChanged.connect(self.pdsLayerModified)
            if self.iface.activeLayer()!=currentLayer:
                currentLayer = self.iface.activeLayer()
                if currentLayer is None:
                    return
                #--- zonation move
                dlg  = QgisPDSCoordFromZoneDialog(self.currentProject, self.iface, currentLayer)
                dlg.exec_()
        
                #---transite
                dlg = QgisPDSTransitionsDialog(self.currentProject, self.iface, currentLayer, allow_split_layer=False)
                dlg.exec_()
        except Exception as e:
            QgsMessageLog.logMessage(u"{}".format(str(e)), tag="QgisPDS.error")  
                
        



    def loadPressure(self):
        try:
            if not QgsProject.instance().homePath():
                self.iface.messageBar().pushMessage(self.tr("Error"),
                            self.tr(u'Save project before load'), level=QgsMessageBar.CRITICAL)
                return
    
            dlg = QgisPDSPressure(self.currentProject, self.iface)
            if dlg.isInitialised():
                result = dlg.exec_()
        except Exception as e:
            QgsMessageLog.logMessage(u"{}".format(str(e)), tag="QgisPDS.error")  
                

    def loadZonations(self):
        try:
            dlg = QgisPDSZonationsDialog(self.currentProject, self.iface)
            dlg.exec_()
        except Exception as e:
            QgsMessageLog.logMessage(u"{}".format(str(e)), tag="QgisPDS.error")  

    def placeLabels(self):
        self.renderComplete()

    def createSummProductionlayer(self):
        try:
            if not QgsProject.instance().homePath():
                self.iface.messageBar().pushMessage(self.tr("Error"),
                            self.tr(u'Save project before load'), level=QgsMessageBar.CRITICAL)
                return
    
            dlg = QgisPDSProductionDialog(self.currentProject, self.iface, isCP=False)
            if dlg.isInitialised():
                result = dlg.exec_()
                if dlg.getLayer() is not None:
                    dlg.getLayer().attributeValueChanged.connect(self.pdsLayerModified)
        except Exception as e:
            QgsMessageLog.logMessage(u"{}".format(str(e)), tag="QgisPDS.error")  


    def refreshProduction(self, layer, project, isCurrentProd=False ,isOnlyFond=False):
        try:        
            dlg = QgisPDSProductionDialog(project, self.iface, isCP=isCurrentProd, isOnlyFond=isOnlyFond, _layer=layer)
            if dlg.isInitialised():
                result = dlg.exec_()
                if result and layer and not isOnlyFond:
                    prodSetup = QgisPDSProdSetup(self.iface, layer)
                    prodSetup.setup(layer)
            del dlg
        except Exception as e:
            QgsMessageLog.logMessage(u"{}".format(str(e)), tag="QgisPDS.error")  


    def createCPointsLayer(self):
        try:
            if not QgsProject.instance().homePath():
                self.iface.messageBar().pushMessage(self.tr("Error"),
                            self.tr(u'Save project before load'), level=QgsMessageBar.CRITICAL)
                return
            dlg = QgisPDSCPointsDialog(self.currentProject, self.iface, ControlPointReader(self.iface))
            dlg.exec_()
        except Exception as e:
            QgsMessageLog.logMessage(u"{}".format(str(e)), tag="QgisPDS.error")  
            


    def createContoursLayer(self):
        try:
            if not QgsProject.instance().homePath():
                self.iface.messageBar().pushMessage(self.tr("Error"),
                            self.tr(u'Save project before load'), level=QgsMessageBar.CRITICAL)
                return
            dlg = QgisPDSCPointsDialog(self.currentProject, self.iface, ContoursReader(self.iface,0 ,styleName=CONTOUR_STYLE,styleUserDir=USER_CONTOUR_STYLE_DIR ,isShowSymbCategrized=False ))
            dlg.exec_()
        except Exception as e:
            QgsMessageLog.logMessage(u"{}".format(str(e)), tag="QgisPDS.error")  
            


    def createPolygonsLayer(self):
        try:
            if not QgsProject.instance().homePath():
                self.iface.messageBar().pushMessage(self.tr("Error"),
                            self.tr(u'Save project before load'), level=QgsMessageBar.CRITICAL)
                return
            dlg = QgisPDSCPointsDialog(self.currentProject, self.iface, ContoursReader(self.iface,1 ,styleName=POLYGON_STYLE,styleUserDir=USER_POLYGON_STYLE_DIR ,isShowSymbCategrized=False ))
            dlg.exec_()
        except Exception as e:
            QgsMessageLog.logMessage(u"{}".format(str(e)), tag="QgisPDS.error")  
            

    def createSurfaceLayer(self):
        try:
            if not QgsProject.instance().homePath():
                self.iface.messageBar().pushMessage(self.tr('Error'),
                            self.tr(u'Save project before load'), level=QgsMessageBar.CRITICAL)
                return
            dlg = QgisPDSCPointsDialog(self.currentProject, self.iface, SurfaceReader(styleName=SURF_SYLE,styleUserDir=USER_SURF_STYLE_DIR  ))
            dlg.exec_()
            del dlg
        except Exception as e:
            QgsMessageLog.logMessage(u"{}".format(str(e)), tag="QgisPDS.error")  


    def createFaultsLayer(self):
        try:
            if not QgsProject.instance().homePath():
                self.iface.messageBar().pushMessage(self.tr("Error"),
                            self.tr(u'Save project before load'), level=QgsMessageBar.CRITICAL)
                return
            dlg = QgisPDSCPointsDialog(self.currentProject, self.iface, ContoursReader(self.iface,2 ,styleName=FAULT_STYLE,styleUserDir=USER_FAULT_STYLE_DIR ,isShowSymbCategrized=False ))
            dlg.exec_()
        except Exception as e:
            QgsMessageLog.logMessage(u"{}".format(str(e)), tag="QgisPDS.error")  
            
    
    def markLayers(self):
        try:
            for currentLayer in self.iface.legendInterface().selectedLayers():
                self.markWells(currentLayer)
        except Exception as e:
            QgsMessageLog.logMessage(u"{}".format(str(e)), tag="QgisPDS.error")  

        
    def markWells(self,currentLayer=None):
        try:
            if currentLayer is None or (not isinstance(currentLayer,QgsMapLayer))  :  currentLayer = self.iface.activeLayer()
            if currentLayer.type() != QgsMapLayer.VectorLayer:
                return
            pr = currentLayer.dataProvider()
    
            projStr = currentLayer.customProperty("pds_project", str(self.currentProject))
            proj = ast.literal_eval(projStr)
    
            currentLayer.blockSignals(True)
            filter_str=currentLayer.subsetString()
            currentLayer.setSubsetString(None)
            
            layerWellNames,_=currentLayer.getValues(Fields.WellId.name)
            
            dlg = QgisPDSWellsMarkDialog(self.iface, self.currentProject, layer=currentLayer ,  checkedWellIds=layerWellNames, checkedWellIdsColumn=1, markedWellIds=layerWellNames)
            if dlg.exec_():
                pass
            del dlg
            currentLayer.setSubsetString(filter_str)
            currentLayer.blockSignals(False)
        except Exception as e:
            QgsMessageLog.logMessage(u"{}".format(str(e)), tag="QgisPDS.error")  
      

    def createWellLayer(self):
        try:
            if not QgsProject.instance().homePath():
                self.iface.messageBar().pushMessage(self.tr("Error"),
                            self.tr(u'Save project before load wells'), level=QgsMessageBar.CRITICAL)
                return
    
            dlg = QgisPDSWellsBrowserDialog(self.iface, self.currentProject)
            if dlg.exec_():
                wells = QgisPDSWells(self.iface, self.currentProject ,styleName=WELL_STYLE,styleUserDir=USER_WELL_STYLE_DIR  )
                wells.setWellList(dlg.getWellIds())
                layer = wells.createWellLayer()
                if layer is not None:
                    layer.attributeValueChanged.connect(self.pdsLayerModified)
            del dlg
        except Exception as e:
            QgsMessageLog.logMessage(u"{}".format(str(e)), tag="QgisPDS.error")  


    def createWellDeviationLayer(self):
        try:
            if not QgsProject.instance().homePath():
                self.iface.messageBar().pushMessage(self.tr("Error"),
                            self.tr(u'Save project before load'), level=QgsMessageBar.CRITICAL)
                return
    
            dlg = QgisPDSWellsBrowserDialog(self.iface, self.currentProject)
            if dlg.exec_():
                wells = QgisPDSDeviation(self.iface, self.currentProject ,styleName=DEVI_STYLE,styleUserDir=USER_DEVI_STYLE_DIR  )
                wells.setWellList(dlg.getWellIds())
                layer = wells.createWellLayer()
    
            # if layer is not None:
            #     layer.attributeValueChanged.connect(self.pdsLayerModified)
        except Exception as e:
            QgsMessageLog.logMessage(u"{}".format(str(e)), tag="QgisPDS.error")  
            

        
    def refreshWells(self, layer, project, isRefreshKoords, isRefreshData, isSelectedOnly, isAddMissing, isDeleteMissing, filterWellIds=None):
        try:
            wells = QgisPDSWells(self.iface, project)
            wells.loadWells(layer, isRefreshKoords, isRefreshData, isSelectedOnly, isAddMissing, isDeleteMissing, filterWellIds=filterWellIds)
        except Exception as e:
            QgsMessageLog.logMessage(u"{}".format(str(e)), tag="QgisPDS.error")  


    def loadWellDeviations(self, layer, project, isRefreshKoords, isRefreshData, isSelectedOnly, isAddMissing, isDeleteMissing, filterWellIds=None):
        try:
            wells = QgisPDSDeviation(self.iface, project ,styleName=DEVI_STYLE,styleUserDir=USER_DEVI_STYLE_DIR  )
            wells.loadWells(layer, isRefreshKoords, isRefreshData, isSelectedOnly, isAddMissing, isDeleteMissing, filterWellIds=filterWellIds)
        except Exception as e:
            QgsMessageLog.logMessage(u"{}".format(str(e)), tag="QgisPDS.error")  


    def productionSetup(self):
        try:
            if not QgsProject.instance().homePath():
                self.iface.messageBar().pushMessage(self.tr('Error'),
                            self.tr(u'Save project before using plugin'), level=QgsMessageBar.CRITICAL)
                return
    
            currentLayer = self.iface.activeLayer()
            if currentLayer is None:
                return
    
            currentLayer.blockSignals(True)
            prodSetup = QgisPDSProdSetup(self.iface, currentLayer)
            prodSetup.exec_()
            currentLayer.blockSignals(False)
        except Exception as e:
            QgsMessageLog.logMessage(u"{}".format(str(e)), tag="QgisPDS.error")  


    def bubblesSetup(self):
        try:
            currentLayer = self.iface.activeLayer()
            if currentLayer is None:
                return
            currentLayer.blockSignals(True)
            prodSetup = QgisPDSBubbleSetup(self.iface, currentLayer)
            prodSetup.exec_()
            currentLayer.blockSignals(False)
        except Exception as e:
            QgsMessageLog.logMessage(u"{}".format(str(e)), tag="QgisPDS.error")  
        


    def wellCoordFromZone(self):
        try:
            selectedLayers = self.iface.legendInterface().selectedLayers()
            map( lambda currentLayer:currentLayer.blockSignals(True),selectedLayers)
            
            currentLayer = self.iface.activeLayer()
            if currentLayer is None:
                return
            #projStr = currentLayer.customProperty("pds_project", str(self.currentProject))
            #proj = ast.literal_eval(projStr)
            if len(selectedLayers)>0:
        
                dlg  = QgisPDSCoordFromZoneDialog(self.currentProject, self.iface, selectedLayers)
                dlg.exec_()
            map(lambda currentLayer:currentLayer.blockSignals(False),selectedLayers)
            return
        except Exception as e:
            QgsMessageLog.logMessage(u"{}".format(str(e)), tag="QgisPDS.error")  


    def transiteWells(self):
        try:
            selectedLayers = self.iface.legendInterface().selectedLayers()
            currentLayer = self.iface.activeLayer()
            if currentLayer is None:
                return
            #projStr = currentLayer.customProperty("pds_project", str(self.currentProject))
            #proj = ast.literal_eval(projStr)
            if len(selectedLayers)>0:
                dlg = QgisPDSTransitionsDialog(self.currentProject, self.iface, selectedLayers)
                dlg.exec_()
            return
        except Exception as e:
            QgsMessageLog.logMessage(u"{}".format(str(e)), tag="QgisPDS.error")  
        

    def refreshLayer(self):
        try:
    #        threads = []
            for currentLayer in self.iface.legendInterface().selectedLayers():
                self.refreshcurrentLayer(currentLayer)
    #             process = Thread(target=self.refreshcurrentLayer, args=[currentLayer])
    #             process.start()
    #             threads.append(process)
        except Exception as e:
            QgsMessageLog.logMessage(u"{}".format(str(e)), tag="QgisPDS.error")  
    
        
        
    def refreshcurrentLayer( self,currentLayer=None):
        try:
            if currentLayer is None:  currentLayer = self.iface.activeLayer()
            if currentLayer.type() != QgsMapLayer.VectorLayer:
                return
            pr = currentLayer.dataProvider()
    
            projStr = currentLayer.customProperty("pds_project", str(self.currentProject))
            proj = ast.literal_eval(projStr)
    
            currentLayer.blockSignals(True)
            filter_str=currentLayer.subsetString()
            currentLayer.setSubsetString(None)
            
            prop = currentLayer.customProperty("qgis_pds_type")
            layerWellIds,_=currentLayer.getValues(Fields.Sldnid.name)
            
            if prop == "pds_wells":
                dlg = QgisPDSRefreshSetup(self.iface, self.currentProject, filterWellIds=layerWellIds)
                if dlg.exec_():
                    self.refreshWells(currentLayer, self.currentProject, dlg.isRefreshKoords,
                                      dlg.isRefreshData, dlg.isSelectedOnly, dlg.isAddMissing, dlg.isDeleteMissing
                                      ,filterWellIds=dlg.filterWellIds if dlg.isNeedFilterWellIds else None
                                      )
            elif prop == "pds_fond":
                self.refreshProduction(currentLayer, self.currentProject, isOnlyFond=True)                
            elif prop == "pds_current_production":
                self.refreshProduction(currentLayer, self.currentProject, isCurrentProd=True)
            elif prop == "pds_cumulative_production":
                self.refreshProduction(currentLayer, self.currentProject, isCurrentProd=False)
            elif prop == "pds_well_deviations":
                dlg = QgisPDSRefreshSetup(self.iface, self.currentProject, filterWellIds=layerWellIds)
                if dlg.exec_():
                    self.loadWellDeviations(currentLayer, self.currentProject, dlg.isRefreshKoords,
                                            dlg.isRefreshData, dlg.isSelectedOnly, dlg.isAddMissing, dlg.isDeleteMissing
                                            ,filterWellIds=dlg.filterWellIds if dlg.isNeedFilterWellIds else None
                                            )
            currentLayer.setSubsetString(filter_str)
            currentLayer.blockSignals(False)
        except Exception as e:
            QgsMessageLog.logMessage(u"{}".format(str(e)), tag="QgisPDS.error")  
            

       
    def addProductionLayer(self):
        layer = QgisPDSProductionLayer(self.iface)
        if layer.isValid():
            QgsMapLayerRegistry.instance().addMapLayer(layer)

    def residuals(self):
        if not QgsProject.instance().homePath():
            self.iface.messageBar().pushMessage(self.tr('Error'),
                        self.tr(u'Save project before using plugin'), level=QgsMessageBar.CRITICAL)
            return
        dlg = QgisPDSResidualDialog(self.currentProject, self.iface)
        dlg.exec_()
        return

    def calcStatistics(self):
        try:
            if not QgsProject.instance().homePath():
                self.iface.messageBar().pushMessage(self.tr('Error'),
                            self.tr(u'Save project before using plugin'), level=QgsMessageBar.CRITICAL)
                return
            dlg = QgisPDSStatisticsDialog(self.currentProject, self.iface)
            dlg.exec_()
            return
        except Exception as e:
            QgsMessageLog.logMessage(u"{}".format(str(e)), tag="QgisPDS.error")  
        

    def calcDCA(self):
        try:
    #         if not QgsProject.instance().homePath():
    #             self.iface.messageBar().pushMessage(self.tr('Error'),
    #                         self.tr(u'Save project before using plugin'), level=QgsMessageBar.CRITICAL)
    #             return
            dlg = QgisPDSDCAForm(self.currentProject, self.iface)
            dlg.exec_()
            #dlg.show()
            return
        except Exception as e:
            QgsMessageLog.logMessage(u"{}".format(str(e)), tag="QgisPDS.error")  
        


    def saveLayerToPDS(self):
        try:
            currentLayer = self.iface.activeLayer()
            if not currentLayer:
                return
    
            dlg = QgisSaveMapsetToPDS(self.currentProject, self.iface, currentLayer)
            dlg.exec_()
        except Exception as e:
            QgsMessageLog.logMessage(u"{}".format(str(e)), tag="QgisPDS.error")  
            

    def dataFromOracleSql(self):
        try:
            if not QgsProject.instance().homePath():
                self.iface.messageBar().pushMessage(self.tr('Error'),
                            self.tr(u'Save project before using plugin'), level=QgsMessageBar.CRITICAL)
                return
    
            dlg = QgisOracleSql(self.currentProject, self.iface)
            dlg.exec_()
        except Exception as e:
            QgsMessageLog.logMessage(u"{}".format(str(e)), tag="QgisPDS.error")  
            

    def createIsolines(self):
        try:
            if not QgsProject.instance().homePath():
                self.iface.messageBar().pushMessage(self.tr('Error'),
                            self.tr(u'Save project before using plugin'), level=QgsMessageBar.CRITICAL)
                return
    
            dlg = QgisPDSCreateIsolines(self.iface)
            dlg.exec_()
        except Exception as e:
            QgsMessageLog.logMessage(u"{}".format(str(e)), tag="QgisPDS.error")  
            

    def createProjectString(self, args={}):
        projectName = args['project']
        options = json.loads(args['options'])
        host = options['host']
        sid = options['sid']

        return u'{0}/{1}/{2}'.format(host, sid, projectName)

    def startSelectMapTool(self, layer, exeName, appArgs):
        '''
            @TODO: work only if layer and map projection equal!!!!. In layer projection... 
        '''
        if not self.selectMapTool:
            self.selectMapTool = QgisPDSSelectMapTool(self.iface.mapCanvas(), layer)
            self.selectMapTool.finished.connect(self.selectMapTool_finished)

        self.selectMapTool.setArgs(exeName, appArgs, layer)
        self.iface.mapCanvas().setMapTool(self.selectMapTool)

    @pyqtSlot(list, str, str)
    def selectMapTool_finished(self, features, exeName, appArgs):
        if len(features):
            ids = self.getSelectedSldnids(features)
            # print  appArgs + '{' + ids + '})" '
            self.runTigressProcess(exeName, appArgs + '{' + ids + '})" ')


    def startWcorr(self):
        currentLayer = self.iface.activeLayer()
        if not currentLayer:
            return

        project = self.createProjectString(args=self.currentProject)
        # ids = self.getSelectedSldnids(currentLayer)
        args = " -script \"wcorr.load_template(" + "'{0}', ".format(project)
        self.startSelectMapTool(currentLayer, 'wcorr.exe', args)
        # args += '{' + ids + '})" '
        # self.runTigressProcess('wcorr.exe', args)

    def startWellView(self):
        currentLayer = self.iface.activeLayer()
        if not currentLayer:
            return

        project = self.createProjectString(args=self.currentProject)
        # ids = self.getSelectedSldnids(currentLayer)
        args = " -script \"wellview.load_well(" + "'{0}', ".format(project)
        self.startSelectMapTool(currentLayer, 'wellview.exe', args)
        # args += '{' + ids + '})" '
        # self.runTigressProcess('wellview.exe', args)

    def startWellLogProcessing(self):
        currentLayer = self.iface.activeLayer()
        if not currentLayer:
            return

        project = self.createProjectString(args=self.currentProject)
        # ids = self.getSelectedSldnids(currentLayer)
        args = " -script \"gsp.load_tz_table(" + "'{0}', ".format(project)
        self.startSelectMapTool(currentLayer, 'gsp.exe', args)
        # args += '{' + ids + '})" '
        # self.runTigressProcess('gsp.exe', args)

    def startDevSurvey(self):
        currentLayer = self.iface.activeLayer()
        if not currentLayer:
            return

        project = self.createProjectString(args=self.currentProject)
        # ids = self.getSelectedSldnids(currentLayer)
        args = " -script \"dvsrvy.load_survey(" + "'{0}', ".format(project)
        self.startSelectMapTool(currentLayer, 'dvsrvy.exe', args)
        # args += '{' + ids + '})" '
        # self.runTigressProcess('dvsrvy.exe', args)

    def startLogPlot(self):
        currentLayer = self.iface.activeLayer()
        if not currentLayer:
            return

        project = self.createProjectString(args=self.currentProject)
        # ids = self.getSelectedSldnids(currentLayer)
        args = " -script \"compos.load_resultsplot(" + "'{0}', ".format(project)
        self.startSelectMapTool(currentLayer, 'compos.exe', args)
        # args += '{' + ids + '})" '
        # self.runTigressProcess('compos.exe', args)

    def seis2D(self):
        currentLayer = self.iface.activeLayer()
        if not currentLayer:
            return

        project = self.createProjectString(args=self.currentProject)
        ids = '0'
        args = " -script \"inp.load_2dlines(" + "'{0}', ".format(project)
        # args += '{' + ids + '})" '
        # self.runTigressProcess('inp.exe', args)

    def seis3D(self):
        currentLayer = self.iface.activeLayer()
        if not currentLayer:
            return

        project = self.createProjectString(args=self.currentProject)
        ids = '0'
        args = " -script \"inp.load_survey3d(" + "'{0}', ".format(project)
        args += '{' + ids + '})" '
        self.runTigressProcess('inp.exe', args)
        
    def saveSettings(self):
        QSettings().setValue('currentProject', self.currentProject)

    def runTigressProcess(self, appName, args):
        tigdir = os.environ['TIGDIR']
        tigdir = tigdir.replace('\\', '/')
        exeName = tigdir + '/bin/' + appName
        if not os.path.exists(exeName):
            exeName = tigdir + '/../bin/' + appName

        if not os.path.exists(exeName):
            QtGui.QMessageBox.critical(None, self.tr(u'Error'),
                                       appName + ': ' + self.tr(u'file not found.\nPlease set TIGDIR variable'.format(appName)),
                                       QtGui.QMessageBox.Ok)
            return

        runStr = exeName + ' ' + args
        QgsMessageLog.logMessage('Running: ' + runStr, 'QGisPDS')
        # os.system(runStr)
        
        process = QProcess(self.iface)
        process_env=QProcessEnvironment()
        process_env=process_env.systemEnvironment() #all environment of parent
#         process_env.insert("PATH",
#                                 ";".join([
#                                         "ORACLE_HOME"
#                                         ,os.path.split(exeName)[0]
#                                         ,process_env.value("PATH")
#                                         ])
#                            )
        process_env.insert("PATH", getenv_system("PATH"))
        process.setProcessEnvironment(process_env)
        QgsMessageLog.logMessage('Running env: ' + "\n".join(process.processEnvironment().toStringList()), 'QGisPDS')
        process.start(runStr)


    # def getSelectedSldnids(self, layer):
    #     idx = layer.fieldNameIndex(self.sldnidFieldName)
    #     if idx < 0:
    #         return '';
    #
    #     result = '0'
    #     features = layer.selectedFeatures()
    #     for f in features:
    #          result += ',{0}'.format(f.attribute(self.sldnidFieldName))
    #
    #     return result
    def getSelectedSldnids(self, features):
        result = '0'
        try:
            for f in features:
                result += ',{0}'.format(f.attribute(self.sldnidFieldName))
        except:
            pass

        return result