"""
The Dipper type system implementation
"""
import math
from collections import OrderedDict
from rpython.rlib.objectmodel import we_are_translated
from rpython.rlib.debug import make_sure_not_resized

from bytecode import INST_STRS


def AutoType(name, ns=None):
    """
    Takes the name of a type and returns the type class associated with it
    """
    if not we_are_translated():
        assert type(name) is str
    types = [DBool, DInteger, DFloat, DString, DList]
    for t in types:
        if t.typename == name:
            return t
    return DUnknown


class DBase(object):
    typename = "base"
    refcnt = 0

    # can this type be hashed?
    hashable = False

    # is this a numeric type?
    numeric = False

    def __init__(self):
        pass

    @property
    def basetype(self):
        return self.__class__.__name__

    def copy(self):
        raise NotImplementedError("%s.copy()" % self.basetype)

    def assign_bool(self, val):
        raise NotImplementedError("%s.assign_bool()" % self.basetype)

    def assign_int(self, val):
        raise NotImplementedError("%s.assign_int()" % self.basetype)

    def assign_float(self, val):
        raise NotImplementedError("%s.assign_float()" % self.basetype)

    def assign_str(self, val):
        raise NotImplementedError("%s.assign_str()" % self.basetype)

    def assign_list(self, vals):
        raise NotImplementedError("%s.assign_list()" % self.basetype)

    def operator_bool(self, op, other):
        """
        Given self, the operator as a string, and other as another DBase object,
        return a Python bool representing the operation.
        """
        raise ValueError("Unimplemented operator_bool %s on type %s" % (op, self.typename))

    def operator_int(self, op, other):
        """
        Given self, the operator as a string, and other as another DBase object,
        return a Python int representing the operation
        """
        raise ValueError("Unimplemented operator_int %s on type %s" % (op, self.typename))

    def operator_float(self, op, other):
        """
        Given self, the operator as a string, and other as another DBase object,
        return a Python float representing the operation
        """
        raise ValueError("Unimplemented operator_float %s on type %s" % (op, self.typename))

    def operator_str(self, op, other):
        """
        Given self, the operator as a string, and other as another DBase object,
        return a Python str representing the operation
        """
        raise ValueError("Unimplemented operator_str %s on type %s" % (op, self.typename))

    def operator_inplace(self, op, other):
        """
        Given self, the operator as a string, and other as another DBase object,
        do an inplace operation on self
        """
        raise ValueError("Unimplemented operator_inplace %s on type %s" % (op, self.typename))

    def typecmp(self, other):
        return DBool(self.typecmp_py())

    def typecmp_py(self, other):
        """
        Returns True if this object and the other object are the same type
        """
        assert isinstance(other, DBase)
        return self.__class__ == other.__class__

    def bool(self):
        return DBool(self.bool_py())

    def bool_py(self):
        raise NotImplementedError("%s.bool_py()" % self.basetype)

    def str(self):
        return DString.new_str(self.str_py())

    def str_py(self):
        raise NotImplementedError("%s.str_py()" % self.basetype)

    def int(self):
        return DInteger(self.int_py())

    def int_py(self):
        raise NotImplementedError("%s.int_py()" % self.basetype)

    def float(self):
        return DFloat(self.float_py())

    def float_py(self):
        raise NotImplementedError("%s.float_py()" % self.basetype)

    def repr(self):
        return DString.new_str(self.repr_py())

    def repr_py(self):
        return "<%s: %s>" % (self.basetype, self.str_py())

    def hash(self):
        return DInteger(self.hash_py())

    def hash_py(self):
        raise NotImplementedError("%s.hash_py()" % self.basetype)

    def len(self):
        return DInteger(self.len_py())

    def len_py(self):
        raise NotImplementedError("%s.len_py()" % self.basetype)

    def __len__(self):
        return self.len_py()

    def sqrt(self):
        return DFloat(self.sqrt_py())

    def sqrt_py(self):
        raise NotImplementedError("%s.sqrt_py()" % self.basetype)

    def getitem(self, key):
        """
        Takes a DBase object for the key and returns a DBase object.
        """
        raise NotImplementedError("%s.getitem()" % self.basetype)

    def setitem(self, key, val):
        """
        Takes a DBase object for both key and val.
        """
        raise NotImplementedError("%s.setitem()" % self.basetype)

    def getattr(self, name):
        """
        Takes a DBase object for the name and returns a DBase object.
        """
        raise NotImplementedError("%s.getattr()" % self.basetype)

    def getattr_py(self, name):
        """
        Takes a string for the name and returns a DBase object.
        """
        raise NotImplementedError("%s.getattr_py()" % self.basetype)

    def setattr(self, name, val):
        """
        Takes a DBase object for both name and val.
        """
        raise NotImplementedError("%s.setattr()" % self.basetype)

    def setattr_py(self, name, val):
        """
        Takes a string for the name and a DBase object for the val
        """
        raise NotImplementedError("%s.setattr_py()" % self.basetype)


