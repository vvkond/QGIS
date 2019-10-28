# -*- coding: utf-8 -*-

from PyQt4 import QtGui, uic, QtCore
# from PyQt4 import QtCore, QtGui
from PyQt4.QtGui import *
# from PyQt4.QtCore import *
from qgis import core, gui
from qgis.gui import QgsColorButtonV2, QgsFieldExpressionWidget, QgsFieldProxyModel, QgsColorDialogV2
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
import inspect
import traceback

IS_DEBUG=False

#Table model for attribute TableView
class AttributeTableModel(QAbstractTableModel):
    ExpressionColumn = 0
    ColorColumn = 1
    ColorLineColumn = 2
    DescrColumn = 3
    FilterColumn = 4
    def __init__(self, headerData, parent=None, *args):
        QAbstractTableModel.__init__(self, parent, *args)
        self.arraydata = []
        self.headerdata = headerData

    def clearRows(self):
        self.beginResetModel()
        self.arraydata = []
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        return len(self.arraydata)

    def columnCount(self, parent=QModelIndex()):
        return len(self.headerdata)

    def insertRows(self, row, count, parent = QModelIndex()):
        if row < 0:
            row = 0

        self.beginInsertRows(parent, row, count + row - 1)
        for i in xrange(0, count):
            newRow = ['', QColor(255, 0, 0), QColor(255, 0, 0), '', '']
            self.arraydata.insert(i + row, newRow)

        self.endInsertRows()
        return True

    def removeRows(self, row, count, parent = QModelIndex()):
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
        elif role == Qt.DecorationRole and index.column() == AttributeTableModel.ColorLineColumn:
            return self.arraydata[index.row()][AttributeTableModel.ColorLineColumn]

        return None

    def setDiagramm(self, row, value):
        if row >= 0 and row < len(self.arraydata):
            self.arraydata[row][self.getFilterColumn()] = value


    def diagramm(self, row):
        if row >= 0 and row < len(self.arraydata) and len(self.arraydata[row])>self.getFilterColumn():
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
    ShowZeroColumn = 2
    NewLineColumn = 3
    IsPercentColumn = 4
    FilterColumn = 5
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


    def insertRows(self, row, count, parent = QModelIndex()):
        if row < 0:
            row = 0

        self.beginInsertRows(parent, row, count + row - 1)
        for i in xrange(0, count):
            newRow = ['', QColor(0, 0, 0), Qt.Unchecked, Qt.Unchecked, Qt.Unchecked, '']
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

            if not descr or len(descr) < 2:
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
        colorEd = QgsColorDialogV2(parent)
        colorEd.setColor(self.newColor)
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
        clr = editor.color()
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
        self.attributeModel = AttributeTableModel([self.tr(u'Attribute'), self.tr(u'Color'), self.tr(u'Line color'), self.tr(u'Legend name')], self)
        self.filteredModel = AttributeFilterProxy(self)
        self.filteredModel.setSourceModel(self.attributeModel)

        self.attributeTableView.setModel(self.filteredModel)
        self.attributeTableView.horizontalHeader().setResizeMode(0, QHeaderView.Stretch)

        exprDelegate = ExpressionDelegate(layer, True, self)
        self.attributeTableView.setItemDelegateForColumn(AttributeTableModel.ExpressionColumn, exprDelegate)

        colorDelegate = ColorDelegate(layer, self)
        self.attributeTableView.setItemDelegateForColumn(AttributeTableModel.ColorColumn, colorDelegate)
        colorDelegate2 = ColorDelegate(layer, self)
        self.attributeTableView.setItemDelegateForColumn(AttributeTableModel.ColorLineColumn, colorDelegate2)

        #Setup Labels TableView
        self.labelAttributeModel = AttributeLabelTableModel([self.tr(u'Attribute'), self.tr(u'Color'),
                                                             self.tr(u'Show zero'), self.tr(u'New line'),
                                                             self.tr(u'In percent')], self)
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
        self.maxValueAttribute.setFilters(QgsFieldProxyModel.Filters(8))
        self.maxValueAttribute.fieldChanged.connect(self.maxValueAttribute_fieldChanged)
        self.horizontalLayout.addWidget(self.maxValueAttribute)


        self.layerDiagramms = []


        self.bubbleProps = None
        renderer = self.currentLayer.rendererV2()
        if renderer is not None and renderer.type() == 'RuleRenderer':
            root_rule = renderer.rootRule()
            for r in root_rule.children():
                if r.symbol():
                    for l in r.symbol().symbolLayers():
                        if l.layerType() == 'BubbleDiagramm':
                            self.bubbleProps = l.properties()
                            break
                if self.bubbleProps is not None:
                    break

        if self.bubbleProps is None:
            registry = QgsSymbolLayerV2Registry.instance()
            bubbleMeta = registry.symbolLayerMetadata('BubbleDiagramm')
            if bubbleMeta is not None:
                bubbleLayer = bubbleMeta.createSymbolLayer({})
                if bubbleLayer:
                    self.bubbleProps = bubbleLayer.properties()

        if self.bubbleProps is None:
            self.bubbleProps = {}

        #Read saved layer settings
        self.readSettings()


        self.isCurrentProd = True if self.currentLayer.customProperty("qgis_pds_type") == 'pds_current_production' else False
        self.defaultUnitNum = 2 if self.isCurrentProd else 3

        self.updateWidgets()

        self.filteredModel.setFilter(self.currentDiagrammId)
        self.labelFilteredModel.setFilter(self.currentDiagrammId)

        self.labelAttributeTableView.resizeColumnsToContents()

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

    @pyqtSlot()
    def on_mSaveToFile_clicked(self):
        plugin_dir = os.path.dirname(__file__)
        lastFileDir = QSettings().value('PDS/BubbleSetup/lastTemplateDir', plugin_dir)
        fname = QFileDialog.getSaveFileName(self, u'Выбрать файл',
                                            lastFileDir, u"Файлы bbl (*.bbl *.BBL)")
        if fname:
            (fname, ext) = os.path.splitext(fname)
            fname += '.bbl'
            self.saveSettingsToFile(fname)
            QSettings().setValue('PDS/BubbleSetup/lastTemplateDir', os.path.dirname(fname))

    @pyqtSlot()
    def on_mReadFromFile_clicked(self):
        plugin_dir = os.path.dirname(__file__)
        lastFileDir = QSettings().value('PDS/BubbleSetup/lastTemplateDir', plugin_dir)
        fname = QFileDialog.getOpenFileName(self, u'Выбрать файл',
                                            lastFileDir, u"Файлы bbl (*.bbl *.BBL);;Все файлы (*.*)")
        if fname:
            if self.readSettingsFromFile(fname):
                self.updateWidgets()
            QSettings().setValue('PDS/BubbleSetup/lastTemplateDir', os.path.dirname(fname))

    def createMyStruct(self):
        newName = u'Диаграмма {}'.format(len(self.layerDiagramms) + 1)
        return MyStruct(name=newName, scale=300000, scaleType=0, scaleAttribute='',
                        scaleMinRadius = 3, scaleMaxRadius = 15,
                        fixedSize = 15, diagrammId=self.diagrammId)

    def addDiagramm(self):
        d = self.createMyStruct()
        self.layerDiagramms.append(d)

        item = QtGui.QListWidgetItem(d.name)
        item.setData(Qt.UserRole, d)
        self.mDiagrammsListWidget.addItem(item)
        self.mDeleteDiagramm.setEnabled(len(self.layerDiagramms) > 1)



    def mAddDiagramm_clicked(self):
        self.addDiagramm()


    def updateWidgets(self):
        self.mDiagrammsListWidget.clear()

        if len(self.layerDiagramms) < 1:
            self.layerDiagramms.append(self.createMyStruct())

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

        idx = self.mDiagrammsListWidget.currentRow()
        if idx >= 0:
            self.layerDiagramms[idx].scaleType = 0 if isOn else 1

    @pyqtSlot(float)
    def on_fixedDiagrammSize_valueChanged(self, value):
        idx = self.mDiagrammsListWidget.currentRow()
        if idx >= 0:
            self.layerDiagramms[idx].fixedSize = value

    @pyqtSlot(str)
    def maxValueAttribute_fieldChanged(self, fieldName):
        idx = self.mDiagrammsListWidget.currentRow()
        if idx >= 0:
            self.layerDiagramms[idx].scaleAttribute = fieldName

    #Calculate max value for diagramm size attribute
    @pyqtSlot()
    def on_scalePushButton_clicked(self):
        idx = self.mDiagrammsListWidget.currentRow()
        if not self.currentLayer or idx < 0:
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
        self.layerDiagramms[idx].scale = maxValue

    #Change current diagramm
    def on_mDiagrammsListWidget_currentRowChanged(self, row):
        if row < 0:
            return

        diagramm = self.layerDiagramms[row]

        self.scaleEdit.setValue(diagramm.scale)
        self.titleEdit.setText(diagramm.name)
        self.maxValueAttribute.setField(diagramm.scaleAttribute)
        self.minDiagrammSize.setValue(diagramm.scaleMinRadius)
        self.maxDiagrammSize.setValue(diagramm.scaleMaxRadius)
        self.fixedDiagrammSize.setValue(diagramm.fixedSize)
        self.fixedSizeRadioButton.setChecked(diagramm.scaleType == 0)
        self.scaledSizeRadioButton.setChecked(diagramm.scaleType == 1)

        self.filteredModel.setFilter(self.currentDiagrammId)
        self.labelFilteredModel.setFilter(self.currentDiagrammId)

    #===========================================================================
    # Delete current diagramm
    #===========================================================================
    def mDeleteDiagramm_clicked(self):
        if len(self.layerDiagramms) < 2:
            return

        idx = self.mDiagrammsListWidget.currentRow()
        if idx >= 0:
            for row in xrange(self.filteredModel.rowCount()):
                self.filteredModel.removeRow(row)

            for row in xrange(self.labelFilteredModel.rowCount()):
                self.labelFilteredModel.removeRow(row)

            self.mDiagrammsListWidget.takeItem(idx)
            del self.layerDiagramms[idx]

        self.mDeleteDiagramm.setEnabled(len(self.layerDiagramms) > 1)

    #===========================================================================
    # Import diagramm from other layer
    #===========================================================================
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
                if self.readSettings():
                    self.updateWidgets()
            except:
                pass
            self.currentLayer = saveLayer

    #Edit diagramm title finished
    def on_titleEdit_editingFinished(self):
        idx = self.mDiagrammsListWidget.currentRow()
        if idx >= 0:
            self.layerDiagramms[idx].name = self.titleEdit.text()
            item = self.mDiagrammsListWidget.item(idx)
            item.setText(self.titleEdit.text())

    def scaleValueEditingFinished(self):
        idx = self.mDiagrammsListWidget.currentRow()
        if idx >= 0:
            self.layerDiagramms[idx].scale = self.scaleEdit.value()

    @pyqtSlot(float)
    def on_maxDiagrammSize_valueChanged(self, val):
        self.minDiagrammSize.blockSignals(True)
        self.minDiagrammSize.setMaximum(val)
        self.minDiagrammSize.blockSignals(False)
        idx = self.mDiagrammsListWidget.currentRow()
        if idx >= 0:
            self.layerDiagramms[idx].scaleMaxRadius = val

    @pyqtSlot(float)
    def on_minDiagrammSize_valueChanged(self, val):
        idx = self.mDiagrammsListWidget.currentRow()
        if idx >= 0:
            self.layerDiagramms[idx].scaleMinRadius = val


    #OK button pressed
    def on_buttonBox_accepted(self):
        self.setup(self.currentLayer)

    # OK or APPLY button pressed
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

        self.saveSettings()

        context = self.createExpressionContext()


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

        if editLayerProvider.fieldNameIndex('LablOffset') < 0:
            editLayerProvider.addAttributes([QgsField('LablOffset', QVariant.String)])

        # if editLayerProvider.fieldNameIndex(OLD_NEW_FIELDNAMES[1]) < 0:
        #     editLayerProvider.addAttributes([QgsField(OLD_NEW_FIELDNAMES[1], QVariant.String)])

        # if editLayerProvider.fieldNameIndex('bbllabels') < 0:
        #     editLayerProvider.addAttributes([QgsField('bbllabels', QVariant.String)])

        if editLayerProvider.fieldNameIndex('bubblesize') < 0:
            editLayerProvider.addAttributes([QgsField('bubblesize', QVariant.Double)])


        diagLabel = ''
        for d in self.layerDiagramms:
            if len(diagLabel) > 0:
                diagLabel += '\n'
            diagLabel += u'{0} {1}'.format(d.name, d.scale)


        iter = editLayerProvider.getFeatures()
        for feature in iter:
            FeatureId = feature.id()

            diagrammSize = 0
            root = ET.Element("root")
            diagramms = []
            for d in self.layerDiagramms:
                rows = [r for r in xrange(self.attributeModel.rowCount()) if
                        self.attributeModel.diagramm(r) == d.diagrammId]

                koef = (d.scaleMaxRadius - d.scaleMinRadius) / d.scale
                sum = 0
                for row in rows:
                    index = self.attributeModel.index(row, AttributeTableModel.ExpressionColumn)
                    expression = self.attributeModel.data(index, Qt.DisplayRole)

                    exp = QgsExpression(expression)
                    exp.prepare(context)
                    val = 0.0
                    if not exp.hasEvalError():
                        context.setFeature(feature)
                        val = exp.evaluate(context)
                    else:
                        try:
                            val = feature[expression]
                        except:
                            pass

                    if val:
                        sum += float(val)

                diagramm = []
                if sum != 0:
                    ds = 0.0
                    if d.scaleType == 0:
                        ds = d.fixedSize
                        diagrammSize = ds
                    else:
                        ds = d.scaleMinRadius + sum * koef
                        if ds > d.scaleMaxRadius:
                            ds = d.scaleMaxRadius
                        if ds < d.scaleMinRadius:
                            ds = d.scaleMinRadius
                        if ds > diagrammSize:
                            diagrammSize = ds

                    diag = ET.SubElement(root, "diagramm", size=str(ds))

                    for row in rows:
                        index = self.attributeModel.index(row, AttributeTableModel.ExpressionColumn)
                        expression = self.attributeModel.data(index, Qt.DisplayRole)

                        exp = QgsExpression(expression)
                        exp.prepare(context)
                        val = 0.0
                        if not exp.hasEvalError():
                            context.setFeature(feature)
                            val = exp.evaluate(context)
                        else:
                            try:
                                val = feature[expression]
                            except:
                                pass

                        percent = float(val) / sum
                        backColor = QColor(self.attributeModel.data(
                                                                    self.attributeModel.index(row, AttributeTableModel.ColorColumn)
                                                                    , Qt.DisplayRole)
                                                                    )
                        lineColor = QColor(self.attributeModel.data(
                                                                    self.attributeModel.index(row, AttributeTableModel.ColorLineColumn)
                                                                    , Qt.DisplayRole)
                                                                    )
                        ET.SubElement(diag, 'value', backColor=QgsSymbolLayerV2Utils.encodeColor(backColor),
                                      lineColor=QgsSymbolLayerV2Utils.encodeColor(lineColor),
                                      fieldName=expression).text = str(percent)

                        key = '{0}_{1}'.format(d.diagrammId, row)
                        slice = {}
                        slice['size'] = ds
                        slice['attr'] = key
                        slice['value'] = percent
                        diagramm.append(slice)
                diagramms.append(diagramm)

            '''
            Add labels to current feature
            '''
            try:
                templateStr = self.addLabels(context, feature)
                if diagrammSize >= d.scaleMinRadius and templateStr:
                    ET.SubElement(root, "label", labelText=templateStr)
                    # editLayer.changeAttributeValue(FeatureId, editLayerProvider.fieldNameIndex('bbllabels'), templateStr)
            except Exception as e:
                QtGui.QMessageBox.critical(None, self.tr(u'Error add label expression'), traceback.format_exc(), QtGui.QMessageBox.Ok)
                break

            offset = diagrammSize if diagrammSize < d.scaleMaxRadius else d.scaleMaxRadius
            LablOffset = feature.attribute('labloffset')
            if LablOffset is None or LablOffset == NULL:
                editLayer.changeAttributeValue(FeatureId, editLayerProvider.fieldNameIndex('labloffx'), offset/3)
                editLayer.changeAttributeValue(FeatureId, editLayerProvider.fieldNameIndex('labloffy'), -offset/3)

            editLayer.changeAttributeValue(FeatureId, editLayerProvider.fieldNameIndex('bubblesize'), diagrammSize)

            # compressedStr = str(diagramms)  # ET.tostring(root)
            # if not editLayer.changeAttributeValue(FeatureId, editLayerProvider.fieldNameIndex(OLD_NEW_FIELDNAMES[0]),
            #                                       compressedStr):
            #     editLayer.changeAttributeValue(FeatureId, editLayerProvider.fieldNameIndex(OLD_NEW_FIELDNAMES[1]),
            #                                    compressedStr)

        editLayer.commitChanges()

        diagramms = []
        for d in self.layerDiagramms:
            rows = [r for r in xrange(self.attributeModel.rowCount()) if
                    self.attributeModel.diagramm(r) == d.diagrammId]

            diagramm = {}
            diagramm['scaleMaxRadius'] = d.scaleMaxRadius
            diagramm['scaleMinRadius'] = d.scaleMinRadius
            diagramm['scale'] = d.scale
            diagramm['scaleType'] = d.scaleType
            diagramm['fixedSize'] = d.fixedSize
            slices = []
            for row in rows:
                index = self.attributeModel.index(row, AttributeTableModel.ExpressionColumn)
                expression = self.attributeModel.data(index, Qt.DisplayRole)
                backColor = QColor(self.attributeModel.data(
                                                            self.attributeModel.index(row, AttributeTableModel.ColorColumn)
                                                            , Qt.DisplayRole)
                                                            )
                lineColor = QColor(self.attributeModel.data(
                                                            self.attributeModel.index(row, AttributeTableModel.ColorLineColumn)
                                                            , Qt.DisplayRole)
                                                            )
                slice = {}
                slice['backColor'] = QgsSymbolLayerV2Utils.encodeColor(backColor)
                slice['lineColor'] = QgsSymbolLayerV2Utils.encodeColor(lineColor)
                slice['expression'] = expression
                # key = '{0}_{1}'.format(d.diagrammId, row)
                slices.append(slice)
            diagramm['slices'] = slices

            rows = [r for r in xrange(self.labelAttributeModel.rowCount()) if
                    self.labelAttributeModel.diagramm(r) == d.diagrammId]
            diagramm['labels'] = self.getLabels(rows)

            diagramms.append(diagramm)

        diagrammStr = str(diagramms)

        plugin_dir = os.path.dirname(__file__)

        registry = QgsSymbolLayerV2Registry.instance()

        symbol = QgsMarkerSymbolV2()
        bubbleMeta = registry.symbolLayerMetadata('BubbleDiagramm')
        if bubbleMeta is not None:
            bubbleProps = {}
            bubbleProps['showLineouts'] = 'False' if self.showLineouts.isChecked() else 'True'
            bubbleProps['showLabels'] = 'True'
            bubbleProps['showDiagramms'] = 'True'
            bubbleProps['labelSize'] = str(self.labelSizeEdit.value())
            bubbleProps['diagrammStr'] = diagrammStr
            bubbleProps['templateStr'] = None
            bubbleLayer = bubbleMeta.createSymbolLayer(bubbleProps)
            if bubbleLayer:
                bubbleLayer.setSize(3)
                bubbleLayer.setSizeUnit(QgsSymbolV2.MM)
                symbol.changeSymbolLayer(0, bubbleLayer)
        else:
            symbol.changeSymbolLayer(0, QgsSvgMarkerSymbolLayerV2())

        renderer = QgsRuleBasedRendererV2(symbol)
        root_rule = renderer.rootRule()
        root_rule.children()[0].setLabel(u'Круговые диаграммы')

        if bubbleMeta:
            bubbleProps = {}
            bubbleProps['showLineouts'] = 'True' if self.showLineouts.isChecked() else 'False'
            bubbleProps['showLabels'] = 'False'
            bubbleProps['showDiagramms'] = 'False'
            bubbleProps['labelSize'] = str(self.labelSizeEdit.value())
            bubbleProps['diagrammStr'] = diagrammStr
            bubbleProps['templateStr'] = None
            bubbleLayer = bubbleMeta.createSymbolLayer(bubbleProps)
            if bubbleLayer:
                bubbleLayer.setSize(3)
                bubbleLayer.setSizeUnit(QgsSymbolV2.MM)
                symbol1 = QgsMarkerSymbolV2()
                symbol1.changeSymbolLayer(0, bubbleLayer)
                rule = QgsRuleBasedRendererV2.Rule(symbol1)
                rule.setLabel(u'Сноски')
                root_rule.appendChild(rule)

        for d in self.layerDiagramms:
            rows = [r for r in xrange(self.attributeModel.rowCount()) if
                    self.attributeModel.diagramm(r) == d.diagrammId]

            koef = (d.scaleMaxRadius - d.scaleMinRadius) / d.scale
            sum = 0
            for row in rows:
                index = self.attributeModel.index(row, AttributeTableModel.ColorColumn)
                backColor = QColor(self.attributeModel.data(index, Qt.DisplayRole))

                index = self.attributeModel.index(row, AttributeTableModel.DescrColumn)
                name = self.attributeModel.data(index, Qt.DisplayRole)

                m = QgsSimpleMarkerSymbolLayerV2()
                m.setSize(4)
                m.setSizeUnit(QgsSymbolV2.MM)
                m.setColor(backColor)
                symbol = QgsMarkerSymbolV2()
                symbol.changeSymbolLayer(0, m)

                rule = QgsRuleBasedRendererV2.Rule(symbol)
                rule.setLabel(name)
                rule.setFilterExpression(u'\"SymbolCode\"=-1')
                root_rule.appendChild(rule)

        renderer.setOrderByEnabled(True)
        orderByClause = QgsFeatureRequest.OrderByClause('BubbleSize', False)
        orderBy = QgsFeatureRequest.OrderBy([orderByClause])
        renderer.setOrderBy(orderBy)
        editLayerStyles=editLayer.styleManager()
        editLayerStyles.addStyle( 'diagrams', editLayerStyles.style(editLayerStyles.styles()[0]) ) 
        editLayerStyles.setCurrentStyle('diagrams')

        editLayer.setRendererV2(renderer)

        palyr = QgsPalLayerSettings()
        palyr.readFromLayer(editLayer)
        palyr=layer_to_labeled(palyr)  #---enable EasyLabel
        palyr.writeToLayer(editLayer)

        editLayer.triggerRepaint()
        self.mIface.layerTreeView().refreshLayerSymbology(editLayer.id())
        
        return

    #===============================================================================
    # 
    #===============================================================================
    def addLabels(self, context, feature):
        templateStr = u''
        for row in xrange(self.labelAttributeModel.rowCount()):
            try:
                index = self.labelAttributeModel.index(row, AttributeTableModel.ExpressionColumn)
                expression = self.labelAttributeModel.data(index, Qt.DisplayRole)
    
                index = self.labelAttributeModel.index(row, AttributeTableModel.ColorColumn)
                color =  QColor(self.labelAttributeModel.data(index, Qt.DisplayRole))
                colorStr = color.name()
    
                index = self.labelAttributeModel.index(row, AttributeLabelTableModel.ShowZeroColumn)
                showZero = self.labelAttributeModel.data(index, Qt.CheckStateRole) == Qt.Checked
    
                index = self.labelAttributeModel.index(row, AttributeLabelTableModel.NewLineColumn)
                isNewLine = self.labelAttributeModel.data(index, Qt.CheckStateRole) == Qt.Checked
                
                exp = QgsExpression(expression)
                
                IS_DEBUG and QgsMessageLog.logMessage(u"Try add label expression: {}\n".format(expression), tag="QgisPDS.bubbleSetup")
                exp.prepare(context)
                val = 0.0
                if not exp.hasEvalError():
                    context.setFeature(feature)
                    val = exp.evaluate(context)
                else:
                    val = feature[expression]
                if val or (not val and showZero):
                    if isNewLine:
                        templateStr += '<div><span><font color="{0}">{1}</font></span></div>'.format(colorStr, str(val))
                    else:
                        templateStr += '<span><font color="{0}">{1}</font></span>'.format(colorStr, str(val))
            except Exception as e:
                IS_DEBUG and QgsMessageLog.logMessage(u"Error add label expression\n", tag="QgisPDS.bubbleSetup")
                raise e
        return templateStr
    
    #===============================================================================
    # 
    #===============================================================================
    def getLabels(self, rows):
        labels = []

        for row in rows:
            label = {}

            label['expName'] = str(row) + '_labexpression'

            index = self.labelAttributeModel.index(row, AttributeTableModel.ExpressionColumn)
            label['expression'] = self.labelAttributeModel.data(index, Qt.DisplayRole)

            index = self.labelAttributeModel.index(row, AttributeTableModel.ColorColumn)
            color =  QColor(self.labelAttributeModel.data(index, Qt.DisplayRole))
            label['color'] = color.name()

            index = self.labelAttributeModel.index(row, AttributeLabelTableModel.ShowZeroColumn)
            label['showZero'] = self.labelAttributeModel.data(index, Qt.CheckStateRole) == Qt.Checked

            index = self.labelAttributeModel.index(row, AttributeLabelTableModel.NewLineColumn)
            label['isNewLine'] = self.labelAttributeModel.data(index, Qt.CheckStateRole) == Qt.Checked

            index = self.labelAttributeModel.index(row, AttributeLabelTableModel.IsPercentColumn)
            label['percent'] = self.labelAttributeModel.data(index, Qt.CheckStateRole) == Qt.Checked

            label['scale'] = 1.0
            label['decimals'] = 2

            labels.append(label)

        return labels

    #===============================================================================
    # 
    #===============================================================================
    def readSettings(self):
        count = int(self.currentLayer.customProperty("PDS/diagrammCount", 0))
        if count < 1:
            return False

        # self.mSymbolSize.setValue(float(self.currentLayer.customProperty("PDS/symbolSize", 4)))
        self.labelSizeEdit.setValue(float(self.currentLayer.customProperty("PDS/labelSize", 7)))
        self.showLineouts.setChecked(True if self.currentLayer.customProperty("PDS/showLineouts", 'true') == 'true' else False)

        '''
            Add bubbles
        '''
        self.layerDiagramms = []
        for num in xrange(count):
            d = str(num+1)
            val = self.createMyStruct()
            try:
                val.name = self.currentLayer.customProperty('PDS/diagramm_name_' + d, "--")
                val.scale = float(self.currentLayer.customProperty('PDS/diagramm_scale_' + d, 300000))
                val.scaleType = int(self.currentLayer.customProperty('PDS/diagramm_scaleType_' + d, 0))
                val.scaleAttribute = self.currentLayer.customProperty('PDS/diagramm_scaleAttribute_' + d, '')
                val.fixedSize = float(self.currentLayer.customProperty('PDS/diagramm_fixedSize_' + d, 15))
                val.scaleMinRadius = float(self.currentLayer.customProperty('PDS/diagramm_scaleMinRadius_' + d, 3))
                val.scaleMaxRadius = float(self.currentLayer.customProperty('PDS/diagramm_scaleMaxRadius_' + d, 15))
                val.diagrammId = int(self.currentLayer.customProperty('PDS/diagramm_diagrammId_' + d, 0))
                self.layerDiagramms.append(val)
            except:
                pass

        '''
            Add attributes
        '''
        count = int(self.currentLayer.customProperty('PDS/diagramm_attributeCount', 0))
        self.attributeModel.clearRows()
        for row in xrange(count):
            try:
                diagrammId=int(self.currentLayer.customProperty('PDS/diagramm_filter_' + str(row)))
            except:
                continue
            if diagrammId in map(lambda v: v.diagrammId,self.layerDiagramms): # add config only if diagram for it presented
                self.attributeModel.insertRows(self.attributeModel.rowCount(), 1)
                rowId=self.attributeModel.rowCount()-1
                self.attributeModel.setDiagramm(rowId,diagrammId)
                for col in xrange(self.attributeModel.columnCount()):
                    try:
                        idxStr = '{0}_{1}'.format(rowId, col)
                        data = self.currentLayer.customProperty('PDS/diagramm_attribute_' + idxStr,'')
                        index = self.attributeModel.index(rowId, col)
                        self.attributeModel.setData(index, data, Qt.EditRole)
                    except:
                        pass
        '''
            Add labels
        '''
        count = int(self.currentLayer.customProperty('PDS/diagramm_labelCount', 0))
        self.labelAttributeModel.clearRows()
        for row in xrange(count):
            try:
                diagrammId=int(self.currentLayer.customProperty('PDS/diagramm_labelfilter_' + str(row)))
            except:
                continue
            if diagrammId in map(lambda v: v.diagrammId,self.layerDiagramms): # add config only if diagram for it presented
                self.labelAttributeModel.insertRows(self.labelAttributeModel.rowCount(), 1)
                rowId=self.labelAttributeModel.rowCount()-1
                self.labelAttributeModel.setDiagramm(rowId,diagrammId )
                for col in xrange(self.labelAttributeModel.columnCount()):
                    index = self.labelAttributeModel.index(rowId, col)
                    idxStr = '{0}_{1}'.format(rowId, col)
                    data = self.currentLayer.customProperty('PDS/diagramm_labelAttribute_' + idxStr)
                    if data:
                        if col > AttributeTableModel.ColorColumn:
                            self.labelAttributeModel.setData(index, int(data), Qt.CheckStateRole)
                        else:
                            self.labelAttributeModel.setData(index, data, Qt.EditRole)
        return True

    #===============================================================================
    # 
    #===============================================================================
    def saveSettings(self):
        self.currentLayer.setCustomProperty("PDS/diagrammCount", len(self.layerDiagramms))
        # self.currentLayer.setCustomProperty("PDS/symbolSize", self.mSymbolSize.value())
        self.currentLayer.setCustomProperty("PDS/labelSize", self.labelSizeEdit.value())
        self.currentLayer.setCustomProperty("PDS/showLineouts", 'true' if self.showLineouts.isChecked() else 'false')

        #Write common diagramm properties
        num = 1
        for val in self.layerDiagramms:
            d = str(num)
            self.currentLayer.setCustomProperty('PDS/diagramm_name_' + d, val.name)
            self.currentLayer.setCustomProperty('PDS/diagramm_scale_' + d, val.scale)
            self.currentLayer.setCustomProperty('PDS/diagramm_scaleType_' + d, val.scaleType)
            self.currentLayer.setCustomProperty('PDS/diagramm_scaleAttribute_' + d, val.scaleAttribute)
            self.currentLayer.setCustomProperty('PDS/diagramm_fixedSize_' + d, val.fixedSize)
            self.currentLayer.setCustomProperty('PDS/diagramm_scaleMinRadius_' + d, val.scaleMinRadius)
            self.currentLayer.setCustomProperty('PDS/diagramm_scaleMaxRadius_' + d, val.scaleMaxRadius)
            self.currentLayer.setCustomProperty('PDS/diagramm_diagrammId_' + d, val.diagrammId)
            num = num + 1

        #Write attributes
        self.currentLayer.setCustomProperty('PDS/diagramm_attributeCount', self.attributeModel.rowCount())
        for row in xrange(self.attributeModel.rowCount()):
            self.currentLayer.setCustomProperty('PDS/diagramm_filter_' + str(row), self.attributeModel.diagramm(row))
            for col in xrange(self.attributeModel.columnCount()):
                index = self.attributeModel.index(row, col)
                data = self.attributeModel.data(index, Qt.DisplayRole)
                idxStr = '{0}_{1}'.format(row, col)
                self.currentLayer.setCustomProperty('PDS/diagramm_attribute_' + idxStr, data)

        #Write label settings
        self.currentLayer.setCustomProperty('PDS/diagramm_labelCount', self.labelAttributeModel.rowCount())
        for row in xrange(self.labelAttributeModel.rowCount()):
            self.currentLayer.setCustomProperty('PDS/diagramm_labelfilter_' + str(row), self.labelAttributeModel.diagramm(row))
            for col in xrange(self.labelAttributeModel.columnCount()):
                index = self.labelAttributeModel.index(row, col)
                if col > AttributeTableModel.ColorColumn:
                    data = self.labelAttributeModel.data(index, Qt.CheckStateRole)
                else:
                    data = self.labelAttributeModel.data(index, Qt.DisplayRole)
                idxStr = '{0}_{1}'.format(row, col)
                self.currentLayer.setCustomProperty('PDS/diagramm_labelAttribute_' + idxStr, data)

    #===========================================================================
    # 
    #===========================================================================
    def saveSettingsToFile(self, fileName):
        settings = QSettings(fileName, QSettings.IniFormat)
        settings.clear()

        settings.setValue("PDS/diagrammCount", len(self.layerDiagramms))
        # settings.setValue("PDS/symbolSize", self.mSymbolSize.value())
        settings.setValue("PDS/labelSize", self.labelSizeEdit.value())
        settings.setValue("PDS/showLineouts", 'true' if self.showLineouts.isChecked() else 'false')

        #Write common diagramm properties
        num = 1
        for val in self.layerDiagramms:
            d = str(num)
            settings.setValue('PDS/diagramm_name_' + d, val.name)
            settings.setValue('PDS/diagramm_scale_' + d, val.scale)
            settings.setValue('PDS/diagramm_scaleType_' + d, val.scaleType)
            settings.setValue('PDS/diagramm_scaleAttribute_' + d, val.scaleAttribute)
            settings.setValue('PDS/diagramm_fixedSize_' + d, val.fixedSize)
            settings.setValue('PDS/diagramm_scaleMinRadius_' + d, val.scaleMinRadius)
            settings.setValue('PDS/diagramm_scaleMaxRadius_' + d, val.scaleMaxRadius)
            settings.setValue('PDS/diagramm_diagrammId_' + d, val.diagrammId)
            num = num + 1

        #Write attributes
        settings.setValue('PDS/diagramm_attributeCount', self.attributeModel.rowCount())
        for row in xrange(self.attributeModel.rowCount()):
            settings.setValue('PDS/diagramm_filter_' + str(row), self.attributeModel.diagramm(row))
            for col in xrange(self.attributeModel.columnCount()):
                index = self.attributeModel.index(row, col)
                data = self.attributeModel.data(index, Qt.DisplayRole)
                idxStr = '{0}_{1}'.format(row, col)
                settings.setValue('PDS/diagramm_attribute_' + idxStr, data)

        #Write label settings
        settings.setValue('PDS/diagramm_labelCount', self.labelAttributeModel.rowCount())
        for row in xrange(self.labelAttributeModel.rowCount()):
            settings.setValue('PDS/diagramm_labelfilter_' + str(row), self.labelAttributeModel.diagramm(row))
            for col in xrange(self.labelAttributeModel.columnCount()):
                index = self.labelAttributeModel.index(row, col)
                if col > AttributeTableModel.ColorColumn:
                    data = self.labelAttributeModel.data(index, Qt.CheckStateRole)
                else:
                    data = self.labelAttributeModel.data(index, Qt.DisplayRole)
                idxStr = '{0}_{1}'.format(row, col)
                settings.setValue('PDS/diagramm_labelAttribute_' + idxStr, data)

    #===============================================================================
    # 
    #===============================================================================
    def readSettingsFromFile(self, fileName):
        settings = QSettings(fileName, QSettings.IniFormat)

        count = int(settings.value("PDS/diagrammCount", 0))
        if count < 1:
            return False

        # self.mSymbolSize.setValue(float(settings.value("PDS/symbolSize", 4)))
        self.labelSizeEdit.setValue(float(settings.value("PDS/labelSize", 7)))
        self.showLineouts.setChecked(
            True if settings.value("PDS/showLineouts", 'true') == 'true' else False)

        '''
            Add bubbles
        '''
        self.layerDiagramms = []
        for num in xrange(count):
            d = str(num + 1)
            val = self.createMyStruct()
            try:
                val.name = settings.value('PDS/diagramm_name_' + d, "--")
                val.scale = float(settings.value('PDS/diagramm_scale_' + d, 300000))
                val.scaleType = int(settings.value('PDS/diagramm_scaleType_' + d, 0))
                val.scaleAttribute = settings.value('PDS/diagramm_scaleAttribute_' + d, '')
                val.fixedSize = float(settings.value('PDS/diagramm_fixedSize_' + d, 15))
                val.scaleMinRadius = float(settings.value('PDS/diagramm_scaleMinRadius_' + d, 3))
                val.scaleMaxRadius = float(settings.value('PDS/diagramm_scaleMaxRadius_' + d, 15))
                val.diagrammId = int(settings.value('PDS/diagramm_diagrammId_' + d, 0))
                self.layerDiagramms.append(val)
            except:
                pass
        '''
            Add attributes
        '''
        count = int(settings.value('PDS/diagramm_attributeCount', 0))
        self.attributeModel.clearRows()
        for row in xrange(count):
            try:
                diagrammId=int(settings.value('PDS/diagramm_filter_' + str(row)))
            except:
                continue
            if diagrammId in map(lambda v: v.diagrammId,self.layerDiagramms): # add config only if diagram for it presented
                self.attributeModel.insertRows(self.attributeModel.rowCount(), 1)
                rowId=self.attributeModel.rowCount()-1
                self.attributeModel.setDiagramm(rowId, diagrammId)
                for col in xrange(self.attributeModel.columnCount()):
                    try:
                        data = settings.value('PDS/diagramm_attribute_' + '{0}_{1}'.format(row, col))
                        index = self.attributeModel.index(rowId, col)
                        self.attributeModel.setData(index, data, Qt.EditRole)
                    except:
                        pass
        '''
            Add labels
        '''
        count = int(settings.value('PDS/diagramm_labelCount', 0))
        self.labelAttributeModel.clearRows()
        for row in xrange(count):
            try:
                diagrammId=int(int(settings.value('PDS/diagramm_labelfilter_' + str(row))))
            except:
                continue
            if diagrammId in map(lambda v: v.diagrammId,self.layerDiagramms): # add config only if diagram for it presented
                self.labelAttributeModel.insertRows(self.labelAttributeModel.rowCount(), 1)
                rowId=self.labelAttributeModel.rowCount()-1
                self.labelAttributeModel.setDiagramm(rowId, diagrammId)
                for col in xrange(self.labelAttributeModel.columnCount()):
                    index = self.labelAttributeModel.index(rowId, col)
                    data = settings.value('PDS/diagramm_labelAttribute_' + '{0}_{1}'.format(row, col))
                    if data:
                        if col > AttributeTableModel.ColorColumn:
                            self.labelAttributeModel.setData(index, int(data), Qt.CheckStateRole)
                        else:
                            self.labelAttributeModel.setData(index, data, Qt.EditRole)

        return True
    
    
    
    
    