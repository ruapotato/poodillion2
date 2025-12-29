#!/usr/bin/env python3
"""
bh2py - Convert Brainhair files from old syntax to Python syntax

This tool reads .bh files with the old Nim-like syntax and outputs them
with Python-style syntax.

Usage:
    python bh2py.py input.bh > output.bh
    python bh2py.py input.bh -o output.bh
    python bh2py.py --dir lib/  # Convert all files in directory
"""

import sys
import os
import argparse

# Add compiler directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'compiler'))

from lexer import Lexer, TokenType
from parser import Parser
from ast_nodes import *


class BH2PYConverter:
    """Converts Brainhair AST to Python-style source code."""

    def __init__(self):
        self.indent = 0
        self.indent_str = "    "  # 4 spaces

    def ind(self) -> str:
        """Return current indentation string."""
        return self.indent_str * self.indent

    def convert_file(self, source: str) -> str:
        """Convert a complete source file from old to new syntax."""
        lexer = Lexer(source)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        ast = parser.parse()
        return self.convert_program(ast)

    def convert_program(self, prog: Program) -> str:
        """Convert a complete program."""
        lines = []

        # Convert imports
        for imp in prog.imports:
            lines.append(self.convert_import(imp))

        if prog.imports:
            lines.append("")  # Blank line after imports

        # Convert declarations
        last_was_const = False
        for i, decl in enumerate(prog.declarations):
            converted = self.convert_decl(decl)
            if not converted:
                continue

            # Group constants together without blank lines
            is_const = isinstance(decl, VarDecl) and decl.is_const

            # Add blank line before functions/classes after constants
            if last_was_const and not is_const and lines:
                lines.append("")
            # Add blank line between non-constant declarations
            elif not is_const and i > 0 and lines and lines[-1]:
                lines.append("")

            lines.append(converted)
            last_was_const = is_const

        return "\n".join(lines)

    def convert_import(self, imp: ImportDecl) -> str:
        """Convert import: import "lib/syscalls" -> from lib.syscalls import *"""
        # Convert path from slash to dot notation
        path = imp.path.replace('/', '.')

        if imp.alias:
            return f"import {path} as {imp.alias}"
        else:
            return f"from {path} import *"

    def convert_decl(self, decl) -> str:
        """Convert a top-level declaration."""
        if isinstance(decl, ProcDecl):
            return self.convert_proc(decl)
        elif isinstance(decl, MethodDecl):
            return self.convert_method(decl)
        elif isinstance(decl, StructDecl):
            return self.convert_struct(decl)
        elif isinstance(decl, EnumDecl):
            return self.convert_enum(decl)
        elif isinstance(decl, ExternDecl):
            return self.convert_extern(decl)
        elif isinstance(decl, VarDecl):
            return self.convert_var_decl(decl, top_level=True)
        else:
            return f"# Unknown declaration: {type(decl)}"

    def convert_proc(self, proc: ProcDecl) -> str:
        """Convert proc declaration to def."""
        lines = []

        # Add @inline decorator if needed
        if proc.is_inline:
            lines.append(f"{self.ind()}@inline")

        # Build function signature
        params = ", ".join(self.convert_param(p) for p in proc.params)

        # Generic type params
        type_params = ""
        if proc.type_params:
            type_params = "[" + ", ".join(tp.name for tp in proc.type_params) + "]"

        # Return type
        ret = ""
        if proc.return_type:
            ret = f" -> {self.convert_type(proc.return_type)}"

        lines.append(f"{self.ind()}def {proc.name}{type_params}({params}){ret}:")

        # Convert body
        self.indent += 1
        if not proc.body:
            lines.append(f"{self.ind()}pass")
        else:
            has_content = False
            for stmt in proc.body:
                converted = self.convert_stmt(stmt)
                if converted:  # Skip empty statements (from discard)
                    lines.append(converted)
                    has_content = True
            if not has_content:
                lines.append(f"{self.ind()}pass")
        self.indent -= 1

        return "\n".join(lines)

    def convert_method(self, method: MethodDecl) -> str:
        """Convert method declaration - standalone version."""
        # This is for methods defined outside class body
        # They get converted to regular methods
        lines = []

        # Get the type name from receiver
        type_name = self.get_base_type_name(method.receiver_type)

        params = ", ".join(self.convert_param(p) for p in method.params)
        if params:
            params = f"self, {params}"
        else:
            params = "self"

        ret = ""
        if method.return_type:
            ret = f" -> {self.convert_type(method.return_type)}"

        lines.append(f"# Method for {type_name}")
        lines.append(f"def {type_name}_{method.name}({params}){ret}:")

        self.indent += 1
        if not method.body:
            lines.append(f"{self.ind()}pass")
        else:
            for stmt in method.body:
                lines.append(self.convert_stmt(stmt))
        self.indent -= 1

        return "\n".join(lines)

    def get_base_type_name(self, t) -> str:
        """Extract base type name from a type (handling pointers)."""
        if isinstance(t, PointerType):
            return self.get_base_type_name(t.base_type)
        elif isinstance(t, Type):
            return t.name
        else:
            return str(t)

    def convert_struct(self, struct: StructDecl) -> str:
        """Convert type declaration to class."""
        lines = []

        # Handle @packed decorator
        if hasattr(struct, 'is_packed') and struct.is_packed:
            lines.append(f"{self.ind()}@packed")

        lines.append(f"{self.ind()}class {struct.name}:")

        self.indent += 1
        if not struct.fields:
            lines.append(f"{self.ind()}pass")
        else:
            for field in struct.fields:
                field_type = self.convert_type(field.field_type)
                if field.default_value:
                    default = self.convert_expr(field.default_value)
                    lines.append(f"{self.ind()}{field.name}: {field_type} = {default}")
                else:
                    lines.append(f"{self.ind()}{field.name}: {field_type}")
        self.indent -= 1

        return "\n".join(lines)

    def convert_enum(self, enum: EnumDecl) -> str:
        """Convert enum declaration."""
        lines = []

        lines.append(f"{self.ind()}class {enum.name}(Enum):")

        self.indent += 1
        if not enum.variants:
            lines.append(f"{self.ind()}pass")
        else:
            for variant in enum.variants:
                if variant.payload_types:
                    types = ", ".join(self.convert_type(t) for t in variant.payload_types)
                    lines.append(f"{self.ind()}{variant.name}({types})")
                else:
                    lines.append(f"{self.ind()}{variant.name}")
        self.indent -= 1

        return "\n".join(lines)

    def convert_extern(self, ext: ExternDecl) -> str:
        """Convert extern declaration."""
        params = ", ".join(self.convert_param(p) for p in ext.params)
        ret = ""
        if ext.return_type:
            ret = f" -> {self.convert_type(ext.return_type)}"
        return f"{self.ind()}extern def {ext.name}({params}){ret}"

    def convert_var_decl(self, decl: VarDecl, top_level=False) -> str:
        """Convert variable declaration."""
        type_str = self.convert_type(decl.var_type)

        if decl.is_const:
            type_str = f"Final[{type_str}]"

        if decl.value:
            value = self.convert_expr(decl.value)
            return f"{self.ind()}{decl.name}: {type_str} = {value}"
        else:
            return f"{self.ind()}{decl.name}: {type_str}"

    def convert_param(self, param: Parameter) -> str:
        """Convert a function parameter."""
        if param.param_type:
            return f"{param.name}: {self.convert_type(param.param_type)}"
        return param.name

    def convert_type(self, t) -> str:
        """Convert a type to Python-style syntax."""
        if isinstance(t, Type):
            return t.name
        elif isinstance(t, PointerType):
            return f"Ptr[{self.convert_type(t.base_type)}]"
        elif isinstance(t, ArrayType):
            return f"Array[{t.size}, {self.convert_type(t.element_type)}]"
        elif isinstance(t, SliceType):
            return f"List[{self.convert_type(t.element_type)}]"
        elif isinstance(t, GenericType):
            return t.name
        elif isinstance(t, GenericInstanceType):
            args = ", ".join(self.convert_type(a) for a in t.type_args)
            return f"{t.base_type}[{args}]"
        else:
            return str(t)

    def convert_stmt(self, stmt) -> str:
        """Convert a statement."""
        if isinstance(stmt, VarDecl):
            return self.convert_var_decl(stmt)
        elif isinstance(stmt, Assignment):
            return self.convert_assignment(stmt)
        elif isinstance(stmt, ReturnStmt):
            return self.convert_return(stmt)
        elif isinstance(stmt, IfStmt):
            return self.convert_if(stmt)
        elif isinstance(stmt, WhileStmt):
            return self.convert_while(stmt)
        elif isinstance(stmt, ForStmt):
            return self.convert_for(stmt)
        elif isinstance(stmt, ForEachStmt):
            return self.convert_foreach(stmt)
        elif isinstance(stmt, BreakStmt):
            return f"{self.ind()}break"
        elif isinstance(stmt, ContinueStmt):
            return f"{self.ind()}continue"
        elif isinstance(stmt, DiscardStmt):
            # Discard is used to ignore return values - in Python we just call the expr
            # So we skip it and let the next statement handle it
            return ""  # Empty - the actual expr comes next
        elif isinstance(stmt, DeferStmt):
            return self.convert_defer(stmt)
        elif isinstance(stmt, ExprStmt):
            return f"{self.ind()}{self.convert_expr(stmt.expr)}"
        elif isinstance(stmt, MatchExpr):
            return self.convert_match(stmt)
        else:
            return f"{self.ind()}# Unknown statement: {type(stmt)}"

    def convert_assignment(self, assign: Assignment) -> str:
        """Convert assignment statement."""
        target = self.convert_expr(assign.target)
        value = self.convert_expr(assign.value)
        return f"{self.ind()}{target} = {value}"

    def convert_return(self, ret: ReturnStmt) -> str:
        """Convert return statement."""
        if ret.value:
            return f"{self.ind()}return {self.convert_expr(ret.value)}"
        return f"{self.ind()}return"

    def convert_if(self, if_stmt: IfStmt) -> str:
        """Convert if statement."""
        lines = []

        cond = self.convert_expr(if_stmt.condition)
        lines.append(f"{self.ind()}if {cond}:")

        self.indent += 1
        if not if_stmt.then_block:
            lines.append(f"{self.ind()}pass")
        else:
            for stmt in if_stmt.then_block:
                lines.append(self.convert_stmt(stmt))
        self.indent -= 1

        # elif blocks
        if if_stmt.elif_blocks:
            for elif_cond, elif_body in if_stmt.elif_blocks:
                cond = self.convert_expr(elif_cond)
                lines.append(f"{self.ind()}elif {cond}:")
                self.indent += 1
                for stmt in elif_body:
                    lines.append(self.convert_stmt(stmt))
                self.indent -= 1

        # else block
        if if_stmt.else_block:
            lines.append(f"{self.ind()}else:")
            self.indent += 1
            for stmt in if_stmt.else_block:
                lines.append(self.convert_stmt(stmt))
            self.indent -= 1

        return "\n".join(lines)

    def convert_while(self, while_stmt: WhileStmt) -> str:
        """Convert while statement."""
        lines = []

        cond = self.convert_expr(while_stmt.condition)
        lines.append(f"{self.ind()}while {cond}:")

        self.indent += 1
        if not while_stmt.body:
            lines.append(f"{self.ind()}pass")
        else:
            for stmt in while_stmt.body:
                lines.append(self.convert_stmt(stmt))
        self.indent -= 1

        return "\n".join(lines)

    def convert_for(self, for_stmt: ForStmt) -> str:
        """Convert for loop: for i in start..end -> for i in range(start, end)."""
        lines = []

        start = self.convert_expr(for_stmt.start)
        end = self.convert_expr(for_stmt.end)

        # Use range() syntax
        if start == "0":
            lines.append(f"{self.ind()}for {for_stmt.var} in range({end}):")
        else:
            lines.append(f"{self.ind()}for {for_stmt.var} in range({start}, {end}):")

        self.indent += 1
        if not for_stmt.body:
            lines.append(f"{self.ind()}pass")
        else:
            for stmt in for_stmt.body:
                lines.append(self.convert_stmt(stmt))
        self.indent -= 1

        return "\n".join(lines)

    def convert_foreach(self, foreach_stmt: ForEachStmt) -> str:
        """Convert for-each loop."""
        lines = []

        iterable = self.convert_expr(foreach_stmt.iterable)
        lines.append(f"{self.ind()}for {foreach_stmt.var} in {iterable}:")

        self.indent += 1
        if not foreach_stmt.body:
            lines.append(f"{self.ind()}pass")
        else:
            for stmt in foreach_stmt.body:
                lines.append(self.convert_stmt(stmt))
        self.indent -= 1

        return "\n".join(lines)

    def convert_defer(self, defer: DeferStmt) -> str:
        """Convert defer statement."""
        if isinstance(defer.stmt, ExprStmt):
            return f"{self.ind()}defer {self.convert_expr(defer.stmt.expr)}"
        return f"{self.ind()}defer # ..."

    def convert_match(self, match: MatchExpr) -> str:
        """Convert match expression."""
        lines = []

        expr = self.convert_expr(match.expr)
        lines.append(f"{self.ind()}match {expr}:")

        self.indent += 1
        for arm in match.arms:
            pattern = arm.pattern.variant_name
            if arm.pattern.bindings:
                bindings = ", ".join(arm.pattern.bindings)
                pattern = f"{pattern}({bindings})"

            lines.append(f"{self.ind()}{pattern}:")
            self.indent += 1
            for stmt in arm.body:
                lines.append(self.convert_stmt(stmt))
            self.indent -= 1
        self.indent -= 1

        return "\n".join(lines)

    def convert_expr(self, expr) -> str:
        """Convert an expression."""
        if isinstance(expr, IntLiteral):
            return str(expr.value)
        elif isinstance(expr, CharLiteral):
            ch = expr.value
            if ch == '\n':
                return r"'\n'"
            elif ch == '\t':
                return r"'\t'"
            elif ch == '\0':
                return r"'\0'"
            elif ch == '\\':
                return r"'\\'"
            elif ch == "'":
                return r"'\''"
            else:
                return f"'{ch}'"
        elif isinstance(expr, StringLiteral):
            # Escape special characters
            s = expr.value.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n').replace('\t', '\\t').replace('\0', '\\0')
            return f'"{s}"'
        elif isinstance(expr, BoolLiteral):
            return "True" if expr.value else "False"
        elif isinstance(expr, Identifier):
            return expr.name
        elif isinstance(expr, BinaryExpr):
            return self.convert_binary(expr)
        elif isinstance(expr, UnaryExpr):
            return self.convert_unary(expr)
        elif isinstance(expr, CallExpr):
            return self.convert_call(expr)
        elif isinstance(expr, MethodCallExpr):
            return self.convert_method_call(expr)
        elif isinstance(expr, IndexExpr):
            return f"{self.convert_expr(expr.array)}[{self.convert_expr(expr.index)}]"
        elif isinstance(expr, FieldAccessExpr):
            return f"{self.convert_expr(expr.object)}.{expr.field_name}"
        elif isinstance(expr, CastExpr):
            return self.convert_cast(expr)
        elif isinstance(expr, AddrOfExpr):
            return f"addr({self.convert_expr(expr.expr)})"
        elif isinstance(expr, ArrayLiteral):
            elements = ", ".join(self.convert_expr(e) for e in expr.elements)
            return f"[{elements}]"
        elif isinstance(expr, StructLiteral):
            fields = ", ".join(f"{k}: {self.convert_expr(v)}"
                             for k, v in expr.field_values.items())
            return f"{expr.struct_type}({fields})"
        elif isinstance(expr, SizeOfExpr):
            return f"sizeof({self.convert_type(expr.target_type)})"
        elif isinstance(expr, SliceExpr):
            arr = self.convert_expr(expr.array)
            start = self.convert_expr(expr.start)
            end = self.convert_expr(expr.end)
            return f"{arr}[{start}..{end}]"
        elif isinstance(expr, ConditionalExpr):
            cond = self.convert_expr(expr.condition)
            then = self.convert_expr(expr.then_expr)
            els = self.convert_expr(expr.else_expr)
            return f"{then} if {cond} else {els}"
        elif isinstance(expr, MatchExpr):
            # Match as expression - this is complex
            return f"match ..."
        else:
            return f"<{type(expr).__name__}>"

    def convert_binary(self, expr: BinaryExpr) -> str:
        """Convert binary expression."""
        left = self.convert_expr(expr.left)
        right = self.convert_expr(expr.right)

        op_map = {
            BinOp.ADD: '+',
            BinOp.SUB: '-',
            BinOp.MUL: '*',
            BinOp.DIV: '/',
            BinOp.MOD: '%',
            BinOp.EQ: '==',
            BinOp.NEQ: '!=',
            BinOp.LT: '<',
            BinOp.LTE: '<=',
            BinOp.GT: '>',
            BinOp.GTE: '>=',
            BinOp.AND: 'and',
            BinOp.OR: 'or',
            BinOp.BIT_OR: '|',
            BinOp.BIT_AND: '&',
            BinOp.BIT_XOR: '^',
            BinOp.SHL: '<<',
            BinOp.SHR: '>>',
        }

        op = op_map.get(expr.op, str(expr.op))
        return f"({left} {op} {right})"

    def convert_unary(self, expr: UnaryExpr) -> str:
        """Convert unary expression."""
        inner = self.convert_expr(expr.expr)

        if expr.op == UnaryOp.NEG:
            return f"-{inner}"
        elif expr.op == UnaryOp.NOT:
            return f"not {inner}"
        else:
            return f"~{inner}"

    def convert_call(self, call: CallExpr) -> str:
        """Convert function call."""
        args = ", ".join(self.convert_expr(a) for a in call.args)

        if call.type_args:
            type_args = ", ".join(self.convert_type(t) for t in call.type_args)
            return f"{call.func}[{type_args}]({args})"

        return f"{call.func}({args})"

    def convert_method_call(self, call: MethodCallExpr) -> str:
        """Convert method call."""
        obj = self.convert_expr(call.object)
        args = ", ".join(self.convert_expr(a) for a in call.args)
        return f"{obj}.{call.method_name}({args})"

    def convert_cast(self, cast: CastExpr) -> str:
        """Convert cast expression: cast[Type](expr) -> Ptr[Type](expr) or cast[Type](expr)"""
        target = self.convert_type(cast.target_type)
        inner = self.convert_expr(cast.expr)

        # If casting to a pointer type, use Ptr[T](expr) syntax
        if isinstance(cast.target_type, PointerType):
            return f"{target}({inner})"

        # Otherwise use cast[T](expr) or int(expr) for primitives
        if target in ('int32', 'int16', 'int8', 'uint32', 'uint16', 'uint8'):
            # Could use int() but cast is more explicit
            return f"cast[{target}]({inner})"

        return f"cast[{target}]({inner})"