class DUnknown(DBase):
    typename = "unknown"
    hashable = False
    numeric = False

    def repr_py(self):
        return "<DUnknown>"


class DNull(DBase):
    typename = "null"
    hashable = False
    numeric = False

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
    hashable = True
    numeric = False

    def __init__(self):
        self._bool = False

    @staticmethod
    def new_bool(val):
        inst = DBool()
        inst._bool = val
        return inst

    @staticmethod
    def true():
        return DBool.new_bool(True)

    @staticmethod
    def false():
        return DBool.new_bool(False)

    def assign_bool(self, val):
        self._bool = val

    def copy(self):
        return DBool.new_bool(self._bool)

    def operator_bool(self, op, other):
        if op == "==":
            return self._bool == other.bool_py()
        elif op == "!=":
            return self._bool != other.bool_py()
        else:
            raise ValueError("Unimplemented operator_bool %s on type %s" % (op, self.typename))

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
    hashable = True
    numeric = True

    def __init__(self):
        self._int = 0

    @staticmethod
    def new_int(val):
        inst = DInteger()
        inst._int = val
        return inst

    def copy(self):
        return DInteger.new_int(self._int)

    def assign_int(self, val):
        if not we_are_translated():
            assert type(val) is int
        self._int = val

    def operator_bool(self, op, other):
        if other.numeric == False:
            raise ValueError("DInteger cannot do operator_bool on non-numeric type")
        if op == "==":
            return self._int == other.int_py()
        elif op == "!=":
            return self._int != other.int_py()
        elif op == "<":
            return self._int < other.int_py()
        elif op == ">":
            return self._int > other.int_py()
        elif op == "<=":
            return self._int <= other.int_py()
        elif op == ">=":
            return self._int >= other.int_py()
        else:
            raise ValueError("Unimplemented operator_bool %s on type %s" % (op, self.typename))

    def operator_int(self, op, other):
        if other.numeric == False:
            raise ValueError("DInteger cannot do operator_int on non-numeric type")
        if op == "+":
            return self._int + other.int_py()
        elif op == "-":
            return self._int - other.int_py()
        elif op == "*":
            return self._int * other.int_py()
        elif op == "/":
            return int(self._int / other.int_py())
        else:
            raise ValueError("Unimplemented operator_int %s on type %s" % (op, self.typename))

    def operator_float(self, op, other):
        if other.numeric == False:
            raise ValueError("DInteger cannot do operator_float on non-numeric type")
        if op == "+":
            return float(self._int) + other.float_py()
        elif op == "-":
            return float(self._int) - other.float_py()
        elif op == "*":
            return float(self._int) * other.float_py()
        elif op == "/":
            return float(self._int) / other.float_py()
        else:
            raise ValueError("Unimplemented operator_float %s on type %s" % (op, self.typename))

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
    hashable = True
    numeric = True

    def __init__(self):
        self._float = 0.0

    @staticmethod
    def new_float(val):
        inst = DFloat()
        inst._float = val
        return inst

    def copy(self):
        return DFloat.new_float(self._float)

    def assign_float(self, val):
        if not we_are_translated():
            assert type(val) is float
        self._float = val

    def operator_bool(self, op, other):
        if other.numeric == False:
            raise ValueError("DFloat cannot do operator_bool on non-numeric type")
        if op == "==":
            return self._float == other.float_py()
        elif op == "!=":
            return self._float != other.float_py()
        elif op == ">":
            return self._float > other.float_py()
        elif op == "<":
            return self._float < other.float_py()
        elif op == ">=":
            return self._float >= other.float_py()
        elif op == "<=":
            return self._float <= other.float_py()
        else:
            raise ValueError("Unimplemented operator_bool %s on type %s" % (op, self.typename))

    def operator_int(self, op, other):
        if other.numeric == False:
            raise ValueError("DFloat cannot do operator_float on non-numeric type")
        if op == "+":
            return int(self._float + other.float_py())
        elif op == "-":
            return int(self._float - other.float_py())
        elif op == "*":
            return int(self._float * other.float_py())
        elif op == "/":
            return int(self._float / other.float_py())
        else:
            raise ValueError("Unimplemented operator_int %s on type %s" % (op, self.typename))

    def operator_float(self, op, other):
        if other.numeric == False:
            raise ValueError("DFloat cannot do operator_float on non-numeric type")
        if op == "+":
            return self._float + other.float_py()
        elif op == "-":
            return self._float - other.float_py()
        elif op == "*":
            return self._float * other.float_py()
        elif op == "/":
            return self._float / other.float_py()
        else:
            raise ValueError("Unimplemented operator_float %s on type %s" % (op, self.typename))

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
        val = str(self._float)
        if "." in val:
            while val.endswith("0"):
                endstop = len(val) - 1
                if endstop > 2:
                    val = val[:endstop]
            if val.endswith("."):
                return val + "0"
            else:
                return val
        else:
            return val


