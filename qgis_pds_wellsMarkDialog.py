# -*- coding: utf-8 -*-

import os
import ast
from qgis.core import *
#from qgis.gui import QgsFieldExpressionWidget,QgsColorButtonV2
from PyQt4 import QtGui, uic
from PyQt4.QtGui import *
from PyQt4.QtCore import *

from QgisPDS.connections import create_connection
from utils import *
from QgisPDS.tig_projection import *
from qgis_pds_wellsBrowserDialog import QgisPDSWellsBrowserDialog
from bblInit import Fields, layer_to_labeled

''' In *.ui replace <header>*.h</header>  to  <header>qgis.gui</header> if use qgis promotoves
    <header>[^<]*</header>
    <header>qgis.gui</header>
'''
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'wellsMarkDialog_base.ui'))

cTxt="mrkTxt"
cFillColor="bufcol"
cLineColor="lablcol"
  

class QgisPDSWellsMarkDialog(QtGui.QDialog, FORM_CLASS):
    def __init__(self, _iface, _project, layer, checkedWellIds=None, markedWellIds=None, checkedWellIdsColumn=0, parent=None):
        '''
            @param checkedWellIds: ids of wells(sldnid) for check by default in wellBrowser
        '''
        super(QgisPDSWellsMarkDialog, self).__init__(parent)
        self.filterWellNames = None # list of selected well names
        self._filterWellIds = checkedWellIds
        self._markedWellIds = markedWellIds 
        self._bckpfilterWellIds = checkedWellIds
        self._checkedWellIdsColumn=checkedWellIdsColumn
        self._isDisableUnmarkedItems=True
        self.isNeedFilterWellIds = False   # need or not use self.filterWellIds
        self.allowCheckRow=True 
        self.setupUi(self)
        self.layer=layer
        
        #cbtn.setDefaultColor(QColor("black")) 
        self.mCBtnLine.setShowNull(False)
        self.mCBtnLine.setDefaultColor(QColor("black"))         
        self.mCBtnFill.setShowNull(True)
        #cbtn.setAllowAlpha(True)
        #cbtn.setShowNoColor(True)
        
        
        self.mFieldExpMarkText.setLayer(self.layer)
        self.fields_info=[ # 0 field_name ,     1 type,      2 editWidget      , 3 value get func                                                              4 widget
                     [cTxt,       QVariant.String      ,  None                  , lambda:QgsExpression(self.mFieldExpMarkText.asExpression())                , self.mFieldExpMarkText ]
                    ,[cLineColor, QVariant.String      ,  u'Color'              , lambda:self.mCBtnLine.color().name() if not self.mCBtnLine.isNull() else "", self.mCBtnLine ] #QColor("black").name() ]
                    ,[cFillColor, QVariant.String      ,  u'Color'              , lambda:self.mCBtnFill.color().name() if not self.mCBtnFill.isNull() else "", self.mCBtnFill ]
                    ]

        if _project:
            scheme = _project['project']
            if scheme:
                self.setWindowTitle(self.windowTitle() + ' - ' + scheme)

        self.project = _project
        self.iface = _iface
        
        self.readSettings()
    #===============================================================================
    # 
    #===============================================================================
    #SLOT
    def on_buttonBox_accepted(self):
        #QgsMessageLog.logMessage(u"accept", tag="QgisPDS.debug")
        self.writeSettings()
        self.process()
    #SLOT
    def on_buttonBox_clicked(self, btn):
        #QgsMessageLog.logMessage(u"apply", tag="QgisPDS.debug")
        if self.buttonBox.buttonRole(btn) == QDialogButtonBox.ApplyRole:
            self.writeSettings()
            self.process()
        
    #=======================================================================
    # 
    #=======================================================================
    def process(self): #default QDialog action
        #--- check enabled widgets
        fields_info=[field_info for field_info in self.fields_info if field_info[4].isEnabled()]
        #QgsMessageLog.logMessage(u"Marks :{}".format(str(field_info)), tag="QgisPDS.markWells")
        
        pr = self.layer.dataProvider()
        #---1 clear column if need
        if self.chkBoxClearOldMark.isChecked():
            f_ids=[]
            for field_info in fields_info:
                f_name= field_info[0]
                field_index = self.layer.fields().indexFromName(f_name)
                if field_index > -1:
                    f_ids.append(field_index)
            pr.deleteAttributes(f_ids)            
            self.layer.updateFields() # tell the vector layer to fetch changes from the provider
        #---2 create columns if need
        for field_info in fields_info:
            f_name=   field_info[0]
            f_type=   field_info[1]
            e_widget= field_info[2]
            field_index = self.layer.fields().indexFromName(f_name)
            if field_index == -1:
                pr.addAttributes([QgsField(f_name,f_type)]) # define/add field data type
                self.layer.updateFields() # tell the vector layer to fetch changes from the provider
                field_index = self.layer.fields().indexFromName(f_name)
            if e_widget is not None:
                self.layer.editFormConfig().setWidgetType(field_index, e_widget) #set editorWidget directly to layer
        self.layer.updateFields() # tell the vector layer to fetch changes from the provider                
        #---3 set values
        f_ids=[]
        for field_info in fields_info:
            f_name       =field_info[0]
            field_index = self.layer.fields().indexFromName(f_name)
            f_ids.append(field_index)
                
        with edit_layer(self.layer):
            context = QgsExpressionContext()
            scope = QgsExpressionContextScope()
            context.appendScope(scope)
            
            feature_filter=None
            if self.isNeedFilterWellIds:
                expr_str='\"{0}\" in (\'{1}\')'.format(Fields.WellId.name,"','".join(self.filterWellNames))
                QgsMessageLog.logMessage(u"Expr:{}".format(expr_str), tag="QgisPDS.markWells")
                expr = QgsExpression(expr_str)        #--- search in layer record with that WELL_ID
                feature_filter=QgsFeatureRequest(expr)
            for feature in (self.layer.getFeatures() if feature_filter is None else self.layer.getFeatures(feature_filter)):
                r_id = feature.id()
                for field_info,f_id in zip(fields_info,f_ids):
                    f_name=   field_info[0]
                    val   =   field_info[3]()
                    if isinstance(val,QgsExpression):
                        scope.setFeature(feature)
                        res = val.evaluate(context)
                    else:
                        res=val
                    #if res==u"#000000":res=""
                    self.layer.changeAttributeValue(r_id, f_id, res)
            #self.layer.updateFeature(feature)
            self.layer.commitChanges()
        #---4 add rendering rules
        if self.chkBoxAddDrawRule.isChecked():
            palyr = QgsPalLayerSettings()
            palyr.readFromLayer(self.layer)
            palyr.enabled = True
            #palyr.fieldName = Fields.WellId.name
            palyr.placement= QgsPalLayerSettings.OverPoint
            palyr.quadOffset = QgsPalLayerSettings.QuadrantAboveRight
            palyr.labelOffsetInMapUnits = False
            palyr.distInMapUnits = True
            palyr.displayAll = True
            palyr.fontSizeInMapUnits = False
            palyr=layer_to_labeled(palyr)  #---enable EasyLabel
            palyr.writeToLayer(self.layer)            


    #===============================================================================
    # from PyQt4.QtGui import *
    # from PyQt4.QtCore import *
    # pr=l.dataProvider()
    # pr.addAttributes([QgsField('test',QVariant.String)]) # define/add field data type
    # l.updateFields() # tell the vector layer to fetch changes from the provider
    #===============================================================================

    #===========================================================================
    # btnOpenBrowser
    #===========================================================================
    @pyqtSlot()
    def on_btnOpenBrowser(self):
        try:
            dlg = QgisPDSWellsBrowserDialog(self.iface, self.project
                                            , selectedIdsCol=self._checkedWellIdsColumn
                                            , selectedIds   =self._filterWellIds
                                            , markedIdsCol  =self._checkedWellIdsColumn
                                            , markedIds     =self._markedWellIds
                                            , allowCheckRow=self.allowCheckRow
                                            , isDisableUnmarkedItems=self._isDisableUnmarkedItems
                                            )
            if dlg.exec_():
                self.btnOpenBrowser.setStyleSheet("background-color: red")
                self._filterWellIds=dlg.getWellIds(return_col=self._checkedWellIdsColumn)
                self.filterWellNames=dlg.getWellIds(return_col=1)
                QgsMessageLog.logMessage(u"Selected {}:".format(str(self._filterWellIds)), tag="QgisPDS.markWells")
                self.isNeedFilterWellIds=True
            else:
                self.btnOpenBrowser.setStyleSheet("")
                self._filterWellIds=self._bckpfilterWellIds
                self.filterWellNames=None
                self.isNeedFilterWellIds=False
                
            del dlg
        except Exception as e:
            QgsMessageLog.logMessage(u"{}".format(str(e)), tag="QgisPDS.error")  

            
    #===========================================================================
    # 
    #===========================================================================
    def readSettings(self):
        settings = QSettings()
        self.mCBtnFill.setColor(QColor(settings.value("/PDS/markwell/FillColor")))  
        self.mCBtnLine.setColor(QColor(settings.value("/PDS/markwell/LineColor")))  
        self.mFieldExpMarkText.setExpression(settings.value("/PDS/markwell/Text",None))
        #---restore checkbox
        for item in [ 
                          self.grpBox1
                         ,self.grpBox2
                         ,self.grpBox3
                         ,self.chkBoxAddDrawRule
                         ,self.chkBoxClearOldMark
                         ]:
            item.setChecked(settings.value("/PDS/markwell/{}".format(item.objectName()),True))
    #===========================================================================
    # 
    #===========================================================================
    def writeSettings(self):
        settings = QSettings()
        settings.setValue("/PDS/markwell/FillColor", self.mCBtnFill.color().name())
        settings.setValue("/PDS/markwell/LineColor", self.mCBtnLine.color().name())
        settings.setValue("/PDS/markwell/Text", self.mFieldExpMarkText.asExpression())
        #---store checkbox
        for item in [ 
                          self.grpBox1
                         ,self.grpBox2
                         ,self.grpBox3
                         ,self.chkBoxAddDrawRule
                         ,self.chkBoxClearOldMark
                         ]:
            settings.setValue("/PDS/markwell/{}".format(item.objectName()), int(item.isChecked()))
        



            