from rpython.rlib import jit
from rpython.rlib.objectmodel import we_are_translated

import typesystem as types
from typesystem import DBase, DNull, DInteger, DFloat, DString, DList
from basicio import Stream

jitdriver = jit.JitDriver(greens=['ptr', 'bytecode'], reds="auto")

# make all the bytecode instructions constants in this module's namespace
import bytecode
from bytecode import INST_STRS
for inst in bytecode.INSTRUCTION_SET:
    globals()[inst] = bytecode.INST[inst]


class InterpreterError(Exception):
    def __init__(self, orig_exception, frame, message=""):
        self.orig_exception = orig_exception
        self.frame = frame
        self.message = message

    def getsource(self):
        return self.frame.func.bytecode_info[self.frame.ptr].source

    def getmessage(self):
        bytecode = self.frame.bytecode[self.frame.ptr]
        instline = "%s, %s, %s, %s" % (INST_STRS[bytecode[0]],
            bytecode[1], bytecode[2], bytecode[3])
        msg = ["Error in bytecode line %s (%s) in function %s:" % (
            self.frame.ptr, instline, self.frame.func.name)]

        msg.append("    %s: %s" % (self.orig_exception.__class__.__name__, str(self.orig_exception)))
        
        msg.append("")
        msg.append("Frame:")
        
        for line in self.frame.toString().split("\n"):
            msg.append(line)

        if len(self.message) > 0:
            msg.append(self.message)

        return "\n".join(msg)


class Frame(object):
    def __init__(self, func, dataregs):
        self.func = func

        # bytecode instructions
        self.bytecode = func.bytecode
        # data registers
        self.data = dataregs
        # variable names
        self.vars = func.vars.copy()

        if not we_are_translated():
            assert type(self.bytecode) is list
            assert type(self.data) is list
            assert type(self.vars) is dict

        # return value (data register index)
        self.ret = -1

        # bytecode instruction pointer
        self.ptr = 0

        # make reverse references
        self.vars_rev = {}
        for key, val in self.vars.items():
            self.vars_rev[val] = key

        self.ret = -1

        # streams
        self.streams = []
        self.streams.append(Stream(Stream.STDIN))
        self.streams.append(Stream(Stream.STDOUT))
        self.streams.append(Stream(Stream.STDERR))

    def toString(self):
        bc = []
        for i, (inst, a, b, c) in enumerate(self.bytecode):
            args = []
            for val in [a, b, c]:
                if val != -1:
                    args.append(str(val))

            instname = INST_STRS[inst]
            argnames = ", ".join(args)
            comment = self.func.bytecode_info[i].comment
            if len(comment) > 0:
                comment = " # %s" % comment
            bc.append("    %s : %s (%s)%s" % (i, instname, argnames, comment))

        data = []
        for i, obj in enumerate(self.data):
            name = ""
            if i in self.vars_rev:
                name = " (bound to name: %s)" % self.vars_rev[i]
            data.append("    %s : %s%s" % (i, obj.repr_py(), name))

        return "bytecode:\n%s\ndata:\n%s" % ("\n".join(bc), "\n".join(data))

    def __str__(self):
        return self.toString()


