
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
    'SET',
    'ADDI', 'SUBI', 'MULI', 'DIVI',
    'ADD', 'SUB', 'MUL', 'DIV',
    'EQ', 'NEQ', 'GT', 'LT', 'GTE', 'LTE',
    'SQRT',
    'LEN',
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


OPERATOR_MAP = {
    ADD: "+",
    SUB: "-",
    MUL: "*",
    DIV: "/",
    EQ: "==",
    NEQ: "!=",
    GT: ">",
    LT: "<",
    GTE: ">=",
    LTE: "<=",
}


class BytecodeAnnotation(object):
    def __init__(self, filename, source, comment=""):
        self.filename = filename
        self.source = source
        self.comment = comment
