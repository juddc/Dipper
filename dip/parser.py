"""
Dipper parser-generator 
"""
import os
import py
from rpython.rlib.objectmodel import we_are_translated
from rpython.rlib.parsing.ebnfparse import parse_ebnf, make_parse_function, EBNFToAST
from rpython.rlib.parsing.parsing import ParseError
import rpython.rlib.parsing.tree as parsetree

from dip import ast

CHILDREN = "children"
ADDITIONAL_INFO = "additional_info"

GRAMMAR_FILE = os.path.join(os.path.dirname(__file__), "grammar.txt")

RPY = False

if RPY:
    grammar = py.path.local("./dip").join("grammar.txt").read("rt")
    regexs, rules, astGenerator = parse_ebnf(grammar)
    parseFunc = make_parse_function(regexs, rules, eof=True)
else:
    with open(GRAMMAR_FILE) as fp:
        grammar = fp.read()
    try:
        regexs, rules, astGenerator = parse_ebnf(grammar)
    except ParseError as e:
        self._printErrorInfo(e)
        raise
    parseFunc = make_parse_function(regexs, rules, eof=True)

# At RPython compile-time, use the AST code-generator to write out the transformer
# module to a file, then import it, so that it gets compiled to C, since RPython
# can't handle dymanically-generated code otherwise
with open("./dip/transformer.py", 'w') as fp:
    fp.write("import py\n")
    fp.write("from rpython.rlib.parsing.tree import Nonterminal, RPythonVisitor\n")
    fp.write("from rpython.rlib.objectmodel import we_are_translated\n")
    fp.write("\n\n")
    fp.write(astGenerator.source)

# import the now-generated class
from dip.transformer import ToAST


