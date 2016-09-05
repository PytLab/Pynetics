# This file was automatically generated by SWIG (http://www.swig.org).
# Version 3.0.7
#
# Do not make changes to this file unless you know what you are doing--modify
# the SWIG interface file instead.





from sys import version_info
if version_info >= (2, 6, 0):
    def swig_import_helper():
        from os.path import dirname
        import imp
        fp = None
        try:
            fp, pathname, description = imp.find_module('_kmc_functions', [dirname(__file__)])
        except ImportError:
            import _kmc_functions
            return _kmc_functions
        if fp is not None:
            try:
                _mod = imp.load_module('_kmc_functions', fp, pathname, description)
            finally:
                fp.close()
            return _mod
    _kmc_functions = swig_import_helper()
    del swig_import_helper
else:
    import _kmc_functions
del version_info
try:
    _swig_property = property
except NameError:
    pass  # Python < 2.2 doesn't have 'property'.


def _swig_setattr_nondynamic(self, class_type, name, value, static=1):
    if (name == "thisown"):
        return self.this.own(value)
    if (name == "this"):
        if type(value).__name__ == 'SwigPyObject':
            self.__dict__[name] = value
            return
    method = class_type.__swig_setmethods__.get(name, None)
    if method:
        return method(self, value)
    if (not static):
        if _newclass:
            object.__setattr__(self, name, value)
        else:
            self.__dict__[name] = value
    else:
        raise AttributeError("You cannot add attributes to %s" % self)


def _swig_setattr(self, class_type, name, value):
    return _swig_setattr_nondynamic(self, class_type, name, value, 0)


def _swig_getattr_nondynamic(self, class_type, name, static=1):
    if (name == "thisown"):
        return self.this.own()
    method = class_type.__swig_getmethods__.get(name, None)
    if method:
        return method(self)
    if (not static):
        return object.__getattr__(self, name)
    else:
        raise AttributeError(name)

def _swig_getattr(self, class_type, name):
    return _swig_getattr_nondynamic(self, class_type, name, 0)


def _swig_repr(self):
    try:
        strthis = "proxy of " + self.this.__repr__()
    except:
        strthis = ""
    return "<%s.%s; %s >" % (self.__class__.__module__, self.__class__.__name__, strthis,)

try:
    _object = object
    _newclass = 1
except AttributeError:
    class _object:
        pass
    _newclass = 0


class SwigPyIterator(_object):
    __swig_setmethods__ = {}
    __setattr__ = lambda self, name, value: _swig_setattr(self, SwigPyIterator, name, value)
    __swig_getmethods__ = {}
    __getattr__ = lambda self, name: _swig_getattr(self, SwigPyIterator, name)

    def __init__(self, *args, **kwargs):
        raise AttributeError("No constructor defined - class is abstract")
    __repr__ = _swig_repr
    __swig_destroy__ = _kmc_functions.delete_SwigPyIterator
    __del__ = lambda self: None

    def value(self):
        return _kmc_functions.SwigPyIterator_value(self)

    def incr(self, n=1):
        return _kmc_functions.SwigPyIterator_incr(self, n)

    def decr(self, n=1):
        return _kmc_functions.SwigPyIterator_decr(self, n)

    def distance(self, x):
        return _kmc_functions.SwigPyIterator_distance(self, x)

    def equal(self, x):
        return _kmc_functions.SwigPyIterator_equal(self, x)

    def copy(self):
        return _kmc_functions.SwigPyIterator_copy(self)

    def next(self):
        return _kmc_functions.SwigPyIterator_next(self)

    def __next__(self):
        return _kmc_functions.SwigPyIterator___next__(self)

    def previous(self):
        return _kmc_functions.SwigPyIterator_previous(self)

    def advance(self, n):
        return _kmc_functions.SwigPyIterator_advance(self, n)

    def __eq__(self, x):
        return _kmc_functions.SwigPyIterator___eq__(self, x)

    def __ne__(self, x):
        return _kmc_functions.SwigPyIterator___ne__(self, x)

    def __iadd__(self, n):
        return _kmc_functions.SwigPyIterator___iadd__(self, n)

    def __isub__(self, n):
        return _kmc_functions.SwigPyIterator___isub__(self, n)

    def __add__(self, n):
        return _kmc_functions.SwigPyIterator___add__(self, n)

    def __sub__(self, *args):
        return _kmc_functions.SwigPyIterator___sub__(self, *args)
    def __iter__(self):
        return self
