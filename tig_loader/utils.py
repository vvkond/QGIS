

class StrictInit(object):
    def __init__(self, **kw):
        assert not set(kw).difference(dir(self.__class__)), '{0} does not declare fields {1}'.format(self.__class__, list(set(kw).difference(dir(self.__class__))))
        self.__dict__.update(kw)


class Args(StrictInit):
    args = None


class Exc(Exception):
    pass


class cached_property(object):

    def __init__(self, func, name=None, doc=None):
        self.__name__ = name or func.__name__
        self.__module__ = func.__module__
        self.__doc__ = doc or func.__doc__
        self.func = func

    def __get__(self, obj, type=None):
        if obj is None:
            return self
        value = self.func(obj)
        setattr(obj, self.__name__, value)
        return value
