import sys
sys.path.insert(0, "../")

import unittest
from dip.typesystem import DNull, DBool, DInteger, DString, DList
from dip.compiler import BytecodeCompiler
from dip.interpreter import VirtualMachine


class TestInterpreter(unittest.TestCase):
    def _execute_simple(self, code, data, argcount=0):
        result = [None]
        def getresult(val):
            result[0] = val
        vm = VirtualMachine([], getresult)
        ctx = BytecodeCompiler("main", code, data, argcount)
        vm.addfunc(ctx)
        vm.run()
        return result[0]

    def test_add(self):
        result = self._execute_simple("""
            ADD        0      1      2       # 0
            RET        2                     # 1
        """, [
            DInteger(32),  # data0
            DInteger(64),  # data1
            DInteger(),    # data2
        ])
        self.assertEqual(result.int_py(), 96)

    def test_sub(self):
        result = self._execute_simple("""
            SUB        0      1      2       # 0
            RET        2                     # 1
        """, [
            DInteger(64),  # data0
            DInteger(32),  # data1
            DInteger(),    # data2
        ])
        self.assertEqual(result.int_py(), 32)

    def test_mul(self):
        result = self._execute_simple("""
            MUL        0      1      2       # 0
            RET        2                     # 1
        """, [
            DInteger(64),  # data0
            DInteger(32),  # data1
            DInteger(),    # data2
        ])
        self.assertEqual(result.int_py(), 2048)

    def test_div(self):
        result = self._execute_simple("""
            DIV        0      1      2       # 0
            RET        2                     # 1
        """, [
            DInteger(64),  # data0
            DInteger(2),   # data1
            DInteger(),    # data2
        ])
        self.assertEqual(result.int_py(), 32)

    def test_jump(self):
        result = self._execute_simple("""
            JMP        2                     # 0
            RET        0                     # 1
            RET        1                     # 2
        """, [
            DInteger(16),  # data0
            DInteger(32),  # data1
        ])
        self.assertEqual(result.int_py(), 32)

    def test_len(self):
        result = self._execute_simple("""
            LEN        0      1              # 0
            RET        1                     # 1
        """, [
            DString("neat"),     # data0
            DInteger(),          # data1
        ])
        self.assertEqual(result.int_py(), 4)

    def test_eq(self):
        result = self._execute_simple("""
            EQ         0      1      2        # 0
            RET        2                      # 1
        """, [
            DInteger(4),  # data0
            DInteger(5),  # data1
            DNull(),      # data2
        ])
        self.assertEqual(result.int_py(), False)

        result = self._execute_simple("""
            EQ         0      1      2        # 0
            RET        2                      # 1
        """, [
            DString("neat"),  # data0
            DString("neat"),  # data1
            DNull(),          # data2
        ])
        self.assertEqual(result.int_py(), True)

    def test_branch(self):
        result = self._execute_simple("""
            EQ         0      1      2        # 0
            BF         2      3               # 1
            RET        0                      # 2
            LABEL      :some_label            # 3
            RET        3                      # 4
        """, [
            DInteger(4),   # data0
            DInteger(5),   # data1
            DNull(),       # data2
            DInteger(999), # data3
        ])
        self.assertEqual(result.int_py(), 999)

    def test_lists(self):
        result = self._execute_simple("""
            LIST_NEW   0
            LIST_ADD   0      1               # 0   data0.append(data1)
            LIST_ADD   0      1               # 1   data0.append(data1)
            LIST_ADD   0      2               # 2   data0.append(data2)
            LEN        0      3               # 3   data3 = len(data0)
            EQ         3      5      6        # 4   data6 = (data3 == data5)
            LIST_REM   0      4               # 5   data0.remove(data4 (represents an index))
            LEN        0      3               # 6   data3 = len(data0)
            NEQ        3      5      7        # 7   data7 = (data3 != data5)
            EQ         6      7      8        # 8   data8 = (data6 == data7)
            RET        8                      # 9   return data8
        """, [
            DNull(),       # data0, list
            DInteger(5),   # data1, fake value to add to the list
            DString("hi"), # data2, fake value to add to the list
            DInteger(),    # data3, list length
            DInteger(2),   # data4, list index
            DInteger(3),   # data5, expected list length
            DNull(),       # data6, comp1
            DNull(),       # data7, comp2
            DNull(),       # data8, output
        ])
        self.assertEqual(result.int_py(), True)



if __name__ == '__main__':
    unittest.main()