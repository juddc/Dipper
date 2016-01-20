"""
Dipper entry-point script
"""
import sys
sys.path.insert(0, "./pypy-source")

import os

try:
    from rpython.rlib.objectmodel import we_are_translated
except ImportError:
    def we_are_translated():
        return False

from dip import parser, compiler, interpreter, basicio
from dip.errors import error_message, error_from_exception
from dip.namespace import Module


def main(argv):
    argc = len(argv)

    # debugging flags
    debug = 0
    debug_parser = False
    debug_compiler = False
    debug_interpreter = False

    if argc == 1:
        print "Usage: %s [-pci] <filename>.dip\n" % argv[0]
        print "    -p: Debug parser/ast"
        print "    -c: Debug compiler/bytecode"
        print "    -i: Debug interpreter/execution"
        return 1
    elif argc == 2:
        debug = 0
        filename = argv[1]
        dip_args = []
    else:
        assert argc > 2
        if argv[1].startswith("-"):
            # figure out debug flags based on the first argument
            for ch in argv[1]:
                if ch == "p":
                    debug_parser = True
                if ch == "c":
                    debug_compiler = True
                elif ch == "i":
                    debug_interpreter = True
            filename = argv[2]
            dip_args = argv[2:]
        else:
            filename = argv[1]
            dip_args = argv[1:]

    if not os.path.exists(filename):
        print "Specified file '%s' does not exist." % filename
        return 1

    # read in the file contents
    data = basicio.readall(filename)

    # create a parser
    dip = parser.DipperParser(debug=debug_parser)

    # just a debugging step so we can see the same input the parser sees
    #print "=============== code ==================="
    #print ">>> Source code (after small preprocessing step) <<<"
    #print dip._prepSource(data)

    if debug_parser > 0:
        print "============== parsing ================="

    try:
        tree = dip.parse(data, filename=filename)
    except Exception as e:
        print "Error parsing file '%s': %s" % (filename, str(e))
        return 1

    if tree is None:
        print "Error parsing file '%s'" % filename
        return 1

    if debug_parser:
        print ">>> AST <<<"
        print tree.show()

    if debug_compiler:
        print "============= compiling ================"

    vm = interpreter.VirtualMachine(dip_args, debug=debug_interpreter)

    mainmodule = Module.from_ast(filename, "main", tree)

    if debug_compiler:
        print mainmodule.toString()
        for name, func in mainmodule.funcs.items():
            print
            print "___ Function '%s' ___" % name
            print func.toString()

    vm.setglobals(mainmodule)

    if debug_parser or debug_compiler or debug_interpreter:
        print "============= executing ================"

    try:
        vm.run()

    except interpreter.InterpreterError as e:
        print error_message(filename, e.getsource(), e.getmessage())
        return 1

    except Exception as e:
        print error_from_exception(filename, (-1, -1), e)
        raise

    return 0


def target(driver, args):
    return main, None


if we_are_translated():
    from rpython.jit.codewriter.policy import JitPolicy

    def jitpolicy(driver):
        return JitPolicy()


# this only runs if the script is being run from a regular Python interpreter,
# so just call the RPython main function
if __name__ == '__main__':
    main(sys.argv)
