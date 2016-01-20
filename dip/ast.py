"""
Dipper AST implementation
"""
from rpython.rlib.objectmodel import we_are_translated

import typesystem as types

import py

from dip.builtins import has_builtin, get_builtin
from dip.bytecode import INST
from dip.common import CompileError


def infix_to_prefix(tokens):
    ops = set(("+", "-", "*", "/"))
    output = [[]]
    for item in tokens:
        if len(output[-1]) >= 3:
            val = output.pop()
            output.append([val])
        if item in ops:
            output[-1].insert(0, item)
        else:
            output[-1].append(item)
    return output[0]


class Node(object):
    name = ""

    def __init__(self, data="", source=(-1, -1)):
        if not we_are_translated():
            assert type(data) is str
        self.children = []
        self.doc = []
        self.data = data
        self.source = source # source pos from the file. a 2-tuple of ints represnting (line, column)
        self.init()

    def init(self):
        pass

    def set(self, nodes):
        for child in nodes:
            self.children.append(child)

    @property
    def type(self):
        return self.__class__.__name__

    def mkobj(self):
        raise NotImplementedError

    def show(self, level=0):
        selfstr = self.toString()
        if len(selfstr.strip()) > 0:
            selfstr = " " + selfstr

        lines = ["%s<%s%s>" % ("    " * level, self.type, selfstr)]
        for item in self:
            lines.append(item.show(level + 1))
        return "\n".join(lines)

    def _getRepr(self):
        """
        Child classes should return a list of strings that should appear in the string
        representation of this AST node.
        """
        return []

    def walk(self):
        def _iter(node, level):
            level += 1
            for child in node:
                yield (child, level)
                for n, nextLevel in _iter(child, level):
                    yield (n, nextLevel)
        yield (self, 0)
        for item in _iter(self, 0):
            yield item

    def compile(self, ctx):
        ctx.start_node(self)
        return -1

    def __iter__(self):
        for item in self.children:
            yield item

    def __len__(self):
        return len(self.children)

    def __repr__(self):
        extra = str(self)
        if len(extra) > 0:
            return "<%s %s>" % (self.type, extra)
        else:
            return "<%s>" % self.type

    def __str__(self):
        return self.toString()

    def toString(self):
        #return ", ".join(self._getRepr())
        # this pretty much just does `return ", ".join(self._getRepr())`,
        # but skips any empty strings and does some type checking for sanity
        extra = []
        reprVals = self._getRepr()
        if not we_are_translated():
            assert type(reprVals) is list
        for item in reprVals:
            if not we_are_translated():
                if not type(item) is str:
                    raise TypeError("Got value '%s' from %s._getRepr() of type '%s' (which is not a string)" % (
                        item, self.type, type(item).__name__))
            if len(item) > 0:
                extra.append(item)
        return ", ".join(extra)


class RootNode(Node):
    pass


class NullNode(Node):
    label = "_nullnode_"

    def __str__(self):
        return ".%s" % self.label

    def __repr__(self):
        return str(self)


class OneChild(Node):
    label = "_one_child_"

    def __str__(self):
        return "_one_child_"

    def __repr__(self):
        return "_one_child_"


class Function(Node):
    def set(self, nodes):
        self.name = nodes.pop(0).data
        self.args = nodes.pop(0)

        # if this function is the main function, then its optional to add an
        # argv argument. if one was not specified, add it to the AST automatically
        # so we can always assume its there.
        if self.name == "main" and len(self.args.children) == 0:
            argv = TypedName()
            argv.set([Name("argv"), Name("list")])
            self.args.children.append(argv)

        if len(nodes) > 0 and nodes[0].type in ("Name", "DottedName"):
            self.returnType = nodes.pop(0)
        else:
            self.returnType = Name("auto")

        if len(nodes) > 0 and isinstance(nodes[0], Block):
            for node in nodes[0]:
                self.children.append(node)

    def compile(self, ctx):
        Node.compile(self, ctx)
        for node in self.children:
            node.compile(ctx)
        if len(ctx.bytecode) == 0 or ctx.bytecode[-1][0] != INST['RET']:
            ctx.emit_RET()
        return -1

    def mkprototype(self):
        """
        Returns an incomplete (without code or data registers) function object.
        Call DFunc.set_code to make it a complete function.
        """
        funcargs = [ (arg.getName(), arg.getFullType()) for arg in self.args ]
        return types.DFunc.new_func(self.name, funcargs, self.returnType.getFullName())

    def _getRepr(self):
        extra = [self.name]
        if len(self.args) > 0:
            extra.append("args( " + self.args.toString() + " )")
        extra.append("returnType: %s" % self.returnType.toString())
        return extra


