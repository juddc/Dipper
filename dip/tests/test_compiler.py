import sys
sys.path.insert(0, "../")

import unittest
from dip.typesystem import DNull, DBool, DInteger, DString, DList
from dip.parser import DipperParser
from dip.compiler import FrameCompiler
from dip.interpreter import VirtualMachine


class TestCompiler(unittest.TestCase):
    def _execute_simple(self, code):
        result = [None]
        def getresult(val):
            result[0] = val
        vm = VirtualMachine(getresult)
        parser = DipperParser()
        astnode = parser.parse(code)
        ctx = FrameCompiler(astnode)
        vm.addfunc(ctx)
        vm.run()
        return result[0]

    def test_simple(self):
        pass


if __name__ == '__main__':
    unittest.main()