class DipperParser(object):
    nodeMap = {
        "NEWLINE":                                  ast.NullNode,
        "NAME":              ast.Name,
        "INTEGER":           ast.Integer,
        "FLOAT":             ast.Float,
        "STRING":            ast.String,
        "BLOCK_START":                              ast.NullNode,
        "BLOCK_END":                                ast.NullNode,
        "program":                                  ast.NullNode,
        "import":                                   ast.NullNode,
        "from_import":                              ast.NullNode,
        "module_const":                             ast.NullNode,
        "struct":            ast.Struct,
        "import_name":                              ast.NullNode,
        "func":              ast.Function,
        "class":             ast.Class,
        "field":             ast.Field,
        "while_block":                              ast.NullNode,
        "if_block":          ast.If,
        "elif_block":        ast.Elif,
        "else_block":        ast.Else,
        "return_stmt":       ast.Return,
        "break_stmt":                               ast.NullNode,
        "continue_stmt":                            ast.NullNode,
        "doc_stmt":                                 ast.NullNode,
        "call_stmt":         ast.CallStatement,
        "assign_stmt":       ast.Assignment,
        "inplace_stmt":      ast.Inplace,
        "print_stmt":        ast.Print,
        "yield_stmt":                               ast.NullNode,
        "del_stmt":                                 ast.NullNode,
        "simple_block":      ast.Block,
        "complex_block":     ast.Block,
        "for_block":                                ast.NullNode,
        "loop_block":                               ast.NullNode,
        "exprblock":                                ast.NullNode,
        "simple_exprblock":                         ast.NullNode,
        "complex_exprblock":                        ast.NullNode,
        "simple_expr":       ast.SimpleExpr,
        "if_expr":           ast.IfExpr,
        "match_expr":        ast.MatchExpr,
        "range_expr":        ast.RangeExpr,
        "arith_expr":        ast.ArithExpr,
        "bool_expr":         ast.BoolExpr,
        "match_query":                              ast.NullNode,
        "match_val":                                ast.NullNode,
        "simple_match_val":                         ast.NullNode,
        "complex_match_val":                        ast.NullNode,
        "dotted_name":       ast.DottedName,
        "call":              ast.Call,
        "typed_name_opt":    ast.TypedName,
        "typed_name_req":    ast.TypedName,
        "call_args":         ast.CallArgs,
        "func_args":         ast.FuncArgs,
        #"func_ret_type":     ast.ReturnType,
        "op_=":              ast.Operator,
        "op_+":              ast.Operator,
        "op_-":              ast.Operator,
        "op_*":              ast.Operator,
        "op_/":              ast.Operator,
        "op_//":             ast.Operator,
        "op_**":             ast.Operator,
        "op_<":              ast.Operator,
        "op_>":              ast.Operator,
        "op_==":             ast.Operator,
        "op_>=":             ast.Operator,
        "op_<=":             ast.Operator,
        "op_<>":             ast.Operator,
        "op_!=":             ast.Operator,
        "op_in":             ast.Operator,
        "op_!in":            ast.Operator,
        "op_!is":            ast.Operator,
        "op_is":             ast.Operator,
        "op_and":            ast.Operator,
        "op_or":             ast.Operator,
        "op_+=":             ast.Operator,
        "op_-=":             ast.Operator,
        "op_*=":             ast.Operator,
        "op_/=":             ast.Operator,
        "op_%=":             ast.Operator,
        "op_&=":             ast.Operator,
        "op_^=":             ast.Operator,
        "op_<<=":            ast.Operator,
        "op_>>=":            ast.Operator,
        "op_**=":            ast.Operator,
        "op_(":              ast.Operator,
        "op_)":              ast.Operator,
        "op_//=":            ast.Operator,
        "op_|=":             ast.Operator,
        "op_,":              ast.Operator,
    }

    def __init__(self, debug=False):
        self.debug = debug

    def _printErrorInfo(self, e):
        pos = e.source_pos
        print "ParseError on line %s, column %s" % (pos.lineno, pos.columnno)
        print e.nice_error_message()
        print ""

    def readDipFile(self, filename):
        with open (filename) as fp:
            return fp.read()

    def _prepSource(self, code):
        """
        Cleans up source to make it easier on the tokenizer.
        Strips comments, removes blank lines, etc.
        """
        lines = []
        for line in code.split("\n"):
            stripped_line = line.strip()
            if stripped_line.startswith("#"):
                continue
            elif len(stripped_line) == 0:
                continue

            # check for comments in the middle of the line,
            # but be careful to ignore comment chars inside a string
            i = 0
            found_comment = False
            in_str = False
            for ch in line:
                if ch == '"' and in_str == False:
                    in_str = True
                elif ch == '"' and in_str == True:
                    in_str = False
                elif ch == '#' and in_str == False:
                    found_comment = True
                    break
                i += 1

            if found_comment:
                line = line[:i]

            lines.append(line)

        return "\n".join(lines)

    def parseFile(self, filename):
        return self.parse(self.readDipFile(filename))

    def parse(self, source):
        source = self._prepSource(source)
        try:
            result = parseFunc(source)
        except ParseError as e:
            self._printErrorInfo(e)
            return None

        newtree = ToAST().transform(result)

        if self.debug:
            self._printTree(newtree)

        tree = ast.RootNode()
        childNodes = []
        assert newtree.symbol == "program"
        for item in newtree.children:
            childNodes.append(self._traverse(item))
        tree.set(childNodes)
        return tree

    def _parseSymbol(self, sym):
        val = sym
        if sym.startswith("__"):
            parts = [ part for part in sym.split("_") if sym ]
            val = "op_%s" % parts[-1]
        return val

    def _mknode(self, item):
        sym = self._parseSymbol(item.symbol)
        if sym in self.nodeMap:
            nodeType = self.nodeMap[sym]
            while nodeType is ast.OneChild:
                item = item.children[0]
                nodeType = self.nodeMap[self._parseSymbol(item.symbol)]

            #node = nodeType(item.additional_info if hasattr(item, ADDITIONAL_INFO) else "")

            try:
                node = nodeType(item.additional_info)
            except AttributeError:
                node = nodeType("")

        else:
            node = ast.NullNode()
            node.label = self._parseSymbol(item.symbol)

        return (item, node)

    def _printTree(self, node, level=0):
        if type(node) is not parsetree.Symbol:
            print "    " * level, node.symbol
        else:
            print "    " * level, node.symbol, node.additional_info

        if type(node) is parsetree.Nonterminal:
            for child in node.children:
                self._printTree(child, level + 1)

    def _traverse(self, item, level=0):
        if item.symbol == "dotted_name" and len(item.children) == 1:
            item, node = self._mknode(item.children[0])
            return node

        item, node = self._mknode(item)

        if type(item) is parsetree.Nonterminal:
            childNodes = []
            for n in item.children:
                #print "    " * (level + 1), n.symbol
                newNode = self._traverse(n, level + 1)
                #print "    " * (level + 1), newNode, "  ---  ", n.symbol
                childNodes.append(newNode)
            node.set(childNodes)

        return node

