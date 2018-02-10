# -*- coding: utf-8 -*-

from PyQt4 import QtGui, uic, QtCore
# from PyQt4 import QtCore, QtGui
from PyQt4.QtGui import *
# from PyQt4.QtCore import *
from qgis import core, gui
from qgis.gui import QgsColorButtonV2, QgsFieldExpressionWidget
# from qgis.gui import *
# from qgscolorbuttonv2 import QgsColorButtonV2
from collections import namedtuple
from qgis_pds_production import *
from bblInit import *
import ast
import math
import xml.etree.cElementTree as ET
import re
import sip

#Table model for attribute TableView
class AttributeTableModel(QAbstractTableModel):
    ExpressionColumn = 0
    ColorColumn = 1
    DescrColumn = 2
    FilterColumn = 3
    def __init__(self, headerData, parent=None, *args):
        QAbstractTableModel.__init__(self, parent, *args)
        self.arraydata = []
        self.headerdata = headerData

    def rowCount(self, parent=QModelIndex()):
        return len(self.arraydata)

    def columnCount(self, parent=QModelIndex()):
        return len(self.headerdata)

    def insertRows(self, row, count, parent):
        if row < 0:
            row = 0

        self.beginInsertRows(parent, row, count + row - 1)
        for i in xrange(0, count):
            newRow = ['', QColor(255, 0, 0), '', '']
            self.arraydata.insert(i + row, newRow)

        self.endInsertRows()
        return True

    def removeRows(self, row, count, parent):
        self.beginRemoveRows(parent, row, row + count -1)
        for r in xrange(0, count):
            del self.arraydata[r + row]
        self.endRemoveRows()

        return True

    def data(self, index, role):
        if not index.isValid():
            return None

        if role == Qt.DisplayRole or role == Qt.EditRole:
            return self.arraydata[index.row()][index.column()]
        elif role == Qt.DecorationRole and index.column() == AttributeTableModel.ColorColumn:
            return self.arraydata[index.row()][AttributeTableModel.ColorColumn]

        return None

    def setDiagramm(self, row, value):
        if row >= 0 and row < len(self.arraydata):
            self.arraydata[row][self.getFilterColumn()] = value


    def diagramm(self, row):
        if row >= 0 and row < len(self.arraydata):
            return self.arraydata[row][self.getFilterColumn()]
        else:
            return 'No Diag ' + str(row)

    def getFilterColumn(self):
        return AttributeTableModel.FilterColumn

    def setData(self, index, value, role):
        if not index.isValid():
            return False

        if role == Qt.EditRole:
            self.arraydata[index.row()][index.column()] = value
            return True

        return False

    def headerData(self, col, orientation, role):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.headerdata[col]
        return None

    def flags(self, index):
        if not index.isValid():
            return Qt.NoItemFlags

        flags = Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable

        return flags

#Table model for Labels TableView
class AttributeLabelTableModel(AttributeTableModel):
    FilterColumn = 4
    def __init__(self, headerData, parent=None):
        AttributeTableModel.__init__(self, headerData, parent)

    def getFilterColumn(self):
        return AttributeLabelTableModel.FilterColumn

    def flags(self, index):
        if not index.isValid():
            return Qt.NoItemFlags

        flags = Qt.ItemIsEnabled | Qt.ItemIsSelectable
        if index.column() > AttributeTableModel.ColorColumn:
            flags = flags | Qt.ItemIsUserCheckable
        else:
            flags = flags | Qt.ItemIsEditable

        return flags

    def data(self, index, role):
        if not index.isValid():
            return None

        if index.column() > AttributeTableModel.ColorColumn:
            if role == Qt.CheckStateRole:
                return self.arraydata[index.row()][index.column()]
            else:
                return None
        else:
            return AttributeTableModel.data(self, index, role)

    def setData(self, index, value, role):
        if not index.isValid():
            return False

        if role == Qt.CheckStateRole and index.column() > AttributeTableModel.ColorColumn:
            self.arraydata[index.row()][index.column()] = value
            return True
        else:
            return AttributeTableModel.setData(self, index, value, role)


    def insertRows(self, row, count, parent):
        if row < 0:
            row = 0

        self.beginInsertRows(parent, row, count + row - 1)
        for i in xrange(0, count):
            newRow = ['', QColor(255, 0, 0), Qt.Unchecked, Qt.Unchecked, '']
            self.arraydata.insert(i + row, newRow)

        self.endInsertRows()
        return True


