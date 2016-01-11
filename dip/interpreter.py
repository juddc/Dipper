import os
from rpython.rlib.objectmodel import we_are_translated
from typesystem import DBase, DNull, DInteger, DFloat, DString, DList


class Stream(object):
    """
    Class that emulates the standard Python sys.stdout/in/err only using
    the ``os`` module.
    """
    STDIN = 0
    STDOUT = 1
    STDERR = 2

    def __init__(self, stream):
        self.stream = stream

    def write(self, val):
        os.write(self.stream, val)

    def read(self):
        res = ""
        while True:
            buf = os.read(self.stream, 16)
            if not buf:
                return res
            else:
                res += buf
        return os.read(self.stream, numbytes)

    def readline(self):
        res = ""
        while True:
            buf = os.read(self.stream, 16)
            if not buf:
                return res
            res += buf
            if res[-1] == "\n":
                return res[:-1]

# VM instructions
INSTRUCTION_SET = [
    'PASS',
    'LABEL',
    'CALL',
    'BT',
    'BF',
    'BEQ',
    'BNE',
    'JMP',
    'RET',
    'ADD',
    'SUB',
    'MUL',
    'DIV',
    'SQRT',
    'LEN',
    'EQ',
    'NEQ',
    'GT',
    'LT',
    'GTE',
    'LTE',
    'EXIT',
    'WRITEI',
    'WRITEO',
    'WRITENL',
    'LIST_NEW',
    'LIST_ADD',
    'LIST_REM',
    'LIST_POP',
]

# dict of instructions to their int codes:
INST = {}

# reverse dict of strings to ints
INST_STRS = {}

for i, inst in enumerate(INSTRUCTION_SET):
    globals()[inst] = i
    INST[inst] = i
    INST_STRS[i] = inst


class Frame(object):
    def __init__(self, bytecode, data, varnames):
        self.bytecode = bytecode

        # data registers
        self.data = data

        # variable names
        self.vars = varnames

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
            bc.append("    %s : %s (%s)" % (i, instname, argnames))

        data = []
        for i, obj in enumerate(self.data):
            name = ""
            if i in self.vars:
                name = " (name: %s)" % self.vars[i]
            data.append("    %s : %s%s" % (i, repr(obj), name))

        return "bytecode:\n%s\ndata:\n%s" % ("\n".join(bc), "\n".join(data))

    def __str__(self):
        return self.toString()