class Struct(Node):
    def set(self, nodes):
        name = nodes.pop(0)
        self.name = name.getName()
        for field in nodes:
            self.children.append(field)

    def mkstruct(self):
        st = types.StructDef(self.name, len(self.children))
        for field in self.children:
            fieldinfo = field.typedname
            st.setfield(fieldinfo.getName(), types.AutoType(fieldinfo.getType()))
        return st

    def _getRepr(self):
        extra = ["%s:" % self.name]
        for n in self.children:
            extra.append(n.name)
        return extra


class Class(Node):
    def set(self, nodes):
        name = nodes.pop(0)
        body = nodes

        self.name = name.getDottedName()

        if body[0].type == "Name":
            self.parent = body[0]
            body = body[1:]
        else:
            self.parent = NullNode()

        for node in body:
            self.children.append(node)

    def _getRepr(self):
        fields = [self.name, "(%s)" % self.parent.toString()]
        for n in self.children:
            if n.type == "Field":
                fields.append(n.name)
        return fields


class Field(Node):
    def init(self):
        self.default = ""
        self.condition = NullNode()

    def set(self, nodes):
        self.typedname = nodes.pop(0)
        assert len(nodes) <= 2
        while len(nodes) > 0:
            arg = nodes.pop(0)
            if arg.type == "ConstValue":
                self.default = arg.data
            elif arg.type == "BoolExpr":
                self.condition = arg
            else:
                raise TypeError("Unexpected node type %s in Field" % arg.type)

    def _getRepr(self):
        default = ""
        cond = ""
        if len(self.default) > 0:
            default = "default:%s" % self.default
        if self.condition.type == "BoolExpr":
            cond = "cond:%s" % self.condition
        return [self.typedname.getName(), default, cond]


class FieldList(Node):
    pass


class FuncArgs(Node):
    def _getRepr(self):
        return [ node.toString() for node in self.children ]


class Block(Node):
    def compile(self, ctx):
        Node.compile(self, ctx)
        for node in self:
            node.compile(ctx)
        return -1

    def _getRepr(self):
        return [self.data]


class If(Block):
    def set(self, nodes):
        boolexpr = nodes.pop(0)
        ifblock = nodes.pop(0)
        blocks = nodes

        self.expr = boolexpr

        ifblock.data = "if"
        self.children.append(ifblock)

        for b in blocks:
            assert b.type in ("Block", "Elif", "Else")
            self.children.append(b)

    def compile(self, ctx):
        Node.compile(self, ctx)
        ctx.emit_LABEL("%s %s" % (self.type, self.toString()))

        boolidx = self.expr.compile(ctx)

        # jump to an intentionally invalid place because we're going to rewrite this
        # with setbranch once we know where to go
        top_jmp = ctx.emit_BF(boolidx, -1)

        # keep track of all jump-to-end instructions so we can fix them up later
        jumpend = []

        for i, block in enumerate(self.children):
            assert block.type in ("Block", "Elif", "Else")

            if block.type == "Elif":
                start_ptr = ctx.emit_LABEL("Elif %s" % block.toString())
                boolidx = block.expr.compile(ctx)

                # jump to an intentionally invalid place because we're going to rewrite it in a bit
                start_jmp = ctx.emit_BF(boolidx, -1)

                # rewrite the previous branch instruction to point towards the top of this one
                ctx.setbranch(top_jmp, start_ptr)

                # the next jump rewrite should apply to this one
                top_jmp = start_jmp

            elif block.type == "Else":
                start_ptr = ctx.emit_LABEL("Else")
                # rewrite any previous branch to point here
                ctx.setbranch(top_jmp, start_ptr)

            start = ctx.emit_LABEL("start_block %s %s" % (block.type, block.toString()))

            block.compile(ctx)

            # no need to jump if there are no blocks after this one
            if i < len(self) - 1:
                # jump to the end of all the blocks (intentionally invalid, will rewrite)
                jmp_ptr = ctx.emit_JMP(-1)
                # mark this jump as needing a rewrite after we know where the bottom is
                jumpend.append(jmp_ptr)

        end = ctx.emit_LABEL("end %s" % self.type)

        # fix up the last branch to point to the end if there is no else block
        if self.children[-1].type != "Else":
            ctx.setbranch(top_jmp, end)

        # fix up all the jump-to-end instructions
        for ptr in jumpend:
            ctx.setbranch(ptr, end)

        return -1

    def _getRepr(self):
        return [ self.expr.toString() ]


