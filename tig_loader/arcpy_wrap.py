import sys

if 'arcpy' in sys.modules:
    import arcpy
else:
    from tig_loader.fake_arcpy import get_instance as _get_instance
    arcpy = _get_instance()