#Filter table model
class AttributeFilterProxy(QSortFilterProxyModel):
    def __init__(self, parent=None):
        QSortFilterProxyModel.__init__(self, parent)
        self.filter = 0

    def setFilter(self, f):
        self.filter = f
        self.invalidateFilter()

    def filterAcceptsRow(self, sourceRow, sourceParent):
        index1 = self.sourceModel().index(sourceRow, 0, sourceParent)

        id = self.sourceModel().diagramm(index1.row())
        return self.filter == id


#Expression delegate
class ExpressionDelegate(QStyledItemDelegate):
    def __init__(self, layer, isDescr, parent=None):
        QStyledItemDelegate.__init__(self, parent)

        self.currentLayer = layer
        self.isDescription = isDescr

    def createEditor(self, parent, option, index):

        self.initStyleOption(option, index)

        fieldEx = QgsFieldExpressionWidget(parent)
        fieldEx.setLayer(self.currentLayer)
        fieldEx.setField(index.data())

        return fieldEx

    def updateEditorGeometry(self, editor, option, index):
        if editor:
            editor.setGeometry(option.rect)

    def setModelData(self, editor, model, index):
        text = editor.currentText()
        model.setData(index, text, Qt.EditRole)

        if self.isDescription:
            index1 = model.index(index.row(), AttributeTableModel.DescrColumn)
            descr = model.data(index1, Qt.DisplayRole)

            if len(descr) < 2:
                model.setData(index1, text, Qt.EditRole)
                model.dataChanged.emit(index1, index1)

#Color delegate
class ColorDelegate(QStyledItemDelegate):
    def __init__(self, layer, parent=None):
        QStyledItemDelegate.__init__(self, parent)

        self.currentLayer = layer
        self.newColor = QColor()

    def createEditor(self, parent, option, index):

        self.initStyleOption(option, index)

        self.newColor = QColor(index.data(Qt.DecorationRole))
        colorEd = QColorDialog(self.newColor, parent)

        return colorEd

    def paint(self, painter, option, index):
        self.initStyleOption(option, index)

        clr = QColor(index.data(Qt.DecorationRole))
        painter.setBrush(clr)
        painter.drawRect(option.rect.adjusted(3, 3, -3, -3))

    def updateEditorGeometry(self, editor, option, index):
        if editor:
            pos = editor.parent().mapToGlobal(option.rect.topLeft())
            ww = editor.rect().width()
            hh = editor.rect().height()
            editor.setGeometry(pos.x() - ww/2, pos.y()-hh/2, ww, hh)


    def setModelData(self, editor, model, index):
        clr = editor.currentColor()
        model.setData(index, clr, Qt.EditRole)
        model.dataChanged.emit(index, index)


FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'qgis_pds_bubblesetup_base.ui'))

