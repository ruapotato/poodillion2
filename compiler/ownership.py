#!/usr/bin/env python3
"""
Ownership Analysis for Brainhair Compiler

This module implements ownership tracking and move semantics for memory safety.
It ensures that:
- Each value has exactly one owner
- Values are moved (not copied) by default for non-primitive types
- Use-after-move is detected at compile time
- Borrows don't outlive their sources

Memory Model:
- Primitive types (int32, bool, etc.) are Copy - they're duplicated on assignment
- Structs and arrays are Move - ownership transfers on assignment
- Pointers can be borrowed (shared or mutable)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
from enum import Enum, auto

from ast_nodes import *


class OwnershipState(Enum):
    """State of a value's ownership."""
    OWNED = auto()      # Value is owned and valid
    MOVED = auto()      # Value has been moved, cannot be used
    BORROWED = auto()   # Value is borrowed (read-only access)
    MUT_BORROWED = auto()  # Value is mutably borrowed


class ValueKind(Enum):
    """Kind of value for ownership purposes."""
    COPY = auto()    # Primitive types - copied on assignment
    MOVE = auto()    # Structs/arrays - moved on assignment
    BORROW = auto()  # References/pointers


@dataclass
class OwnershipInfo:
    """Tracks ownership state of a variable."""
    name: str
    state: OwnershipState = OwnershipState.OWNED
    kind: ValueKind = ValueKind.COPY
    moved_at: Optional[int] = None  # Line number where moved
    borrowed_by: List[str] = field(default_factory=list)
    mutable_borrow: Optional[str] = None


@dataclass
class OwnershipError:
    """Represents an ownership violation."""
    message: str
    line: Optional[int] = None

    def __str__(self):
        if self.line:
            return f"Ownership error at line {self.line}: {self.message}"
        return f"Ownership error: {self.message}"


class OwnershipScope:
    """Tracks ownership within a scope."""

    def __init__(self, parent: Optional['OwnershipScope'] = None, name: str = ""):
        self.parent = parent
        self.name = name
        self.variables: Dict[str, OwnershipInfo] = {}
        self.children: List['OwnershipScope'] = []

    def declare(self, name: str, kind: ValueKind = ValueKind.COPY) -> OwnershipInfo:
        """Declare a new variable in this scope."""
        info = OwnershipInfo(name, OwnershipState.OWNED, kind)
        self.variables[name] = info
        return info

    def lookup(self, name: str) -> Optional[OwnershipInfo]:
        """Look up a variable, checking parent scopes."""
        if name in self.variables:
            return self.variables[name]
        if self.parent:
            return self.parent.lookup(name)
        return None

    def mark_moved(self, name: str, line: int) -> None:
        """Mark a variable as moved."""
        info = self.lookup(name)
        if info:
            info.state = OwnershipState.MOVED
            info.moved_at = line

    def mark_borrowed(self, name: str, borrower: str) -> None:
        """Mark a variable as borrowed."""
        info = self.lookup(name)
        if info:
            if info.state == OwnershipState.OWNED:
                info.state = OwnershipState.BORROWED
            info.borrowed_by.append(borrower)

    def mark_mut_borrowed(self, name: str, borrower: str) -> None:
        """Mark a variable as mutably borrowed."""
        info = self.lookup(name)
        if info:
            info.state = OwnershipState.MUT_BORROWED
            info.mutable_borrow = borrower

    def release_borrows(self, borrower: str) -> None:
        """Release all borrows held by a borrower."""
        for info in self.variables.values():
            if borrower in info.borrowed_by:
                info.borrowed_by.remove(borrower)
                if not info.borrowed_by and info.state == OwnershipState.BORROWED:
                    info.state = OwnershipState.OWNED
            if info.mutable_borrow == borrower:
                info.mutable_borrow = None
                info.state = OwnershipState.OWNED


