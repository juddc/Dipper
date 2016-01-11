"""
Implementation of builtin functions.
"""
from rpython.rlib.objectmodel import we_are_translated
import dip.typesystem as types


class NativeFunction(object):
    argcount = 0

    def __init__(self, args):
        if not we_are_translated():
            assert type(args) is list
        if len(args) != self.argcount:
            raise Exception("Invalid number of arguments for %s" %
                self.__class__.__name__)
        self.args = args

    def compile(self, ctx):
        return -1


class Len(NativeFunction):
    argcount = 1

    def compile(self, ctx):
        expridx = self.args[0].compile(ctx)
        resultidx = ctx.pushobj(types.DInteger())
        ctx.emit_LEN(expridx, resultidx)
        return resultidx


class Sqrt(NativeFunction):
    argcount = 1

    def compile(self, ctx):
        expridx = self.args[0].compile(ctx)
        resultidx = ctx.pushobj(types.DFloat())
        ctx.emit_SQRT(expridx, resultidx)
        return resultidx


#
# Dictionary of dipper builtin function names to their NativeFunction handler class.
# If you add a new NativeFunction class, you MUST add it to this dictionary.
#
builtins = {
    "len": Len,
    "sqrt": Sqrt,
}

#
# builtins API
#
def has_builtin(funcname):
    return funcname in builtins

def get_builtin(funcname):
    return builtins[funcname]
