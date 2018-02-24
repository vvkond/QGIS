# -*- coding: utf-8 -*-

from PyQt4 import QtGui, uic, QtCore
# from PyQt4 import QtCore, QtGui
from PyQt4.QtGui import *
# from PyQt4.QtCore import *
from qgis import core, gui
from qgis.gui import QgsColorButtonV2
# from qgis.gui import *
# from qgscolorbuttonv2 import QgsColorButtonV2
from collections import namedtuple
from qgis_pds_production import *
from bblInit import *
import ast
import math
import xml.etree.cElementTree as ET
import re

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'qgis_pds_prodsetup_base.ui'))

class QgisPDSProdSetup(QtGui.QDialog, FORM_CLASS):
    def __init__(self, iface, layer, parent=None):
        super(QgisPDSProdSetup, self).__init__(parent)

        self.setupUi(self)

        self.scaleEdit.setVisible(False)
        self.mScaleEditLabel.setVisible(False)

        self.backColorEdit = QgsColorButtonV2(self)
        self.fluidGridLayout.addWidget(self.backColorEdit, 0, 1)
        QObject.connect(self.backColorEdit, SIGNAL("colorChanged(const QColor &)"), self.backColorChanged)

        self.lineColorEdit = QgsColorButtonV2(self)
        self.fluidGridLayout.addWidget(self.lineColorEdit, 1, 1)
        QObject.connect(self.lineColorEdit, SIGNAL("colorChanged(const QColor &)"), self.lineColorChanged)

        self.labelColorEdit = QgsColorButtonV2(self)
        self.labelGridLayout.addWidget(self.labelColorEdit, 0, 1)
        QObject.connect(self.labelColorEdit, SIGNAL("colorChanged(const QColor &)"), self.labelColorChanged)

        self.mIface = iface
        self.currentLayer = layer       

        self.standardDiagramms = {
                    "1_liquidproduction": MyStruct(name=u'Диаграмма жидкости', scale=300000, testval=1, unitsType=0, units=0, fluids=[1, 0, 1, 0, 0, 0, 0, 0]),
                    "2_liquidinjection": MyStruct(name=u'Диаграмма закачки', scale=300000, testval=1,unitsType=0, units=0, fluids=[0, 0, 0, 0, 1, 1, 0, 0]),
                    "3_gasproduction": MyStruct(name=u"Диаграмма газа", scale=300000, testval=1,unitsType=1, units=0, fluids=[0, 1, 0, 0, 0, 0, 0, 0]),
                    "4_condensatproduction": MyStruct(name=u"Диаграмма конденсата", scale=3000000, testval=1,unitsType=0, units=0, fluids=[0, 0, 0, 1, 0, 0, 0, 0])
                }

        self.layerDiagramms = []

        self.componentsList.clear()
        i = 1
        for fl in bblInit.fluidCodes:
            try:
                item = QtGui.QListWidgetItem(str(i)+". "+ QCoreApplication.translate('bblInit', fl.name))
            except:
                item = QtGui.QListWidgetItem(str(i) + ". " + fl.name)
            item.setData(Qt.UserRole, fl.code)
            item.setCheckState(Qt.Unchecked)
            self.componentsList.addItem(item)
            i = i + 1


        self.bubbleProps = None
        renderer = self.currentLayer.rendererV2()
        if renderer is not None and renderer.type() == 'RuleRenderer':
            root_rule = renderer.rootRule()
            for r in root_rule.children():
                for l in r.symbol().symbolLayers():
                    if l.layerType() == 'BubbleMarker':
                        self.bubbleProps = l.properties()
                        break
                if self.bubbleProps is not None:
                    break

        if self.bubbleProps is None:
            registry = QgsSymbolLayerV2Registry.instance()
            bubbleMeta = registry.symbolLayerMetadata('BubbleMarker')
            if bubbleMeta is not None:
                bubbleLayer = bubbleMeta.createSymbolLayer({})
                self.bubbleProps = bubbleLayer.properties()

        if self.bubbleProps is None:
            self.bubbleProps = {}

        #Read saved layer settings
        self.readSettings()
    
        self.scaleUnitsMass.setVisible(False)
        self.scaleUnitsVolume.setVisible(False)

        self.isCurrentProd = True if self.currentLayer.customProperty("qgis_pds_type") == 'pds_current_production' else False
        self.defaultUnitNum = 2 if self.isCurrentProd else 3

        self.updateWidgets()
        # if len(self.layerDiagramms) < 1:
        #     self.dailyProduction.setChecked(self.isCurrentProd)
        #     self.layerDiagramms.append(MyStruct(name=u'Диаграмма жидкости', scale=300000, testval=1, unitsType=0,
        #                                         units=self.defaultUnitNum, fluids=[1, 0, 1, 0, 0, 0, 0, 0]))
        #
        # self.mDeleteDiagramm.setEnabled(len(self.layerDiagramms) > 1)
        # for d in self.layerDiagramms:
        #     name = d.name
        #     item = QtGui.QListWidgetItem(name)
        #     item.setData(Qt.UserRole, d)
        #     self.mDiagrammsListWidget.addItem(item)

        return

    def updateWidgets(self):
        self.mDiagrammsListWidget.clear()

        if len(self.layerDiagramms) < 1:
            self.dailyProduction.setChecked(self.isCurrentProd)
            self.layerDiagramms.append(MyStruct(name=u'Диаграмма жидкости', scale=300000, testval=1, unitsType=0,
                                                units=self.defaultUnitNum, fluids=[1, 0, 1, 0, 0, 0, 0, 0]))

        self.mDeleteDiagramm.setEnabled(len(self.layerDiagramms) > 1)
        for d in self.layerDiagramms:
            name = d.name
            item = QtGui.QListWidgetItem(name)
            item.setData(Qt.UserRole, d)
            self.mDiagrammsListWidget.addItem(item)


    # SLOT
    def on_mDiagrammsListWidget_currentRowChanged(self, row):
        if row < 0:
            return

        item = self.mDiagrammsListWidget.item(row)
        diagramm = item.data(Qt.UserRole)
        self.scaleUnitsType.setCurrentIndex(diagramm.unitsType)
        self.scaleEdit.setValue(diagramm.scale)
        self.titleEdit.setText(diagramm.name)

        self.scaleUnitsMass.setVisible(diagramm.unitsType == 0)
        self.scaleUnitsVolume.setVisible(diagramm.unitsType == 1)

        if diagramm.unitsType == 0:
            self.scaleUnitsMass.setCurrentIndex(diagramm.units)
        else:
            self.scaleUnitsVolume.setCurrentIndex(diagramm.units - 10)

        vec = diagramm.fluids
        for idx, v in enumerate(vec):
            self.componentsList.item(idx).setCheckState(Qt.Checked if v else Qt.Unchecked)

    def mAddDiagramm_clicked(self):
        newName = u'Диаграмма {}'.format(len(self.layerDiagramms)+1)
        d = MyStruct(name=newName, scale=300000, testval=1, unitsType=0, units=self.defaultUnitNum,
                                            fluids=[0, 0, 0, 0, 0, 0, 0, 0])
        self.layerDiagramms.append(d)

        item = QtGui.QListWidgetItem(newName)
        item.setData(Qt.UserRole, d)
        self.mDiagrammsListWidget.addItem(item)
        self.mDeleteDiagramm.setEnabled(len(self.layerDiagramms) > 1)

    def mDeleteDiagramm_clicked(self):
        if len(self.layerDiagramms) < 2:
            return

        idx = self.mDiagrammsListWidget.currentRow()
        if idx >= 0:
            self.mDiagrammsListWidget.takeItem(idx)
            del self.layerDiagramms[idx]

        self.mDeleteDiagramm.setEnabled(len(self.layerDiagramms) > 1)

    def mImportFromLayer_clicked(self):
        layers = self.mIface.legendInterface().layers()

        layersList = []
        for layer in layers:
            if bblInit.isProductionLayer(layer) and layer.name() != self.currentLayer.name():
                layersList.append(layer.name())

        name, result = QInputDialog.getItem(self, self.tr("Layers"), self.tr("Select layer"), layersList, 0, False)
        lay = None
        for layer in layers:
            if layer.name() == name:
                lay = layer
                break

        if result and lay:
            saveLayer = self.currentLayer
            self.currentLayer = lay
            try:
                if self.readSettingsNew():
                    self.updateWidgets()
            except:
                pass
            self.currentLayer = saveLayer


    # SLOT
    def on_titleEdit_editingFinished(self):
        idx = self.mDiagrammsListWidget.currentRow()
        if idx >= 0:
            self.layerDiagramms[idx].name = self.titleEdit.text()
            item = self.mDiagrammsListWidget.item(idx)
            item.setText(self.titleEdit.text())


    def on_buttonBox_accepted(self):
        self.setup(self.currentLayer)

    # SLOT
    def on_buttonBox_clicked(self, btn):
        if self.buttonBox.buttonRole(btn) == QDialogButtonBox.ApplyRole:
            self.setup(self.currentLayer)


    # SLOT
    # def setup(self, editLayer):
    #
    #     self.applySettings()
    #
    #     maxDiagrammSize = self.maxDiagrammSize.value() / 2
    #     minDiagrammSize = self.minDiagrammSize.value() / 2
    #     dScale = self.scaleEdit.value()
    #
    #     code = self.diagrammType.itemData(self.diagrammType.currentIndex())
    #
    #
    #     vec = self.standardDiagramms[code].fluids
    #     if self.scaleUnitsType.currentIndex() == 0:
    #         scaleType = QgisPDSProductionDialog.attrFluidMass("")
    #     else:
    #         scaleType = QgisPDSProductionDialog.attrFluidVolume("")
    #
    #     prodFields = [ bblInit.fluidCodes[idx].code for idx, v in enumerate(vec) if v]
    #     prods = [ bblInit.fluidCodes[idx] for idx, v in enumerate(vec) if v]
    #
    #     koef = (maxDiagrammSize-minDiagrammSize) / dScale
    #
    #     editLayerProvider = editLayer.dataProvider()
    #
    #     uniqSymbols = {}
    #
    #     editLayer.startEditing()
    #
    #     idxOffX = editLayerProvider.fieldNameIndex('LablOffX')
    #     idxOffY = editLayerProvider.fieldNameIndex('LablOffY')
    #     if idxOffX < 0 or idxOffY < 0:
    #         editLayerProvider.addAttributes(
    #             [QgsField("LablOffX", QVariant.Double),
    #              QgsField("LablOffY", QVariant.Double)])
    #
    #     iter = editLayerProvider.getFeatures()
    #     for feature in iter:
    #         geom = feature.geometry()
    #         FeatureId = feature.id()
    #
    #         uniqSymbols[feature['SymbolCode']] = feature['SymbolName']
    #
    #         sum = 0
    #         for attrName in prodFields:
    #             attr = attrName+scaleType
    #             if feature[attr] is not None:
    #                 sum += feature[attr]
    #
    #         diagrammSize = minDiagrammSize + sum * koef
    #
    #         point = geom.asPoint()
    #         origX = point.x()
    #         origY = point.y()
    #
    #         offset = diagrammSize if diagrammSize < maxDiagrammSize else maxDiagrammSize
    #         if feature.attribute('LablOffset') is None:
    #             editLayer.changeAttributeValue(FeatureId, editLayerProvider.fieldNameIndex('LablOffX'), offset)
    #             editLayer.changeAttributeValue(FeatureId, editLayerProvider.fieldNameIndex('LablOffY'), -offset)
    #
    #         # editLayer.changeAttributeValue(FeatureId, editLayerProvider.fieldNameIndex('LablOffset'), offset)
    #
    #         editLayer.changeAttributeValue(FeatureId, editLayerProvider.fieldNameIndex('BubbleSize'), diagrammSize*2)
    #         editLayer.changeAttributeValue(FeatureId, editLayerProvider.fieldNameIndex('BubbleFields'), ','.join(prodFields))
    #         editLayer.changeAttributeValue(FeatureId, editLayerProvider.fieldNameIndex('ScaleType'), scaleType)
    #
    #     editLayer.commitChanges()
    #
    #     plugin_dir = os.path.dirname(__file__)
    #
    #     registry = QgsSymbolLayerV2Registry.instance()
    #
    #     symbol = QgsMarkerSymbolV2()
    #     bubbleMeta = registry.symbolLayerMetadata('BubbleMarker')
    #     if bubbleMeta is not None:
    #         bubbleLayer = bubbleMeta.createSymbolLayer(self.bubbleProps)
    #         bubbleLayer.setSize(0.001)
    #         bubbleLayer.setSizeUnit(QgsSymbolV2.MapUnit)
    #         symbol.changeSymbolLayer(0, bubbleLayer)
    #     else:
    #         symbol.changeSymbolLayer(0, QgsSvgMarkerSymbolLayerV2())
    #
    #     renderer = QgsRuleBasedRendererV2(symbol)
    #     root_rule = renderer.rootRule()
    #
    #     args = (self.standardDiagramms[code].name, self.standardDiagramms[code].scale)
    #     root_rule.children()[0].setLabel(u'{0} {1}'.format(*args))
    #     for symId in uniqSymbols:
    #         svg = QgsSvgMarkerSymbolLayerV2()
    #         svg.setPath(plugin_dir+"/svg/WellSymbol"+str(symId).zfill(3)+".svg")
    #         svg.setSize(4)
    #         svg.setSizeUnit(QgsSymbolV2.MM)
    #         symbol = QgsMarkerSymbolV2()
    #         symbol.changeSymbolLayer(0, svg)
    #
    #         rule = QgsRuleBasedRendererV2.Rule(symbol)
    #         rule.setLabel(uniqSymbols[symId])
    #
    #         args = ("SymbolCode", symId)
    #         rule.setFilterExpression(u'\"{0}\"={1}'.format("SymbolCode", symId))
    #         root_rule.appendChild(rule)
    #
    #     #add lift method
    #     # ggMeta = registry.symbolLayerMetadata('GeometryGenerator')
    #     # if ggMeta is not None:
    #     #     gg = ggMeta.createSymbolLayer({})
    #     #     gg.setGeometryExpression ("make_line(  make_point( $x, $y),  make_point( $x, $y+ \"BubbleSize\"/1.5 ))")
    #     #     gg.setSymbolType(QgsSymbolV2.Line)
    #     #     symbol = QgsMarkerSymbolV2()
    #     #     symbol.changeSymbolLayer(0, gg)
    #     #     rule = QgsRuleBasedRendererV2.Rule(symbol)
    #     #     rule.setLabel('flowing')
    #
    #     #     args = ("LiftMethod", "flowing")
    #     #     rule.setFilterExpression(u'\"{0}\"=\'{1}\''.format(*args))
    #     #     root_rule.appendChild(rule)
    #
    #
    #     for ff in prods:
    #         m = QgsSimpleMarkerSymbolLayerV2()
    #         m.setSize(4)
    #         m.setSizeUnit(QgsSymbolV2.MM)
    #         m.setColor(ff.backColor)
    #         symbol = QgsMarkerSymbolV2()
    #         symbol.changeSymbolLayer(0, m)
    #
    #         rule = QgsRuleBasedRendererV2.Rule(symbol)
    #         rule.setLabel(ff.name)
    #         rule.setFilterExpression(u'\"SymbolCode\"=-1')
    #         root_rule.appendChild(rule)
    #
    #     renderer.setOrderByEnabled(True)
    #     orderByClause = QgsFeatureRequest.OrderByClause('BubbleSize', False)
    #     orderBy = QgsFeatureRequest.OrderBy([orderByClause])
    #     renderer.setOrderBy(orderBy)
    #     editLayer.setRendererV2(renderer)
    #
    #     editLayer.triggerRepaint()
    #
    #     return

    def getCoordinatesForPercent(self, percent):
        x = math.cos(2 * math.pi * percent)
        y = math.sin(2 * math.pi * percent)
        return (x, y)

    def fluidByCode(self, code):
        for f in bblInit.fluidCodes:
            if f.code == code:
                return f
        return None

    def setup(self, editLayer):

        self.applySettings()

        maxDiagrammSize = self.maxDiagrammSize.value()
        minDiagrammSize = self.minDiagrammSize.value()
        if maxDiagrammSize < minDiagrammSize:
            maxDiagrammSize = minDiagrammSize

        editLayerProvider = editLayer.dataProvider()

        uniqSymbols = {}
        prods = {}

        editLayer.startEditing()

        idxOffX = editLayerProvider.fieldNameIndex('LablOffX')
        idxOffY = editLayerProvider.fieldNameIndex('LablOffY')
        if idxOffX < 0 or idxOffY < 0:
            editLayerProvider.addAttributes(
                [QgsField("LablOffX", QVariant.Double),
                 QgsField("LablOffY", QVariant.Double)])

        diagLabel = ''
        for d in self.layerDiagramms:
            if len(diagLabel) > 0:
                diagLabel += '\n'
            diagLabel += u'{0} {1}'.format(d.name, d.scale)

        iter = editLayerProvider.getFeatures()

        maxSum = 0.0
        for feature in iter:
            for d in self.layerDiagramms:
                vec = d.fluids
                if d.unitsType == 0:
                    scaleType = QgisPDSProductionDialog.attrFluidMass("")
                else:
                    scaleType = QgisPDSProductionDialog.attrFluidVolume("")

                prodFields = [bblInit.fluidCodes[idx].code for idx, v in enumerate(vec) if v]

                sum = 0
                multiplier = bblInit.unit_to_mult.get(d.units, 1.0)
                for attrName in prodFields:
                    attr = attrName + scaleType
                    if feature[attr] is not None:
                        val = feature[attr] * multiplier
                        sum += val

                if maxSum < sum:
                    maxSum = sum

        if maxSum == 0.0:
            maxSum = maxSum + 1

        iter = editLayerProvider.getFeatures()
        for feature in iter:
            FeatureId = feature.id()

            uniqSymbols[feature['SymbolCode']] = feature['SymbolName']

            diagrammSize = 0
            root = ET.Element("root")
            templateStr = self.templateExpression.text()
            for d in self.layerDiagramms:
                vec = d.fluids
                if d.unitsType == 0:
                    scaleType = QgisPDSProductionDialog.attrFluidMass("")
                else:
                    scaleType = QgisPDSProductionDialog.attrFluidVolume("")

                prodFields = [bblInit.fluidCodes[idx].code for idx, v in enumerate(vec) if v]

                koef = (maxDiagrammSize - minDiagrammSize) / maxSum # d.scale
                sum = 0
                multiplier = bblInit.unit_to_mult.get(d.units, 1.0)
                for attrName in prodFields:
                    attr = attrName + scaleType
                    if feature[attr] is not None:
                        val = feature[attr] * multiplier
                        sum += val

                if sum != 0:
                    diag = ET.SubElement(root, "diagramm", size=str(minDiagrammSize + sum * koef))
                    for attrName in prodFields:
                        attr = attrName + scaleType
                        fluid = self.fluidByCode(attrName)
                        prods[fluid.code] = fluid
                        if feature[attr] is not None and fluid is not None:
                            val = feature[attr] * multiplier
                            percent = val / sum
                            ET.SubElement(diag, 'value', backColor=QgsSymbolLayerV2Utils.encodeColor(fluid.backColor),
                                          lineColor=QgsSymbolLayerV2Utils.encodeColor(fluid.lineColor),
                                          fieldName=attr).text = str(percent)

                if minDiagrammSize + sum * koef > diagrammSize:
                    diagrammSize = minDiagrammSize + sum * koef

                templateStr = self.addLabels(templateStr, sum, vec, feature, scaleType, multiplier)

            if diagrammSize >= minDiagrammSize:
                ET.SubElement(root, "label", labelText=templateStr)

            offset = diagrammSize if diagrammSize < maxDiagrammSize else maxDiagrammSize
            if feature.attribute('LablOffset') is None:
                editLayer.changeAttributeValue(FeatureId, editLayerProvider.fieldNameIndex('LablOffX'), offset/3)
                editLayer.changeAttributeValue(FeatureId, editLayerProvider.fieldNameIndex('LablOffY'), -offset/3)

            editLayer.changeAttributeValue(FeatureId, editLayerProvider.fieldNameIndex('BubbleSize'), diagrammSize)
            editLayer.changeAttributeValue(FeatureId, editLayerProvider.fieldNameIndex('BubbleFields'),
                                           ET.tostring(root))
            editLayer.changeAttributeValue(FeatureId, editLayerProvider.fieldNameIndex('ScaleType'), scaleType)

        editLayer.commitChanges()

        plugin_dir = os.path.dirname(__file__)

        registry = QgsSymbolLayerV2Registry.instance()

        symbol = QgsMarkerSymbolV2()
        bubbleMeta = registry.symbolLayerMetadata('BubbleMarker')
        if bubbleMeta is not None:
            bubbleProps = {}
            bubbleProps['showLineout'] = str(int(not self.showLineouts.isChecked()))
            bubbleProps['showLabels'] = '1'
            bubbleProps['showDiagramms'] = '1'
            bubbleProps['labelSize'] = str(self.labelSizeEdit.value())
            bubbleLayer = bubbleMeta.createSymbolLayer(bubbleProps)
            bubbleLayer.setSize(3)
            bubbleLayer.setSizeUnit(QgsSymbolV2.MM)
            symbol.changeSymbolLayer(0, bubbleLayer)
        else:
            symbol.changeSymbolLayer(0, QgsSvgMarkerSymbolLayerV2())

        renderer = QgsRuleBasedRendererV2(symbol)
        root_rule = renderer.rootRule()

        if bubbleMeta:
            bubbleProps = {}
            bubbleProps['showLineout'] = str(int(self.showLineouts.isChecked()))
            bubbleProps['showLabels'] = '0'
            bubbleProps['showDiagramms'] = '0'
            bubbleProps['labelSize'] = str(self.labelSizeEdit.value())
            bubbleLayer = bubbleMeta.createSymbolLayer(bubbleProps)
            bubbleLayer.setSize(3)
            bubbleLayer.setSizeUnit(QgsSymbolV2.MM)
            symbol1 = QgsMarkerSymbolV2()
            symbol1.changeSymbolLayer(0, bubbleLayer)
            rule = QgsRuleBasedRendererV2.Rule(symbol1)
            rule.setLabel(u'Скважины')
            root_rule.appendChild(rule)

        # args = (self.standardDiagramms[code].name, self.standardDiagramms[code].scale)
        sSize = self.mSymbolSize.value()
        root_rule.children()[0].setLabel(diagLabel)
        for symId in uniqSymbols:
            svg = QgsSvgMarkerSymbolLayerV2()
            svg.setPath(plugin_dir + "/svg/WellSymbol" + str(symId).zfill(3) + ".svg")
            svg.setSize(sSize)
            svg.setSizeUnit(QgsSymbolV2.MM)
            symbol = QgsMarkerSymbolV2()
            symbol.changeSymbolLayer(0, svg)

            rule = QgsRuleBasedRendererV2.Rule(symbol)
            rule.setLabel(uniqSymbols[symId])

            rule.setFilterExpression(u'\"{0}\"={1}'.format("SymbolCode", symId))
            root_rule.appendChild(rule)

        for key,ff in prods.iteritems():
            m = QgsSimpleMarkerSymbolLayerV2()
            m.setSize(4)
            m.setSizeUnit(QgsSymbolV2.MM)
            m.setColor(ff.backColor)
            symbol = QgsMarkerSymbolV2()
            symbol.changeSymbolLayer(0, m)

            rule = QgsRuleBasedRendererV2.Rule(symbol)
            try:
                rule.setLabel(QCoreApplication.translate('bblInit', ff.name))
            except:
                rule.setLabel(ff.name)
            rule.setFilterExpression(u'\"SymbolCode\"=-1')
            root_rule.appendChild(rule)

        renderer.setOrderByEnabled(True)
        orderByClause = QgsFeatureRequest.OrderByClause('BubbleSize', False)
        orderBy = QgsFeatureRequest.OrderBy([orderByClause])
        renderer.setOrderBy(orderBy)
        editLayer.setRendererV2(renderer)

        editLayer.triggerRepaint()

        return

    def addLabels(self, templateStr, sum, fluids, feature, scaleType, multiplier):
        showZero = int(self.mShowZero.isChecked())
        formatString = "{:."+str(self.decimalEdit.value())+"f}"
        days = feature["Days"]
        if days:
            days = 1.0 / days
        for idx, v in enumerate(fluids):
            if v:
                fluid = bblInit.fluidCodes[idx]
                code = '%'+str(idx+1)
                strVal = '0'
                val = 0.0
                percentStr = ''
                if code in templateStr:
                    attr = fluid.code + scaleType
                    val = feature[attr]
                    if val is not None:
                        val *= multiplier
                    else:
                        val = 0
                    if fluid.inPercent and sum != 0:
                        val = val / sum * 100
                        percentStr = '%'
                    elif self.dailyProduction.isChecked() and days:
                        val *= days
                    strVal = formatString.format(val) + percentStr

                colorStr = fluid.labelColor.name()
                if float(formatString.format(val)) > float(0) or showZero == 1:
                    templateStr = templateStr.replace(code, '<span><font color="{0}">{1}</font></span>'.format(colorStr,
                                                                                                               strVal))
                else:
                    templateStr = templateStr.replace(code, '')

        templateStr = re.sub('^[\,\:\;\.\-/\\_ ]+|[\,\:\;\.\-/\\_ ]+$', '', templateStr)
        return templateStr


    def scaleValueEditingFinished(self):
        idx = self.mDiagrammsListWidget.currentRow()
        if idx >= 0:
            self.layerDiagramms[idx].scale = self.scaleEdit.value()
            # code = self.diagrammType.itemData(idx)
            # self.standardDiagramms[code].scale = self.scaleEdit.value()


    def scaleUnitsChanged(self, index):
        idx = self.mDiagrammsListWidget.currentRow()
        if idx >= 0:
            self.layerDiagramms[idx].unitsType = index
        # self.standardDiagramms[self.currentDiagramm].unitsType = index

        self.scaleUnitsMass.setVisible(index == 0)
        self.scaleUnitsVolume.setVisible(index == 1)


    def unitsChanged(self, index):
        idx = self.mDiagrammsListWidget.currentRow()
        if idx >= 0:
            self.layerDiagramms[idx].units = index
        # self.standardDiagramms[self.currentDiagramm].units = index


    def unitsChangedVol(self, index):
        idx = self.mDiagrammsListWidget.currentRow()
        if idx >= 0:
            self.layerDiagramms[idx].units = index+10
        # self.standardDiagramms[self.currentDiagramm].units = index+10


    def componentsItemClicked(self, item):
        # idx = self.diagrammType.currentIndex()
        # if idx >= 0:
        #     code = self.diagrammType.itemData(idx)
        idx = self.mDiagrammsListWidget.currentRow()
        if idx >= 0:
            val = self.layerDiagramms[idx]
            # val = self.standardDiagramms[code]
            row = self.componentsList.row(item)
            val.fluids[row] = 1 if item.checkState() == Qt.Checked else 0

