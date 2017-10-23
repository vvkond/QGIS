# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QgisPDSDialog
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

import os

from PyQt4 import QtGui, uic
from qgis.gui import QgsMessageBar
from QgisPDS.db import Sqlite
from QgisPDS.connections import create_connection
from QgisPDS.utils import to_unicode
from os.path import abspath
import json

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'qgis_pds_dialog_base.ui'))

    
class Db(object):
    def __init__(self, db_path):
        self.db = Sqlite(db_path)

    def enumerate_connections(self):
        return self.db.execute('select id, name from connections order by name, id')

    def get_connection(self, id):
        row = self.db.fetch_assoc('select * from connections where id=:id', id=id)
        row['options'] = json.loads(row['options'])
        return row

    def delete_connection(self, id):
        self.db.execute('delete from connections where id=:id', id=id)
        self.db.connection.commit()

    def create_connection(self, **args): 
        id = self.db.execute('insert into connections (type, name, options) values(:type, :name, :options)', **args).lastrowid
        self.db.connection.commit()
        return id

    def update_connection(self, **args):
        self.db.execute('update connections set type=:type, name=:name, options=:options where id=:id', **args)

    def enumerate_tools(self):
        return self.db.execute_assoc('select id, name from tools t order by name, id')


class QgisPDSDialog(QtGui.QDialog, FORM_CLASS):
    def __init__(self, iface, parent=None):
        """Constructor."""
        super(QgisPDSDialog, self).__init__(parent)
        
        self.setupUi(self)
        
        self.iface = iface
        self.db_path = abspath(os.path.join(os.path.dirname(__file__), u'TigLoader.sqlite'))
        self._fillProjectList(self.db_path)
        
         
    def selectedProject(self):
        currRow = self.tableWidget.currentRow()
        if currRow >= 0 and currRow < self.tableWidget.rowCount():
            hostItem = self.tableWidget.item(currRow, 0)
            sidItem = self.tableWidget.item(currRow, 1)
            projItem = self.tableWidget.item(currRow, 2)
            return self.projects[currRow]
            
    def setCurrentProject(self, project):
        conn1 = create_connection(project)
        for row,prj in enumerate(self.projects):
            conn = create_connection(prj)
            if prj['project'] == project['project'] and conn1.host == conn.host and conn1.sid == conn.sid:
                self.tableWidget.setCurrentCell(row, 0)
                break
           
    def _fillProjectList(self, db_path):
        self.tableWidget.setRowCount(0)
        
        if os.path.isfile(db_path):
            db = Db(db_path)
        else:
            QtGui.QMessageBox.critical(None, self.tr(u'Error'), self.tr(u'File not exists - ')+db_path, QtGui.QMessageBox.Ok)
            return
                       
        try:	
            row = 0
            self.projects = []
            for connection_id, connection_name in db.enumerate_connections():
                conn_row = db.get_connection(connection_id)
                opt = self._getUiOptions(conn_row, connection_id)
                projects = self._getPDSProjects(opt)
                
                if projects is not None:
                    for project, host, server in projects:
                        self.tableWidget.insertRow(row)
                        
                        item = QtGui.QTableWidgetItem(host)                     
                        self.tableWidget.setItem(row, 0, item)
                        
                        item = QtGui.QTableWidgetItem(server)                     
                        self.tableWidget.setItem(row, 1, item)
                        
                        item = QtGui.QTableWidgetItem(project)                     
                        self.tableWidget.setItem(row, 2, item)
                        
                        port = conn_row['options']['port']
                        user = to_unicode(conn_row['options']['user'])
                        password = to_unicode(conn_row['options']['password'])

                        self.projects.append(self._createProjectRecord(host, server, project, port, user, password))
                        
                        row += 1
                
        except Exception as e:
            QtGui.QMessageBox.critical(None, self.tr(u'Error'), self.tr(str(e)), QtGui.QMessageBox.Ok)
     
    def _createProjectRecord(self, host, server, project, port, user, password):
        return {
            'type': u'tigress',
            'project': to_unicode(project),
            'options': json.dumps({
                'host': to_unicode(host),
                'port': port,
                'sid': to_unicode(server),
                'user': to_unicode(user),
                'password': to_unicode(password),
            }, ensure_ascii=False),       
        }
      
    def _getUiOptions(self, d, connection_id):  
        """ get ui options """    
        return {
            'id': connection_id,
            'name': to_unicode(d['name']),
            'type': u'tigress',
            'options': json.dumps({
                'host': to_unicode(d['options']['host']),
                'port': d['options']['port'],
                'sid': to_unicode(d['options']['sid']),
                'user': to_unicode(d['options']['user']),
                'password': to_unicode(d['options']['password']),
            }, ensure_ascii=False),
        }
 
    def _getPDSProjects(self, options):
        connection = create_connection(options)
        try:
            db = connection.get_db()
            result = db.execute('SELECT PROJECT_NAME, PROJECT_HOST, PROJECT_SERVER FROM GLOBAL.project WHERE PROJECT_NAME <> \'global\' ')
            db.disconnect()
            return result
        except Exception as e:
            #print 'Connection {0}: {1}'.format(connection.name, str(e))
            self.iface.messageBar().pushMessage(self.tr("Error"), 
                            self.tr(u'Connection {0}: {1}').format(connection.name, str(e)), 
                            level=QgsMessageBar.CRITICAL)
            return None