class Elif(Block):
    def set(self, nodes):
        boolexpr = nodes.pop(0)
        blockbody = nodes

        self.expr = boolexpr
        for node in blockbody:
            self.children.append(node)

    def _getRepr(self):
        return [ self.expr.toString() ]


class Else(Block):
    def _getRepr(self):
        return []


class ForLoop(Block):
    def set(self, nodes):
        assert len(nodes) == 3
        self.loopvar = nodes.pop(0).data
        self.expr = nodes.pop(0)

        if not isinstance(self.expr, RangeExpr):
            raise NotImplementedError("For loops only support range expressions right now")

        block = nodes.pop(0)
        for node in block:
            self.children.append(node)

    def compile(self, ctx):
        assert isinstance(self.expr, RangeExpr)
        self.expr.compile(ctx)
        startval_idx = self.expr.start_idx
        endval_idx = self.expr.end_idx
        assert startval_idx > -1 and endval_idx > -1

        loopval_idx = ctx.pushobj(types.DInteger())
        ctx.register_var(self.loopvar, loopval_idx)
        ctx.emit_SET(startval_idx, loopval_idx)

        top_idx = ctx.emit_LABEL("For loop start")
        
        for child in self.children:
            child.compile(ctx)

        # increment the loop counter
        ctx.emit_ADDI(loopval_idx, 1)

        # if the loop counter is equal to the end value, keep going in the bytecode.
        # otherwise jump backwards to the top of the loop
        ctx.emit_BNE(loopval_idx, endval_idx, top_idx)
        
        return -1

    def _getRepr(self):
        return [ "%s in %s" % (self.loopvar, self.expr.toString()) ]


class Expression(Node):
    def compile(self, ctx):
        """
        Generates bytecode to eval an expression, then returns the data index
        of the resulting data object. (implemented in subclasses)
        """
        raise NotImplementedError("%s.compile(ctx)" % self.type)
        Node.compile(self, ctx)
        return -1

    def _getRepr(self):
        expr = []
        for node in self.children:
            val = node.toString()
            if len(val) > 0:
                expr.append(val)
        return [" ".join(expr)]


class SimpleExpr(Expression):
    """
    Call or dotted name
    """
    def _getRepr(self):
        return [ self.children[0].toString() ]


class IfExpr(Expression):
    def compile(self, ctx):
        raise NotImplementedError("If expressions")
        Node.compile(self, ctx)
        return -1


class MatchExpr(Expression):
    pass


class RangeExpr(Expression):
    def init(self):
        self.start_idx = -1
        self.end_idx = -1

    def set(self, nodes):
        assert len(nodes) == 2
        self._leftnode = nodes.pop(0)
        self._rightnode = nodes.pop(0)

    def compile(self, ctx):
        self.start_idx = self._leftnode.compile(ctx)
        self.end_idx = self._rightnode.compile(ctx)
        if not (ctx.is_int(self.start_idx) and ctx.is_int(self.end_idx)):
            raise NotImplementedError("Ranges must be integers")
        return self.start_idx

    def _getRepr(self):
        return [self._leftnode.toString(), self._rightnode.toString()]


