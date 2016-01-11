"""
Dipper entry-point script
"""
from rpython.rlib.objectmodel import we_are_translated

if we_are_translated():
    from rpython.rlib.streamio import open_file_as_stream
    from rpython.jit.codewriter.policy import JitPolicy

from dip import parser, compiler, interpreter


if we_are_translated():
    def readfile(filename):
        f = open_file_as_stream(argv[1])
        data = f.readall()
        f.close()
else:
    def readfile(filename):
        f = open(argv[1])
        data = f.read()
        f.close()


def main(argv):
    if not len(argv) == 2:
        print "Usage: %s <filename>.dip\n" % argv[0]
        return 1

    data = readfile(argv[1])

    dip = parser.DipperParser(debug=False)

    #print "=============== code ==================="
    # just a debugging step so we can see the same input the parser sees
    #print dip._prepSource(data)

    #print "============== parsing ================="
    tree = dip.parse(data)
    #print tree.show()

    #print "============= compiling ================"

    args = []
    for arg in argv[1:]:
        args.append(arg)

    vm = interpreter.VirtualMachine(args, debug=False)

    for node in tree:
        assert node.type == "Function"
        ctx = compiler.FrameCompiler(node)
        #print ctx
        vm.addfunc(ctx)

    #print "============= executing ================"
    vm.run()

    return 0


if we_are_translated():
    def target(driver, args):
        return main, None

    def jitpolicy(driver):
        return JitPolicy()
        

# this only runs if the script is being run from a regular Python interpreter,
# so just call the RPython main function
if __name__ == '__main__':
    import sys
    main(sys.argv)
