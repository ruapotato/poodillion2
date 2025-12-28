#!/usr/bin/env python3
"""
Brainhair x86_64 Code Generator

Takes AST and generates x86_64 assembly (NASM syntax)
Uses System V AMD64 ABI calling convention.
"""

from ast_nodes import *
from typing import Dict, List, Optional

class X86_64CodeGen:
    # System V AMD64 ABI argument registers (in order)
    ARG_REGS = ['rdi', 'rsi', 'rdx', 'rcx', 'r8', 'r9']

    # Callee-saved registers
    CALLEE_SAVED = ['rbx', 'rbp', 'r12', 'r13', 'r14', 'r15']

    # Caller-saved registers (scratch)
    CALLER_SAVED = ['rax', 'rcx', 'rdx', 'rsi', 'rdi', 'r8', 'r9', 'r10', 'r11']

    def __init__(self, kernel_mode=False):
        self.output = []
        self.data_section = []
        self.bss_section = []
        self.kernel_mode = kernel_mode

        # Symbol table for variables (name -> stack offset)
        self.local_vars: Dict[str, int] = {}
        self.stack_offset = 0

        # Type table (name -> Type)
        self.type_table: Dict[str, Type] = {}

        # Struct type definitions
        self.struct_types: Dict[str, 'StructDecl'] = {}

        # Enum type definitions
        self.enum_types: Dict[str, 'EnumDecl'] = {}

        # String literals
        self.string_counter = 0
        self.strings: Dict[str, str] = {}

        # Label counter
        self.label_counter = 0

        # Defer stack
        self.defer_stack: List[ASTNode] = []

        # Constants
        self.constants: Dict[str, int] = {}

    def emit(self, instruction: str):
        """Emit an assembly instruction"""
        self.output.append(f"    {instruction}")

    def emit_label(self, label: str):
        """Emit a label"""
        self.output.append(f"{label}:")

    def new_label(self, prefix="L") -> str:
        """Generate a unique label"""
        label = f"{prefix}{self.label_counter}"
        self.label_counter += 1
        return label

    def add_string(self, value: str) -> str:
        """Add string to data section, return label"""
        label = f"str_{self.string_counter}"
        self.string_counter += 1
        self.strings[label] = value
        return label

    def type_size(self, typ: Type) -> int:
        """Get size in bytes for a type"""
        if typ is None:
            return 8

        if isinstance(typ, PointerType):
            return 8  # 64-bit pointers

        if isinstance(typ, SliceType):
            return 16  # Fat pointer: ptr (8) + len (8)

        if isinstance(typ, ListType):
            return 32  # List struct: data(8) + len(8) + cap(8) + elem_size(8)

        if isinstance(typ, DictType):
            return 40  # Dict struct: keys(8) + values(8) + flags(8) + cap(8) + len(8)

        if isinstance(typ, ArrayType):
            return typ.size * self.type_size(typ.element_type)

        type_sizes = {
            'int8': 1, 'uint8': 1, 'char': 1, 'bool': 1,
            'int16': 2, 'uint16': 2,
            'int32': 4, 'uint32': 4,
            'int64': 8, 'uint64': 8,
        }

        if typ.name in self.struct_types:
            return self.struct_size(typ.name)
        if typ.name in self.enum_types:
            return self.enum_size(typ.name)
        return type_sizes.get(typ.name, 4)

    def struct_size(self, struct_name: str) -> int:
        """Calculate total size of a struct"""
        if struct_name not in self.struct_types:
            return 8
        struct_decl = self.struct_types[struct_name]
        total = 0
        for field in struct_decl.fields:
            total += self.type_size(field.field_type)
        return total

    def enum_size(self, enum_name: str) -> int:
        """Enums are 32-bit integers"""
        return 4

    def get_field_offset(self, struct_name: str, field_name: str) -> int:
        """Get byte offset of a field within a struct"""
        if struct_name not in self.struct_types:
            return 0
        struct_decl = self.struct_types[struct_name]
        offset = 0
        for field in struct_decl.fields:
            if field.name == field_name:
                return offset
            offset += self.type_size(field.field_type)
        return 0

    def reg_for_size(self, reg: str, size: int) -> str:
        """Get the appropriate register name for a given size"""
        reg_map = {
            'rax': {1: 'al', 2: 'ax', 4: 'eax', 8: 'rax'},
            'rbx': {1: 'bl', 2: 'bx', 4: 'ebx', 8: 'rbx'},
            'rcx': {1: 'cl', 2: 'cx', 4: 'ecx', 8: 'rcx'},
            'rdx': {1: 'dl', 2: 'dx', 4: 'edx', 8: 'rdx'},
            'rsi': {1: 'sil', 2: 'si', 4: 'esi', 8: 'rsi'},
            'rdi': {1: 'dil', 2: 'di', 4: 'edi', 8: 'rdi'},
            'r8':  {1: 'r8b', 2: 'r8w', 4: 'r8d', 8: 'r8'},
            'r9':  {1: 'r9b', 2: 'r9w', 4: 'r9d', 8: 'r9'},
            'r10': {1: 'r10b', 2: 'r10w', 4: 'r10d', 8: 'r10'},
            'r11': {1: 'r11b', 2: 'r11w', 4: 'r11d', 8: 'r11'},
        }
        if reg in reg_map:
            return reg_map[reg].get(size, reg)
        return reg

    def get_expr_type(self, expr: ASTNode) -> Optional[Type]:
        """Infer the type of an expression"""
        if isinstance(expr, Identifier):
            return self.type_table.get(expr.name)
        if isinstance(expr, IntLiteral):
            return Type('int32')
        if isinstance(expr, BoolLiteral):
            return Type('bool')
        if isinstance(expr, NoneLiteral):
            return PointerType(Type('void'))
        if isinstance(expr, StringLiteral):
            return PointerType(Type('uint8'))
        if isinstance(expr, FStringLiteral):
            return PointerType(Type('uint8'))
        if isinstance(expr, UnaryExpr) and expr.op == UnaryOp.ADDR:
            inner = self.get_expr_type(expr.expr)
            if inner:
                return PointerType(inner)
        if isinstance(expr, UnaryExpr) and expr.op == UnaryOp.DEREF:
            inner = self.get_expr_type(expr.expr)
            if isinstance(inner, PointerType):
                return inner.base_type
        return None

    # Expression code generation - result in RAX
    def gen_expression(self, expr: ASTNode) -> str:
        """Generate code for expression, result in RAX"""

        if isinstance(expr, IntLiteral):
            if expr.value >= 0 and expr.value <= 0xFFFFFFFF:
                self.emit(f"mov eax, {expr.value}")  # Zero-extends to RAX
            else:
                self.emit(f"mov rax, {expr.value}")
            return "rax"

        if isinstance(expr, CharLiteral):
            self.emit(f"mov eax, {ord(expr.value)}")
            return "rax"

        if isinstance(expr, BoolLiteral):
            self.emit(f"mov eax, {1 if expr.value else 0}")
            return "rax"

        if isinstance(expr, NoneLiteral):
            self.emit("xor eax, eax")  # None = 0 (null pointer)
            return "rax"

        if isinstance(expr, StringLiteral):
            label = self.add_string(expr.value)
            if self.kernel_mode:
                self.emit(f"lea rax, [{label}]")
            else:
                self.emit(f"lea rax, [rel {label}]")
            return "rax"

        if isinstance(expr, FStringLiteral):
            # Treat f-string as regular string for now (no interpolation)
            label = self.add_string(expr.value)
            if self.kernel_mode:
                self.emit(f"lea rax, [{label}]")
            else:
                self.emit(f"lea rax, [rel {label}]")
            return "rax"

        if isinstance(expr, Identifier):
            if expr.name in self.constants:
                val = self.constants[expr.name]
                if val >= 0 and val <= 0xFFFFFFFF:
                    self.emit(f"mov eax, {val}")
                else:
                    self.emit(f"mov rax, {val}")
                return "rax"

            if expr.name in self.local_vars:
                offset = self.local_vars[expr.name]
                var_type = self.type_table.get(expr.name)
                var_size = self.type_size(var_type) if var_type else 8

                if offset > 0:
                    addr = f"[rbp+{offset}]"
                    lea_addr = f"rbp+{offset}"
                else:
                    addr = f"[rbp{offset}]"
                    lea_addr = f"rbp{offset}"

                # For arrays, load address not value
                if isinstance(var_type, ArrayType):
                    self.emit(f"lea rax, [{lea_addr}]")
                elif var_size == 1:
                    self.emit(f"movzx eax, byte {addr}")
                elif var_size == 2:
                    self.emit(f"movzx eax, word {addr}")
                elif var_size == 4:
                    # Sign-extend for signed types, zero-extend for unsigned
                    type_name = var_type.name if var_type else 'int32'
                    if type_name in ('int32', 'int'):
                        self.emit(f"movsxd rax, dword {addr}")
                    else:
                        self.emit(f"mov eax, dword {addr}")
                else:
                    self.emit(f"mov rax, {addr}")
            else:
                # Global variable
                var_type = self.type_table.get(expr.name)
                var_size = self.type_size(var_type) if var_type else 8

                addr = f"[{expr.name}]" if self.kernel_mode else f"[rel {expr.name}]"
                lea_addr = expr.name if self.kernel_mode else f"rel {expr.name}"

                # For arrays, load address not value
                if isinstance(var_type, ArrayType):
                    self.emit(f"lea rax, [{lea_addr}]")
                elif var_size == 1:
                    self.emit(f"movzx eax, byte {addr}")
                elif var_size == 2:
                    self.emit(f"movzx eax, word {addr}")
                elif var_size == 4:
                    # Sign-extend for signed types, zero-extend for unsigned
                    type_name = var_type.name if var_type else 'int32'
                    if type_name in ('int32', 'int'):
                        self.emit(f"movsxd rax, dword {addr}")
                    else:
                        self.emit(f"mov eax, dword {addr}")
                else:
                    self.emit(f"mov rax, {addr}")
            return "rax"

        if isinstance(expr, UnaryExpr):
            self.gen_expression(expr.expr)

            if expr.op == UnaryOp.NEG:
                self.emit("neg rax")
            elif expr.op == UnaryOp.NOT:
                self.emit("test rax, rax")
                self.emit("setz al")
                self.emit("movzx rax, al")
            elif expr.op == UnaryOp.BITNOT:
                self.emit("not rax")
            elif expr.op == UnaryOp.DEREF:
                # Dereference pointer in RAX
                expr_type = self.get_expr_type(expr.expr)
                if isinstance(expr_type, PointerType):
                    base_type = expr_type.base_type
                    elem_size = self.type_size(base_type)
                    if elem_size == 1:
                        self.emit("movzx eax, byte [rax]")
                    elif elem_size == 2:
                        self.emit("movzx eax, word [rax]")
                    elif elem_size == 4:
                        # Sign-extend for signed types
                        type_name = base_type.name if base_type else 'int32'
                        if type_name in ('int32', 'int'):
                            self.emit("movsxd rax, dword [rax]")
                        else:
                            self.emit("mov eax, dword [rax]")
                    else:
                        self.emit("mov rax, [rax]")
                else:
                    self.emit("mov rax, [rax]")
            return "rax"

        if isinstance(expr, BinaryExpr):
            # Evaluate left operand
            self.gen_expression(expr.left)
            self.emit("push rax")

            # Evaluate right operand
            self.gen_expression(expr.right)
            self.emit("mov rcx, rax")
            self.emit("pop rax")

            # Now: RAX = left, RCX = right
            if expr.op == BinOp.ADD:
                self.emit("add rax, rcx")
            elif expr.op == BinOp.SUB:
                self.emit("sub rax, rcx")
            elif expr.op == BinOp.MUL:
                self.emit("imul rax, rcx")
            elif expr.op == BinOp.DIV:
                self.emit("cqo")  # Sign-extend RAX to RDX:RAX
                self.emit("idiv rcx")
            elif expr.op == BinOp.MOD:
                self.emit("cqo")
                self.emit("idiv rcx")
                self.emit("mov rax, rdx")  # Remainder in RDX
            elif expr.op == BinOp.BIT_AND:
                self.emit("and rax, rcx")
            elif expr.op == BinOp.BIT_OR:
                self.emit("or rax, rcx")
            elif expr.op == BinOp.BIT_XOR:
                self.emit("xor rax, rcx")
            elif expr.op == BinOp.SHL:
                self.emit("shl rax, cl")
            elif expr.op == BinOp.SHR:
                self.emit("shr rax, cl")
            elif expr.op == BinOp.AND:
                self.emit("test rax, rax")
                self.emit("setne al")
                self.emit("test rcx, rcx")
                self.emit("setne cl")
                self.emit("and al, cl")
                self.emit("movzx rax, al")
            elif expr.op == BinOp.OR:
                self.emit("or rax, rcx")
                self.emit("setne al")
                self.emit("movzx rax, al")
            elif expr.op in (BinOp.EQ, BinOp.NEQ, BinOp.LT, BinOp.LTE, BinOp.GT, BinOp.GTE):
                self.emit("cmp rax, rcx")
                setcc = {
                    BinOp.EQ: 'sete',
                    BinOp.NEQ: 'setne',
                    BinOp.LT: 'setl',
                    BinOp.LTE: 'setle',
                    BinOp.GT: 'setg',
                    BinOp.GTE: 'setge',
                }
                self.emit(f"{setcc[expr.op]} al")
                self.emit("movzx rax, al")
            return "rax"

        if isinstance(expr, CallExpr):
            # System V AMD64 ABI: args in RDI, RSI, RDX, RCX, R8, R9
            # Then on stack (right to left)

            num_args = len(expr.args)
            stack_args = max(0, num_args - 6)

            # First, push stack arguments (args 6+) in right-to-left order
            if stack_args > 0:
                for i in range(num_args - 1, 5, -1):
                    self.gen_expression(expr.args[i])
                    self.emit("push rax")

            # Now evaluate register arguments (0-5) and save to stack temporarily
            reg_count = min(num_args, 6)
            for i in range(reg_count):
                self.gen_expression(expr.args[i])
                self.emit("push rax")

            # Pop into registers in reverse order
            for i in range(reg_count - 1, -1, -1):
                self.emit(f"pop {self.ARG_REGS[i]}")

            # 16-byte stack alignment before call
            # (caller is responsible for alignment)

            self.emit(f"call {expr.func}")

            # Clean up stack arguments
            if stack_args > 0:
                self.emit(f"add rsp, {stack_args * 8}")

            return "rax"

        if isinstance(expr, CastExpr):
            self.gen_expression(expr.expr)
            # Most casts are no-op at runtime in our simple type system
            return "rax"

        if isinstance(expr, IsInstanceExpr):
            # isinstance() check - in BH, this is a compile-time operation
            # For now, we'll evaluate the expression and return 1 (true)
            self.gen_expression(expr.expr)  # Evaluate for side effects
            self.emit("mov rax, 1")  # Always return true (statically typed)
            return "rax"

        if isinstance(expr, IndexExpr):
            # array[index]
            self.gen_expression(expr.index)
            self.emit("push rax")  # Save index
            self.gen_expression(expr.array)
            self.emit("pop rcx")   # Index in RCX

            # Get element type and size
            arr_type = self.get_expr_type(expr.array)
            elem_size = 8
            elem_type = None
            if isinstance(arr_type, ArrayType):
                elem_size = self.type_size(arr_type.element_type)
                elem_type = arr_type.element_type
            elif isinstance(arr_type, PointerType):
                elem_size = self.type_size(arr_type.base_type)
                elem_type = arr_type.base_type

            if elem_size == 1:
                self.emit("movzx eax, byte [rax + rcx]")
            elif elem_size == 2:
                self.emit("movzx eax, word [rax + rcx*2]")
            elif elem_size == 4:
                # Sign-extend for signed types
                type_name = elem_type.name if elem_type else 'int32'
                if type_name in ('int32', 'int'):
                    self.emit("movsxd rax, dword [rax + rcx*4]")
                else:
                    self.emit("mov eax, dword [rax + rcx*4]")
            else:
                self.emit("mov rax, [rax + rcx*8]")
            return "rax"

        if isinstance(expr, AddrOfExpr):
            # Address-of operator: get the address of a variable, array element, or function
            if isinstance(expr.expr, Identifier):
                if expr.expr.name in self.local_vars:
                    offset = self.local_vars[expr.expr.name]
                    if offset > 0:
                        self.emit(f"lea rax, [rbp+{offset}]")
                    else:
                        self.emit(f"lea rax, [rbp{offset}]")
                else:
                    # Global variable or function - use LEA to get address
                    if self.kernel_mode:
                        self.emit(f"lea rax, [{expr.expr.name}]")
                    else:
                        self.emit(f"lea rax, [rel {expr.expr.name}]")
            elif isinstance(expr.expr, IndexExpr):
                # addr(arr[i]) - get address of array element
                self.gen_expression(expr.expr.index)
                self.emit("push rax")  # Save index
                self.gen_expression(expr.expr.array)
                self.emit("pop rcx")   # Index in RCX
                # Get element type and size
                arr_type = self.get_expr_type(expr.expr.array)
                elem_size = 8
                if isinstance(arr_type, ArrayType):
                    elem_size = self.type_size(arr_type.element_type)
                elif isinstance(arr_type, PointerType):
                    elem_size = self.type_size(arr_type.base_type)
                # Calculate element address
                if elem_size == 1:
                    self.emit("lea rax, [rax + rcx]")
                elif elem_size == 2:
                    self.emit("lea rax, [rax + rcx*2]")
                elif elem_size == 4:
                    self.emit("lea rax, [rax + rcx*4]")
                else:
                    self.emit("lea rax, [rax + rcx*8]")
            elif isinstance(expr.expr, FieldAccessExpr):
                # addr(obj.field) - get address of struct field
                self.gen_expression(expr.expr.object)
                # TODO: add field offset
            else:
                # For other expressions, just return the result
                self.gen_expression(expr.expr)
            return "rax"

        # Default: return 0
        self.emit("xor eax, eax")
        return "rax"

    def gen_statement(self, stmt: ASTNode):
        """Generate code for a statement"""

        if isinstance(stmt, VarDecl):
            # Allocate stack space
            var_size = self.type_size(stmt.var_type)
            var_size = max(var_size, 8)  # Minimum 8 bytes for alignment
            self.stack_offset += var_size
            self.local_vars[stmt.name] = -self.stack_offset
            self.type_table[stmt.name] = stmt.var_type

            # Initialize if there's a value
            if stmt.value:
                self.gen_expression(stmt.value)
                offset = self.local_vars[stmt.name]
                self.emit(f"mov [rbp{offset}], rax")

        elif isinstance(stmt, Assignment):
            # Generate RHS
            self.gen_expression(stmt.value)
            self.emit("push rax")

            # Generate LHS address
            if isinstance(stmt.target, Identifier):
                if stmt.target.name in self.local_vars:
                    offset = self.local_vars[stmt.target.name]
                    self.emit("pop rax")
                    if offset > 0:
                        self.emit(f"mov [rbp+{offset}], rax")
                    else:
                        self.emit(f"mov [rbp{offset}], rax")
                else:
                    self.emit("pop rax")
                    addr = f"[{stmt.target.name}]" if self.kernel_mode else f"[rel {stmt.target.name}]"
                    self.emit(f"mov {addr}, rax")
            elif isinstance(stmt.target, IndexExpr):
                # array[index] = value
                self.gen_expression(stmt.target.index)
                self.emit("push rax")  # index
                self.gen_expression(stmt.target.array)
                self.emit("pop rcx")   # index in RCX
                self.emit("pop rdx")   # value in RDX

                arr_type = self.get_expr_type(stmt.target.array)
                elem_size = 8
                if isinstance(arr_type, ArrayType):
                    elem_size = self.type_size(arr_type.element_type)
                elif isinstance(arr_type, PointerType):
                    elem_size = self.type_size(arr_type.base_type)

                if elem_size == 1:
                    self.emit("mov [rax + rcx], dl")
                elif elem_size == 2:
                    self.emit("mov [rax + rcx*2], dx")
                elif elem_size == 4:
                    self.emit("mov [rax + rcx*4], edx")
                else:
                    self.emit("mov [rax + rcx*8], rdx")
            elif isinstance(stmt.target, UnaryExpr) and stmt.target.op == UnaryOp.DEREF:
                # *ptr = value
                self.gen_expression(stmt.target.expr)
                self.emit("pop rdx")  # value
                self.emit("mov [rax], rdx")
            else:
                self.emit("pop rax")

        elif isinstance(stmt, IfStmt):
            else_label = self.new_label("else")
            end_label = self.new_label("endif")

            self.gen_expression(stmt.condition)
            self.emit("test rax, rax")
            self.emit(f"jz {else_label}")

            for s in stmt.then_block:
                self.gen_statement(s)
            self.emit(f"jmp {end_label}")

            self.emit_label(else_label)
            if stmt.else_block:
                for s in stmt.else_block:
                    self.gen_statement(s)

            self.emit_label(end_label)

        elif isinstance(stmt, WhileStmt):
            start_label = self.new_label("while_start")
            end_label = self.new_label("while_end")

            self.emit_label(start_label)
            self.gen_expression(stmt.condition)
            self.emit("test rax, rax")
            self.emit(f"jz {end_label}")

            for s in stmt.body:
                self.gen_statement(s)
            self.emit(f"jmp {start_label}")

            self.emit_label(end_label)

        elif isinstance(stmt, ReturnStmt):
            if stmt.value:
                self.gen_expression(stmt.value)
            self.emit(f"jmp {self.return_label}")

        elif isinstance(stmt, ExprStmt):
            self.gen_expression(stmt.expr)

        elif isinstance(stmt, DiscardStmt):
            pass  # No code needed

        elif isinstance(stmt, BreakStmt):
            if hasattr(self, 'break_label'):
                self.emit(f"jmp {self.break_label}")

        elif isinstance(stmt, ContinueStmt):
            if hasattr(self, 'continue_label'):
                self.emit(f"jmp {self.continue_label}")

    def gen_procedure(self, proc: ProcDecl):
        """Generate code for a procedure"""
        self.emit("")

        func_name = proc.name
        if self.kernel_mode and proc.name == "main":
            func_name = "brainhair_kernel_main"

        self.emit_label(func_name)

        # Prologue
        self.emit("push rbp")
        self.emit("mov rbp, rsp")

        # Mark where stack allocation goes
        stack_alloc_pos = len(self.output)

        # Save local state
        old_locals = self.local_vars
        old_offset = self.stack_offset
        self.local_vars = {}
        self.stack_offset = 0

        old_defer_stack = self.defer_stack
        self.defer_stack = []

        old_return_label = getattr(self, 'return_label', None)
        self.return_label = f"{func_name}_return"

        # Parameters: System V AMD64 passes first 6 in registers
        # Move them to stack for simplicity
        for i, param in enumerate(proc.params):
            self.type_table[param.name] = param.param_type
            param_size = max(self.type_size(param.param_type), 8)
            self.stack_offset += param_size
            self.local_vars[param.name] = -self.stack_offset

            if i < 6:
                # Move from register to stack
                reg = self.ARG_REGS[i]
                offset = self.local_vars[param.name]
                self.emit(f"mov [rbp{offset}], {reg}")
            else:
                # Parameter on stack (above RBP)
                stack_param_offset = 16 + (i - 6) * 8
                self.local_vars[param.name] = stack_param_offset

        # Default return value
        if proc.return_type and proc.return_type.name in ('int32', 'int64', 'uint32', 'uint64', 'int8', 'uint8', 'int16', 'uint16'):
            self.emit("xor eax, eax")

        # Generate body
        for stmt in proc.body:
            self.gen_statement(stmt)

        # Insert stack allocation
        if self.stack_offset > 0:
            # Align to 16 bytes
            aligned_size = (self.stack_offset + 15) & ~15
            self.output.insert(stack_alloc_pos, f"    sub rsp, {aligned_size}")

        # Epilogue
        self.emit_label(self.return_label)
        if self.defer_stack:
            self.emit("push rax")
            self.emit_deferred()
            self.emit("pop rax")
        self.emit("mov rsp, rbp")
        self.emit("pop rbp")
        self.emit("ret")

        # Restore state
        self.local_vars = old_locals
        self.stack_offset = old_offset
        self.return_label = old_return_label
        self.defer_stack = old_defer_stack

    def emit_deferred(self):
        """Emit deferred statements in reverse order"""
        for stmt in reversed(self.defer_stack):
            self.gen_statement(stmt)

    def generate(self, program: Program) -> str:
        """Generate assembly for the entire program"""
        asm = []

        # Header
        asm.append("; Generated by Brainhair x86_64 compiler")
        asm.append("[BITS 64]")
        asm.append("")

        # Collect constants, structs, enums, and global variable types first
        for decl in program.declarations:
            if isinstance(decl, VarDecl) and decl.is_const and decl.value:
                # Inline constants
                if isinstance(decl.value, IntLiteral):
                    self.constants[decl.name] = decl.value.value
                elif isinstance(decl.value, UnaryExpr) and decl.value.op == UnaryOp.NEG and isinstance(decl.value.expr, IntLiteral):
                    # Handle negative constants like -1
                    self.constants[decl.name] = -decl.value.expr.value
            elif isinstance(decl, VarDecl) and not decl.is_const:
                # Register global variable types BEFORE generating code
                self.type_table[decl.name] = decl.var_type
            elif isinstance(decl, StructDecl):
                self.struct_types[decl.name] = decl
            elif isinstance(decl, EnumDecl):
                self.enum_types[decl.name] = decl
                for i, variant in enumerate(decl.variants):
                    self.constants[variant] = i

        # Extern declarations
        for decl in program.declarations:
            if isinstance(decl, ExternDecl):
                asm.append(f"extern {decl.name}")

        # Global exports
        if self.kernel_mode:
            asm.append("")
            asm.append("; Kernel exports")
            asm.append("global brainhair_kernel_main")
            # Add other kernel exports here as needed
        else:
            asm.append("")
            asm.append("; Userland exports")
            asm.append("global main")

        # Text section
        asm.append("")
        asm.append("section .text")

        # Generate procedures
        for decl in program.declarations:
            if isinstance(decl, ProcDecl):
                self.gen_procedure(decl)

        asm.extend(self.output)

        # Data section
        if self.strings:
            asm.append("")
            asm.append("section .data")
            for label, value in self.strings.items():
                # Convert string to NASM byte sequence
                bytes_list = []
                i = 0
                while i < len(value):
                    ch = value[i]
                    if ch == '\\' and i + 1 < len(value):
                        next_ch = value[i + 1]
                        if next_ch == 'n':
                            bytes_list.append('10')
                            i += 2
                            continue
                        elif next_ch == 'r':
                            bytes_list.append('13')
                            i += 2
                            continue
                        elif next_ch == 't':
                            bytes_list.append('9')
                            i += 2
                            continue
                        elif next_ch == '0':
                            bytes_list.append('0')
                            i += 2
                            continue
                        elif next_ch == '\\':
                            bytes_list.append('92')
                            i += 2
                            continue
                    bytes_list.append(str(ord(ch)))
                    i += 1
                bytes_list.append('0')  # Null terminator
                asm.append(f'{label}: db {", ".join(bytes_list)}')

        # BSS section for global variables
        bss_vars = []
        for decl in program.declarations:
            if isinstance(decl, VarDecl) and decl.name not in self.local_vars:
                self.type_table[decl.name] = decl.var_type
                var_size = self.type_size(decl.var_type)
                bss_vars.append((decl.name, var_size))

        if bss_vars:
            asm.append("")
            asm.append("section .bss")
            for name, size in bss_vars:
                asm.append(f"{name}: resb {size}")

        return "\n".join(asm)
