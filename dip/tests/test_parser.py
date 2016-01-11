import sys
sys.path.insert(0, "../")

import unittest
from dip.typesystem import DNull, DBool, DInteger, DString, DList
from dip.parser import DipperParser
from dip.compiler import FrameCompiler
from dip.interpreter import VirtualMachine


class TestParser(unittest.TestCase):
    def _execute_simple(self, code):
        result = [None]
        def getresult(val):
            result[0] = val
        vm = VirtualMachine(getresult)
        parser = DipperParser()
        tree = parser.parse(code)
        for node in tree:
            assert node.type == "Function"
            vm.addfunc(FrameCompiler(node))
        vm.run()
        return result[0]

    def test_simple(self):
        pass
        #result = self._execute_simple("""
        #fn main() {
        #    return 0
        #}
        #""")
        #self.assertEqual(result.val, 0)


if __name__ == '__main__':
    unittest.main()