#            self.backColorEdit.setColor(val.backColor

    def on_componentsList_currentRowChanged(self, row):
        if row < 0:
            return

        self.backColorEdit.blockSignals(True)
        self.lineColorEdit.blockSignals(True)
        self.labelColorEdit.blockSignals(True)
        self.showInPercent.blockSignals(True)

        self.backColorEdit.setColor(bblInit.fluidCodes[row].backColor)
        self.lineColorEdit.setColor(bblInit.fluidCodes[row].lineColor)
        self.labelColorEdit.setColor(bblInit.fluidCodes[row].labelColor)
        self.showInPercent.setChecked(bblInit.fluidCodes[row].inPercent);

        self.backColorEdit.blockSignals(False)
        self.lineColorEdit.blockSignals(False)
        self.labelColorEdit.blockSignals(False)
        self.showInPercent.blockSignals(False)
        return


    def on_showInPercent_clicked(self):
        row = self.componentsList.currentRow()
        if row < 0:
            return

        bblInit.fluidCodes[row].inPercent = 1 if self.showInPercent.isChecked() else 0
        return

    #SLOT
    def backColorChanged(self, color):
        row = self.componentsList.currentRow()
        if row < 0:
            return

        bblInit.fluidCodes[row].backColor = color
        return


    def lineColorChanged(self, color):
        row = self.componentsList.currentRow()
        if row < 0:
            return

        bblInit.fluidCodes[row].lineColor = color
        return


    def labelColorChanged(self, color):
        row = self.componentsList.currentRow()
        if row < 0:
            return

        bblInit.fluidCodes[row].labelColor = color
        return


    # def on_diagrammType_editTextChanged(self, text):
    #     idx = self.diagrammType.currentIndex()
    #     if idx >= 0:
    #         self.diagrammType.setItemText(idx, text);
    #         code = self.diagrammType.itemData(idx)
    #         self.standardDiagramms[code].name = text

    def on_addToTemplate_pressed(self):
        row = self.componentsList.currentRow()
        if row < 0:
            return

        tmpStr = self.templateExpression.text()
        if self.mNewLineCheckBox.isChecked():
            self.templateExpression.setText(tmpStr + '<div>%' + str(row + 1) + '</div>')
        else:
            self.templateExpression.setText(tmpStr + '-%' + str(row+1))

    def on_maxDiagrammSize_valueChanged(self, val):
        if type(val) is float:
            self.minDiagrammSize.blockSignals(True)
            self.minDiagrammSize.setMaximum(val)
            self.minDiagrammSize.blockSignals(False)


    #Read layer settings
    def readSettings(self):
        try:
            if self.readSettingsNew():
                return
        except:
            return

        self.currentDiagramm = self.bubbleProps['diagrammType'] if 'diagrammType' in self.bubbleProps else '1_liquidproduction'
        # self.maxDiagrammSize.setValue(float(self.bubbleProps["maxDiagrammSize"]) if 'maxDiagrammSize' in self.bubbleProps else 0.01)
        # self.minDiagrammSize.setValue(float(self.bubbleProps["minDiagrammSize"]) if 'minDiagrammSize' in self.bubbleProps else 0.0)

        for d in self.standardDiagramms:
            val = self.standardDiagramms[d]
            name = self.bubbleProps['diagramm_name_'+d] if 'diagramm_name_'+d in self.bubbleProps else ''
            if name :
                val.name = name
            val.scale = float(self.bubbleProps['diagramm_scale_'+d]) if 'diagramm_scale_'+d in self.bubbleProps else val.scale
            val.unitsType =  int(self.bubbleProps['diagramm_unitsType_'+d]) if 'diagramm_unitsType_'+d in self.bubbleProps else val.unitsType
            val.units = int(self.bubbleProps['diagramm_units_'+d]) if 'diagramm_units_'+d in self.bubbleProps else val.units
            if 'diagramm_fluids_'+d in self.bubbleProps :
                val.fluids = QgsSymbolLayerV2Utils.decodeRealVector(self.bubbleProps['diagramm_fluids_'+d])
            self.standardDiagramms[d] = val

        scope = QgsExpressionContextUtils.layerScope(self.currentLayer)

        self.labelSizeEdit.setValue(float(self.bubbleProps['labelSize']) if 'labelSize' in self.bubbleProps else self.labelSizeEdit.value() )
        self.decimalEdit.setValue(int(self.bubbleProps['decimal']) if 'decimal' in self.bubbleProps else self.decimalEdit.value())
        self.templateExpression.setText(self.bubbleProps['labelTemplate'] if 'labelTemplate' in self.bubbleProps else self.templateExpression.text())
        self.showLineouts.setChecked(int(self.bubbleProps['showLineout']) if 'showLineout' in self.bubbleProps else 1)
        self.dailyProduction.setChecked(int(self.bubbleProps['dailyProduction']) if 'dailyProduction' in self.bubbleProps else 0)

        for fl in bblInit.fluidCodes:
            if 'fluid_background_'+fl.code in self.bubbleProps:
                fl.backColor = QgsSymbolLayerV2Utils.decodeColor(self.bubbleProps['fluid_background_'+fl.code])
            if 'fluid_line_color_'+fl.code in self.bubbleProps:
                fl.lineColor = QgsSymbolLayerV2Utils.decodeColor(self.bubbleProps['fluid_line_color_'+fl.code])
            if 'fluid_label_color_'+fl.code in self.bubbleProps:
                fl.labelColor = QgsSymbolLayerV2Utils.decodeColor(self.bubbleProps['fluid_label_color_'+fl.code])
            if 'fluid_inPercent_'+fl.code in self.bubbleProps:
                fl.inPercent = int(self.bubbleProps['fluid_inPercent_'+fl.code])

        return

    #Write layer settings
    def applySettings(self):
        try:
            self.saveSettings()
        except:
            pass

        # self.bubbleProps['diagrammType'] = self.currentDiagramm
        # self.bubbleProps["maxDiagrammSize"] = str(self.maxDiagrammSize.value())
        # self.bubbleProps["minDiagrammSize"] = str(self.minDiagrammSize.value())
        #
        # for d in self.standardDiagramms:
        #     val = self.standardDiagramms[d]
        #     self.bubbleProps['diagramm_name_'+d] = val.name
        #     self.bubbleProps['diagramm_scale_'+d] = str(val.scale)
        #     self.bubbleProps['diagramm_unitsType_'+d] = str(val.unitsType)
        #     self.bubbleProps['diagramm_units_'+d] = str(val.units)
        #     self.bubbleProps['diagramm_fluids_'+d] = QgsSymbolLayerV2Utils.encodeRealVector(val.fluids)
        #
        # self.bubbleProps['labelSize'] = str(self.labelSizeEdit.value())
        # self.bubbleProps['decimal'] = str(self.decimalEdit.value())
        # self.bubbleProps['labelTemplate'] = self.templateExpression.text()
        # self.bubbleProps['showLineout'] = str(int(self.showLineouts.isChecked()))
        # self.bubbleProps['dailyProduction'] = str(int(self.dailyProduction.isChecked()))
        # for fl in bblInit.fluidCodes:
        #     self.bubbleProps['fluid_background_'+fl.code] =  QgsSymbolLayerV2Utils.encodeColor(fl.backColor)
        #     self.bubbleProps['fluid_line_color_'+fl.code] = QgsSymbolLayerV2Utils.encodeColor(fl.lineColor)
        #     self.bubbleProps['fluid_label_color_'+fl.code] = QgsSymbolLayerV2Utils.encodeColor(fl.labelColor)
        #     self.bubbleProps['fluid_inPercent_'+fl.code] = str(fl.inPercent)

        return

    def readSettingsNew(self):
        self.currentDiagramm = '1_liquidproduction'
        self.maxDiagrammSize.setValue(float(self.currentLayer.customProperty('maxDiagrammSize', 15)))
        self.minDiagrammSize.setValue(float(self.currentLayer.customProperty('minDiagrammSize', 3.0)))
        self.mShowZero.setChecked(int(self.currentLayer.customProperty("alwaysShowZero", "0")) == 1)
        self.mSymbolSize.setValue(float(self.currentLayer.customProperty("defaultSymbolSize", 4.0)))

        count = int(self.currentLayer.customProperty("diagrammCount", 0))
        if count < 1:
            return False

        self.layerDiagramms = []
        for num in xrange(count):
            d = str(num+1)
            val = MyStruct()
            val.name = self.currentLayer.customProperty('diagramm_name_' + d, "--")
            val.scale = float(self.currentLayer.customProperty('diagramm_scale_' + d, 300000))
            val.unitsType = int(self.currentLayer.customProperty('diagramm_unitsType_' + d, 0))
            val.units = int(self.currentLayer.customProperty('diagramm_units_' + d, 0))
            val.fluids = QgsSymbolLayerV2Utils.decodeRealVector(self.currentLayer.customProperty('diagramm_fluids_' + d))
            self.layerDiagramms.append(val)

        self.labelSizeEdit.setValue(float(self.currentLayer.customProperty('labelSize', self.labelSizeEdit.value())))
        self.decimalEdit.setValue(int(self.currentLayer.customProperty('decimal', self.decimalEdit.value())))
        self.templateExpression.setText(self.currentLayer.customProperty('labelTemplate', self.templateExpression.text()))
        self.showLineouts.setChecked(int(self.currentLayer.customProperty('showLineout')))
        self.dailyProduction.setChecked(int(self.currentLayer.customProperty('dailyProduction')))
        for fl in bblInit.fluidCodes:
            backColor = self.currentLayer.customProperty('fluid_background_' + fl.code,
                                                            QgsSymbolLayerV2Utils.encodeColor(fl.backColor))
            fl.backColor = QgsSymbolLayerV2Utils.decodeColor(backColor)
            lineColor = self.currentLayer.customProperty('fluid_line_color_' + fl.code,
                                                            QgsSymbolLayerV2Utils.encodeColor(fl.lineColor))
            fl.lineColor = QgsSymbolLayerV2Utils.decodeColor(lineColor)
            labelColor = self.currentLayer.customProperty('fluid_label_color_' + fl.code,
                                                             QgsSymbolLayerV2Utils.encodeColor(fl.labelColor))
            fl.labelColor = QgsSymbolLayerV2Utils.decodeColor(labelColor)
            fl.inPercent = int(self.currentLayer.customProperty('fluid_inPercent_' + fl.code))

        return True

    def saveSettings(self):
        self.currentLayer.setCustomProperty("diagrammCount", len(self.layerDiagramms))

        self.currentLayer.setCustomProperty("maxDiagrammSize", self.maxDiagrammSize.value())
        self.currentLayer.setCustomProperty("minDiagrammSize", self.minDiagrammSize.value())
        self.currentLayer.setCustomProperty("alwaysShowZero", int(self.mShowZero.isChecked()))
        self.currentLayer.setCustomProperty("defaultSymbolSize", self.mSymbolSize.value())

        num = 1
        for val in self.layerDiagramms:
            d = str(num)
            self.currentLayer.setCustomProperty('diagramm_name_' + d, val.name)
            self.currentLayer.setCustomProperty('diagramm_scale_' + d, val.scale)
            self.currentLayer.setCustomProperty('diagramm_unitsType_' + d, val.unitsType)
            self.currentLayer.setCustomProperty('diagramm_units_' + d, val.units)
            self.currentLayer.setCustomProperty('diagramm_fluids_' + d,
                                                QgsSymbolLayerV2Utils.encodeRealVector(val.fluids))
            num = num + 1

        self.currentLayer.setCustomProperty('labelSize', self.labelSizeEdit.value())
        self.currentLayer.setCustomProperty('decimal', self.decimalEdit.value())
        self.currentLayer.setCustomProperty('labelTemplate', self.templateExpression.text())
        self.currentLayer.setCustomProperty('showLineout', str(int(self.showLineouts.isChecked())))
        self.currentLayer.setCustomProperty('dailyProduction', str(int(self.dailyProduction.isChecked())))
        for fl in bblInit.fluidCodes:
            self.currentLayer.setCustomProperty('fluid_background_' + fl.code,
                                                QgsSymbolLayerV2Utils.encodeColor(fl.backColor))
            self.currentLayer.setCustomProperty('fluid_line_color_' + fl.code,
                                                QgsSymbolLayerV2Utils.encodeColor(fl.lineColor))
            self.currentLayer.setCustomProperty('fluid_label_color_' + fl.code,
                                                QgsSymbolLayerV2Utils.encodeColor(fl.labelColor))
            self.currentLayer.setCustomProperty('fluid_inPercent_' + fl.code, str(fl.inPercent))
