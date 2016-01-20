from collections import OrderedDict
from rpython.rlib.objectmodel import we_are_translated

import typesystem as types
import errors
import compiler


class Namespace(object):
    UNKNOWN = 0
    CONST = 1
    STRUCT = 2
    FUNC = 3
    NAMESPACE = 4

    def __init__(self, name):
        if not we_are_translated():
            assert type(name) is str
        self.name = name

        self.consts = OrderedDict()
        self.structs = OrderedDict()
        self.funcs = OrderedDict()
        self.namespaces = OrderedDict()

    def set_const(self, name, val):
        if not we_are_translated():
            assert type(name) is str
        assert isinstance(val, types.DBase)
        self.consts[name] = val

    def set_struct(self, name, struct):
        if not we_are_translated():
            assert type(name) is str
        assert isinstance(struct, types.StructDef)
        self.structs[name] = struct

    def set_func(self, name, func):
        if not we_are_translated():
            assert type(name) is str
        assert isinstance(func, types.DFunc)
        self.funcs[name] = func

    def set_namespace(self, name, namespace):
        if not we_are_translated():
            assert type(name) is str
        assert isinstance(namespace, Namespace)
        self.namespaces[name] = namespace

    def get_const(self, name):
        if not we_are_translated():
            assert type(name) is str
        return self.consts[name]

    def get_struct(self, name):
        if not we_are_translated():
            assert type(name) is str
        return self.structs[name]

    def get_func(self, name):
        if not we_are_translated():
            assert type(name) is str
        return self.funcs[name]

    def get_namespace(self, name):
        if not we_are_translated():
            assert type(name) is str
        return self.namespaces[name]

    def get_type(self, name):
        """
        Returns the type of the specified name
        """
        if not we_are_translated():
            assert type(name) is str
        if name in self.consts:
            return self.CONST
        elif name in self.structs:
            return self.STRUCT
        elif name in self.funcs:
            return self.FUNC
        elif name in self.namespaces:
            return self.NAMESPACE
        else:
            return self.UNKNOWN

    def contains_const(self, name):
        return name in self.consts

    def contains_struct(self, name):
        return name in self.structs

    def contains_func(self, name):
        return name in self.funcs

    def contains_namespace(self, name):
        return name in self.namespaces

    def toString(self):
        ns = ["--- Namespace '%s' ---" % self.name]

        if len(self.consts) > 0:
            ns.append("Constants:")
            for name, item in self.consts.items():
                ns.append("    %s = %s" % (name, item.repr_py()))

        if len(self.structs) > 0:
            ns.append("Structs:")
            for name, item in self.structs.items():
                ns.append("    %s = %s" % (name, item.repr_py()))

        if len(self.funcs) > 0:
            ns.append("Functions:")
            for name, item in self.funcs.items():
                ns.append("    %s = %s" % (name, item.repr_py()))

        if len(self.namespaces) > 0:
            ns.append("Namespaces:")
            for name, item in self.namespaces.items():
                ns.append("    %s = %s" % (name, item.repr_py()))

        return "\n".join(ns)


class Module(Namespace):
    @staticmethod
    def from_ast(filename, name, tree):
        module = Module(name)

        # Populate the namespace with all of the top-level objects as a first pass
        # before compiling any code. This way once we do the compilation step,
        # we'll have references to the right types and functions.

        # first pass for prototypes
        for node in tree:
            try:
                if node.type == "Function":
                    module.set_func(node.name, node.mkprototype())
                elif node.type == "Struct":
                    module.set_struct(node.name, node.mkstruct())
                else:
                    raise ValueError("Unhandled top-level node type '%s'" % node.type)
            except Exception as e:
                print errors.error_from_exception(filename, node.source, e)
                raise

        # second pass for function bytecode compilation
        for node in tree:
            try:
                if node.type == "Function":
                    ctx = compiler.FrameCompiler(filename, node, namespace=module)
                    module.set_func(node.name, ctx.mkfunc())
            except Exception as e:
                print errors.error_from_exception(filename, node.source, e)
                raise

        return module


