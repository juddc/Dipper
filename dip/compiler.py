"""
Dipper bytecode compilers
"""
from rpython.rlib.objectmodel import we_are_translated

from interpreter import Frame
from bytecode import BytecodeAnnotation, INSTRUCTION_SET, INST, INST_STRS
from basicio import Stream
from namespace import Namespace
import typesystem as types
from common import CompileError


class Compiler(object):
    """
    Abstract compiler interface
    """
    def __init__(self, namespace=None):
        if namespace is not None:
            assert isinstance(namespace, Namespace)
            self.namespace = namespace
        else:
            self.namespace = Namespace("unknown")

    def mkfunc(self):
        """
        Returns a DFunc object representing the compiled function
        """
        return types.DFunc()


class BytecodeCompiler(Compiler):
    """
    Compiles text that represents raw bytecode

    Example:
        BytecodeCompiler("main", "ADD 0 1 2\nRET 2", [
            DInteger(32), DInteger(64), DInteger()])

    Strings:
        Starts with a colon, no spaces allowed.
        CALL :some_func
        LABEL :if_block

    """
    def __init__(self, name, code, data, namespace=None):
        Compiler.__init__(self, namespace=namespace)
        self.name = name
        self.bytecode = self._parse(code)
        self.data = data
        self.vars = {}

    def mkframe(self, args):
        if not we_are_translated():
            assert args is None or isinstance(args, types.DList)
        data = [ val.copy() if val is not None else None for val in self.data ]
        return Frame(self.name, self.bytecode, data, self.vars.copy())

    def mkfunc(self):
        """
        Returns a DFunc object representing the compiled function
        """
        fn = types.DFunc.new_func(self.name, [], "int")
        funcargs = []
        fn.set_code(self.bytecode, [], self.data, self.vars)
        return fn

    def _parse(self, code):
        bc = []
        for line in code.split("\n"):
            line = line.strip()
            if not line:
                continue
            elif line.startswith("#"):
                continue
            line = line.split("#")[0]
            parts = [ part.strip() for part in line.split(" ") if len(part.strip()) > 0 ]

            inst = parts[0]
            a = -1
            b = -1
            c = -1

            if len(parts) >= 2:
                a = parts[1]
            if len(parts) >= 3:
                b = parts[2]
            if len(parts) >= 4:
                c = parts[3]

            def convert(val):
                if isinstance(val, str) and val.startswith(":"):
                    return val[1:]
                else:
                    return int(val)

            bc.append( (INST[inst.upper()], convert(a), convert(b), convert(c)) )
        return bc


