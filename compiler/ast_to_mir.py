#!/usr/bin/env python3
"""
AST to MIR Lowering Pass for Brainhair Compiler

This module transforms the Abstract Syntax Tree (AST) into Mid-Level
Intermediate Representation (MIR). The lowering process includes:
- Converting control flow to basic blocks
- Generating explicit loads/stores for variables
- Lowering high-level constructs to primitive operations
"""

from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass

from ast_nodes import *
from mir import (
    MIRModule, MIRFunction, MIRBasicBlock, MIRBuilder,
    MIRType, MIRAnyType, PointerMIRType, ArrayMIRType, StructMIRType,
    MIRValue, MIRConstant, MIRVirtualReg, MIRParam, MIRGlobal,
    MIROp
)


def brainhair_type_to_mir(ty) -> MIRAnyType:
    """Convert a Brainhair AST type to MIR type."""
    if isinstance(ty, Type):
        type_map = {
            'int8': MIRType.I8,
            'int16': MIRType.I16,
            'int32': MIRType.I32,
            'uint8': MIRType.U8,
            'uint16': MIRType.U16,
            'uint32': MIRType.U32,
            'bool': MIRType.BOOL,
            'char': MIRType.I8,  # char is 8-bit
            'void': MIRType.VOID,
        }
        return type_map.get(ty.name, MIRType.I32)

    elif isinstance(ty, PointerType):
        base = brainhair_type_to_mir(ty.base_type)
        return PointerMIRType(base)

    elif isinstance(ty, ArrayType):
        elem = brainhair_type_to_mir(ty.element_type)
        return ArrayMIRType(elem, ty.size)

    return MIRType.I32  # Default


@dataclass
class VariableInfo:
    """Information about a variable during lowering."""
    ptr: MIRValue  # Stack slot (alloca result)
    ty: MIRAnyType  # Variable type
    is_const: bool = False


