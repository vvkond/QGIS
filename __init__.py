# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QgisPDS
                                 A QGIS plugin
 PDS link
                             -------------------
        begin                : 2016-11-05
        copyright            : (C) 2016 by Viktor Kondrashov
        email                : viktor@gmail.com
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
    from .qgis_pds import QgisPDS
    return QgisPDS(iface)