class DString(DBase):
    typename = "str"
    hashable = True
    numeric = False

    def __init__(self):
        self._str = ""

    @staticmethod
    def new_str(val):
        inst = DString()
        inst._str = val
        return inst

    def copy(self):
        return DString.new_str(self._str)

    def assign_str(self, val):
        if not we_are_translated():
            assert type(val) is str
        self._str = val

    def operator_bool(self, op, other):
        # avoid a PHP situation where ("123" == 123)
        if not isinstance(other, DString):
            raise ValueError("Cannot compare strings with non-strings")
        if op == "==":
            return self._str == other.str_py()
        elif op == "!=":
            return self._str != other.str_py()
        else:
            raise ValueError("Unimplemented operator_bool %s on type %s" % (op, self.typename))

    def operator_str(self, op, other):
        if op == "+":
            return self._str + other.str_py()
        else:
            raise ValueError("Unimplemented operator_str %s on type %s" % (op, self.typename))

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
    hashable = False
    numeric = False

    @staticmethod
    def new_func(name, args, rettype):
        inst = DFunc()
        inst.name = name
        inst.args = args
        inst.rettype = rettype
        inst.is_complete = False # this function lacks code and can't be called
        return inst

    def set_code(self, bytecode, bytecode_info, data, vars):
        # the bytecode instructions
        self.bytecode = bytecode
        # bytecode annotations like source line number
        self.bytecode_info = bytecode_info
        # data registers
        self.data = data
        # name to data register binding dict
        self.vars = vars
        # this function is now a complete function object
        self.is_complete = True

    def get_return_type_name(self):
        return self.rettype[len(self.rettype) - 1]

    def mkdatareg(self, args):
        """
        Takes the arguments to the function and returns a fresh copy of a data array
        suitable for Frame.data registers.
        """
        if self.is_complete == False:
            raise ValueError("Cannot call mkdata on incomplete function")

        assert type(args) is DList

        # make a copy of the function registers that will be the "register" stack during execution
        framedata = [DNull()] * len(self.data)
        make_sure_not_resized(framedata)
        for i, val in enumerate(self.data):
            framedata[i] = val.copy()

        # populate function argument values
        if args.len_py() != len(self.args):
            raise ValueError("Wrong number of arguments passed to function %s" % self.name)
        for i in range(len(self.args)):
            name, fulltype = self.args[i]
            framedata[i] = args.getitem_pyidx(i)

        return framedata

    def operator_bool(self, op, other):
        if not isinstance(other, DFunc):
            return False
        elif op == "==":
            return self == other
        elif op == "!=":
            return self != other
        else:
            raise ValueError("Unimplemented operator_bool %s on type %s" % (op, self.typename))

    def repr_py(self):
        return "<%s: %s>" % (self.basetype, self.name)

    def toString(self):
        bc = []
        for i, (inst, a, b, c) in enumerate(self.bytecode):
            args = []
            for val in [a, b, c]:
                if val != -1:
                    args.append(str(val))

            instname = INST_STRS[inst]
            argnames = ", ".join(args)
            comment = self.bytecode_info[i].comment
            if len(comment) > 0:
                comment = " # %s" % comment
            bc.append("    %s : %s (%s)%s" % (i, instname, argnames, comment))

        # make reverse references
        vars_rev = {}
        for key, val in self.vars.items():
            vars_rev[val] = key

        data = []
        for i, obj in enumerate(self.data):
            name = ""
            if i in vars_rev:
                name = " (bound to name: %s)" % vars_rev[i]
            data.append("    %s : %s%s" % (i, obj.repr_py(), name))

        return "bytecode:\n%s\ndata:\n%s" % ("\n".join(bc), "\n".join(data))


