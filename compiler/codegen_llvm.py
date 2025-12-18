#!/usr/bin/env python3
"""
LLVM IR Code Generator for Brainhair Compiler

Generates LLVM IR text from Brainhair AST.
Target: i686-unknown-linux-gnu (32-bit x86 Linux)

Output can be compiled with:
  llc -march=x86 -filetype=obj output.ll -o output.o
  clang -m32 output.ll -o output
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
from enum import Enum, auto

from ast_nodes import *
from llvm_types import (
    LLVMTypeMapper, LLVMType, LLVMIntType, LLVMFloatType,
    LLVMVoidType, LLVMPointerType, LLVMArrayType, LLVMStructType
)


class LLVMCodeGen:
    """
    Generates LLVM IR from Brainhair AST.

    Produces textual LLVM IR that can be compiled with llc or clang.
    """

    def __init__(self):
        self.type_mapper = LLVMTypeMapper()
        self.output: List[str] = []
        self.current_function: Optional[str] = None
        self.temp_counter = 0
        self.label_counter = 0
        self.string_counter = 0

        # Track local variables (name -> LLVM register)
        self.locals: Dict[str, str] = {}
        # Track local variable types
        self.local_types: Dict[str, LLVMType] = {}

        # Global strings
        self.string_literals: List[Tuple[str, str]] = []

        # Extern declarations
        self.externs: Set[str] = set()

    def generate(self, program: Program) -> str:
        """Generate LLVM IR for entire program."""
        self.output = []
        self.string_literals = []
        self.externs = set()

        # Target triple and data layout for 32-bit Linux
        self._emit("; ModuleID = 'brainhair'")
        self._emit('target datalayout = "e-m:e-p:32:32-p270:32:32-p271:32:32-p272:64:64-f64:32:64-f80:32-n8:16:32-S128"')
        self._emit('target triple = "i686-unknown-linux-gnu"')
        self._emit("")

        # First pass: collect struct definitions
        for decl in program.declarations:
            if isinstance(decl, StructDecl):
                self._define_struct(decl)

        # Emit struct definitions
        if self.type_mapper.struct_definitions:
            for defn in self.type_mapper.struct_definitions:
                self._emit(defn)
            self._emit("")

        # Second pass: generate code
        for decl in program.declarations:
            if isinstance(decl, ProcDecl):
                self._gen_proc(decl)
            elif isinstance(decl, VarDecl):
                self._gen_global_var(decl)
            elif isinstance(decl, ExternDecl):
                self._gen_extern(decl)

        # Emit string literals
        if self.string_literals:
            self._emit("")
            self._emit("; String literals")
            for name, value in self.string_literals:
                escaped = self._escape_string(value)
                length = len(value) + 1  # +1 for null terminator
                self._emit(f'{name} = private unnamed_addr constant [{length} x i8] c"{escaped}\\00"')

        return "\n".join(self.output)

    def _emit(self, line: str) -> None:
        """Emit a line of LLVM IR."""
        self.output.append(line)

    def _emit_indented(self, line: str) -> None:
        """Emit an indented line (for function bodies)."""
        self.output.append(f"  {line}")

    def _new_temp(self) -> str:
        """Generate a new temporary register name."""
        self.temp_counter += 1
        return f"%t{self.temp_counter}"

    def _new_label(self, prefix: str = "L") -> str:
        """Generate a new label name."""
        self.label_counter += 1
        return f"{prefix}{self.label_counter}"

    def _new_string(self, value: str) -> str:
        """Create a new string literal and return its name."""
        self.string_counter += 1
        name = f"@.str.{self.string_counter}"
        self.string_literals.append((name, value))
        return name

    def _escape_string(self, s: str) -> str:
        """Escape a string for LLVM IR."""
        result = []
        for c in s:
            if c == '\n':
                result.append('\\0A')
            elif c == '\r':
                result.append('\\0D')
            elif c == '\t':
                result.append('\\09')
            elif c == '"':
                result.append('\\22')
            elif c == '\\':
                result.append('\\5C')
            elif ord(c) < 32 or ord(c) > 126:
                result.append(f'\\{ord(c):02X}')
            else:
                result.append(c)
        return ''.join(result)

    def _define_struct(self, decl: StructDecl) -> None:
        """Define a struct type."""
        fields = [(f.name, f.field_type) for f in decl.fields]
        self.type_mapper.define_struct(decl.name, fields)

    def _gen_extern(self, decl: ExternDecl) -> None:
        """Generate extern declaration."""
        if decl.name in self.externs:
            return
        self.externs.add(decl.name)

        # Map return type
        ret_type = self.type_mapper.map_type(decl.return_type)

        # Map parameter types
        param_types = []
        for param in decl.params:
            ptype = self.type_mapper.map_type(param.param_type)
            param_types.append(str(ptype))

        params_str = ", ".join(param_types)
        self._emit(f"declare {ret_type} @{decl.name}({params_str})")

    def _gen_global_var(self, decl: VarDecl) -> None:
        """Generate a global variable."""
        llvm_type = self.type_mapper.map_type(decl.var_type)

        # Initialize with zero if no value
        if decl.value:
            init_val = self._gen_const_expr(decl.value)
        else:
            init_val = self._get_zero_init(llvm_type)

        self._emit(f"@{decl.name} = global {llvm_type} {init_val}")

    def _get_zero_init(self, ty: LLVMType) -> str:
        """Get zero initializer for a type."""
        if isinstance(ty, LLVMIntType):
            return "0"
        elif isinstance(ty, LLVMFloatType):
            return "0.0"
        elif isinstance(ty, LLVMPointerType):
            return "null"
        elif isinstance(ty, LLVMArrayType):
            return "zeroinitializer"
        elif isinstance(ty, LLVMStructType):
            return "zeroinitializer"
        return "0"

    def _gen_const_expr(self, expr: ASTNode) -> str:
        """Generate a constant expression."""
        if isinstance(expr, IntLiteral):
            return str(expr.value)
        elif isinstance(expr, BoolLiteral):
            return "1" if expr.value else "0"
        elif isinstance(expr, CharLiteral):
            return str(ord(expr.value))
        elif isinstance(expr, StringLiteral):
            # Return a pointer to the string
            name = self._new_string(expr.value)
            length = len(expr.value) + 1
            return f"getelementptr inbounds ([{length} x i8], [{length} x i8]* {name}, i32 0, i32 0)"
        return "0"

    def _gen_proc(self, proc: ProcDecl) -> None:
        """Generate a procedure/function."""
        self.current_function = proc.name
        self.temp_counter = 0
        self.label_counter = 0
        self.locals = {}
        self.local_types = {}

        # Map return type
        ret_type = self.type_mapper.map_type(proc.return_type)

        # Build parameter list
        params = []
        for param in proc.params:
            ptype = self.type_mapper.map_type(param.param_type)
            params.append(f"{ptype} %{param.name}.arg")

        params_str = ", ".join(params)

        # Function header
        self._emit("")
        self._emit(f"define {ret_type} @{proc.name}({params_str}) {{")
        self._emit_indented("")

        # Entry block
        self._emit("entry:")

        # Allocate stack space for parameters
        for param in proc.params:
            ptype = self.type_mapper.map_type(param.param_type)
            ptr = f"%{param.name}"
            self._emit_indented(f"{ptr} = alloca {ptype}")
            self._emit_indented(f"store {ptype} %{param.name}.arg, {ptype}* {ptr}")
            self.locals[param.name] = ptr
            self.local_types[param.name] = ptype

        # Generate body
        for stmt in proc.body:
            self._gen_statement(stmt)

        # Add implicit return if needed
        if isinstance(ret_type, LLVMVoidType):
            self._emit_indented("ret void")
        elif not self.output[-1].strip().startswith("ret"):
            # Add default return
            self._emit_indented(f"ret {ret_type} {self._get_zero_init(ret_type)}")

        self._emit("}")
        self.current_function = None

    def _gen_statement(self, stmt: ASTNode) -> None:
        """Generate a statement."""
        if isinstance(stmt, VarDecl):
            self._gen_var_decl(stmt)
        elif isinstance(stmt, Assignment):
            self._gen_assignment(stmt)
        elif isinstance(stmt, ReturnStmt):
            self._gen_return(stmt)
        elif isinstance(stmt, IfStmt):
            self._gen_if(stmt)
        elif isinstance(stmt, WhileStmt):
            self._gen_while(stmt)
        elif isinstance(stmt, ForStmt):
            self._gen_for(stmt)
        elif isinstance(stmt, ExprStmt):
            self._gen_expr(stmt.expr)
        elif isinstance(stmt, DiscardStmt):
            self._gen_expr(stmt.expr)

    def _gen_var_decl(self, decl: VarDecl) -> None:
        """Generate a local variable declaration."""
        llvm_type = self.type_mapper.map_type(decl.var_type)
        ptr = f"%{decl.name}"

        # Allocate on stack
        self._emit_indented(f"{ptr} = alloca {llvm_type}")
        self.locals[decl.name] = ptr
        self.local_types[decl.name] = llvm_type

        # Initialize if value provided
        if decl.value:
            val, val_type = self._gen_expr(decl.value)
            self._emit_indented(f"store {val_type} {val}, {llvm_type}* {ptr}")

    def _gen_assignment(self, stmt: Assignment) -> None:
        """Generate an assignment."""
        val, val_type = self._gen_expr(stmt.value)

        if isinstance(stmt.target, Identifier):
            ptr = self.locals.get(stmt.target.name)
            if ptr:
                target_type = self.local_types.get(stmt.target.name, val_type)
                self._emit_indented(f"store {val_type} {val}, {target_type}* {ptr}")
            else:
                # Global variable
                target_type = val_type
                self._emit_indented(f"store {val_type} {val}, {target_type}* @{stmt.target.name}")

        elif isinstance(stmt.target, IndexExpr):
            # Array/pointer index assignment
            ptr, ptr_type = self._gen_gep(stmt.target)
            self._emit_indented(f"store {val_type} {val}, {ptr_type} {ptr}")

        elif isinstance(stmt.target, DerefExpr):
            # Pointer dereference assignment
            ptr_val, ptr_type = self._gen_expr(stmt.target.expr)
            self._emit_indented(f"store {val_type} {val}, {ptr_type} {ptr_val}")

        elif isinstance(stmt.target, FieldAccessExpr):
            # Struct field assignment
            ptr, ptr_type = self._gen_field_gep(stmt.target)
            self._emit_indented(f"store {val_type} {val}, {ptr_type} {ptr}")

    def _gen_return(self, stmt: ReturnStmt) -> None:
        """Generate a return statement."""
        if stmt.value:
            val, val_type = self._gen_expr(stmt.value)
            self._emit_indented(f"ret {val_type} {val}")
        else:
            self._emit_indented("ret void")

    def _gen_if(self, stmt: IfStmt) -> None:
        """Generate an if statement."""
        then_label = self._new_label("then")
        else_label = self._new_label("else")
        end_label = self._new_label("endif")

        # Generate condition
        cond, _ = self._gen_expr(stmt.condition)
        self._emit_indented(f"br i1 {cond}, label %{then_label}, label %{else_label}")

        # Then block
        self._emit(f"{then_label}:")
        for s in stmt.then_block:
            self._gen_statement(s)
        self._emit_indented(f"br label %{end_label}")

        # Else block
        self._emit(f"{else_label}:")
        if stmt.else_block:
            for s in stmt.else_block:
                self._gen_statement(s)
        self._emit_indented(f"br label %{end_label}")

        # End
        self._emit(f"{end_label}:")

    def _gen_while(self, stmt: WhileStmt) -> None:
        """Generate a while loop."""
        cond_label = self._new_label("while.cond")
        body_label = self._new_label("while.body")
        end_label = self._new_label("while.end")

        # Branch to condition
        self._emit_indented(f"br label %{cond_label}")

        # Condition block
        self._emit(f"{cond_label}:")
        cond, _ = self._gen_expr(stmt.condition)
        self._emit_indented(f"br i1 {cond}, label %{body_label}, label %{end_label}")

        # Body block
        self._emit(f"{body_label}:")
        for s in stmt.body:
            self._gen_statement(s)
        self._emit_indented(f"br label %{cond_label}")

        # End
        self._emit(f"{end_label}:")

    def _gen_for(self, stmt: ForStmt) -> None:
        """Generate a for loop."""
        cond_label = self._new_label("for.cond")
        body_label = self._new_label("for.body")
        inc_label = self._new_label("for.inc")
        end_label = self._new_label("for.end")

        # Initialize loop variable
        start_val, _ = self._gen_expr(stmt.start)
        ptr = f"%{stmt.var}"
        self._emit_indented(f"{ptr} = alloca i32")
        self._emit_indented(f"store i32 {start_val}, i32* {ptr}")
        self.locals[stmt.var] = ptr
        self.local_types[stmt.var] = LLVMIntType(32)

        # Branch to condition
        self._emit_indented(f"br label %{cond_label}")

        # Condition block
        self._emit(f"{cond_label}:")
        end_val, _ = self._gen_expr(stmt.end)
        current = self._new_temp()
        self._emit_indented(f"{current} = load i32, i32* {ptr}")
        cond = self._new_temp()
        self._emit_indented(f"{cond} = icmp slt i32 {current}, {end_val}")
        self._emit_indented(f"br i1 {cond}, label %{body_label}, label %{end_label}")

        # Body block
        self._emit(f"{body_label}:")
        for s in stmt.body:
            self._gen_statement(s)
        self._emit_indented(f"br label %{inc_label}")

        # Increment block
        self._emit(f"{inc_label}:")
        curr = self._new_temp()
        self._emit_indented(f"{curr} = load i32, i32* {ptr}")
        next_val = self._new_temp()
        self._emit_indented(f"{next_val} = add i32 {curr}, 1")
        self._emit_indented(f"store i32 {next_val}, i32* {ptr}")
        self._emit_indented(f"br label %{cond_label}")

        # End
        self._emit(f"{end_label}:")

        # Remove loop variable from scope
        del self.locals[stmt.var]

    def _gen_expr(self, expr: ASTNode) -> Tuple[str, LLVMType]:
        """Generate an expression. Returns (value, type)."""

        if isinstance(expr, IntLiteral):
            return str(expr.value), LLVMIntType(32)

        elif isinstance(expr, BoolLiteral):
            return ("1" if expr.value else "0"), LLVMIntType(1)

        elif isinstance(expr, CharLiteral):
            return str(ord(expr.value)), LLVMIntType(8)

        elif isinstance(expr, StringLiteral):
            name = self._new_string(expr.value)
            length = len(expr.value) + 1
            ptr = self._new_temp()
            self._emit_indented(f"{ptr} = getelementptr inbounds [{length} x i8], [{length} x i8]* {name}, i32 0, i32 0")
            return ptr, LLVMPointerType(LLVMIntType(8))

        elif isinstance(expr, Identifier):
            ptr = self.locals.get(expr.name)
            if ptr:
                llvm_type = self.local_types.get(expr.name, LLVMIntType(32))
                result = self._new_temp()
                self._emit_indented(f"{result} = load {llvm_type}, {llvm_type}* {ptr}")
                return result, llvm_type
            else:
                # Global variable
                result = self._new_temp()
                # Assume i32 for now
                self._emit_indented(f"{result} = load i32, i32* @{expr.name}")
                return result, LLVMIntType(32)

        elif isinstance(expr, BinaryExpr):
            return self._gen_binary(expr)

        elif isinstance(expr, UnaryExpr):
            return self._gen_unary(expr)

        elif isinstance(expr, CallExpr):
            return self._gen_call(expr)

        elif isinstance(expr, IndexExpr):
            ptr, ptr_type = self._gen_gep(expr)
            result = self._new_temp()
            elem_type = ptr_type.pointee if isinstance(ptr_type, LLVMPointerType) else LLVMIntType(32)
            self._emit_indented(f"{result} = load {elem_type}, {ptr_type} {ptr}")
            return result, elem_type

        elif isinstance(expr, AddrOfExpr):
            if isinstance(expr.expr, Identifier):
                ptr = self.locals.get(expr.expr.name)
                if ptr:
                    llvm_type = self.local_types.get(expr.expr.name, LLVMIntType(32))
                    return ptr, LLVMPointerType(llvm_type)
            return "null", LLVMPointerType(LLVMIntType(8))

        elif isinstance(expr, DerefExpr):
            ptr_val, ptr_type = self._gen_expr(expr.expr)
            result = self._new_temp()
            elem_type = ptr_type.pointee if isinstance(ptr_type, LLVMPointerType) else LLVMIntType(32)
            self._emit_indented(f"{result} = load {elem_type}, {ptr_type} {ptr_val}")
            return result, elem_type

        elif isinstance(expr, CastExpr):
            val, from_type = self._gen_expr(expr.expr)
            to_type = self.type_mapper.map_type(expr.target_type)
            return self._gen_cast(val, from_type, to_type)

        elif isinstance(expr, FieldAccessExpr):
            ptr, ptr_type = self._gen_field_gep(expr)
            result = self._new_temp()
            elem_type = ptr_type.pointee if isinstance(ptr_type, LLVMPointerType) else LLVMIntType(32)
            self._emit_indented(f"{result} = load {elem_type}, {ptr_type} {ptr}")
            return result, elem_type

        return "0", LLVMIntType(32)

    def _gen_binary(self, expr: BinaryExpr) -> Tuple[str, LLVMType]:
        """Generate a binary expression."""
        left, left_type = self._gen_expr(expr.left)
        right, right_type = self._gen_expr(expr.right)
        result = self._new_temp()

        op = expr.op

        # Integer operations
        if isinstance(left_type, LLVMIntType):
            if op == '+':
                self._emit_indented(f"{result} = add {left_type} {left}, {right}")
            elif op == '-':
                self._emit_indented(f"{result} = sub {left_type} {left}, {right}")
            elif op == '*':
                self._emit_indented(f"{result} = mul {left_type} {left}, {right}")
            elif op == '/':
                self._emit_indented(f"{result} = sdiv {left_type} {left}, {right}")
            elif op == '%':
                self._emit_indented(f"{result} = srem {left_type} {left}, {right}")
            elif op == '&':
                self._emit_indented(f"{result} = and {left_type} {left}, {right}")
            elif op == '|':
                self._emit_indented(f"{result} = or {left_type} {left}, {right}")
            elif op == '^':
                self._emit_indented(f"{result} = xor {left_type} {left}, {right}")
            elif op == '<<':
                self._emit_indented(f"{result} = shl {left_type} {left}, {right}")
            elif op == '>>':
                self._emit_indented(f"{result} = ashr {left_type} {left}, {right}")
            elif op == '==':
                self._emit_indented(f"{result} = icmp eq {left_type} {left}, {right}")
                return result, LLVMIntType(1)
            elif op == '!=':
                self._emit_indented(f"{result} = icmp ne {left_type} {left}, {right}")
                return result, LLVMIntType(1)
            elif op == '<':
                self._emit_indented(f"{result} = icmp slt {left_type} {left}, {right}")
                return result, LLVMIntType(1)
            elif op == '<=':
                self._emit_indented(f"{result} = icmp sle {left_type} {left}, {right}")
                return result, LLVMIntType(1)
            elif op == '>':
                self._emit_indented(f"{result} = icmp sgt {left_type} {left}, {right}")
                return result, LLVMIntType(1)
            elif op == '>=':
                self._emit_indented(f"{result} = icmp sge {left_type} {left}, {right}")
                return result, LLVMIntType(1)
            elif op == 'and':
                self._emit_indented(f"{result} = and {left_type} {left}, {right}")
            elif op == 'or':
                self._emit_indented(f"{result} = or {left_type} {left}, {right}")
            else:
                self._emit_indented(f"{result} = add {left_type} {left}, {right}")
            return result, left_type

        return result, left_type

    def _gen_unary(self, expr: UnaryExpr) -> Tuple[str, LLVMType]:
        """Generate a unary expression."""
        val, val_type = self._gen_expr(expr.expr)
        result = self._new_temp()
        op = expr.op

        if op == '-':
            self._emit_indented(f"{result} = sub {val_type} 0, {val}")
        elif op == 'not' or op == '!':
            self._emit_indented(f"{result} = xor {val_type} {val}, 1")
        elif op == '~':
            self._emit_indented(f"{result} = xor {val_type} {val}, -1")
        else:
            return val, val_type

        return result, val_type

    def _gen_call(self, expr: CallExpr) -> Tuple[str, LLVMType]:
        """Generate a function call."""
        # Generate arguments
        args = []
        for arg in expr.args:
            val, val_type = self._gen_expr(arg)
            args.append(f"{val_type} {val}")

        args_str = ", ".join(args)

        # TODO: Look up actual return type
        ret_type = LLVMIntType(32)

        if isinstance(ret_type, LLVMVoidType):
            self._emit_indented(f"call void @{expr.func}({args_str})")
            return "void", ret_type
        else:
            result = self._new_temp()
            self._emit_indented(f"{result} = call {ret_type} @{expr.func}({args_str})")
            return result, ret_type

    def _gen_gep(self, expr: IndexExpr) -> Tuple[str, LLVMType]:
        """Generate a GEP (getelementptr) for array/pointer indexing."""
        # Get base pointer
        if isinstance(expr.array, Identifier):
            ptr = self.locals.get(expr.array.name)
            base_type = self.local_types.get(expr.array.name, LLVMIntType(32))

            if isinstance(base_type, LLVMArrayType):
                # Array: need to load address and index
                idx, _ = self._gen_expr(expr.index)
                result = self._new_temp()
                elem_type = base_type.element_type
                self._emit_indented(f"{result} = getelementptr inbounds {base_type}, {base_type}* {ptr}, i32 0, i32 {idx}")
                return result, LLVMPointerType(elem_type)

            elif isinstance(base_type, LLVMPointerType):
                # Pointer: load then index
                loaded = self._new_temp()
                self._emit_indented(f"{loaded} = load {base_type}, {base_type}* {ptr}")
                idx, _ = self._gen_expr(expr.index)
                result = self._new_temp()
                elem_type = base_type.pointee
                self._emit_indented(f"{result} = getelementptr inbounds {elem_type}, {base_type} {loaded}, i32 {idx}")
                return result, LLVMPointerType(elem_type)

        # Fallback
        idx, _ = self._gen_expr(expr.index)
        return f"null", LLVMPointerType(LLVMIntType(8))

    def _gen_field_gep(self, expr: FieldAccessExpr) -> Tuple[str, LLVMType]:
        """Generate GEP for struct field access."""
        # Get base struct pointer
        if isinstance(expr.object, Identifier):
            ptr = self.locals.get(expr.object.name)
            struct_type = self.local_types.get(expr.object.name)

            if struct_type and isinstance(struct_type, LLVMStructType):
                # Get field index
                field_idx = self.type_mapper.get_struct_field_index(struct_type.name, expr.field)
                if field_idx >= 0:
                    result = self._new_temp()
                    field_type = struct_type.fields[field_idx][1]
                    self._emit_indented(f"{result} = getelementptr inbounds {struct_type}, {struct_type}* {ptr}, i32 0, i32 {field_idx}")
                    return result, LLVMPointerType(field_type)

        return "null", LLVMPointerType(LLVMIntType(32))

    def _gen_cast(self, val: str, from_type: LLVMType, to_type: LLVMType) -> Tuple[str, LLVMType]:
        """Generate a type cast."""
        if str(from_type) == str(to_type):
            return val, to_type

        result = self._new_temp()

        # Integer to integer
        if isinstance(from_type, LLVMIntType) and isinstance(to_type, LLVMIntType):
            if from_type.bits < to_type.bits:
                self._emit_indented(f"{result} = sext {from_type} {val} to {to_type}")
            else:
                self._emit_indented(f"{result} = trunc {from_type} {val} to {to_type}")

        # Pointer to integer
        elif isinstance(from_type, LLVMPointerType) and isinstance(to_type, LLVMIntType):
            self._emit_indented(f"{result} = ptrtoint {from_type} {val} to {to_type}")

        # Integer to pointer
        elif isinstance(from_type, LLVMIntType) and isinstance(to_type, LLVMPointerType):
            self._emit_indented(f"{result} = inttoptr {from_type} {val} to {to_type}")

        # Pointer to pointer (bitcast)
        elif isinstance(from_type, LLVMPointerType) and isinstance(to_type, LLVMPointerType):
            self._emit_indented(f"{result} = bitcast {from_type} {val} to {to_type}")

        else:
            # Fallback to bitcast
            self._emit_indented(f"{result} = bitcast {from_type} {val} to {to_type}")

        return result, to_type


# ============================================================================
# Test
# ============================================================================

if __name__ == "__main__":
    from lexer import Lexer
    from parser import Parser

    code = """
proc add(a: int32, b: int32): int32 =
    return a + b

proc main(): int32 =
    var x: int32 = 10
    var y: int32 = 20
    var sum: int32 = add(x, y)
    return sum
"""

    print("=== Source Code ===")
    print(code)

    lexer = Lexer(code)
    tokens = lexer.tokenize()
    parser = Parser(tokens)
    ast = parser.parse()

    codegen = LLVMCodeGen()
    llvm_ir = codegen.generate(ast)

    print("\n=== LLVM IR ===")
    print(llvm_ir)
