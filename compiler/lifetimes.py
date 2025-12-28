#!/usr/bin/env python3
"""
Lifetime Analysis for Brainhair Compiler

This module tracks the lifetimes of values and ensures that:
- References don't outlive their referents
- Stack-allocated values are valid within their scope
- Returned pointers point to valid (non-stack) memory

Lifetime Model:
- Each scope introduces a new lifetime region
- Stack variables have the lifetime of their enclosing scope
- Pointers to stack variables cannot escape their scope
- Arena-allocated memory has a lifetime tied to the arena
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
from enum import Enum, auto

from ast_nodes import *


class LifetimeKind(Enum):
    """Kind of lifetime for a value."""
    STATIC = auto()     # Lives for entire program (global, constant)
    STACK = auto()      # Lives until end of current block
    HEAP = auto()       # Lives until explicitly freed
    ARENA = auto()      # Lives until arena is destroyed
    PARAM = auto()      # Function parameter lifetime


@dataclass
class Lifetime:
    """Represents a lifetime region."""
    id: int
    name: str
    kind: LifetimeKind
    parent: Optional['Lifetime'] = None

    def outlives(self, other: 'Lifetime') -> bool:
        """Check if this lifetime outlives another."""
        if self.kind == LifetimeKind.STATIC:
            return True
        if other.kind == LifetimeKind.STATIC:
            return False
        if self.id == other.id:
            return True
        # Check if other is nested within self
        current = other.parent
        while current:
            if current.id == self.id:
                return True
            current = current.parent
        return False


@dataclass
class ValueLifetime:
    """Tracks lifetime information for a value."""
    name: str
    lifetime: Lifetime
    is_pointer: bool = False
    points_to_lifetime: Optional[Lifetime] = None


@dataclass
class LifetimeError:
    """Represents a lifetime violation."""
    message: str
    line: Optional[int] = None

    def __str__(self):
        if self.line:
            return f"Lifetime error at line {self.line}: {self.message}"
        return f"Lifetime error: {self.message}"


class LifetimeScope:
    """Tracks lifetimes within a scope."""

    def __init__(self, lifetime: Lifetime, parent: Optional['LifetimeScope'] = None):
        self.lifetime = lifetime
        self.parent = parent
        self.values: Dict[str, ValueLifetime] = {}
        self.children: List['LifetimeScope'] = []

    def declare(self, name: str, is_pointer: bool = False,
                points_to: Optional[Lifetime] = None) -> ValueLifetime:
        """Declare a new value in this scope."""
        info = ValueLifetime(
            name=name,
            lifetime=self.lifetime,
            is_pointer=is_pointer,
            points_to_lifetime=points_to
        )
        self.values[name] = info
        return info

    def lookup(self, name: str) -> Optional[ValueLifetime]:
        """Look up a value, checking parent scopes."""
        if name in self.values:
            return self.values[name]
        if self.parent:
            return self.parent.lookup(name)
        return None


class LifetimeChecker:
    """
    Performs lifetime analysis on Brainhair AST.

    Checks for:
    - Returning pointers to stack-allocated values
    - Storing stack pointers in longer-lived locations
    - Using values after their scope ends
    """

    def __init__(self):
        self.errors: List[LifetimeError] = []
        self.current_scope: Optional[LifetimeScope] = None
        self.scope_stack: List[LifetimeScope] = []
        self.lifetime_counter = 0
        self.current_function_return_lifetime: Optional[Lifetime] = None

    def _new_lifetime(self, name: str, kind: LifetimeKind) -> Lifetime:
        """Create a new lifetime."""
        self.lifetime_counter += 1
        parent_lifetime = self.current_scope.lifetime if self.current_scope else None
        return Lifetime(self.lifetime_counter, name, kind, parent_lifetime)

    def check(self, program: Program) -> List[LifetimeError]:
        """Check lifetimes for entire program."""
        self.errors = []

        # Create static lifetime for global scope
        static_lifetime = Lifetime(0, "static", LifetimeKind.STATIC)
        self.current_scope = LifetimeScope(static_lifetime)
        self.scope_stack = [self.current_scope]

        for decl in program.declarations:
            self._check_declaration(decl)

        return self.errors

    def _push_scope(self, name: str, kind: LifetimeKind = LifetimeKind.STACK) -> None:
        """Enter a new scope."""
        lifetime = self._new_lifetime(name, kind)
        new_scope = LifetimeScope(lifetime, self.current_scope)
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

    def _is_pointer_type(self, ty) -> bool:
        """Check if type is a pointer type."""
        return isinstance(ty, PointerType)

    def _check_declaration(self, decl: ASTNode) -> None:
        """Check a top-level declaration."""
        if isinstance(decl, ProcDecl):
            self._check_proc(decl)
        elif isinstance(decl, VarDecl):
            self._check_var_decl(decl, is_global=True)

    def _check_proc(self, proc: ProcDecl) -> None:
        """Check a procedure for lifetime violations."""
        # Create function scope
        self._push_scope(f"fn_{proc.name}", LifetimeKind.STACK)

        # Track if return type is a pointer
        returns_pointer = self._is_pointer_type(proc.return_type)

        # For functions returning pointers, we need to track what lifetimes are valid
        if returns_pointer:
            # Can only return static lifetime or arena-allocated pointers
            self.current_function_return_lifetime = self.scope_stack[0].lifetime  # static

        # Add parameters (they have PARAM lifetime, outlive the function body)
        param_lifetime = self._new_lifetime(f"params_{proc.name}", LifetimeKind.PARAM)
        for param in proc.params:
            is_ptr = self._is_pointer_type(param.param_type)
            self.current_scope.declare(param.name, is_pointer=is_ptr, points_to=param_lifetime if is_ptr else None)

        # Check body
        for stmt in proc.body:
            self._check_statement(stmt)

        self.current_function_return_lifetime = None
        self._pop_scope()

    def _check_statement(self, stmt: ASTNode) -> None:
        """Check a statement for lifetime violations."""
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

    def _check_var_decl(self, decl: VarDecl, is_global: bool = False) -> None:
        """Check a variable declaration."""
        is_ptr = self._is_pointer_type(decl.var_type)

        # Determine what the pointer points to if it's initialized
        points_to = None
        if is_ptr and decl.value:
            points_to = self._get_expression_lifetime(decl.value)

        if is_global:
            # Global variables have static lifetime
            points_to_lt = self.scope_stack[0].lifetime if is_ptr else None
            self.current_scope.declare(decl.name, is_pointer=is_ptr, points_to=points_to_lt)
        else:
            self.current_scope.declare(decl.name, is_pointer=is_ptr, points_to=points_to)

        if decl.value:
            self._check_expression(decl.value)

    def _check_assignment(self, stmt: Assignment) -> None:
        """Check an assignment for lifetime violations."""
        line = self._get_line(stmt)

        # If assigning to a pointer, check lifetime compatibility
        if isinstance(stmt.target, Identifier):
            target_info = self.current_scope.lookup(stmt.target.name)
            if target_info and target_info.is_pointer:
                value_lifetime = self._get_expression_lifetime(stmt.value)
                if value_lifetime and target_info.lifetime:
                    # Value's lifetime must outlive target's lifetime
                    if not value_lifetime.outlives(target_info.lifetime):
                        self.errors.append(LifetimeError(
                            f"Assigned value does not live long enough for '{stmt.target.name}'",
                            line
                        ))
                # Update what the pointer points to
                target_info.points_to_lifetime = value_lifetime

        self._check_expression(stmt.value)

    def _check_return(self, stmt: ReturnStmt) -> None:
        """Check a return statement for lifetime violations."""
        if not stmt.value:
            return

        line = self._get_line(stmt)

        # Only check if returning a pointer-like expression
        is_returning_pointer = self._is_pointer_expression(stmt.value)

        if is_returning_pointer:
            value_lifetime = self._get_expression_lifetime(stmt.value)
            # If returning a pointer, it must not point to stack-local data
            if value_lifetime and value_lifetime.kind == LifetimeKind.STACK:
                # Check if it's from current function's stack
                if len(self.scope_stack) > 1 and value_lifetime.id >= self.scope_stack[1].lifetime.id:
                    self.errors.append(LifetimeError(
                        "Cannot return pointer to stack-allocated value",
                        line
                    ))

        self._check_expression(stmt.value)

    def _is_pointer_expression(self, expr: ASTNode) -> bool:
        """Check if an expression produces a pointer value."""
        if isinstance(expr, AddrOfExpr):
            return True
        elif isinstance(expr, Identifier):
            info = self.current_scope.lookup(expr.name)
            return info.is_pointer if info else False
        elif isinstance(expr, CastExpr):
            return self._is_pointer_type(expr.target_type)
        elif isinstance(expr, CallExpr):
            # Can't easily determine from just the call; assume not
            return False
        return False

    def _check_if(self, stmt: IfStmt) -> None:
        """Check an if statement."""
        self._check_expression(stmt.condition)

        self._push_scope("if_then")
        for s in stmt.then_block:
            self._check_statement(s)
        self._pop_scope()

        if stmt.elif_blocks:
            for cond, block in stmt.elif_blocks:
                self._check_expression(cond)
                self._push_scope("elif")
                for s in block:
                    self._check_statement(s)
                self._pop_scope()

        if stmt.else_block:
            self._push_scope("else")
            for s in stmt.else_block:
                self._check_statement(s)
            self._pop_scope()

    def _check_while(self, stmt: WhileStmt) -> None:
        """Check a while loop."""
        self._check_expression(stmt.condition)

        self._push_scope("while")
        for s in stmt.body:
            self._check_statement(s)
        self._pop_scope()

    def _check_for(self, stmt: ForStmt) -> None:
        """Check a for loop."""
        self._check_expression(stmt.start)
        self._check_expression(stmt.end)

        self._push_scope("for")
        self.current_scope.declare(stmt.var, is_pointer=False)
        for s in stmt.body:
            self._check_statement(s)
        self._pop_scope()

    def _check_expression(self, expr: ASTNode) -> None:
        """Check an expression for lifetime violations."""
        if isinstance(expr, BinaryExpr):
            self._check_expression(expr.left)
            self._check_expression(expr.right)
        elif isinstance(expr, UnaryExpr):
            self._check_expression(expr.expr)
        elif isinstance(expr, CallExpr):
            for arg in expr.args:
                self._check_expression(arg)
        elif isinstance(expr, IndexExpr):
            self._check_expression(expr.base)
            self._check_expression(expr.index)
        elif isinstance(expr, AddrOfExpr):
            self._check_expression(expr.expr)
        elif isinstance(expr, DerefExpr):
            self._check_expression(expr.expr)
        elif isinstance(expr, CastExpr):
            self._check_expression(expr.expr)
        elif isinstance(expr, FieldAccessExpr):
            self._check_expression(expr.object)
        elif isinstance(expr, StructLiteral):
            for field_val in expr.field_values.values():
                self._check_expression(field_val)
        elif isinstance(expr, ArrayLiteral):
            for elem in expr.elements:
                self._check_expression(elem)
        elif isinstance(expr, ConditionalExpr):
            self._check_expression(expr.condition)
            self._check_expression(expr.then_expr)
            self._check_expression(expr.else_expr)

    def _get_expression_lifetime(self, expr: ASTNode) -> Optional[Lifetime]:
        """Get the lifetime of an expression's result."""
        if isinstance(expr, Identifier):
            info = self.current_scope.lookup(expr.name)
            if info:
                if info.is_pointer:
                    return info.points_to_lifetime
                return info.lifetime
            return None

        elif isinstance(expr, AddrOfExpr):
            # Address-of returns a pointer with the lifetime of the operand
            if isinstance(expr.expr, Identifier):
                info = self.current_scope.lookup(expr.expr.name)
                if info:
                    return info.lifetime
            return self.current_scope.lifetime

        elif isinstance(expr, DerefExpr):
            # Dereferencing returns the pointed-to value's lifetime
            return self._get_expression_lifetime(expr.expr)

        elif isinstance(expr, CallExpr):
            # Function calls might return pointers - assume they're valid
            # (In a more complete system, we'd track function signatures)
            return self.scope_stack[0].lifetime  # Assume static for now

        elif isinstance(expr, (IntLiteral, BoolLiteral, CharLiteral, StringLiteral)):
            # Literals have static lifetime
            return self.scope_stack[0].lifetime

        elif isinstance(expr, CastExpr):
            return self._get_expression_lifetime(expr.expr)

        elif isinstance(expr, IndexExpr):
            return self._get_expression_lifetime(expr.base)

        elif isinstance(expr, FieldAccessExpr):
            return self._get_expression_lifetime(expr.object)

        elif isinstance(expr, StructLiteral):
            # Struct literals have the current scope's lifetime
            return self.current_scope.lifetime

        return None


