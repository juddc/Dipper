"""
The Dipper type system implementation
"""
import math
from rpython.rlib.objectmodel import we_are_translated


class DBase(object):
    typename = "base"
    refcnt = 0

    def copy(self):
        raise NotImplementedError("%s.copy()" % self.__class__.__name__)

    def assign_int(self, val):
        raise NotImplementedError("%s.assign_int()" % self.__class__.__name__)

    def assign_float(self, val):
        raise NotImplementedError("%s.assign_int()" % self.__class__.__name__)

    def assign_str(self, val):
        raise NotImplementedError("%s.assign_int()" % self.__class__.__name__)

    def operator(self, op, other):
        raise ValueError("Unimplemented operator %s on type %s" % (op, self.typename))

    def operator_py(self, op, other):
        raise ValueError("Unimplemented operator %s on type %s" % (op, self.typename))

    def bool(self):
        return DBool(self.bool_py())

    def bool_py(self):
        raise NotImplementedError("%s.bool_py()" % self.__class__.__name__)

    def str(self):
        return DString(self.str_py())

    def str_py(self):
        return self.repr_py()

    def int(self):
        return DInteger(self.int_py())

    def int_py(self):
        raise NotImplementedError("%s.int_py()" % self.__class__.__name__)

    def float(self):
        return DFloat(self.float_py())

    def float_py(self):
        raise NotImplementedError("%s.float_py()" % self.__class__.__name__)

    def repr(self):
        return DString(self.repr_py())

    def repr_py(self):
        return "<%s: %s>" % (self.__class__.__name__, self.str_py())

    def hash(self):
        return DInteger(self.hash_py())

    def hash_py(self):
        raise NotImplementedError("%s.hash_py()" % self.__class__.__name__)

    def len(self):
        return DInteger(self.len_py())

    def len_py(self):
        raise NotImplementedError("%s.len_py()" % self.__class__.__name__)

    def sqrt(self):
        return DFloat(self.sqrt_py())

    def sqrt_py(self):
        raise NotImplementedError("%s.sqrt_py()" % self.__class__.__name__)

    def getitem(self, key):
        """
        Takes a DBase object for the key and returns a DBase object.
        """
        raise NotImplementedError("%s.getitem()" % self.__class__.__name__)

    def getitem_py(self, key):
        """
        The _py version of this returns a DBase object. It's just the key argument that takes a Python integer.
        """
        raise NotImplementedError("%s.getitem_py()" % self.__class__.__name__)

    def setitem(self, key, val):
        """
        Takes a DBase object for both key and val.
        """
        raise NotImplementedError("%s.setitem()" % self.__class__.__name__)

    def setitem_py(self, key, val):
        """
        The _py version of this expects a DBase object for the `val` argument. It's just the key argument that
        takes a Python integer.
        """
        raise NotImplementedError("%s.setitem_py()" % self.__class__.__name__)


class DNull(DBase):
    typename = "null"

    def copy(self):
        return self

    def bool_py(self):
        return False

    def int_py(self):
        return 0

    def hash_py(self):
        raise TypeError("Unhashable type: %s" % self.typename)

    def str_py(self):
        return "null"

    def repr_py(self):
        return "<DNull>"


class DBool(DBase):
    typename = "bool"

    def __init__(self, val):
        if not we_are_translated():
            assert type(val) is bool
        self._bool = val

    @staticmethod
    def true():
        return DBool(True)

    @staticmethod
    def false():
        return DBool(False)

    def copy(self):
        return DBool(self._bool)

    def operator(self, op, other):
        if op == "==":
            return DBool(self._bool == other.bool_py())
        elif op == "!=":
            return DBool(self._bool != other.bool_py())
        else:
            raise ValueError("Invalid operator %s" % op)

    def bool_py(self):
        return self._bool

    def int_py(self):
        if self._bool is True:
            return 1
        else:
            return 0

    def hash_py(self):
        return self.int_py()

    def str_py(self):
        return "True" if self._bool else "False"

    def repr_py(self):
        return "<%s>" % self.str_py()