class ASTToMIRLowerer:
    """
    Lowers AST to MIR.

    This class walks the AST and generates corresponding MIR instructions.
    It maintains mappings between AST variables and their MIR representations.
    """

    def __init__(self):
        self.module: Optional[MIRModule] = None
        self.current_func: Optional[MIRFunction] = None
        self.builder: Optional[MIRBuilder] = None

        # Variable mapping: name -> VariableInfo
        self.variables: Dict[str, VariableInfo] = {}

        # For loop handling
        self.loop_stack: List[Tuple[MIRBasicBlock, MIRBasicBlock]] = []  # (continue_block, break_block)

    def lower(self, program: Program) -> MIRModule:
        """
        Lower an entire program to MIR.

        Args:
            program: The AST program node

        Returns:
            MIR module containing the lowered program
        """
        self.module = MIRModule("brainhair_module")

        # First pass: register all functions and types
        for decl in program.declarations:
            if isinstance(decl, StructDecl):
                self._register_struct(decl)
            elif isinstance(decl, (ProcDecl, ExternDecl)):
                self._register_function(decl)

        # Second pass: lower function bodies
        for decl in program.declarations:
            if isinstance(decl, ProcDecl):
                self._lower_function(decl)
            elif isinstance(decl, VarDecl):
                self._lower_global_var(decl)

        return self.module

    def _register_struct(self, decl: StructDecl) -> None:
        """Register a struct type in the module."""
        fields = {}
        field_order = []
        for field in decl.fields:
            field_ty = brainhair_type_to_mir(field.field_type)
            fields[field.name] = field_ty
            field_order.append(field.name)

        struct_type = StructMIRType(decl.name, fields, field_order)
        self.module.add_type(struct_type)

    def _register_function(self, decl) -> None:
        """Register a function signature."""
        func = MIRFunction(decl.name)

        # Add parameters
        for i, param in enumerate(decl.params):
            param_ty = brainhair_type_to_mir(param.param_type)
            mir_param = MIRParam(f"%{param.name}", param_ty, i)
            func.params.append(mir_param)

        # Return type
        if decl.return_type:
            func.return_type = brainhair_type_to_mir(decl.return_type)
        else:
            func.return_type = MIRType.VOID

        if isinstance(decl, ExternDecl):
            func.is_extern = True

        self.module.add_function(func)

    def _lower_global_var(self, decl: VarDecl) -> None:
        """Lower a global variable declaration."""
        ty = brainhair_type_to_mir(decl.var_type)
        glob = self.module.add_global(decl.name, ty)
        # Note: global initialization would need to be handled separately

    def _lower_function(self, decl: ProcDecl) -> None:
        """Lower a function body to MIR."""
        self.current_func = self.module.get_function(decl.name)
        if self.current_func is None or self.current_func.is_extern:
            return

        self.builder = MIRBuilder(self.current_func)
        self.variables = {}
        self.loop_stack = []

        # Create entry block
        entry = self.builder.create_block("entry")

        # Allocate stack space for parameters and copy them
        for i, param in enumerate(decl.params):
            param_ty = brainhair_type_to_mir(param.param_type)
            # Allocate stack slot
            ptr = self.builder.alloca(param_ty, param.name)
            # Store parameter value
            mir_param = self.current_func.params[i]
            self.builder.store(mir_param, ptr)
            # Record in variables map
            self.variables[param.name] = VariableInfo(ptr, param_ty)

        # Lower function body
        for stmt in decl.body:
            self._lower_statement(stmt)

        # Add implicit return if needed
        if not self.builder.current_block.is_terminated():
            if self.current_func.return_type == MIRType.VOID:
                self.builder.ret()
            else:
                # Return 0 as default
                zero = self.builder.const_int(0, self.current_func.return_type)
                self.builder.ret(zero)

    def _lower_statement(self, stmt: ASTNode) -> None:
        """Lower a statement to MIR."""
        if isinstance(stmt, VarDecl):
            self._lower_var_decl(stmt)
        elif isinstance(stmt, Assignment):
            self._lower_assignment(stmt)
        elif isinstance(stmt, ReturnStmt):
            self._lower_return(stmt)
        elif isinstance(stmt, IfStmt):
            self._lower_if(stmt)
        elif isinstance(stmt, WhileStmt):
            self._lower_while(stmt)
        elif isinstance(stmt, ForStmt):
            self._lower_for(stmt)
        elif isinstance(stmt, ExprStmt):
            self._lower_expression(stmt.expr)
        elif isinstance(stmt, BreakStmt):
            self._lower_break()
        elif isinstance(stmt, ContinueStmt):
            self._lower_continue()
        elif isinstance(stmt, DiscardStmt):
            pass  # Nothing to do

    def _lower_var_decl(self, decl: VarDecl) -> None:
        """Lower a variable declaration."""
        ty = brainhair_type_to_mir(decl.var_type)

        # Allocate stack space
        ptr = self.builder.alloca(ty, decl.name)

        # Store initial value if present
        if decl.value:
            value = self._lower_expression(decl.value)
            self.builder.store(value, ptr)

        # Record in variables map
        self.variables[decl.name] = VariableInfo(ptr, ty, decl.is_const)

    def _lower_assignment(self, stmt: Assignment) -> None:
        """Lower an assignment statement."""
        value = self._lower_expression(stmt.value)

        if isinstance(stmt.target, Identifier):
            # Simple variable assignment
            var_info = self.variables.get(stmt.target.name)
            if var_info:
                self.builder.store(value, var_info.ptr)
        elif isinstance(stmt.target, IndexExpr):
            # Array/pointer element assignment
            ptr = self._lower_lvalue(stmt.target)
            self.builder.store(value, ptr)
        elif isinstance(stmt.target, FieldAccessExpr):
            # Struct field assignment
            ptr = self._lower_lvalue(stmt.target)
            self.builder.store(value, ptr)
        elif isinstance(stmt.target, DerefExpr):
            # Pointer dereference assignment
            ptr = self._lower_expression(stmt.target.expr)
            self.builder.store(value, ptr)

    def _lower_lvalue(self, expr: ASTNode) -> MIRValue:
        """
        Lower an expression to get its address (for assignment targets).
        Returns a pointer to the location.
        """
        if isinstance(expr, Identifier):
            var_info = self.variables.get(expr.name)
            if var_info:
                return var_info.ptr
            # Could be a global
            glob = self.module.globals.get(expr.name)
            if glob:
                return glob
            raise ValueError(f"Unknown variable: {expr.name}")

        elif isinstance(expr, IndexExpr):
            base = self._lower_expression(expr.base)
            index = self._lower_expression(expr.index)
            return self.builder.gep(base, [index])

        elif isinstance(expr, FieldAccessExpr):
            base = self._lower_lvalue(expr.object)
            # For struct field access, we need field index
            # This is simplified - real implementation would look up field offset
            field_idx = self.builder.const_int(0)  # Placeholder
            return self.builder.gep(base, [field_idx])

        elif isinstance(expr, DerefExpr):
            return self._lower_expression(expr.expr)

        raise ValueError(f"Cannot get lvalue for {type(expr).__name__}")

    def _lower_return(self, stmt: ReturnStmt) -> None:
        """Lower a return statement."""
        if stmt.value:
            value = self._lower_expression(stmt.value)
            self.builder.ret(value)
        else:
            self.builder.ret()

    def _lower_if(self, stmt: IfStmt) -> None:
        """Lower an if statement."""
        # Create blocks
        then_block = self.current_func.create_block("if.then")
        merge_block = self.current_func.create_block("if.end")

        # Handle else/elif
        if stmt.elif_blocks or stmt.else_block:
            else_block = self.current_func.create_block("if.else")
        else:
            else_block = merge_block

        # Evaluate condition
        cond = self._lower_expression(stmt.condition)
        self.builder.cond_br(cond, then_block, else_block)

        # Then block
        self.builder.set_insert_point(then_block)
        for s in stmt.then_block:
            self._lower_statement(s)
        if not self.builder.current_block.is_terminated():
            self.builder.br(merge_block)

        # Elif blocks
        if stmt.elif_blocks:
            for i, (elif_cond, elif_body) in enumerate(stmt.elif_blocks):
                self.builder.set_insert_point(else_block)

                # Next elif/else block
                if i + 1 < len(stmt.elif_blocks):
                    next_else = self.current_func.create_block(f"elif.else.{i}")
                elif stmt.else_block:
                    next_else = self.current_func.create_block("else")
                else:
                    next_else = merge_block

                elif_then = self.current_func.create_block(f"elif.then.{i}")

                cond = self._lower_expression(elif_cond)
                self.builder.cond_br(cond, elif_then, next_else)

                self.builder.set_insert_point(elif_then)
                for s in elif_body:
                    self._lower_statement(s)
                if not self.builder.current_block.is_terminated():
                    self.builder.br(merge_block)

                else_block = next_else

        # Else block
        if stmt.else_block:
            self.builder.set_insert_point(else_block)
            for s in stmt.else_block:
                self._lower_statement(s)
            if not self.builder.current_block.is_terminated():
                self.builder.br(merge_block)

        # Continue with merge block
        self.builder.set_insert_point(merge_block)

    def _lower_while(self, stmt: WhileStmt) -> None:
        """Lower a while loop."""
        cond_block = self.current_func.create_block("while.cond")
        body_block = self.current_func.create_block("while.body")
        end_block = self.current_func.create_block("while.end")

        # Push loop context
        self.loop_stack.append((cond_block, end_block))

        # Jump to condition
        self.builder.br(cond_block)

        # Condition block
        self.builder.set_insert_point(cond_block)
        cond = self._lower_expression(stmt.condition)
        self.builder.cond_br(cond, body_block, end_block)

        # Body block
        self.builder.set_insert_point(body_block)
        for s in stmt.body:
            self._lower_statement(s)
        if not self.builder.current_block.is_terminated():
            self.builder.br(cond_block)

        # Pop loop context
        self.loop_stack.pop()

        # Continue after loop
        self.builder.set_insert_point(end_block)

    def _lower_for(self, stmt: ForStmt) -> None:
        """Lower a for loop."""
        # Allocate loop variable
        loop_var_ty = MIRType.I32  # Default to i32
        ptr = self.builder.alloca(loop_var_ty, stmt.var)
        self.variables[stmt.var] = VariableInfo(ptr, loop_var_ty)

        # Initialize with start value
        start = self._lower_expression(stmt.start)
        self.builder.store(start, ptr)

        # Create blocks
        cond_block = self.current_func.create_block("for.cond")
        body_block = self.current_func.create_block("for.body")
        inc_block = self.current_func.create_block("for.inc")
        end_block = self.current_func.create_block("for.end")

        # Push loop context (continue goes to inc, break goes to end)
        self.loop_stack.append((inc_block, end_block))

        # Jump to condition
        self.builder.br(cond_block)

        # Condition block: loop_var < end
        self.builder.set_insert_point(cond_block)
        current = self.builder.load(ptr)
        end = self._lower_expression(stmt.end)
        cond = self.builder.cmp_lt(current, end)
        self.builder.cond_br(cond, body_block, end_block)

        # Body block
        self.builder.set_insert_point(body_block)
        for s in stmt.body:
            self._lower_statement(s)
        if not self.builder.current_block.is_terminated():
            self.builder.br(inc_block)

        # Increment block
        self.builder.set_insert_point(inc_block)
        current = self.builder.load(ptr)
        one = self.builder.const_int(1)
        next_val = self.builder.add(current, one)
        self.builder.store(next_val, ptr)
        self.builder.br(cond_block)

        # Pop loop context
        self.loop_stack.pop()

        # Clean up loop variable (set to None for Brainhair compatibility)
        self.variables[stmt.var] = None

        # Continue after loop
        self.builder.set_insert_point(end_block)

    def _lower_break(self) -> None:
        """Lower a break statement."""
        if self.loop_stack:
            _, break_block = self.loop_stack[-1]
            self.builder.br(break_block)

    def _lower_continue(self) -> None:
        """Lower a continue statement."""
        if self.loop_stack:
            continue_block, _ = self.loop_stack[-1]
            self.builder.br(continue_block)

    def _lower_expression(self, expr: ASTNode) -> MIRValue:
        """Lower an expression to MIR, returning its value."""
        if isinstance(expr, IntLiteral):
            return self.builder.const_int(expr.value)

        elif isinstance(expr, CharLiteral):
            return self.builder.const_int(ord(expr.value), MIRType.I8)

        elif isinstance(expr, BoolLiteral):
            return self.builder.const_bool(expr.value)

        elif isinstance(expr, StringLiteral):
            # Strings are represented as global constant pointers
            # For now, return a placeholder
            return self.builder.const_int(0, PointerMIRType(MIRType.I8))

        elif isinstance(expr, Identifier):
            var_info = self.variables.get(expr.name)
            if var_info:
                # Load the value from the stack slot
                return self.builder.load(var_info.ptr)
            # Could be a global or function
            glob = self.module.globals.get(expr.name)
            if glob:
                return self.builder.load(glob)
            func = self.module.get_function(expr.name)
            if func:
                return MIRGlobal(f"@{expr.name}", PointerMIRType(MIRType.VOID), is_function=True)
            raise ValueError(f"Unknown identifier: {expr.name}")

        elif isinstance(expr, BinaryExpr):
            return self._lower_binary_expr(expr)

        elif isinstance(expr, UnaryExpr):
            return self._lower_unary_expr(expr)

        elif isinstance(expr, CallExpr):
            return self._lower_call_expr(expr)

        elif isinstance(expr, CastExpr):
            value = self._lower_expression(expr.expr)
            target_ty = brainhair_type_to_mir(expr.target_type)
            return self.builder.cast(value, target_ty)

        elif isinstance(expr, IndexExpr):
            base = self._lower_expression(expr.base)
            index = self._lower_expression(expr.index)
            ptr = self.builder.gep(base, [index])
            return self.builder.load(ptr)

        elif isinstance(expr, AddrOfExpr):
            return self._lower_lvalue(expr.expr)

        elif isinstance(expr, DerefExpr):
            ptr = self._lower_expression(expr.expr)
            return self.builder.load(ptr)

        elif isinstance(expr, ConditionalExpr):
            return self._lower_conditional_expr(expr)

        elif isinstance(expr, FieldAccessExpr):
            ptr = self._lower_lvalue(expr)
            return self.builder.load(ptr)

        # Fallback for unhandled expressions
        raise NotImplementedError(f"Expression type {type(expr).__name__} not implemented")

    def _lower_binary_expr(self, expr: BinaryExpr) -> MIRValue:
        """Lower a binary expression."""
        left = self._lower_expression(expr.left)
        right = self._lower_expression(expr.right)

        op_map = {
            BinOp.ADD: self.builder.add,
            BinOp.SUB: self.builder.sub,
            BinOp.MUL: self.builder.mul,
            BinOp.DIV: self.builder.div,
            BinOp.MOD: self.builder.mod,
            BinOp.BIT_AND: self.builder.and_,
            BinOp.BIT_OR: self.builder.or_,
            BinOp.BIT_XOR: self.builder.xor,
            BinOp.SHL: self.builder.shl,
            BinOp.SHR: self.builder.shr,
            BinOp.EQ: self.builder.cmp_eq,
            BinOp.NEQ: self.builder.cmp_ne,
            BinOp.LT: self.builder.cmp_lt,
            BinOp.LTE: self.builder.cmp_le,
            BinOp.GT: self.builder.cmp_gt,
            BinOp.GTE: self.builder.cmp_ge,
        }

        if expr.op in op_map:
            return op_map[expr.op](left, right)

        # Logical operators need short-circuit evaluation
        if expr.op == BinOp.AND:
            return self._lower_logical_and(expr)
        elif expr.op == BinOp.OR:
            return self._lower_logical_or(expr)

        raise NotImplementedError(f"Binary operator {expr.op} not implemented")

    def _lower_logical_and(self, expr: BinaryExpr) -> MIRValue:
        """Lower logical AND with short-circuit evaluation."""
        left = self._lower_expression(expr.left)

        # Create blocks for short-circuit
        rhs_block = self.current_func.create_block("and.rhs")
        merge_block = self.current_func.create_block("and.merge")

        # If left is false, skip right side
        self.builder.cond_br(left, rhs_block, merge_block)

        # Evaluate right side
        self.builder.set_insert_point(rhs_block)
        right = self._lower_expression(expr.right)
        self.builder.br(merge_block)
        rhs_block = self.builder.current_block  # May have changed

        # Merge with phi
        self.builder.set_insert_point(merge_block)
        false_const = self.builder.const_bool(False)
        return self.builder.phi(MIRType.BOOL, [
            (false_const, rhs_block.predecessors[0] if rhs_block.predecessors else self.builder.current_block),
            (right, rhs_block)
        ])

    def _lower_logical_or(self, expr: BinaryExpr) -> MIRValue:
        """Lower logical OR with short-circuit evaluation."""
        left = self._lower_expression(expr.left)

        # Create blocks for short-circuit
        rhs_block = self.current_func.create_block("or.rhs")
        merge_block = self.current_func.create_block("or.merge")

        # If left is true, skip right side
        self.builder.cond_br(left, merge_block, rhs_block)

        # Evaluate right side
        self.builder.set_insert_point(rhs_block)
        right = self._lower_expression(expr.right)
        self.builder.br(merge_block)
        rhs_block = self.builder.current_block

        # Merge with phi
        self.builder.set_insert_point(merge_block)
        true_const = self.builder.const_bool(True)
        return self.builder.phi(MIRType.BOOL, [
            (true_const, rhs_block.predecessors[0] if rhs_block.predecessors else self.builder.current_block),
            (right, rhs_block)
        ])

    def _lower_unary_expr(self, expr: UnaryExpr) -> MIRValue:
        """Lower a unary expression."""
        operand = self._lower_expression(expr.expr)

        if expr.op == UnaryOp.NEG:
            return self.builder.neg(operand)
        elif expr.op == UnaryOp.NOT:
            return self.builder.not_(operand)

        raise NotImplementedError(f"Unary operator {expr.op} not implemented")

    def _lower_call_expr(self, expr: CallExpr) -> MIRValue:
        """Lower a function call."""
        # Lower arguments
        args = [self._lower_expression(arg) for arg in expr.args]

        # Get return type from function
        func = self.module.get_function(expr.func)
        return_ty = func.return_type if func else MIRType.I32

        return self.builder.call(expr.func, args, return_ty)

    def _lower_conditional_expr(self, expr: ConditionalExpr) -> MIRValue:
        """Lower a conditional (ternary) expression."""
        cond = self._lower_expression(expr.condition)

        then_block = self.current_func.create_block("cond.then")
        else_block = self.current_func.create_block("cond.else")
        merge_block = self.current_func.create_block("cond.merge")

        self.builder.cond_br(cond, then_block, else_block)

        # Then branch
        self.builder.set_insert_point(then_block)
        then_val = self._lower_expression(expr.then_expr)
        self.builder.br(merge_block)
        then_block = self.builder.current_block

        # Else branch
        self.builder.set_insert_point(else_block)
        else_val = self._lower_expression(expr.else_expr)
        self.builder.br(merge_block)
        else_block = self.builder.current_block

        # Merge with phi
        self.builder.set_insert_point(merge_block)
        return self.builder.phi(then_val.ty, [
            (then_val, then_block),
            (else_val, else_block)
        ])


def lower_to_mir(program: Program) -> MIRModule:
    """
    Convenience function to lower AST to MIR.

    Args:
        program: The AST program node

    Returns:
        MIR module
    """
    lowerer = ASTToMIRLowerer()
    return lowerer.lower(program)


# ============================================================================
# Test
# ============================================================================

if __name__ == "__main__":
    # Test with a simple program
    from lexer import Lexer
    from parser import Parser

    code = """
proc add(a: int32, b: int32): int32 =
  return a + b

proc main() =
  var x: int32 = 10
  var y: int32 = 20
  var z: int32 = add(x, y)
  if z > 25:
    z = z - 5
  return
"""

    lexer = Lexer(code)
    tokens = lexer.tokenize()

    parser = Parser(tokens)
    ast = parser.parse()

    mir = lower_to_mir(ast)
    print(mir)
