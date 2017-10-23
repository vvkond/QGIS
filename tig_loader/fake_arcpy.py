import itertools

from tig_loader.dbg import log_method
from tig_loader.utils import StrictInit, cached_property


def log(fn):
    return log_method(enabled=True, log_args=True)(fn)


class Obj(object):
    def __init__(self, *a, **kw):
        self._args = a, kw

    def __repr__(self):
        return '{0}({1})'.format(
            self.__class__.__name__,
            ', '.join(itertools.chain(
                ('{0!r}'.format(arg) for arg in self._args[0]),
                ('{0}={1!r}'.format(k, v) for k, v in self._args[1].iteritems()),
            )),
        )


class FakeArcpy(StrictInit):

    @log
    def SetProgressor(self, *a, **kw):
        pass

    @log
    def SetProgressorLabel(self, *a, **kw):
        pass

    @log
    def ResetProgressor(self, *a, **kw):
        pass

    @log
    def SetProgressorPosition(self, *a, **kw):
        pass

    @cached_property
    def da(self):

        class Da(object):
            @log
            def InsertCursor(self, *_a, **_kw):

                class Cursor(object):
                    def __enter__(self):
                        return self

                    def __exit__(self, *a):
                        pass

                    @log
                    def insertRow(self, *a, **kw):
                        pass

                return Cursor()

        return Da()

    @cached_property
    def env(self):

        class Env(Obj):
            pass

        return Env()

    @cached_property
    def SpatialReference(self):

        class SpatialReference(Obj):
            def create(self):
                pass

            @log
            def loadFromString(self, *a, **kw):
                pass

        return SpatialReference

    @log
    def CreateFeatureclass_management(self, *a, **kw):
        pass

    @log
    def AddField_management(self, *a, **kw):
        pass

    @cached_property
    def Polyline(self):

        class Polyline(Obj):
            pass

        return Polyline

    @cached_property
    def Multipoint(self):

        class Multipoint(Obj):
            pass

        return Multipoint

    @cached_property
    def Array(self):

        class Array(Obj):
            pass

        return Array

    @cached_property
    def Point(self):

        class Point(Obj):
            pass

        return Point

    @cached_property
    def Parameter(self):

        class Filter(Obj):
            pass

        class Parameter(Obj):
            altered = False

            @log
            def __init__(self, **kw):
                Obj.__init__(self, **kw)
                for k, v in kw.iteritems():
                    setattr(self, k, v)
                self.filter = Filter(list=[], type='')

            @property
            def valueAsText(self):
                return unicode(self.value)

            @log
            def setErrorMessage(self, *a, **kw):
                pass

            @log
            def clearMessage(self, *a, **kw):
                pass

        return Parameter

    @log
    def NumPyArrayToRaster(self, *a, **kw):

        class Raster(Obj):
            @log
            def save(self, *a, **kw):
                pass

        return Raster(*a, **kw)

    @cached_property
    def _PassedParameter(self):

        class PassedParameter(object):
            def __init__(self, name, value):
                self.name = name
                self.value = value

            @property
            def valueAsText(self):
                return unicode(self.value)

        return PassedParameter

    @cached_property
    def _Messages(self):

        class Messages(object):
            @log
            def addMessage(self, *a, **kw):
                pass

            @log
            def addWarningMessage(self, *a, **kw):
                pass

        return Messages


_instance = [None]


def get_instance():
    if _instance[0] is None:
        _instance[0] = FakeArcpy()
    return _instance[0]


def execute_tool(Tool, parameters):
    fake_arcpy = get_instance()
    passed_parameters = [
        fake_arcpy._PassedParameter('p{}'.format(i), parameter)
        for i, parameter in enumerate(parameters)
    ]
    messages = fake_arcpy._Messages()
    Tool().execute(passed_parameters, messages)