class DInteger(DBase):
    typename = "int"

    def __init__(self, val=0):
        if not we_are_translated():
            assert type(val) is int
        self._int = val

    def copy(self):
        return DInteger(self._int)

    def assign_int(self, val):
        if not we_are_translated():
            assert type(val) is int
        self._int = val

    def operator(self, op, other):
        if not we_are_translated():
            assert type(other) is DInteger
        if op == "+":
            return DInteger(self._int + other._int)
        elif op == "-":
            return DInteger(self._int - other._int)
        elif op == "*":
            return DInteger(self._int * other._int)
        elif op == "/":
            return DInteger(self._int // other._int)
        elif op == "==":
            return DBool(self._int == other._int)
        elif op == "!=":
            return DBool(self._int != other._int)
        elif op == "<":
            return DBool(self._int < other._int)
        elif op == ">":
            return DBool(self._int > other._int)
        elif op == "<=":
            return DBool(self._int <= other._int)
        elif op == ">=":
            return DBool(self._int >= other._int)
        else:
            raise ValueError("Invalid operator %s" % op)

    def sqrt_py(self):
        return math.sqrt(self.float_py())

    def bool_py(self):
        if self._int == 0:
            return False
        else:
            return True

    def int_py(self):
        return self._int

    def float_py(self):
        return float(self._int)

    def hash_py(self):
        return self._int

    def str_py(self):
        return str(self._int)



class DFloat(DBase):
    typename = "float"

    def __init__(self, val=0.0):
        if not we_are_translated():
            assert type(val) is float
        self._float = val

    def copy(self):
        return DFloat(self._float)

    def assign_float(self, val):
        if not we_are_translated():
            assert type(val) is float
        self._float = val

    def operator(self, op, other):
        if not we_are_translated():
            assert type(other) is DFloat
        if op == "+":
            return DFloat(self._float + other._float)
        elif op == "-":
            return DFloat(self._float - other._float)
        elif op == "*":
            return DFloat(self._float * other._float)
        elif op == "/":
            return DFloat(self._float / other._float)
        elif op == "==":
            return DBool(self._float == other._float)
        elif op == "!=":
            return DBool(self._float != other._float)
        else:
            raise ValueError("Invalid operator")

    def sqrt_py(self):
        return math.sqrt(self._float)

    def bool_py(self):
        if self._float == 0.0:
            return False
        else:
            return True

    def int_py(self):
        return int(self._float)

    def float_py(self):
        return self._float

    def hash_py(self):
        return int(self._float)

    def str_py(self):
        return str(self._float)


class DString(DBase):
    typename = "str"

    def __init__(self, val=""):
        if not we_are_translated():
            assert type(val) is str
        self._str = val

    def copy(self):
        return DString(self._str)

    def assign_str(self, val):
        if not we_are_translated():
            assert type(val) is str
        self._str = val

    def operator(self, op, other):
        if not we_are_translated():
            assert type(other) is DString
        if op == "+":
            return DString(self._str + other._str)
        elif op == "==":
            return DBool(self._str == other._str)
        elif op == "!=":
            return DBool(self._str != other._str)
        else:
            raise ValueError("Invalid operator")

    def bool_py(self):
        if len(self._str) == 0:
            return False
        else:
            return True

    def len_py(self):
        return len(self._str)

    def hash_py(self):
        return hash(self._str)

    def str_py(self):
        return self._str

    def repr_py(self):
        return "<DString: '%s'>" % self.str_py()


class DFunc(DBase):
    typename = "func"

    def __init__(self, code, data, varnames):
        self.code = code
        self.data = data
        self.varnames = varnames



class DList(DBase):
    """
    Untyped array object
    """
    typename = "list"

    def __init__(self):
        self._list = []

    def copy(self):
        newlist = DList()
        for item in self._list:
            newlist._list.append(item.copy())
        return newlist

    def operator(self, op, other):
        if not we_are_translated():
            assert type(other) is DList
        if op == "+":
            newlist = DList()
            for item in self._list:
                newlist._list.append(item)
            for item in other._list:
                newlist._list.append(item)
            return newlist
        else:
            raise ValueError("Invalid operator %s" % op)

    def hash_py(self):
        return id(self._list)

    def getitem(self, idx):
        if not we_are_translated():
            assert type(idx) is DInteger
        return self._list[idx.int_py()]

    def getitem_py(self, idx):
        if not we_are_translated():
            assert type(idx) is int
        return self._list[idx]

    def setitem(self, idx, val):
        if not we_are_translated():
            assert type(idx) is DInteger
            assert isinstance(val, DBase)
        self._list[idx.int_py()] = val

    def setitem_py(self, idx, val):
        if not we_are_translated():
            assert type(idx) is int
            assert isinstance(val, DBase)
        self._list[idx] = val

    @staticmethod
    def args(vals):
        """ Helper for creating a list for use as function arguments """
        inst = DList()
        for val in vals:
            inst.append(val)
        return inst

    def append(self, item):
        if not we_are_translated():
            assert isinstance(item, DBase)
        self._list.append(item)

    def pop(self, idx):
        if not we_are_translated():
            assert type(idx) is DInteger
        return self._list.pop(idx.int_py())

    def len_py(self):
        return len(self._list)

    def str_py(self):
        items = []
        for v in self._list:
            items.append(v.str_py())
        return "[%s]" % ", ".join(items)


class DArray(DBase):
    """
    Typed array object
    """
    typename = "array"

    def __init__(self, listtype):
        self._array = []
        self._type = listtype

    def copy(self):
        newlist = DList()
        for item in self._array:
            newlist.append(item.copy())
        return newlist

    def operator(self, op, other):
        if we_are_translated():
            assert type(other) is DArray
        if not self._type == other._type:
            raise TypeError("Cannot use operators on two arrays of different types (%s and %s)" % (
                self._type, other._type))
        if op == "+":
            newarr = DArray(self._type)
            for item in self._array:
                newarr._array.append(item)
            for item in other._array:
                newarr._array.append(item)
            return newarr
        else:
            raise ValueError("Invalid operator %s" % op)

    def hash_py(self):
        return id(self._array)

    def getitem(self, idx):
        return self._array[idx.int_py()]

    def setitem(self, idx, val):
        self._array[idx.int_py()] = val

    def append(self, item):
        if not we_are_translated():
            assert isinstance(item, DBase)
        if type(item) is self._type:
            self._array.append(item)
        else:
            raise TypeError("Cannot add %s to array of type %s" % (item, self._type))

    def pop(self, idx):
        if not we_are_translated():
            assert type(idx) is DInteger
        return self.val.pop(idx.int_py())

    def len_py(self):
        return len(self._array)

    def str_py(self):
        items = []
        for v in self._array:
            items.append(v.str_py())
        return "[%s]" % ", ".join(items)


class DObject(DBase):
    typename = "obj"

    def __init__(self, type, fields):
        self.type = type
        self.val = {}
        for name in fields:
            self.val[name] = None

    def setattr(self, attr, val):
        if attr not in self.val:
            raise KeyError(attr)
        self.val[attr] = val

    def getattr(self, attr):
        return self.val[attr]