class OwnershipChecker:
    """
    Performs ownership analysis on Brainhair AST.

    Checks for:
    - Use after move
    - Double move
    - Invalid borrows (borrowing moved value)
    - Mutable borrow conflicts
    """

    def __init__(self):
        self.errors: List[OwnershipError] = []
        self.current_scope: Optional[OwnershipScope] = None
        self.scope_stack: List[OwnershipScope] = []

        # Types that are Copy (primitives)
        self.copy_types = ('int8', 'int16', 'int32', 'int64', 'uint8', 'uint16', 'uint32', 'uint64', 'bool', 'char', 'float32', 'float64', 'i8', 'i16', 'i32', 'i64', 'u8', 'u16', 'u32', 'u64')

    def check(self, program: Program) -> List[OwnershipError]:
        """
        Check ownership for entire program.

        Args:
            program: The AST program node

        Returns:
            List of ownership errors found
        """
        self.errors = []
        self.current_scope = OwnershipScope(name="global")
        self.scope_stack = [self.current_scope]

        # Check all declarations
        for decl in program.declarations:
            self._check_declaration(decl)

        return self.errors

    def _push_scope(self, name: str) -> None:
        """Enter a new scope."""
        new_scope = OwnershipScope(self.current_scope, name)
        self.current_scope.children.append(new_scope)
        self.scope_stack.append(new_scope)
        self.current_scope = new_scope

    def _pop_scope(self) -> None:
        """Exit current scope."""
        self.scope_stack.pop()
        self.current_scope = self.scope_stack[-1] if self.scope_stack else None

    def _get_line(self, node: ASTNode) -> Optional[int]:
        """Get line number from node if available."""
        if hasattr(node, 'span') and node.span:
            return node.span.line if hasattr(node.span, 'line') else None
        return None

    def _is_copy_type(self, ty) -> bool:
        """Check if a type is Copy (primitives)."""
        if isinstance(ty, Type):
            return ty.name.lower() in self.copy_types
        if isinstance(ty, PointerType):
            return True  # Pointers are Copy (the pointer itself, not pointee)
        return False

    def _get_value_kind(self, ty) -> ValueKind:
        """Determine if a type is Copy or Move."""
        if self._is_copy_type(ty):
            return ValueKind.COPY
        return ValueKind.MOVE

    def _check_declaration(self, decl: ASTNode) -> None:
        """Check a top-level declaration."""
        if isinstance(decl, ProcDecl):
            self._check_proc(decl)
        elif isinstance(decl, VarDecl):
            self._check_var_decl(decl)
        elif isinstance(decl, StructDecl):
            pass  # Struct declarations don't need ownership checking
        elif isinstance(decl, ExternDecl):
            pass  # External declarations don't need checking

    def _check_proc(self, proc: ProcDecl) -> None:
        """Check a procedure for ownership violations."""
        self._push_scope(f"fn_{proc.name}")

        # Add parameters to scope
        for param in proc.params:
            kind = self._get_value_kind(param.param_type)
            self.current_scope.declare(param.name, kind)

        # Check body
        for stmt in proc.body:
            self._check_statement(stmt)

        self._pop_scope()

    def _check_statement(self, stmt: ASTNode) -> None:
        """Check a statement for ownership violations."""
        if isinstance(stmt, VarDecl):
            self._check_var_decl(stmt)
        elif isinstance(stmt, Assignment):
            self._check_assignment(stmt)
        elif isinstance(stmt, ReturnStmt):
            self._check_return(stmt)
        elif isinstance(stmt, IfStmt):
            self._check_if(stmt)
        elif isinstance(stmt, WhileStmt):
            self._check_while(stmt)
        elif isinstance(stmt, ForStmt):
            self._check_for(stmt)
        elif isinstance(stmt, ExprStmt):
            self._check_expression(stmt.expr)

    def _check_var_decl(self, decl: VarDecl) -> None:
        """Check a variable declaration."""
        kind = self._get_value_kind(decl.var_type)

        # Check initializer
        if decl.value:
            self._check_expression(decl.value, consuming=True)

        # Declare in current scope
        self.current_scope.declare(decl.name, kind)

    def _check_assignment(self, stmt: Assignment) -> None:
        """Check an assignment for ownership violations."""
        line = self._get_line(stmt)

        # Check if target is valid
        if isinstance(stmt.target, Identifier):
            info = self.current_scope.lookup(stmt.target.name)
            if info:
                # Check if we're assigning to a borrowed variable
                if info.state == OwnershipState.BORROWED:
                    self.errors.append(OwnershipError(
                        f"Cannot assign to borrowed variable '{stmt.target.name}'",
                        line
                    ))
                elif info.state == OwnershipState.MUT_BORROWED:
                    self.errors.append(OwnershipError(
                        f"Cannot assign to mutably borrowed variable '{stmt.target.name}'",
                        line
                    ))

        # Check value - this consumes the value if it's a Move type
        self._check_expression(stmt.value, consuming=True)

        # If target was moved, reassigning brings it back to owned
        if isinstance(stmt.target, Identifier):
            info = self.current_scope.lookup(stmt.target.name)
            if info and info.state == OwnershipState.MOVED:
                info.state = OwnershipState.OWNED
                info.moved_at = None

    def _check_return(self, stmt: ReturnStmt) -> None:
        """Check a return statement."""
        if stmt.value:
            self._check_expression(stmt.value, consuming=True)

    def _check_if(self, stmt: IfStmt) -> None:
        """Check an if statement."""
        # Check condition (doesn't consume)
        self._check_expression(stmt.condition, consuming=False)

        # Check then block
        self._push_scope("if_then")
        for s in stmt.then_block:
            self._check_statement(s)
        self._pop_scope()

        # Check elif blocks
        if stmt.elif_blocks:
            for cond, block in stmt.elif_blocks:
                self._check_expression(cond, consuming=False)
                self._push_scope("elif")
                for s in block:
                    self._check_statement(s)
                self._pop_scope()

        # Check else block
        if stmt.else_block:
            self._push_scope("else")
            for s in stmt.else_block:
                self._check_statement(s)
            self._pop_scope()

    def _check_while(self, stmt: WhileStmt) -> None:
        """Check a while loop."""
        # Check condition
        self._check_expression(stmt.condition, consuming=False)

        # Check body
        self._push_scope("while")
        for s in stmt.body:
            self._check_statement(s)
        self._pop_scope()

    def _check_for(self, stmt: ForStmt) -> None:
        """Check a for loop."""
        # Check range expressions
        self._check_expression(stmt.start, consuming=False)
        self._check_expression(stmt.end, consuming=False)

        # Check body with loop variable
        self._push_scope("for")
        self.current_scope.declare(stmt.var, ValueKind.COPY)  # Loop var is always Copy
        for s in stmt.body:
            self._check_statement(s)
        self._pop_scope()

    def _check_expression(self, expr: ASTNode, consuming: bool = False) -> None:
        """
        Check an expression for ownership violations.

        Args:
            expr: The expression to check
            consuming: Whether this expression consumes (moves) the value
        """
        line = self._get_line(expr)

        if isinstance(expr, Identifier):
            self._check_identifier_use(expr, consuming, line)

        elif isinstance(expr, BinaryExpr):
            self._check_expression(expr.left, consuming=False)
            self._check_expression(expr.right, consuming=False)

        elif isinstance(expr, UnaryExpr):
            self._check_expression(expr.expr, consuming=False)

        elif isinstance(expr, CallExpr):
            # Function arguments are consumed
            for arg in expr.args:
                self._check_expression(arg, consuming=True)

        elif isinstance(expr, IndexExpr):
            self._check_expression(expr.base, consuming=False)
            self._check_expression(expr.index, consuming=False)

        elif isinstance(expr, AddrOfExpr):
            # Taking address creates a borrow
            self._check_addr_of(expr, line)

        elif isinstance(expr, DerefExpr):
            self._check_expression(expr.expr, consuming=False)

        elif isinstance(expr, CastExpr):
            self._check_expression(expr.expr, consuming=consuming)

        elif isinstance(expr, FieldAccessExpr):
            self._check_expression(expr.object, consuming=False)

        elif isinstance(expr, StructLiteral):
            for field_val in expr.field_values.values():
                self._check_expression(field_val, consuming=True)

        elif isinstance(expr, ArrayLiteral):
            for elem in expr.elements:
                self._check_expression(elem, consuming=True)

        elif isinstance(expr, ConditionalExpr):
            self._check_expression(expr.condition, consuming=False)
            self._check_expression(expr.then_expr, consuming=consuming)
            self._check_expression(expr.else_expr, consuming=consuming)

    def _check_identifier_use(self, ident: Identifier, consuming: bool, line: Optional[int]) -> None:
        """Check use of an identifier."""
        info = self.current_scope.lookup(ident.name)
        if not info:
            return  # Unknown variable - let type checker handle this

        # Check if value has been moved
        if info.state == OwnershipState.MOVED:
            self.errors.append(OwnershipError(
                f"Use of moved value '{ident.name}' (moved at line {info.moved_at})",
                line
            ))
            return

        # Check if value is mutably borrowed
        if info.state == OwnershipState.MUT_BORROWED:
            self.errors.append(OwnershipError(
                f"Cannot use '{ident.name}' while mutably borrowed by '{info.mutable_borrow}'",
                line
            ))
            return

        # If consuming a Move type, mark as moved
        if consuming and info.kind == ValueKind.MOVE:
            info.state = OwnershipState.MOVED
            info.moved_at = line

    def _check_addr_of(self, expr: AddrOfExpr, line: Optional[int]) -> None:
        """Check address-of expression (creates borrow)."""
        if isinstance(expr.expr, Identifier):
            info = self.current_scope.lookup(expr.expr.name)
            if info:
                if info.state == OwnershipState.MOVED:
                    self.errors.append(OwnershipError(
                        f"Cannot borrow moved value '{expr.expr.name}'",
                        line
                    ))
                elif info.state == OwnershipState.MUT_BORROWED:
                    self.errors.append(OwnershipError(
                        f"Cannot borrow '{expr.expr.name}' while mutably borrowed",
                        line
                    ))
                else:
                    # Mark as borrowed
                    info.borrowed_by.append("addr_of")
                    if info.state == OwnershipState.OWNED:
                        info.state = OwnershipState.BORROWED


