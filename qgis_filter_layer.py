#!/usr/local/bin/python2.7
# -*- coding: utf-8 -*-

'''
Created on 6 дек. 2019 г.

@author: Alexey Russkikh
'''
from qgis.core import *
from qgis.gui import QgsMessageBar
from PyQt4 import QtGui, uic
from PyQt4.QtGui import *
from PyQt4.QtCore import *
from utils import saveSetting, loadSetting, store_layer_filter,\
    restore_layer_filter, delete_layer_filter
import os

import inspect
from itertools import chain


FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'qgis_filter_layers_base.ui'))


#===============================================================================
# 
#===============================================================================
class QgsFilterLoaderDialog(QtGui.QDialog,FORM_CLASS):
    def __init__(self
                 ,iface
                 ,Lbl="Select item"
                 ,default_selection=None
                 ,parent=None
                 ):
        super(QgsFilterLoaderDialog, self).__init__(parent)
        self.iface=iface
        filters_list=[loadSetting(settings=None, layer=lyr, name=u"Filter", default={}, check_global=False) for lyr in self.iface.legendInterface().selectedLayers()]
        items=[]
        [items.extend(keys) for keys in [list(f.keys()) for f in filters_list  ]]
        items=list(set(items))

        
        self.setWindowTitle("Layers filters")
        self.setWindowModality(Qt.ApplicationModal)
        self.setupUi(self) # load items from .ui file
        
        self.default=default_selection
        self.cb.addItems(items)
        self.cb.setInsertPolicy(QComboBox.InsertBeforeCurrent)
        self.cb.setEditable(True)   
        self.cb.setDuplicatesEnabled(False)     

        #button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel | QDialogButtonBox.Apply)
        self.accepted.connect(self.accept) #OK button

        apply_button =   QPushButton(self.tr("Load"))
        reset_button =   QPushButton(self.tr("Delete"))
        restore_button = QPushButton(self.tr("Reset"))
        save_button =    QPushButton(self.tr("Save"))
        self.buttonBox.addButton(apply_button,   QDialogButtonBox.ActionRole)
        self.buttonBox.addButton(save_button,    QDialogButtonBox.ActionRole)
        self.buttonBox.addButton(restore_button, QDialogButtonBox.ActionRole)
        self.buttonBox.addButton(reset_button,   QDialogButtonBox.ActionRole)

#         apply_button =self.buttonBox.button(QDialogButtonBox.Apply)
#         reset_button = self.buttonBox.button(QDialogButtonBox.Reset)
#         restore_button = self.buttonBox.button(QDialogButtonBox.RestoreDefaults)
#         save_button = self.buttonBox.button(QDialogButtonBox.Save)
        
        apply_button.clicked.connect(   self.apply)
        reset_button.clicked.connect(   self.reset)
        restore_button.clicked.connect( self.restoreDefault) 
        save_button.clicked.connect(    self.save) 

    #===========================================================================
    # tr
    #===========================================================================
    def tr(self, message):
        return QCoreApplication.translate('QgisPDS', message)

    #===========================================================================
    # 
    #===========================================================================
    def on_buttonBox_accepted(self):
        name=inspect.currentframe().f_code.co_name
        QgsMessageLog.logMessage(u"{}".format(name), tag="QgisPDS.debug")
        
        pass 
    
    #===========================================================================
    # accept
    #===========================================================================
    def accept(self):
        name=inspect.currentframe().f_code.co_name
        QgsMessageLog.logMessage(u"{}".format(name), tag="QgisPDS.debug")
        pass
    
    #===========================================================================
    # apply
    #===========================================================================
    def apply(self):
        name=inspect.currentframe().f_code.co_name
        QgsMessageLog.logMessage(u"{}".format(name), tag="QgisPDS.debug")
        name=self.cb.currentText() 
        for lyr in self.iface.legendInterface().selectedLayers():
            for lyr in self.iface.legendInterface().selectedLayers():
                restore_layer_filter(
                                    lyr=lyr
                                    ,filter_name=name
                                    )
        pass
    
    #===========================================================================
    # reset
    #===========================================================================
    def restoreDefault(self):
        name=inspect.currentframe().f_code.co_name
        QgsMessageLog.logMessage(u"{}".format(name), tag="QgisPDS.debug")
        for lyr in self.iface.legendInterface().selectedLayers():
            lyr.setSubsetString('')
        pass
    #===========================================================================
    # reset
    #===========================================================================
    def reset(self):
        name=inspect.currentframe().f_code.co_name
        QgsMessageLog.logMessage(u"{}".format(name), tag="QgisPDS.debug")
        name=self.cb.currentText()
        for lyr in self.iface.legendInterface().selectedLayers():
            delete_layer_filter(lyr=lyr, filter_name=name)
        self.cb.removeItem(self.cb.currentIndex())
        pass
    
    #===========================================================================
    # save
    #===========================================================================
    def save(self):
        name=inspect.currentframe().f_code.co_name
        QgsMessageLog.logMessage(u"{}".format(name), tag="QgisPDS.debug")

        name=self.cb.currentText() 
        for lyr in self.iface.legendInterface().selectedLayers():
            if lyr.subsetString() is not None and len(lyr.subsetString())>0:
                store_layer_filter(
                                lyr=lyr
                                ,filter_name=name
                                ,clear_after=False
                                  )
        pass