SwigPyIterator_swigregister = _kmc_functions.SwigPyIterator_swigregister
SwigPyIterator_swigregister(SwigPyIterator)

class StdVectorString(_object):
    __swig_setmethods__ = {}
    __setattr__ = lambda self, name, value: _swig_setattr(self, StdVectorString, name, value)
    __swig_getmethods__ = {}
    __getattr__ = lambda self, name: _swig_getattr(self, StdVectorString, name)
    __repr__ = _swig_repr

    def iterator(self):
        return _kmc_functions.StdVectorString_iterator(self)
    def __iter__(self):
        return self.iterator()

    def __nonzero__(self):
        return _kmc_functions.StdVectorString___nonzero__(self)

    def __bool__(self):
        return _kmc_functions.StdVectorString___bool__(self)

    def __len__(self):
        return _kmc_functions.StdVectorString___len__(self)

    def pop(self):
        return _kmc_functions.StdVectorString_pop(self)

    def __getslice__(self, i, j):
        return _kmc_functions.StdVectorString___getslice__(self, i, j)

    def __setslice__(self, *args):
        return _kmc_functions.StdVectorString___setslice__(self, *args)

    def __delslice__(self, i, j):
        return _kmc_functions.StdVectorString___delslice__(self, i, j)

    def __delitem__(self, *args):
        return _kmc_functions.StdVectorString___delitem__(self, *args)

    def __getitem__(self, *args):
        return _kmc_functions.StdVectorString___getitem__(self, *args)

    def __setitem__(self, *args):
        return _kmc_functions.StdVectorString___setitem__(self, *args)

    def append(self, x):
        return _kmc_functions.StdVectorString_append(self, x)

    def empty(self):
        return _kmc_functions.StdVectorString_empty(self)

    def size(self):
        return _kmc_functions.StdVectorString_size(self)

    def clear(self):
        return _kmc_functions.StdVectorString_clear(self)

    def swap(self, v):
        return _kmc_functions.StdVectorString_swap(self, v)

    def get_allocator(self):
        return _kmc_functions.StdVectorString_get_allocator(self)

    def begin(self):
        return _kmc_functions.StdVectorString_begin(self)

    def end(self):
        return _kmc_functions.StdVectorString_end(self)

    def rbegin(self):
        return _kmc_functions.StdVectorString_rbegin(self)

    def rend(self):
        return _kmc_functions.StdVectorString_rend(self)

    def pop_back(self):
        return _kmc_functions.StdVectorString_pop_back(self)

    def erase(self, *args):
        return _kmc_functions.StdVectorString_erase(self, *args)

    def __init__(self, *args):
        this = _kmc_functions.new_StdVectorString(*args)
        try:
            self.this.append(this)
        except:
            self.this = this

    def push_back(self, x):
        return _kmc_functions.StdVectorString_push_back(self, x)

    def front(self):
        return _kmc_functions.StdVectorString_front(self)

    def back(self):
        return _kmc_functions.StdVectorString_back(self)

    def assign(self, n, x):
        return _kmc_functions.StdVectorString_assign(self, n, x)

    def resize(self, *args):
        return _kmc_functions.StdVectorString_resize(self, *args)

    def insert(self, *args):
        return _kmc_functions.StdVectorString_insert(self, *args)

    def reserve(self, n):
        return _kmc_functions.StdVectorString_reserve(self, n)

    def capacity(self):
        return _kmc_functions.StdVectorString_capacity(self)
    __swig_destroy__ = _kmc_functions.delete_StdVectorString
    __del__ = lambda self: None
StdVectorString_swigregister = _kmc_functions.StdVectorString_swigregister
StdVectorString_swigregister(StdVectorString)

