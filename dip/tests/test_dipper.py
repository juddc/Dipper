import sys
sys.path.insert(0, "../")

import unittest
from dip.typesystem import DNull, DBool, DInteger, DString, DList
from dip.parser import DipperParser
from dip.compiler import FrameCompiler
from dip.interpreter import VirtualMachine
from dip.namespace import Namespace


class TestDipper(unittest.TestCase):
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
        result = self._execute_simple("""
        fn main() {
            return 0
        }
        """)
        self.assertEqual(result.int_py(), 0)


    def test_add_consts(self):
        result = self._execute_simple("""
        fn main() {
            return 5 + 5
        }
        """)
        self.assertEqual(result.int_py(), 10)


    def test_add_vars(self):
        result = self._execute_simple("""
        fn main() {
            x = 5
            y = 5
            return x + y
        }
        """)
        self.assertEqual(result.int_py(), 10)


    def test_sub_consts(self):
        result = self._execute_simple("""
        fn main() {
            return 5 - 4
        }
        """)
        self.assertEqual(result.int_py(), 1)


    def test_sub_vars(self):
        result = self._execute_simple("""
        fn main() {
            x = 5
            y = 4
            return x - y
        }
        """)
        self.assertEqual(result.int_py(), 1)


    def test_mul_consts(self):
        result = self._execute_simple("""
        fn main() {
            return 2 * 3
        }
        """)
        self.assertEqual(result.int_py(), 6)


    def test_mul_vars(self):
        result = self._execute_simple("""
        fn main() {
            x = 2
            y = 3
            return x * y
        }
        """)
        self.assertEqual(result.int_py(), 6)


    def test_div_consts(self):
        result = self._execute_simple("""
        fn main() {
            return 6 / 3
        }
        """)
        self.assertEqual(result.int_py(), 2)


    def test_div_vars(self):
        result = self._execute_simple("""
        fn main() {
            x = 6
            y = 3
            return x / y
        }
        """)
        self.assertEqual(result.int_py(), 2)


    def test_sqrt_int(self):
        result = self._execute_simple("""
        fn main() {
            x : int = 4
            return sqrt(x)
        }
        """)
        self.assertEqual(result.float_py(), 2.0)


    def test_sqrt_float(self):
        result = self._execute_simple("""
        fn main() {
            x : float = 4.0
            return sqrt(x)
        }
        """)
        self.assertEqual(result.float_py(), 2.0)

    def test_eq(self):
        result = self._execute_simple("""
        fn main() {
            x = 4
            return 4 == x
        }
        """)
        self.assertEqual(result.bool_py(), True)


    def test_neq(self):
        result = self._execute_simple("""
        fn main() {
            x = 4
            return 4 != x
        }
        """)
        self.assertEqual(result.bool_py(), False)


    def test_strings(self):
        result = self._execute_simple("""
        fn main() {
            x = "a"
            return x + "b"
        }
        """)
        self.assertEqual(result.str_py(), "ab")

        result = self._execute_simple("""
        fn main() {
            x = "abcd"
            return len(x) == 4
        }
        """)
        self.assertEqual(result.bool_py(), True)

        result = self._execute_simple("""
        fn main() {
            x = "abcd"
            return len(x + "zzzz") == 8
        }
        """)
        self.assertEqual(result.bool_py(), True)


    def test_if(self):
        result = self._execute_simple("""
        fn main() {
            x = 10
            if x > 20 {
                return x
            }
            else {
                return x + 10
            }
        }
        """)
        self.assertEqual(result.int_py(), 20)


    def test_elif(self):
        result = self._execute_simple("""
        fn main() {
            x = 10
            if x > 20 {
                return x
            }
            elif x > 15 {
                return 2
            }
            elif x > 11 {
                return 3
            }
            elif x == 10 {
                return 999
            }
            else {
                return x + 10
            }
        }
        """)
        self.assertEqual(result.int_py(), 999)


    def test_func(self):
        result = self._execute_simple("""
        fn add(x, y) {
            return x + y
        }
        fn main() {
            return add(5, 5)
        }
        """)
        self.assertEqual(result.int_py(), 10)


    def test_recursion(self):
        result = self._execute_simple("""
        fn fib(n) {
            if n < 2 { return n }
            return fib(n - 2) + fib(n - 1)
        }
        fn main() {
            return fib(10)
        }
        """)
        self.assertEqual(result.int_py(), 55)


    # TODO: implement for loops
    #def test_for_loop(self):
    #    result = self._execute_simple("""
    #    fn main() {
    #        x = 10
    #        for i in 0..10 {
    #            x += 1
    #        }
    #        return x
    #    }
    #    """)
    #    self.assertEqual(result.int_py(), 20)


    # TODO: implement while loops
    #def test_for_loop(self):
    #    result = self._execute_simple("""
    #    fn main() {
    #        x = 10
    #        while x < 20 {
    #            x += 1
    #        }
    #        return x
    #    }
    #    """)
    #    self.assertEqual(result.int_py(), 20)


    def test_docstrings(self):
        result = self._execute_simple("""
        fn main() {
            | "this is a docstring of sorts"
            | "this is also a docstring"
            x = 10
            x += 2
            return x
        }
        """)
        self.assertEqual(result.int_py(), 12)


    def test_goofy_syntax(self):
        result = self._execute_simple("""
        fn add1(x : int, y : int) {
            result : int = x
            x += y
            return result
        }
        fn !add2(x, y) { return add1(x, y) }
        fn main() {
            return !add2(2, 2)
        }
        """)
        self.assertEqual(result.int_py(), 4)


    # TODO: implement if expressions
    #def test_if_expressions(self):
    #    result = self._execute_simple("""
    #    fn main() {
    #        x = 10
    #        x += 2
    #        return if x > 5 { 20 } else { 30 }
    #    }
    #    """)
    #    self.assertEqual(result.int_py(), 30)


if __name__ == '__main__':
    unittest.main()