class VirtualMachine(object):
    def __init__(self, args, cb=None, debug=False):
        self.debug = debug

        self.args = args

        self.fn = {}
        # callback for extracting the return value from unit tests
        self.cb = cb

    def addfunc(self, compiler):
        self.fn[compiler.name] = compiler

    def run(self):
        debug = self.debug

        # keep a reference to null handy so we don't have to keep creating new ones
        null = DNull()

        callstack = []

        # add main function to callstack
        if 'main' in self.fn:
            if self.fn['main'].argcount() == 1:
                argv = DList()
                for v in self.args:
                    argv.append(DString(v))
                callstack.append(self.fn['main'].mkframe(argv))
            elif self.fn['main'].argcount() == 0:
                callstack.append(self.fn['main'].mkframe(DList()))
            else:
                raise ValueError("Main function must accept zero or one arguments")
        else:
            print "No main function, exiting"
            return

        while True:
            frame = callstack[-1]

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
                    print "    ", i, ":", obj

            if inst == JMP:
                assert a >= 0 and a < len(frame.bytecode)
                frame.ptr = a
                continue

            elif inst == ADD:
                data[c] = data[a].operator('+', data[b])

            elif inst == SUB:
                data[c] = data[a].operator('-', data[b])

            elif inst == MUL:
                data[c] = data[a].operator('*', data[b])

            elif inst == DIV:
                data[c] = data[a].operator('/', data[b])

            elif inst == SQRT:
                data[b].assign_float(data[a].sqrt_py())

            elif inst == LEN:
                data[b].assign_int(data[a].len_py())

            elif inst == EQ:
                data[c] = data[a].operator('==', data[b])

            elif inst == NEQ:
                data[c] = data[a].operator('!=', data[b])

            elif inst == GT:
                data[c] = data[a].operator('>', data[b])

            elif inst == LT:
                data[c] = data[a].operator('<', data[b])

            elif inst == GTE:
                data[c] = data[a].operator('>=', data[b])

            elif inst == LTE:
                data[c] = data[a].operator('<=', data[b])

            elif inst == CALL:
                frame.ret = c
                funcname = data[a]
                assert type(funcname) is DString
                assert funcname.len_py() > 0
                callstack.append(self.fn[funcname.str_py()].mkframe(data[b]))

                # guard against crazy
                if len(callstack) > 500000:
                    print "Error: callstack size over 500,000"
                    break
                    #sys.exit(1)

                if debug:
                    print "------- call %s ------- (stacksize: %s)" % (a, len(callstack))

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
                if data[a].operator('!=', data[b]):
                    frame.ptr = c
                    continue

            elif inst == BEQ:
                assert c >= 0 and c < len(frame.bytecode)
                assert isinstance(data[a], DBase)
                if data[a].operator('==', data[b]):
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
                callstack.pop(-1)
                if len(callstack) == 0:
                    if debug:
                        print "Exit: return called from main"
                    if self.cb is not None:
                        self.cb(data[a])
                    break
                nextframe = callstack[-1]

                assert isinstance(data[a], DBase)

                # if we have a return value, let the next frame know about it
                if a >= 0:
                    nextframe.data[nextframe.ret] = data[a]

                # otherwise return null
                else:
                    nextframe.data[nextframe.ret] = null

                if debug:
                    print "------- return ------- (stacksize: %s)" % len(callstack)
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


def execute(code, data=None):
    vm = VirtualMachine()
    bytecode = parseBytecodeString(code)
    frame = Frame(bytecode, data, {})
    vm.push(frame)
    vm.run()


if __name__ == '__main__':
    execute("""
        LIST_NEW   0
        LIST_ADD   0    1
        LIST_ADD   0    2
        LIST_LEN   0    4
        LIST_POP   0    0    3
        WRITEO     0    0
        WRITENL    0
        RET
    """, [
        DNull(),       # data 0, list
        DInteger(2),   # data 1, A
        DInteger(4),   # data 2, B
        DInteger(),    # data 3, list 0, popped
        DInteger(),    # data 4, list 0 length
    ])

    execute("""
        ADD        0      1      2       # 0    data2 = data0 + data1
        WRITEO     0      2              # 1    stdout.write(data2)
        WRITENL    0                     # 2    stdout.write(newline)
        RET                              # 3    return
    """, [
        DInteger(32),  # data 0
        DInteger(64),  # data 1
        DInteger()],   # data 2
    )

    execute("""
        BNE       1      2      2       # 0    if data1 != data2: goto 2
        RET                             # 1    return
        ADD       0      1      1       # 2    data1 = data0 + data1
        WRITEO    0      1              # 3    stdout.write(data1)
        WRITENL   0                     # 4    stdout.write(newline)
        PASS      0                     # 5    no-op
        JMP       0                     # 6    goto 0
    """, [
        DInteger(1),    # data 0
        DInteger(32),   # data 1
        DInteger(64),   # data 2
    ])

    execute("""
        MUL     0    1    0        # data0 * data1 = data0
        ADD     2    0    2        # data2 + data0 = data2
        ADD     2    3    2        # data2 + data3 = data2
        WRITEO  0    2             # stdout.write(data2)
        RET                        # return
    """, [
        DFloat(0.123),   # data 0
        DFloat(0.450),   # data 1
        DString(),       # data 2
        DString("\n"),   # data 3
    ])