class StructDef(object):
    """
    Struct type defintion
    """
    def __init__(self, name, numfields):
        if not we_are_translated():
            assert type(name) is str
            assert type(numfields) is int
        self.name = name
        self.numfields = numfields
        self.fielddefs = OrderedDict()

    def setfield(self, name, newtype):
        if not we_are_translated():
            assert type(name) is str
            assert issubclass(newtype, DBase)
        self.fielddefs[name] = newtype

    def mkinst(self):
        if self.numfields <= 0:
            raise ValueError("Empty struct or invalid field count")
        if len(fielddefs) != self.numfields:
            raise ValueError("Cannot instantiate a partially defined struct")
        return DStructInstance(self)

    def repr_py(self):
        return "<StructDef: %s>" % self.name


class DStructInstance(DBase):
    """
    Instance of struct
    """
    typename = "struct"
    hashable = True # maybe - depends on contained types
    numeric = False

    #def __init__(self):
    #    self.set_structdef(StructDef("empty", 0))

    @staticmethod
    def new_struct(structdef):
        inst = DStructInstance()
        inst.set_structdef(structdef)
        return inst

    def set_structdef(self, structdef):
        assert isinstance(structdef, StructDef)
        self.structdef = structdef
        self.typename = structdef.name
        # struct data:
        self.fields = [DNull()] * structdef.numfields
        make_sure_not_resized(self.fields)
        # struct name lookup dict:
        self.fieldnames = OrderedDict()
        # populate fields and fieldnames with data from the StructDef
        for i, (name, FieldCls) in enumerate(structdef.fielddefs.items()):
            self.fields[i] = FieldCls()
            self.fieldnames[name] = i
        # calculate if this type is hashable (eg, if all contained types are):
        self.hashable = True
        for val in self.fields:
            if val.hashable == False:
                self.hashable = False
                break

    def copy(self):
        inst = DStructInstance.new_struct(self.structdef)
        for i, val in enumerate(self.fields):
            inst.fields[i] = val.copy()
        return inst

    def assign_list(self, vals):
        assert isinstance(vals, DList)
        if self.structdef.numfields != vals.len_py():
            raise ValueError("Cannot assign list to struct: argument count doesn't "
                "match field count.")
        for i in range(vals.len_py()):
            self.fields[i] = vals.getitem_pyidx(i)

    def typecmp_py(self, other):
        assert isinstance(other, DBase)
        if isinstance(other, DStructInstance) and other.structdef == self.structdef:
            return True
        return False

    def repr_py(self):
        vals = []
        for name, i in self.fieldnames.items():
            vals.append("%s=%s" % (name, self.fields[i].repr_py()))
        return "<%s: %s>" % (self.typename, ", ".join(vals))

    def str_py(self):
        vals = []
        for name, i in self.fieldnames.items():
            vals.append("%s=%s" % (name, self.fields[i].str_py()))
        return "{ %s }" % ", ".join(vals)

    def hash_py(self):
        if self.hashable:
            h = 0
            for val in self.fields:
                h += val.hash_py()
            return int(h / len(self.fields))
        else:
            raise ValueError("This struct cannot be hashed because it contains unhashable types.")

    def getattr_py(self, name):
        if not we_are_translated():
            assert type(name) is str
        idx = self.fieldnames[name]
        return self.fields[idx]

    def setattr_py(self, name, val):
        if not we_are_translated():
            assert type(name) is str
        idx = self.fieldnames[name]
        if val.typecmp_py(self.fields[idx]):
            self.fields[idx] = val
        else:
            raise TypeError("Cannot assign a new value to field '%s.%s' - "
                "new type '%s' doesn't match old type '%s'." % (
                    self.typename, name, val.typename, self.fields[idx].typename))

    def getattr(self, name):
        assert isinstance(name, DString)
        return self.getattr_py(name.str_py())

    def setattr(self, name, val):
        assert isinstance(name, DString)
        return self.setattr_py(name.str_py(), val)

    def __getitem__(self, name):
        return self.getitem_py(name)

    def __setitem__(self, name, val):
        self.setitem_py(name, val)


