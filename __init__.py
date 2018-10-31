# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QgisPDS
                                 A QGIS plugin
 PDS link
                             -------------------
        begin                : 2016-11-05
        copyright            : (C) 2016 by SoyuzGeoService
        email                : viktor@gmail.com, skylex72rus@gmail.com
        git sha              : $Format:%H$
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load QgisPDS class from file QgisPDS.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from qgis.PyQt.QtCore import QSettings
    import os
    #settings = QSettings().allKeys()
    #for setting in settings:
    #    print setting
    settings_svg_path=QSettings().value( 'svg/searchPathsForSVG').split("|")
    svg_path=os.path.join(os.environ['USERPROFILE'],u'.qgis2',u'python',u'plugins',u'QgisPDS',u'svg')
    if svg_path not in settings_svg_path:
        QSettings().setValue('svg/searchPathsForSVG', QSettings().value( 'svg/searchPathsForSVG')+u'|'+svg_path)
    #QSettings().setValue('svg/searchPathsForSVG',u'C:\\Users\\tig\\.qgis2\\python\\plugins\\QgisPDS\\svg')
    #QSettings().setValue('svg/searchPathsForSVG', QSettings().value( 'svg/searchPathsForSVG')+u'|'+u'C:\\Users\\tig\\.qgis2\\python\\plugins\\QgisPDS\\svg')
        
    from .qgis_pds import QgisPDS
    return QgisPDS(iface)