class ArithExpr(Expression):
    # all ops listed here must have the same bytecode syntax:
    #     OP  A  B  DEST
    ops = {
        '+': 'ADD',
        '-': 'SUB',
        '*': 'MUL',
        '/': 'DIV',
        '==': 'EQ',
        '!=': 'NEQ',
        '<': 'LT',
        '>': 'GT',
        '<=': 'LTE',
        '>=': 'GTE',
    }

    def compile(self, ctx):
        Node.compile(self, ctx)
        if len(self.children) == 1:
            return self.children[0].compile(ctx)
        elif len(self.children) == 3:
            op = self.children[1]
            a = self.children[0]
            b = self.children[2]

            # if both values are actually constants, we can do this operation at compile-time
            if isinstance(a, ConstValue) and isinstance(b, ConstValue):
                if op.data in ("==", "!=", "<", ">", "<=", ">="):
                    result = a.mkobj().operator_bool(op.data, b.mkobj())
                    return ctx.pushobj(types.DBool.new_bool(result))

                elif isinstance(a, Float) or isinstance(b, Float):
                    result = a.mkobj().operator_float(op.data, b.mkobj())
                    return ctx.pushobj(types.DFloat.new_float(result))

                elif isinstance(a, Integer) and isinstance(b, Integer):
                    result = a.mkobj().operator_int(op.data, b.mkobj())
                    return ctx.pushobj(types.DInteger.new_int(result))

                elif isinstance(a, String):
                    result = a.mkobj().operator_str(op.data, b.mkobj())
                    return ctx.pushobj(types.DString.new_str(result))

                else:
                    raise NotImplementedError("ArithExpr with types (%s, %s) and op '%s'" % (
                        a.__class__.__name__, b.__class__.__name__, op.data))

            # otherwise emit bytecode to do this operation at run-time
            else:
                a_idx = a.compile(ctx)
                b_idx = b.compile(ctx)

                a_data = ctx.data[a_idx]
                b_data = ctx.data[b_idx]

                if op.data in ("==", "!=", "<", ">", "<=", ">="):
                    c_idx = ctx.pushobj(types.DBool())

                elif isinstance(a_data, types.DFloat) or isinstance(b_data, types.DFloat):
                    c_idx = ctx.pushobj(types.DFloat())

                elif isinstance(a_data, types.DInteger) and isinstance(b_data, types.DInteger):
                    c_idx = ctx.pushobj(types.DInteger())

                elif isinstance(a_data, types.DString):
                    c_idx = ctx.pushobj(types.DString())

                else:
                    raise NotImplementedError("ArithExpr with types (%s, %s) and op '%s'" % (
                        a_data.__class__.__name__, b_data.__class__.__name__, op.data))

                #c_idx = ctx.pushobj(types.DInteger())
                ctx.emit(self.ops[op.data], a_idx, b_idx, c_idx)
                return c_idx

        raise NotImplementedError("ArithExpr")
        return -1


class BoolExpr(Expression):
    ops = {
        '==': 'EQ',
        '!=': 'NEQ',
        '>': 'GT',
        '<': 'LT',
        '>=': 'GTE',
        '<=': 'LTE',
    }

    def compile(self, ctx):
        Node.compile(self, ctx)
        if len(self.children) == 1:
            return self.children[0].compile(ctx)
        elif len(self.children) == 3:
            op = self.children[1]
            a = self.children[0]
            b = self.children[2]
            if isinstance(a, ConstValue) and isinstance(b, ConstValue):
                result = a.mkobj().operator_bool(op.data, b.mkobj())
                return ctx.pushobj(types.DBool.new_bool(result))
            else:
                a_idx = a.compile(ctx)
                b_idx = b.compile(ctx)
                result_idx = ctx.pushobj(types.DBool())
                if op.data not in self.ops:
                    raise NotImplementedError("BoolExpr operator '%s'" % op.data)
                ctx.emit(self.ops[op.data], a_idx, b_idx, result_idx)
                return result_idx

        raise NotImplementedError("BoolExpr")
        return -1


class Statement(Node):
    pass


class CallStatement(Statement):
    def compile(self, ctx):
        Node.compile(self, ctx)
        assert len(self.children) == 1
        assert self.children[0].type == "Call"
        self.children[0].compile(ctx)
        return -1