def check_lifetimes(program: Program) -> List[LifetimeError]:
    """
    Convenience function to check lifetimes.

    Args:
        program: The AST program node

    Returns:
        List of lifetime errors found
    """
    checker = LifetimeChecker()
    return checker.check(program)


# ============================================================================
# Test
# ============================================================================

if __name__ == "__main__":
    from lexer import Lexer
    from parser import Parser

    # Test: Return pointer to stack variable
    code1 = """
proc bad(): ptr int32 =
    var x: int32 = 42
    return addr(x)
"""

    print("=== Test 1: Return pointer to stack variable ===")
    lexer = Lexer(code1)
    tokens = lexer.tokenize()
    parser = Parser(tokens)
    ast = parser.parse()

    errors = check_lifetimes(ast)
    for error in errors:
        print(f"  {error}")
    if not errors:
        print("  No lifetime errors")

    # Test: Valid code with local pointer
    code2 = """
proc good() =
    var x: int32 = 42
    var p: ptr int32 = addr(x)
    var y: int32 = p[0]
"""

    print("\n=== Test 2: Valid local pointer use ===")
    lexer = Lexer(code2)
    tokens = lexer.tokenize()
    parser = Parser(tokens)
    ast = parser.parse()

    errors = check_lifetimes(ast)
    for error in errors:
        print(f"  {error}")
    if not errors:
        print("  No lifetime errors")

    # Test: Passing local address to function (valid)
    code3 = """
proc use_ptr(p: ptr int32) =
    discard p[0]

proc caller() =
    var x: int32 = 42
    use_ptr(addr(x))
"""

    print("\n=== Test 3: Passing local address to function ===")
    lexer = Lexer(code3)
    tokens = lexer.tokenize()
    parser = Parser(tokens)
    ast = parser.parse()

    errors = check_lifetimes(ast)
    for error in errors:
        print(f"  {error}")
    if not errors:
        print("  No lifetime errors")