class DList(DBase):
    """
    Untyped array object
    """
    typename = "list"
    hashable = False
    numeric = False

    def __init__(self):
        self._list = []

    @staticmethod
    def new_list(vals):
        inst = DList()
        for val in vals:
            inst.append(val)
        return inst

    def copy(self):
        newlist = DList()
        for item in self._list:
            newlist._list.append(item.copy())
        return newlist

    def operator_bool(self, op, other):
        if not isinstance(other, DList):
            return False
        elif op == "==":
            if len(self._list) != other.len_py():
                return False
            else:
                for i in range(len(self._list)):
                    if self._list[i].operator_bool("!=", other.getitem_pyidx(i)):
                        return False
                return True
        elif op == "!=":
            if len(self._list) == other.len_py():
                return False
            else:
                for i in range(len(self._list)):
                    if self._list[i].operator_bool("==", other.getitem_pyidx(i)):
                        return False
                return True
        else:
            raise ValueError("Unimplemented operator_bool %s on type %s" % (op, self.typename))

    def getitem(self, idx):
        assert isinstance(idx, DInteger)
        return self._list[idx.int_py()]

    def getitem_pyidx(self, idx):
        if not we_are_translated():
            assert type(idx) is int
        return self._list[idx]

    def setitem(self, idx, val):
        assert isinstance(idx, DInteger)
        assert isinstance(val, DBase)
        self._list[idx.int_py()] = val

    def setitem_pyidx(self, idx, val):
        if not we_are_translated():
            assert type(idx) is int
        assert isinstance(val, DBase)
        self._list[idx] = val

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

    def __getitem__(self, name):
        return self.getitem_pyidx(name)

    def __setitem__(self, name, val):
        self.setitem_pyidx(name, val)


#class DArray(DBase):
#    """
#    Typed array object
#    """
#    typename = "array"
#    hashable = False
#
#    def __init__(self, listtype):
#        self._array = []
#        self._type = listtype
#
#    def copy(self):
#        newlist = DList()
#        for item in self._array:
#            newlist.append(item.copy())
#        return newlist
#
#    def operator(self, op, other):
#        if we_are_translated():
#            assert type(other) is DArray
#        if not self._type == other._type:
#            raise TypeError("Cannot use operators on two arrays of different types (%s and %s)" % (
#                self._type, other._type))
#        if op == "+":
#            newarr = DArray(self._type)
#            for item in self._array:
#                newarr._array.append(item)
#            for item in other._array:
#                newarr._array.append(item)
#            return newarr
#        else:
#            raise ValueError("Invalid operator %s" % op)
#
#    def getitem(self, idx):
#        return self._array[idx.int_py()]
#
#    def setitem(self, idx, val):
#        self._array[idx.int_py()] = val
#
#    def append(self, item):
#        if not we_are_translated():
#            assert isinstance(item, DBase)
#        if type(item) is self._type:
#            self._array.append(item)
#        else:
#            raise TypeError("Cannot add %s to array of type %s" % (item, self._type))
#
#    def pop(self, idx):
#        if not we_are_translated():
#            assert type(idx) is DInteger
#        return self.val.pop(idx.int_py())
#
#    def len_py(self):
#        return len(self._array)
#
#    def str_py(self):
#        items = []
#        for v in self._array:
#            items.append(v.str_py())
#        return "[%s]" % ", ".join(items)


#class DObject(DBase):
#    typename = "obj"
#    hashable = False
#
#    def __init__(self, type, fields):
#        self.type = type
#        self.val = {}
#        for name in fields:
#            self.val[name] = None
#
#    def setattr(self, attr, val):
#        if attr not in self.val:
#            raise KeyError(attr)
#        self.val[attr] = val
#
#    def getattr(self, attr):
#        return self.val[attr]
