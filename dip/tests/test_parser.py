import sys
sys.path.insert(0, "../")

import unittest
from dip.typesystem import DNull, DBool, DInteger, DString, DList
from dip.parser import DipperParser
from dip.compiler import FrameCompiler
from dip.interpreter import VirtualMachine
from dip.namespace import Namespace


class TestParser(unittest.TestCase):
    def _execute_simple(self, code):
        # set up the global namespace
        globalns = Namespace("globals")
        for node in DipperParser().parse(code):
            if node.type == "Function":
                globalns.add_func(node.name, FrameCompiler(node).mkfunc())
            elif node.type == "Struct":
                globalns.add_struct(node.name, node.mkstruct())
        # set up a hacky way to extract data from the VM via a callback
        result = [None] # we need a mutable object we can put data in
        def getresult(val):
            result[0] = val
        # set up the VM
        vm = VirtualMachine([], cb=getresult, debug=False)
        vm.setglobals(globalns)
        vm.run()
        return result[0]

    def test_simple(self):
        pass


if __name__ == '__main__':
    unittest.main()