class VirtualMachine(object):
    def __init__(self, args, cb=None, debug=False):
        self.debug = debug
        self.args = args
        self.callstack = []
        # callback for extracting the return value from unit tests
        self.cb = cb

    def setglobals(self, namespace):
        self.globals = namespace

    def callstack_push(self, funcname, args):
        assert isinstance(args, DList)
        func = self.globals.get_func(funcname)
        self.callstack.append(Frame(func, func.mkdatareg(args)))

    def run(self, pass_argv=True):
        debug = self.debug

        # keep a reference to null handy so we don't have to keep creating new ones
        null = DNull()

        # add main function to callstack
        if self.globals.contains_func("main"):
            if pass_argv:
                # construct an array and populate it with argv values
                argv = DList()
                for v in self.args:
                    argv.append(DString.new_str(v))
                mainargs = DList.new_list([argv])
            else:
                mainargs = DList()

            self.callstack_push("main", mainargs)
        else:
            print "No main function, exiting"
            return

        # init the most important loop vars here so we can access them from outside
        # the loop when something goes horribly wrong
        frame = self.callstack[-1]
        data = frame.data

        try:
            while True:
                frame = self.callstack[-1]

                jitdriver.jit_merge_point(ptr=frame.ptr, bytecode=frame.bytecode)

                if len(frame.bytecode) == 0:
                    print "Got empty frame; exiting"
                    break

                data = frame.data

                inst, a, b, c = frame.bytecode[frame.ptr]

                if inst == PASS or inst == LABEL:
                    if debug:
                        print frame.ptr, INST_STRS[inst], a, b, c
                    frame.ptr += 1
                    inst, a, b, c = frame.bytecode[frame.ptr]

                if debug:
                    print frame.ptr, INST_STRS[inst], a, b, c
                    for i, obj in enumerate(data):
                        binding = ""
                        if i in frame.vars_rev:
                            binding = "(bound to: '%s')" % frame.vars_rev[i]
                        print "    ", i, ":", obj.repr_py(), binding

                if inst == JMP:
                    assert a >= 0 and a < len(frame.bytecode)
                    # give the JIT engine a hint that we're about to step backwards
                    if a < frame.ptr:
                        jitdriver.can_enter_jit(ptr=frame.ptr, bytecode=frame.bytecode)
                    frame.ptr = a
                    continue

                # SET instruction:
                #   Sets a value from another value
                #
                #   Arguments:
                #   a = dataidx of source value
                #   b = dataidx of dest value
                elif inst == SET:
                    if isinstance(data[b], types.DInteger):
                        data[b].assign_int(data[a].int_py())
                    elif isinstance(data[b], types.DBool):
                        data[b].assign_bool(data[a].bool_py())
                    elif isinstance(data[b], types.DFloat):
                        data[b].assign_float(data[a].float_py())
                    elif isinstance(data[b], types.DString):
                        data[b].assign_str(data[a].str_py())
                    else:
                        raise TypeError(INST_STRS[inst])

                # ___I instructions:
                #   Adds a hardcoded integer value to a data register in-place
                #
                #   Arguments:
                #   a = dataidx of var to increment
                #   b = integer value to increment with
                elif inst == ADDI:
                    data[a].assign_int(data[a].int_py() + b)
                elif inst == SUBI:
                    data[a].assign_int(data[a].int_py() - b)
                elif inst == MULI:
                    data[a].assign_int(data[a].int_py() * b)
                elif inst == DIVI:
                    data[a].assign_int(data[a].int_py() // b)

                elif inst in (ADD, SUB, MUL, DIV):
                    if isinstance(data[c], types.DInteger):
                        data[c].assign_int(data[a].operator_int(bytecode.OPERATOR_MAP[inst], data[b]))
                    elif isinstance(data[c], types.DFloat):
                        data[c].assign_float(data[a].operator_float(bytecode.OPERATOR_MAP[inst], data[b]))
                    elif isinstance(data[c], types.DString):
                        data[c].assign_str(data[a].operator_str(bytecode.OPERATOR_MAP[inst], data[b]))
                    else:
                        raise TypeError(INST_STRS[inst])

                elif inst == SQRT:
                    data[b].assign_float(data[a].sqrt_py())

                elif inst == LEN:
                    data[b].assign_int(data[a].len_py())

                elif inst in (EQ, NEQ, GT, LT, GTE, LTE):
                    data[c].assign_bool(data[a].operator_bool(bytecode.OPERATOR_MAP[inst], data[b]))

                elif inst == CALL:
                    callable_name = data[a]
                    assert type(callable_name) is DString # func name
                    assert callable_name.len_py() > 0
                    assert isinstance(data[b], DList) # args
                    name = callable_name.str_py()

                    # calling a function
                    if self.globals.contains_func(name):
                        frame.ret = c

                        self.callstack_push(name, data[b])

                        # guard against crazy
                        if len(self.callstack) > 500000:
                            print "Error: callstack size over 500,000"
                            break
                            #sys.exit(1)

                        if debug:
                            print "------- call %s ------- (stacksize: %s)" % (a, len(self.callstack))

                    # init'ing a struct
                    elif self.globals.contains_struct(name):
                        assert isinstance(data[c], types.DStructInstance)
                        assert data[c].structdef == self.globals.get_struct(name)
                        data[c].assign_list(data[b])

                    else:
                        print "Error calling '%s': item cannot be found." % name
                        break

                elif inst == BT:
                    assert b >= 0 and b < len(frame.bytecode)
                    assert isinstance(data[a], DBase)
                    if data[a].bool_py() == True:
                        frame.ptr = b
                        continue

                elif inst == BF:
                    assert b >= 0 and b < len(frame.bytecode)
                    assert isinstance(data[a], DBase)
                    if data[a].bool_py() == False:
                        frame.ptr = b
                        continue

                elif inst == BNE:
                    assert c >= 0 and c < len(frame.bytecode)
                    assert isinstance(data[a], DBase)
                    if data[a].operator_bool('!=', data[b]):
                        frame.ptr = c
                        continue

                elif inst == BEQ:
                    assert c >= 0 and c < len(frame.bytecode)
                    assert isinstance(data[a], DBase)
                    if data[a].operator_bool('==', data[b]):
                        frame.ptr = c
                        continue

                elif inst == WRITEI:
                    assert type(data[b]) is DInteger
                    intval = data[b].int_py()
                    if not we_are_translated():
                        assert type(intval) is int
                    frame.streams[a].write(chr(intval))

                elif inst == WRITEO:
                    frame.streams[a].write(data[b].str_py())

                elif inst == WRITENL:
                    frame.streams[a].write("\n")

                elif inst == RET:
                    self.callstack.pop(-1)
                    if len(self.callstack) == 0:
                        if debug:
                            print "Exit: return called from main"
                        if self.cb is not None:
                            self.cb(data[a])
                        break
                    nextframe = self.callstack[-1]

                    assert isinstance(data[a], DBase)

                    # if we have a return value, let the next frame know about it
                    if a >= 0:
                        nextframe.data[nextframe.ret] = data[a]

                    # otherwise return null
                    else:
                        nextframe.data[nextframe.ret] = null

                    if debug:
                        print "------- return ------- (stacksize: %s)" % len(self.callstack)
                    continue

                elif inst == EXIT:
                    print "Exit: syscall"
                    assert type(data[a]) is DInteger
                    break
                    #sys.exit(data[a].val)

                elif inst == LIST_NEW:
                    data[a] = DList()

                elif inst == LIST_ADD:
                    assert type(data[a]) is DList
                    assert isinstance(data[b], DBase)
                    data[a].append(data[b])

                elif inst == LIST_REM:
                    assert type(data[a]) is DList
                    assert isinstance(data[b], DBase)
                    data[a].pop(data[b])

                elif inst == LIST_POP:
                    assert type(data[a]) is DList
                    assert isinstance(data[b], DBase)
                    data[c] = data[a].pop(data[b])

                frame.ptr += 1

        except Exception as e:
            if not we_are_translated():
                import traceback
                traceback.print_exc()

            if self.cb is None:
                raise InterpreterError(e, frame)
            else:
                raise