class FrameCompiler(Compiler):
    """
    Compiles an AST to bytecode
    """
    # These are just here so that the AST code that calls into this class have an easy
    # way to get at the stream indices by name without any extra imports
    STDOUT = Stream.STDOUT
    STDIN = Stream.STDIN
    STDERR = Stream.STDERR

    def __init__(self, filename, astnode, namespace=None):
        Compiler.__init__(self, namespace=namespace)

        if not we_are_translated():
            assert type(astnode.name) is str

            # sanity check to make sure we're covering all instructions
            for inst in INSTRUCTION_SET:
                if not hasattr(self, "emit_%s" % inst):
                    raise AssertionError("FrameCompiler lacks a emit_%s() method" % inst)

        # source filename
        self.filename = filename

        # root astnode we're compiling
        self.astnode = astnode
        
        # name of the root ast node. usually the function name
        self.name = astnode.name

        # actual bytecode storage
        self.bytecode = []

        # bytecode annotations like source file and line number
        self._current_node = None
        self.bytecode_info = []

        self.data = []
        self.vars = {}

        # keep a ref to null around so we don't have to keep recreating it
        self.null = types.DNull()

        # hold on to the argument data indices for ease of plugging in argument values
        self.argIdx = []

        if astnode.type == "Function":
            for arg in astnode.args:
                self.data.append(types.AutoType(arg.getType())())
                idx = len(self.data) - 1
                self.argIdx.append(idx)
                self.register_var(arg.getName(), idx)

        self.astnode.compile(self)

    def mkfunc(self):
        """
        Returns a DFunc object representing the compiled function
        """
        assert self.astnode.type == "Function"
        fn = self.astnode.mkprototype()
        fn.set_code(self.bytecode, self.bytecode_info, self.data, self.vars)
        return fn

    def pushobj(self, val):
        assert isinstance(val, types.DBase)
        self.data.append(val)
        return len(self.data) - 1

    def pushnull(self):
        """
        Same thing as pushobj, but pushes a null object, generally used as a placeholder
        for something like a return value.
        """
        self.data.append(self.null)
        return len(self.data) - 1

    def setbranch(self, instptr, newptr):
        vals = list(self.bytecode[instptr])
        inst = vals[0]
        if inst in (INST['BT'], INST['BF']):
            vals[2] = newptr
        elif inst in (INST['BNE'], INST['BEQ']):
            vals[3] = newptr
        elif inst == INST['JMP']:
            vals[1] = newptr
        else:
            raise ValueError("Unsupported instruction for setbranch (%s)" % INST_STRS[inst])
        self.bytecode[instptr] = (vals[0], vals[1], vals[2], vals[3])

    def currentptr(self):
        return len(self.bytecode) - 1

    def getdataidx(self, name):
        if not we_are_translated():
            assert type(name) is str
        if name in self.vars:
            return self.vars[name]
        else:
            raise CompileError("Variable '%s' not defined" % name)

    def register_var(self, name, dataidx):
        if not we_are_translated():
            assert type(name) is str
        self.vars[name] = dataidx

    def is_int(self, dataidx):
        """ Simple helper for typechecking data registers """
        return isinstance(self.data[dataidx], types.DInteger)

    def is_float(self, dataidx):
        """ Simple helper for typechecking data registers """
        return isinstance(self.data[dataidx], types.DFloat)

    def is_str(self, dataidx):
        """ Simple helper for typechecking data registers """
        return isinstance(self.data[dataidx], types.DString)

    def is_type(self, dataidx, datatype):
        """ Simple helper for typechecking data registers """
        return isinstance(self.data[dataidx], datatype)

    def start_node(self, node):
        self._current_node = node

    def emit(self, opcode, a=-1, b=-1, c=-1, comment=""):
        self.bytecode.append( (INST[opcode], a, b, c) )
        self.bytecode_info.append(BytecodeAnnotation(self.filename, self._current_node.source, comment=comment))
        # return the instruction pointer location for the emitted inst
        return self.currentptr()

    def emit_PASS(self):
        return self.emit('PASS')

    def emit_LABEL(self, label):
        return self.emit('LABEL', comment=label)

    def emit_BT(self, idx, ptr):
        return self.emit('BT', idx, ptr)

    def emit_BF(self, idx, ptr):
        return self.emit('BF', idx, ptr)

    def emit_BEQ(self, a, b, ptr):
        return self.emit('BEQ', a, b, ptr)

    def emit_BNE(self, a, b, ptr):
        return self.emit('BNE', a, b, ptr)

    def emit_JMP(self, ptr):
        return self.emit('JMP', ptr)

    def emit_RET(self, val=-1):
        return self.emit('RET', val)

    def emit_SET(self, src, dest):
        return self.emit('SET', src, dest)

    def emit_ADDI(self, dataidx, val):
        return self.emit('ADDI', dataidx, val)

    def emit_SUBI(self, dataidx, val):
        return self.emit('SUBI', dataidx, val)

    def emit_MULI(self, dataidx, val):
        return self.emit('MULI', dataidx, val)

    def emit_DIVI(self, dataidx, val):
        return self.emit('DIVI', dataidx, val)

    def emit_ADD(self, a, b, dest):
        return self.emit('ADD', a, b, dest)

    def emit_SUB(self, a, b, dest):
        return self.emit('SUB', a, b, dest)

    def emit_MUL(self, a, b, dest):
        return self.emit('MUL', a, b, dest)

    def emit_DIV(self, a, b, dest):
        return self.emit('DIV', a, b, dest)

    def emit_SQRT(self, val, dest):
        return self.emit('SQRT', val, dest)

    def emit_EQ(self, a, b, dest):
        return self.emit('EQ', a, b, dest)

    def emit_NEQ(self, a, b, dest):
        return self.emit('NEQ', a, b, dest)

    def emit_GT(self, a, b, dest):
        return self.emit('GT', a, b, dest)

    def emit_LT(self, a, b, dest):
        return self.emit('LT', a, b, dest)

    def emit_GTE(self, a, b, dest):
        return self.emit('GTE', a, b, dest)

    def emit_LTE(self, a, b, dest):
        return self.emit('LTE', a, b, dest)

    def emit_LEN(self, itemidx, destidx):
        return self.emit('LEN', itemidx, destidx)

    def emit_EXIT(self, code):
        return self.emit('EXIT', code)

    def emit_WRITEI(self, stream, val):
        return self.emit('WRITEI', stream, val)

    def emit_WRITEO(self, stream, dataidx):
        return self.emit('WRITEO', stream, dataidx)

    def emit_WRITENL(self, stream):
        return self.emit('WRITENL', stream)

    def emit_CALL(self, name, argsidx, retidx=-1):
        if not we_are_translated():
            assert type(name) is int
        return self.emit('CALL', name, argsidx, retidx)

    def emit_LIST_NEW(self, idx):
        return self.emit('LIST_NEW', idx)

    def emit_LIST_ADD(self, idx, dataidx):
        return self.emit('LIST_ADD', idx, dataidx)

    def emit_LIST_REM(self, idx, listindex):
        return self.emit('LIST_REM', idx, listindex)

    def emit_LIST_POP(self, idx, listindex, dest):
        return self.emit('LIST_POP', idx, listindex, dest)

    def emit_LIST_LEN(self, idx, dest):
        return self.emit('LIST_LEN', idx, dest)

    def toString(self):
        fakeFrameArgs = types.DList.new_list([types.DNull() for _ in range(len(self.argIdx))])
        fakeFrame = self.mkframe(fakeFrameArgs)
        return "----- %s -----\n%s" % (self.name, fakeFrame.toString())

    def __str__(self):
        return self.toString()