class StdVectorDouble(_object):
    __swig_setmethods__ = {}
    __setattr__ = lambda self, name, value: _swig_setattr(self, StdVectorDouble, name, value)
    __swig_getmethods__ = {}
    __getattr__ = lambda self, name: _swig_getattr(self, StdVectorDouble, name)
    __repr__ = _swig_repr

    def iterator(self):
        return _kmc_functions.StdVectorDouble_iterator(self)
    def __iter__(self):
        return self.iterator()

    def __nonzero__(self):
        return _kmc_functions.StdVectorDouble___nonzero__(self)

    def __bool__(self):
        return _kmc_functions.StdVectorDouble___bool__(self)

    def __len__(self):
        return _kmc_functions.StdVectorDouble___len__(self)

    def pop(self):
        return _kmc_functions.StdVectorDouble_pop(self)

    def __getslice__(self, i, j):
        return _kmc_functions.StdVectorDouble___getslice__(self, i, j)

    def __setslice__(self, *args):
        return _kmc_functions.StdVectorDouble___setslice__(self, *args)

    def __delslice__(self, i, j):
        return _kmc_functions.StdVectorDouble___delslice__(self, i, j)

    def __delitem__(self, *args):
        return _kmc_functions.StdVectorDouble___delitem__(self, *args)

    def __getitem__(self, *args):
        return _kmc_functions.StdVectorDouble___getitem__(self, *args)

    def __setitem__(self, *args):
        return _kmc_functions.StdVectorDouble___setitem__(self, *args)

    def append(self, x):
        return _kmc_functions.StdVectorDouble_append(self, x)

    def empty(self):
        return _kmc_functions.StdVectorDouble_empty(self)

    def size(self):
        return _kmc_functions.StdVectorDouble_size(self)

    def clear(self):
        return _kmc_functions.StdVectorDouble_clear(self)

    def swap(self, v):
        return _kmc_functions.StdVectorDouble_swap(self, v)

    def get_allocator(self):
        return _kmc_functions.StdVectorDouble_get_allocator(self)

    def begin(self):
        return _kmc_functions.StdVectorDouble_begin(self)

    def end(self):
        return _kmc_functions.StdVectorDouble_end(self)

    def rbegin(self):
        return _kmc_functions.StdVectorDouble_rbegin(self)

    def rend(self):
        return _kmc_functions.StdVectorDouble_rend(self)

    def pop_back(self):
        return _kmc_functions.StdVectorDouble_pop_back(self)

    def erase(self, *args):
        return _kmc_functions.StdVectorDouble_erase(self, *args)

    def __init__(self, *args):
        this = _kmc_functions.new_StdVectorDouble(*args)
        try:
            self.this.append(this)
        except:
            self.this = this

    def push_back(self, x):
        return _kmc_functions.StdVectorDouble_push_back(self, x)

    def front(self):
        return _kmc_functions.StdVectorDouble_front(self)

    def back(self):
        return _kmc_functions.StdVectorDouble_back(self)

    def assign(self, n, x):
        return _kmc_functions.StdVectorDouble_assign(self, n, x)

    def resize(self, *args):
        return _kmc_functions.StdVectorDouble_resize(self, *args)

    def insert(self, *args):
        return _kmc_functions.StdVectorDouble_insert(self, *args)

    def reserve(self, n):
        return _kmc_functions.StdVectorDouble_reserve(self, n)

    def capacity(self):
        return _kmc_functions.StdVectorDouble_capacity(self)
    __swig_destroy__ = _kmc_functions.delete_StdVectorDouble
    __del__ = lambda self: None
StdVectorDouble_swigregister = _kmc_functions.StdVectorDouble_swigregister
StdVectorDouble_swigregister(StdVectorDouble)


def collect_coverages(types, possible_types, coverage_ratios):
    return _kmc_functions.collect_coverages(types, possible_types, coverage_ratios)
collect_coverages = _kmc_functions.collect_coverages
# This file is compatible with both classic and new-style classes.


