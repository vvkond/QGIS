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
    import os,sys
    #settings = QSettings().allKeys()
    #for setting in settings:
    #    print setting
    current_conf=QSettings().value( 'svg/searchPathsForSVG')
    if current_conf is None: current_conf=u'' 
    settings_svg_path=current_conf.split("|")
    #svg_path=os.path.join(os.environ['USERPROFILE'],u'.qgis2',u'python',u'plugins',u'QgisPDS',u'svg')
    svg_path=os.path.join(os.path.dirname(os.path.abspath(__file__)),u'svg')
    utils_path=os.path.join(os.path.dirname(os.path.abspath(__file__)),u'libs\\pds_opt_py')
    utils_platform_depended=str(os.path.join(
                                os.path.dirname(os.path.abspath(__file__))
                                ,r"libs\x86_64" if sys.maxsize > 2**32 else r"libs\i386" 
                            ))
    bin_platform_depended=str(os.path.join(
                                os.path.dirname(os.path.abspath(__file__))
                                ,r"bin\x86_64" if sys.maxsize > 2**32 else r"bin\i386" 
                            ))
    sys.path.insert(0, utils_platform_depended)
    sys.path.insert(0, utils_path)
    sys.path.insert(0, bin_platform_depended)

    
    if svg_path not in settings_svg_path and svg_path is not None:
        QSettings().setValue('svg/searchPathsForSVG', current_conf+u'|'+svg_path)
    #QSettings().setValue('svg/searchPathsForSVG',u'C:\\Users\\tig\\.qgis2\\python\\plugins\\QgisPDS\\svg')
    #QSettings().setValue('svg/searchPathsForSVG', QSettings().value( 'svg/searchPathsForSVG')+u'|'+u'C:\\Users\\tig\\.qgis2\\python\\plugins\\QgisPDS\\svg')
        
    from .qgis_pds import QgisPDS
    return QgisPDS(iface)