def convert_file(input_path: str, output_path: str = None):
    """Convert a single file."""
    with open(input_path, 'r') as f:
        source = f.read()

    converter = BH2PYConverter()
    try:
        result = converter.convert_file(source)
    except Exception as e:
        print(f"Error converting {input_path}: {e}", file=sys.stderr)
        return False

    if output_path:
        with open(output_path, 'w') as f:
            f.write(result)
    else:
        print(result)

    return True


def convert_directory(dir_path: str, in_place: bool = False):
    """Convert all .bh files in a directory."""
    import glob

    pattern = os.path.join(dir_path, '**', '*.bh')
    files = glob.glob(pattern, recursive=True)

    success = 0
    failed = 0

    for file_path in files:
        if in_place:
            # Create backup
            backup_path = file_path + '.bak'
            os.rename(file_path, backup_path)

            if convert_file(backup_path, file_path):
                success += 1
                os.remove(backup_path)  # Remove backup on success
            else:
                failed += 1
                os.rename(backup_path, file_path)  # Restore on failure
        else:
            # Output to stdout with filename header
            print(f"\n# ===== {file_path} =====\n")
            if convert_file(file_path):
                success += 1
            else:
                failed += 1

    print(f"\nConverted: {success}, Failed: {failed}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description='Convert Brainhair files to Python syntax')
    parser.add_argument('input', nargs='?', help='Input file or directory')
    parser.add_argument('-o', '--output', help='Output file')
    parser.add_argument('--dir', action='store_true', help='Convert all files in directory')
    parser.add_argument('--in-place', action='store_true', help='Modify files in place (with --dir)')

    args = parser.parse_args()

    if not args.input:
        parser.print_help()
        sys.exit(1)

    if args.dir or os.path.isdir(args.input):
        convert_directory(args.input, args.in_place)
    else:
        convert_file(args.input, args.output)


if __name__ == '__main__':
    main()
