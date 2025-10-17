#!/usr/bin/env python3
"""
Mini-Nim x86 Code Generator

Takes AST and generates x86 assembly (NASM syntax)
Phase 1: Generate assembly
Phase 2: Assemble to machine code
"""

from ast_nodes import *
from typing import Dict, List

class X86CodeGen:
    def __init__(self, kernel_mode=False):
        self.output = []
        self.data_section = []
        self.bss_section = []
        self.kernel_mode = kernel_mode  # If True, don't generate _start

        # Symbol table for variables (name -> stack offset)
        self.local_vars: Dict[str, int] = {}
        self.stack_offset = 0

        # String literals
        self.string_counter = 0
        self.strings: Dict[str, str] = {}

        # Label counter
        self.label_counter = 0

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

    # Code generation for types
    def type_size(self, typ: Type) -> int:
        """Get size in bytes for a type"""
        if isinstance(typ, PointerType):
            return 4  # 32-bit pointers

        type_sizes = {
            'int8': 1, 'uint8': 1, 'char': 1, 'bool': 1,
            'int16': 2, 'uint16': 2,
            'int32': 4, 'uint32': 4,
        }
        return type_sizes.get(typ.name, 4)

    # Expression code generation
    def gen_expression(self, expr: ASTNode) -> str:
        """
        Generate code for expression, result in EAX
        Returns the register containing the result
        """
        if isinstance(expr, IntLiteral):
            self.emit(f"mov eax, {expr.value}")
            return "eax"

        if isinstance(expr, CharLiteral):
            self.emit(f"mov eax, {ord(expr.value)}")
            return "eax"

        if isinstance(expr, BoolLiteral):
            self.emit(f"mov eax, {1 if expr.value else 0}")
            return "eax"

        if isinstance(expr, Identifier):
            # Check if it's a constant
            if hasattr(self, 'constants') and expr.name in self.constants:
                self.emit(f"mov eax, {self.constants[expr.name]}")
                return "eax"
            # Load variable from stack
            if expr.name in self.local_vars:
                offset = self.local_vars[expr.name]
                # Local variables are at negative offsets, parameters at positive
                if offset > 0:
                    self.emit(f"mov eax, [ebp+{offset}]")
                else:
                    self.emit(f"mov eax, [ebp{offset}]")
            else:
                # Global variable
                self.emit(f"mov eax, [rel {expr.name}]")
            return "eax"

        if isinstance(expr, BinaryExpr):
            # Evaluate left operand
            self.gen_expression(expr.left)
            self.emit("push eax")  # Save left result

            # Evaluate right operand
            self.gen_expression(expr.right)
            self.emit("mov ebx, eax")  # Right result in EBX

            # Pop left result
            self.emit("pop eax")  # Left result in EAX

            # Perform operation
            if expr.op == BinOp.ADD:
                self.emit("add eax, ebx")
            elif expr.op == BinOp.SUB:
                self.emit("sub eax, ebx")
            elif expr.op == BinOp.MUL:
                self.emit("imul eax, ebx")
            elif expr.op == BinOp.DIV:
                self.emit("xor edx, edx")  # Clear EDX for division
                self.emit("idiv ebx")
            elif expr.op == BinOp.EQ:
                self.emit("cmp eax, ebx")
                self.emit("sete al")
                self.emit("movzx eax, al")
            elif expr.op == BinOp.NEQ:
                self.emit("cmp eax, ebx")
                self.emit("setne al")
                self.emit("movzx eax, al")
            elif expr.op == BinOp.LT:
                self.emit("cmp eax, ebx")
                self.emit("setl al")
                self.emit("movzx eax, al")
            elif expr.op == BinOp.GT:
                self.emit("cmp eax, ebx")
                self.emit("setg al")
                self.emit("movzx eax, al")
            elif expr.op == BinOp.LTE:
                self.emit("cmp eax, ebx")
                self.emit("setle al")
                self.emit("movzx eax, al")
            elif expr.op == BinOp.GTE:
                self.emit("cmp eax, ebx")
                self.emit("setge al")
                self.emit("movzx eax, al")
            # Bitwise operators
            elif expr.op == BinOp.BIT_OR:
                self.emit("or eax, ebx")
            elif expr.op == BinOp.BIT_AND:
                self.emit("and eax, ebx")
            elif expr.op == BinOp.BIT_XOR:
                self.emit("xor eax, ebx")
            elif expr.op == BinOp.SHL:
                self.emit("mov ecx, ebx")  # Shift count must be in CL
                self.emit("shl eax, cl")
            elif expr.op == BinOp.SHR:
                self.emit("mov ecx, ebx")  # Shift count must be in CL
                self.emit("shr eax, cl")

            return "eax"

        if isinstance(expr, CallExpr):
            # Push arguments in reverse order
            for arg in reversed(expr.args):
                self.gen_expression(arg)
                self.emit("push eax")

            # Call function
            self.emit(f"call {expr.func}")

            # Clean up stack
            if expr.args:
                self.emit(f"add esp, {len(expr.args) * 4}")

            return "eax"

        if isinstance(expr, CastExpr):
            # For now, just generate the expression
            # Type casting is mostly a no-op in assembly
            return self.gen_expression(expr.expr)

        if isinstance(expr, IndexExpr):
            # Array indexing: array[index]
            # Generate index
            self.gen_expression(expr.index)
            self.emit("mov ebx, eax")  # Index in EBX

            # Generate array base address
            if isinstance(expr.array, Identifier):
                if expr.array.name in self.local_vars:
                    offset = self.local_vars[expr.array.name]
                    self.emit(f"lea eax, [ebp-{offset}]")
                else:
                    self.emit(f"lea eax, [rel {expr.array.name}]")

            # Calculate address: base + index * element_size
            # Assuming 2-byte elements for now (uint16)
            self.emit("shl ebx, 1")  # index * 2
            self.emit("add eax, ebx")
            self.emit("mov eax, [eax]")

            return "eax"

        raise NotImplementedError(f"Code generation for {type(expr).__name__} not implemented")

    # Statement code generation
    def gen_statement(self, stmt: ASTNode):
        if isinstance(stmt, VarDecl):
            # Allocate space on stack (negative offset from EBP)
            size = self.type_size(stmt.var_type)
            self.stack_offset += size
            self.local_vars[stmt.name] = -self.stack_offset  # Negative for local vars

            # Initialize if there's a value
            if stmt.value:
                self.gen_expression(stmt.value)
                self.emit(f"mov [ebp-{self.stack_offset}], eax")

        elif isinstance(stmt, Assignment):
            # Generate value
            self.gen_expression(stmt.value)

            # Store to target
            if isinstance(stmt.target, Identifier):
                if stmt.target.name in self.local_vars:
                    offset = self.local_vars[stmt.target.name]
                    if offset > 0:
                        self.emit(f"mov [ebp+{offset}], eax")
                    else:
                        self.emit(f"mov [ebp{offset}], eax")  # offset is already negative
                else:
                    self.emit(f"mov [rel {stmt.target.name}], eax")

            elif isinstance(stmt.target, IndexExpr):
                # Array assignment
                self.emit("push eax")  # Save value

                # Calculate address
                self.gen_expression(stmt.target.index)
                self.emit("mov ebx, eax")

                if isinstance(stmt.target.array, Identifier):
                    if stmt.target.array.name in self.local_vars:
                        offset = self.local_vars[stmt.target.array.name]
                        self.emit(f"lea eax, [ebp-{offset}]")

                self.emit("shl ebx, 1")
                self.emit("add eax, ebx")

                self.emit("pop ebx")  # Restore value
                self.emit("mov [eax], ebx")

        elif isinstance(stmt, ReturnStmt):
            if stmt.value:
                self.gen_expression(stmt.value)
            # Leave and return (handled by procedure epilogue)
            self.emit("jmp .return")

        elif isinstance(stmt, IfStmt):
            end_label = self.new_label("endif")
            else_label = self.new_label("else")

            # Generate condition
            self.gen_expression(stmt.condition)
            self.emit("test eax, eax")
            self.emit(f"jz {else_label}")

            # Then block
            for s in stmt.then_block:
                self.gen_statement(s)
            self.emit(f"jmp {end_label}")

            # Else block
            self.emit_label(else_label)
            if stmt.else_block:
                for s in stmt.else_block:
                    self.gen_statement(s)

            self.emit_label(end_label)

        elif isinstance(stmt, WhileStmt):
            start_label = self.new_label("while_start")
            end_label = self.new_label("while_end")

            self.emit_label(start_label)

            # Generate condition
            self.gen_expression(stmt.condition)
            self.emit("test eax, eax")
            self.emit(f"jz {end_label}")

            # Body
            for s in stmt.body:
                self.gen_statement(s)

            self.emit(f"jmp {start_label}")
            self.emit_label(end_label)

        elif isinstance(stmt, ForStmt):
            # for i in start..end:
            # Initialize loop variable
            self.stack_offset += 4
            self.local_vars[stmt.var] = self.stack_offset

            self.gen_expression(stmt.start)
            self.emit(f"mov [ebp-{self.stack_offset}], eax")

            # Generate end value (keep in register)
            self.gen_expression(stmt.end)
            self.emit("push eax")  # Save end value

            start_label = self.new_label("for_start")
            end_label = self.new_label("for_end")

            self.emit_label(start_label)

            # Check condition: i <= end
            offset = self.local_vars[stmt.var]
            self.emit(f"mov eax, [ebp-{offset}]")
            self.emit("mov ebx, [esp]")  # End value from stack
            self.emit("cmp eax, ebx")
            self.emit(f"jg {end_label}")

            # Body
            for s in stmt.body:
                self.gen_statement(s)

            # Increment i
            self.emit(f"inc dword [ebp-{offset}]")
            self.emit(f"jmp {start_label}")

            self.emit_label(end_label)
            self.emit("add esp, 4")  # Clean up end value

        elif isinstance(stmt, ExprStmt):
            self.gen_expression(stmt.expr)

        elif isinstance(stmt, DiscardStmt):
            pass  # No code needed

    # Procedure code generation
    def gen_procedure(self, proc: ProcDecl):
        self.emit("")
        self.emit_label(proc.name)

        # Prologue
        self.emit("push ebp")
        self.emit("mov ebp, esp")

        # Save and reset local variables for this function
        old_locals = self.local_vars
        old_offset = self.stack_offset
        self.local_vars = {}
        self.stack_offset = 0

        # Parameters (on stack, above EBP)
        # Stack layout: [param2][param1][return addr][saved EBP] <- EBP
        param_offset = 8  # Skip return address (4 bytes) and saved EBP (4 bytes)
        for param in proc.params:
            # Parameters are at positive offsets from EBP - mark with a special flag
            self.local_vars[param.name] = param_offset
            param_offset += 4

        # Generate body (this will add local variables with negative offsets)
        for stmt in proc.body:
            self.gen_statement(stmt)

        # Epilogue
        self.emit_label(".return")
        self.emit("mov esp, ebp")
        self.emit("pop ebp")
        self.emit("ret")

        # Restore
        self.local_vars = old_locals
        self.stack_offset = old_offset

    # Program generation
    def generate(self, program: Program) -> str:
        """Generate complete x86 assembly"""
        # First pass: collect constants
        self.constants = {}
        for decl in program.declarations:
            if isinstance(decl, VarDecl) and decl.is_const and decl.value:
                # Inline constants - store for lookup
                if isinstance(decl.value, IntLiteral):
                    self.constants[decl.name] = decl.value.value

        # Generate code for all declarations
        for decl in program.declarations:
            if isinstance(decl, ProcDecl):
                self.gen_procedure(decl)
            elif isinstance(decl, VarDecl):
                # Skip constants (they're inlined)
                if decl.is_const:
                    continue
                # Global variable
                self.bss_section.append(f"{decl.name}: resb {self.type_size(decl.var_type)}")

        # Build final assembly
        asm = []
        asm.append("; Generated by Mini-Nim Compiler")
        asm.append("bits 32")
        asm.append("")

        # Data section
        if self.strings or self.data_section:
            asm.append("section .data")
            for label, value in self.strings.items():
                # Escape and add string
                escaped = value.replace('\\', '\\\\').replace('"', '\\"')
                asm.append(f'{label}: db "{escaped}", 0')
            asm.extend(self.data_section)
            asm.append("")

        # BSS section
        if self.bss_section:
            asm.append("section .bss")
            asm.extend(self.bss_section)
            asm.append("")

        # Text section
        asm.append("section .text")

        # Only generate _start if not in kernel mode
        if not self.kernel_mode:
            asm.append("global _start")
            asm.append("")
            asm.append("_start:")
            asm.append("    call main")
            asm.append("    ; Halt (infinite loop)")
            asm.append(".halt:")
            asm.append("    hlt")
            asm.append("    jmp .halt")
        else:
            # In kernel mode, export main
            asm.append("global main")
            asm.append("")

        asm.extend(self.output)

        return '\n'.join(asm)

# Test the code generator
if __name__ == '__main__':
    from lexer import Lexer
    from parser import Parser

    code = """
proc add(a: int32, b: int32): int32 =
  return a + b

proc main() =
  var x: int32 = 10
  var y: int32 = 20
  var result: int32 = add(x, y)
"""

    lexer = Lexer(code)
    tokens = lexer.tokenize()

    parser = Parser(tokens)
    ast = parser.parse()

    codegen = X86CodeGen()
    asm_code = codegen.generate(ast)

    print(asm_code)