class QgisPDSBubbleSetup(QtGui.QDialog, FORM_CLASS):
    def __init__(self, iface, layer, parent=None):
        super(QgisPDSBubbleSetup, self).__init__(parent)

        self.setupUi(self)

        self.mDiagrammId = 0

        self.mIface = iface
        self.currentLayer = layer

        #Setup attributes tableView
        self.attributeModel = AttributeTableModel([self.tr(u'Attribute'), self.tr(u'Color'), self.tr(u'Legend name')], self)
        self.filteredModel = AttributeFilterProxy(self)
        self.filteredModel.setSourceModel(self.attributeModel)

        self.attributeTableView.setModel(self.filteredModel)
        self.attributeTableView.horizontalHeader().setResizeMode(0, QHeaderView.Stretch)

        exprDelegate = ExpressionDelegate(layer, True, self)
        self.attributeTableView.setItemDelegateForColumn(AttributeTableModel.ExpressionColumn, exprDelegate)

        colorDelegate = ColorDelegate(layer, self)
        self.attributeTableView.setItemDelegateForColumn(AttributeTableModel.ColorColumn, colorDelegate)

        #Setup Labels TableView
        self.labelAttributeModel = AttributeLabelTableModel([self.tr(u'Attribute'), self.tr(u'Color'),
                                                            self.tr(u'Show zero'), self.tr(u'New line')], self)
        self.labelFilteredModel = AttributeFilterProxy(self)
        self.labelFilteredModel.setSourceModel(self.labelAttributeModel)

        self.labelAttributeTableView.setModel(self.labelFilteredModel)
        self.labelAttributeTableView.horizontalHeader().setResizeMode(0, QHeaderView.Stretch)

        labelExprDelegate = ExpressionDelegate(layer, False, self)
        self.labelAttributeTableView.setItemDelegateForColumn(AttributeTableModel.ExpressionColumn, labelExprDelegate)

        labelColorDelegate = ColorDelegate(layer, self)
        self.labelAttributeTableView.setItemDelegateForColumn(AttributeTableModel.ColorColumn, labelColorDelegate)

        #Add FieldExpression for maximum value calculate
        self.maxValueAttribute = QgsFieldExpressionWidget(self)
        self.maxValueAttribute.setLayer(self.currentLayer)
        self.scaledSizeGridLayout.addWidget(self.maxValueAttribute, 0, 1, 1, 2)

        self.standardDiagramms = {
                    "1_liquidproduction": MyStruct(name=u'Диаграмма жидкости', scale=300000, testval=1, unitsType=0, units=0, fluids=[1, 0, 1, 0, 0, 0, 0, 0]),
                    "2_liquidinjection": MyStruct(name=u'Диаграмма закачки', scale=300000, testval=1,unitsType=0, units=0, fluids=[0, 0, 0, 0, 1, 1, 0, 0]),
                    "3_gasproduction": MyStruct(name=u"Диаграмма газа", scale=300000, testval=1,unitsType=1, units=0, fluids=[0, 1, 0, 0, 0, 0, 0, 0]),
                    "4_condensatproduction": MyStruct(name=u"Диаграмма конденсата", scale=3000000, testval=1,unitsType=0, units=0, fluids=[0, 0, 0, 1, 0, 0, 0, 0])
                }

        self.layerDiagramms = []




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


        self.isCurrentProd = True if self.currentLayer.customProperty("qgis_pds_type") == 'pds_current_production' else False
        self.defaultUnitNum = 2 if self.isCurrentProd else 3

        self.updateWidgets()

        self.filteredModel.setFilter(self.currentDiagrammId)

        return

    @property
    def currentDiagrammId(self):
        id = 0
        try:
            data = self.mDiagrammsListWidget.currentItem().data(Qt.UserRole)
            id = data.diagrammId
        except:
            pass

        return id

    @property
    def diagrammId(self):
        self.mDiagrammId = self.mDiagrammId + 1
        return self.mDiagrammId


    def addAttributePushButton_clicked(self):
        curRow = self.attributeModel.rowCount()
        self.attributeModel.insertRow(curRow)

        self.attributeModel.setDiagramm(curRow, self.currentDiagrammId)
        self.filteredModel.setFilter(self.currentDiagrammId)

    @pyqtSlot()
    def on_deleteAttributePushButton_clicked(self):
        rows = [r.row() for r in self.attributeTableView.selectionModel().selectedIndexes()]
        rows.sort(reverse=True)
        for row in rows:
            self.attributeTableView.model().removeRow(row)

    @pyqtSlot()
    def on_addLabelAttributePushButton_clicked(self):
        curRow = self.labelAttributeModel.rowCount()
        self.labelAttributeModel.insertRow(curRow)

        self.labelAttributeModel.setDiagramm(curRow, self.currentDiagrammId)
        self.labelFilteredModel.setFilter(self.currentDiagrammId)

    @pyqtSlot()
    def on_deleteLabelAttributePushButton_clicked(self):
        rows = [r.row() for r in self.labelAttributeTableView.selectionModel().selectedIndexes()]
        rows.sort(reverse=True)
        for row in rows:
            self.labelAttributeTableView.model().removeRow(row)

    def addDiagramm(self):
        newName = u'Диаграмма {}'.format(len(self.layerDiagramms) + 1)
        d = MyStruct(name=newName, scale=300000, testval=1, unitsType=0, units=self.defaultUnitNum,
                     attributes=[], diagrammId=self.diagrammId)
        self.layerDiagramms.append(d)

        item = QtGui.QListWidgetItem(newName)
        item.setData(Qt.UserRole, d)
        self.mDiagrammsListWidget.addItem(item)
        self.mDeleteDiagramm.setEnabled(len(self.layerDiagramms) > 1)



    def mAddDiagramm_clicked(self):
        self.addDiagramm()


    def updateWidgets(self):
        self.mDiagrammsListWidget.clear()

        if len(self.layerDiagramms) < 1:
            self.layerDiagramms.append(MyStruct(name=u'Диаграмма жидкости', scale=300000, testval=1, unitsType=0,
                                                units=self.defaultUnitNum, attributes=[], diagrammId=self.diagrammId))

        self.mDeleteDiagramm.setEnabled(len(self.layerDiagramms) > 1)
        for d in self.layerDiagramms:
            name = d.name
            item = QtGui.QListWidgetItem(name)
            item.setData(Qt.UserRole, d)
            self.mDiagrammsListWidget.addItem(item)

        self.mDiagrammsListWidget.setCurrentRow(0)

    def createExpressionContext(self):
        context = QgsExpressionContext()
        context.appendScope(QgsExpressionContextUtils.globalScope())
        context.appendScope(QgsExpressionContextUtils.projectScope())
        context.appendScope(QgsExpressionContextUtils.mapSettingsScope(self.mIface.mapCanvas().mapSettings()))
        context.appendScope(QgsExpressionContextUtils.layerScope(self.currentLayer))

        return context

    # SLOTS
    #Toggle diagramm size type (Fixed/Scaled)
    def on_fixedSizeRadioButton_toggled(self, isOn):
        self.fixedDiagrammSize.setEnabled(isOn)
        self.scaledSizeFrame.setEnabled(not isOn)

    @pyqtSlot()
    def on_scalePushButton_clicked(self):
        if not self.currentLayer:
            return;

        maxValue = 0.0;

        isExpression = self.maxValueAttribute.isExpression()
        sizeFieldNameOrExp = self.maxValueAttribute.currentText()
        if isExpression:
            exp = QgsExpression(sizeFieldNameOrExp)
            context = self.createExpressionContext()
            exp.prepare( context )
            if not exp.hasEvalError():
                features = self.currentLayer.getFeatures()
                for feature in features:
                    context.setFeature(feature)
                    val = exp.evaluate(context)
                    if val:
                        maxValue = max(maxValue, float(val))
        else:
            attributeNumber = self.currentLayer.fieldNameIndex(sizeFieldNameOrExp)
            maxValue = float(self.currentLayer.maximumValue(attributeNumber))

        self.scaleEdit.setValue(maxValue);

    #Change current diagramm
    def on_mDiagrammsListWidget_currentRowChanged(self, row):
        if row < 0:
            return

        item = self.mDiagrammsListWidget.item(row)
        diagramm = item.data(Qt.UserRole)

        self.scaleEdit.setValue(diagramm.scale)
        self.titleEdit.setText(diagramm.name)


        self.filteredModel.setFilter(self.currentDiagrammId)
        self.labelFilteredModel.setFilter(self.currentDiagrammId)

    #Delete current diagramm
    def mDeleteDiagramm_clicked(self):
        if len(self.layerDiagramms) < 2:
            return

        idx = self.mDiagrammsListWidget.currentRow()
        if idx >= 0:
            self.mDiagrammsListWidget.takeItem(idx)
            del self.layerDiagramms[idx]

        self.mDeleteDiagramm.setEnabled(len(self.layerDiagramms) > 1)

    #Import diagramm from other layer
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

        idxOffX = editLayerProvider.fieldNameIndex('labloffx')
        idxOffY = editLayerProvider.fieldNameIndex('labloffy')
        if idxOffX < 0 or idxOffY < 0:
            editLayerProvider.addAttributes(
                [QgsField("labloffx", QVariant.Double),
                 QgsField("labloffy", QVariant.Double)])

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
        for fl in bblInit.fluidCodes:
            self.currentLayer.setCustomProperty('fluid_background_' + fl.code,
                                                QgsSymbolLayerV2Utils.encodeColor(fl.backColor))
            self.currentLayer.setCustomProperty('fluid_line_color_' + fl.code,
                                                QgsSymbolLayerV2Utils.encodeColor(fl.lineColor))
            self.currentLayer.setCustomProperty('fluid_label_color_' + fl.code,
                                                QgsSymbolLayerV2Utils.encodeColor(fl.labelColor))
            self.currentLayer.setCustomProperty('fluid_inPercent_' + fl.code, str(fl.inPercent))