class Assignment(Statement):
    def set(self, nodes):
        assert len(nodes) == 3
        self.typedName = nodes.pop(0)
        assert self.typedName.type == "TypedName"

        op = nodes.pop(0)
        assert op.type == "Operator"

        expr = nodes.pop(0)

        if not op.data == "=":
            raise ValueError("Assignments expect a '=' operator (got %s)" % op.data)

        self.children.append(expr)

    def compile(self, ctx):
        Node.compile(self, ctx)
        assert len(self.children) == 1
        assert isinstance(self.children[0], Expression)
        dataidx = self.children[0].compile(ctx)
        ctx.register_var(self.typedName.getName(), dataidx)
        return -1

    def _getRepr(self):
        return ["to %s (type %s)" % (self.typedName.getDottedName(), self.typedName.getDottedType())]


class Inplace(Statement):
    ops = {
        '+=': 'ADD',
        '-=': 'SUB',
        '*=': 'MUL',
        '/=': 'DIV',
    }

    def set(self, nodes):
        assert len(nodes) == 3
        name = nodes.pop(0)
        op = nodes.pop(0)
        expr = nodes.pop(0)

        self.name = name.data
        #assert type(self.name) is str

        self.op = op.data
        if len(expr) == 1:
            self.children.append(expr.children[0])
        else:
            self.children.append(expr)

    def compile(self, ctx):
        Node.compile(self, ctx)
        varidx = ctx.getdataidx(self.name)

        if len(self) == 1:
            node = self.children[0]
            resultidx = node.compile(ctx)
            ctx.emit(self.ops[self.op], varidx, resultidx, varidx)
            return -1

        raise NotImplementedError
        return -1

    def _getRepr(self):
        return ["%s '%s'" % (self.name, self.op)]


class Print(Statement):
    def init(self):
        self.add_newline = True

    def set(self, nodes):
        if len(nodes) == 0:
            return

        # if the print statement ends with a semicolon, don't print a newline
        if nodes[-1].type == "Operator" and nodes[-1].data == ",":
            self.add_newline = False
            for node in nodes[:-1]:
                self.children.append(node)
        else:
            for node in nodes:
                self.children.append(node)

    def compile(self, ctx):
        Node.compile(self, ctx)
        if len(self.children) == 0:
            ctx.emit_WRITENL(ctx.STDOUT)
        else:
            spacechr = -1
            for i, node in enumerate(self.children):
                assert isinstance(node, Expression)
                dataidx = node.compile(ctx)
                ctx.emit_WRITEO(ctx.STDOUT, dataidx)
                if i < len(self.children) - 1:
                    if spacechr == -1:
                        spacechr = ctx.pushobj(types.DInteger.new_int(32))
                    ctx.emit_WRITEI(ctx.STDOUT, spacechr)
                if self.add_newline:
                    ctx.emit_WRITENL(ctx.STDOUT)
        return -1

    def repr(self):
        return ["(no newline)" if not self.add_newline else ""]


class Return(Statement):
    def compile(self, ctx):
        Node.compile(self, ctx)
        assert len(self.children) == 1
        idx = self.children[0].compile(ctx)
        ctx.emit_RET(idx)
        return -1


class ConstValue(Node):
    def mkobj(self):
        """
        Subclasses should implement this and return a new typesystem object based on their type
        """
        raise NotImplementedError


class Integer(ConstValue):
    def init(self):
        self._int = int(self.data.rstrip("i"))

    def compile(self, ctx):
        Node.compile(self, ctx)
        return ctx.pushobj(self.mkobj())

    def mkobj(self):
        return types.DInteger.new_int(self._int)

    def _getRepr(self):
        return [str(self._int)]


class Float(ConstValue):
    def init(self):
        self._float = float(self.data.rstrip("f"))

    def compile(self, ctx):
        Node.compile(self, ctx)
        return ctx.pushobj(self.mkobj())

    def mkobj(self):
        return types.DFloat.new_float(self._float)

    def _getRepr(self):
        return [str(self._float)]


class String(ConstValue):
    def init(self):
        # need to strip doublequotes from data
        self._str = ""
        if len(self.data) > 2:
            # strip front doublequote
            self._str = self.data[1:]
            # strop back doublequote
            endstop = len(self._str) - 1
            if endstop > 0:
                self._str = self._str[:endstop]

    def compile(self, ctx):
        Node.compile(self, ctx)
        return ctx.pushobj(self.mkobj())

    def mkobj(self):
        return types.DString.new_str(self._str)

    def _getRepr(self):
        return ['"%s"' % self._str]