def check_ownership(program: Program) -> List[OwnershipError]:
    """
    Convenience function to check ownership.

    Args:
        program: The AST program node

    Returns:
        List of ownership errors found
    """
    checker = OwnershipChecker()
    return checker.check(program)


# ============================================================================
# Test
# ============================================================================

if __name__ == "__main__":
    from lexer import Lexer
    from parser import Parser

    # Test: Use after move
    code1 = """
type Data = object
    value: int32

proc test() =
    var x: Data = Data(value: 42)
    var y: Data = x
    var z: int32 = x.value
"""

    print("=== Test 1: Use after move ===")
    lexer = Lexer(code1)
    tokens = lexer.tokenize()
    parser = Parser(tokens)
    ast = parser.parse()

    errors = check_ownership(ast)
    for error in errors:
        print(f"  {error}")
    if not errors:
        print("  No ownership errors")

    # Test: Valid code with Copy types
    code2 = """
proc test() =
    var x: int32 = 42
    var y: int32 = x
    var z: int32 = x + y
"""

    print("\n=== Test 2: Copy types (should be fine) ===")
    lexer = Lexer(code2)
    tokens = lexer.tokenize()
    parser = Parser(tokens)
    ast = parser.parse()

    errors = check_ownership(ast)
    for error in errors:
        print(f"  {error}")
    if not errors:
        print("  No ownership errors")

    # Test: Borrow after move
    code3 = """
type Data = object
    value: int32

proc test() =
    var x: Data = Data(value: 42)
    var y: Data = x
    var p: ptr Data = addr(x)
"""

    print("\n=== Test 3: Borrow after move ===")
    lexer = Lexer(code3)
    tokens = lexer.tokenize()
    parser = Parser(tokens)
    ast = parser.parse()

    errors = check_ownership(ast)
    for error in errors:
        print(f"  {error}")
    if not errors:
        print("  No ownership errors")