class Call(Node):
    def set(self, nodes):
        assert len(nodes) >= 1
        self.target = nodes.pop(0)

        if len(nodes) > 0:
            args = nodes.pop(0)
            for node in args:
                self.children.append(node)

    def compile(self, ctx):
        Node.compile(self, ctx)
        name = self.target.getName()

        if has_builtin(name):
            FuncCls = get_builtin(name)
            args = []
            for arg in self.children:
                args.append(arg)
            return FuncCls(args).compile(ctx)

        arglist = types.DList()
        args = []
        for arg in self.children:
            args.append(arg.compile(ctx))
        assert len(args) == len(self.children)

        arglistidx = ctx.pushobj(types.DList())
        for argvalidx in args:
            ctx.emit_LIST_ADD(arglistidx, argvalidx)

        # get return value type
        if ctx.namespace.contains_func(name):
            rettype_name = ctx.namespace.get_func(name).get_return_type_name()
            if rettype_name != "auto":
                # return value dest
                RetType = types.AutoType(rettype_name)
                retidx = ctx.pushobj(RetType())
            else:
                # no return value
                retidx = -1

            funcnameidx = ctx.pushobj(types.DString.new_str(name))
            ctx.emit_CALL(funcnameidx, arglistidx, retidx)
            return retidx

        elif ctx.namespace.contains_struct(name):
            structnameidx = ctx.pushobj(types.DString.new_str(name))
            retidx = ctx.pushobj(types.DStructInstance.new_struct(
                ctx.namespace.get_struct(name)))
            ctx.emit_CALL(structnameidx, arglistidx, retidx)
            return retidx

        else:
            # no function found
            raise ValueError("No function found named '%s'" % name)


    def _getRepr(self):
        return [self.target.getDottedName()]


class CallArgs(Node):
    pass


class Operator(Node):
    def _getRepr(self):
        return ["'%s'" % self.data]


class VarName(Node):
    """
    Abstract parent class of Name and DottedName to provide the same interface for both
    """
    def getName(self):
        """
        Return the name of the item (the last part of a dotted name or the only part of a regular name)
        Eg:
            The code "collections.trees.RedBlackTree" would return "RedBlackTree"
        """
        return ""

    def getFullName(self):
        """
        Return the full name as a list of parts
        Eg:
            The code "math.pow" would return ["math", "pow"]
        """ 
        return []

    def getDottedName(self):
        """
        Returns a string representing the full name.
        Eg:
            The code "types.Vector3" would return the string "types.Vector3"
        """
        return ""


class Name(VarName):
    def init(self):
        self._name = self.data

    def set(self, nodes):
        raise NotImplementedError("Names can't have child nodes")

    def compile(self, ctx):
        Node.compile(self, ctx)
        return ctx.getdataidx(self._name)

    def getName(self):
        return self._name

    def getFullName(self):
        return [self._name]

    def getDottedName(self):
        return self._name

    def _getRepr(self):
        return [self._name]


class DottedName(VarName):
    def set(self, names):
        for name in names:
            if name.type == "Name":
                self.children.append(name)
            else:
                raise TypeError(name.type)

    def compile(self, ctx):
        Node.compile(self, ctx)
        return ctx.getdataidx(self.getName())

    def getName(self):
        return self.children[-1].getName()

    def getFullName(self):
        parts = []
        for node in self:
            parts.append(node.getName())
        return parts

    def getDottedName(self):
        return ".".join(self.getFullName())

    def _getRepr(self):
        return [self.getDottedName()]


class TypedName(VarName):
    def set(self, nodes):
        assert len(nodes) == 1 or len(nodes) == 2
        self._name = nodes.pop(0)
        self._type = nodes.pop(0) if len(nodes) > 0 else Name("auto")

    def getType(self):
        return self._type.getName()

    def getDottedType(self):
        return self._type.getDottedName()

    def getFullType(self):
        return self._type.getFullName()

    def getName(self):
        return self._name.getName()

    def getFullName(self):
        return self._name.getFullName()

    def getDottedName(self):
        return self._name.getDottedName()

    def _getRepr(self):
        return ["%s:%s" % (self.getDottedName(), self.getDottedType())]
