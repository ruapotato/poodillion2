#!/usr/bin/env python3
"""
Type Checker for Brainhair Compiler

This module implements static type checking for the Brainhair language.
It validates type annotations, infers expression types, and ensures type
safety throughout the program.
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Set
from enum import Enum

from ast_nodes import *
from symbols import (
    SymbolTable, TypeInfo, Span, FunctionSymbol, VariableSymbol,
    ParamSymbol, TypeSymbol, Symbol, SymbolKind,
    create_builtin_type, create_pointer_type, create_array_type,
    is_numeric_type, is_integer_type, is_float_type
)


@dataclass
class TypeError:
    """Represents a type error found during type checking."""
    message: str
    span: Optional[Span] = None

    def __str__(self) -> str:
        location = f" at {self.span}" if self.span else ""
        return f"Type error{location}: {self.message}"


class TypeChecker:
    """
    Type checker for Brainhair programs.

    Performs static type analysis including:
    - Type annotation validation
    - Expression type inference
    - Binary/unary operation type checking
    - Function call validation
    - Assignment compatibility checking
    """

    def __init__(self):
        self.symbol_table = SymbolTable()
        self.errors: List[TypeError] = []
        self.current_function: Optional[FunctionSymbol] = None
        self.in_loop: int = 0  # Track loop nesting for break/continue

        # Cache for expression types (AST node id -> TypeInfo)
        self.expr_types: Dict[int, TypeInfo] = {}

    def check(self, ast: Program) -> List[TypeError]:
        """
        Type check the entire program.

        Args:
            ast: The program AST to check

        Returns:
            List of type errors found (empty if no errors)
        """
        self.errors = []
        self.expr_types = {}

        try:
            self._check_program(ast)
        except Exception as e:
            # Catch any unexpected errors during type checking
            self.errors.append(TypeError(f"Internal type checker error: {e}"))

        return self.errors

    def _check_program(self, node: Program) -> None:
        """Check all top-level declarations in the program."""
        # First pass: collect all type and function declarations
        for decl in node.declarations:
            if isinstance(decl, StructDecl):
                self._register_struct(decl)
            elif isinstance(decl, ProcDecl):
                self._register_function(decl)
            elif isinstance(decl, ExternDecl):
                self._register_extern(decl)

        # Second pass: check function bodies and global variables
        for decl in node.declarations:
            if isinstance(decl, ProcDecl):
                self._check_proc_decl(decl)
            elif isinstance(decl, VarDecl):
                self._check_var_decl(decl)

    def _register_struct(self, node: StructDecl) -> None:
        """Register a struct type in the symbol table."""
        try:
            # Build field type map
            fields = {}
            for field in node.fields:
                field_type = self._resolve_type(field.field_type)
                if field_type:
                    fields[field.name] = field_type

            # Create type symbol
            span = self._get_span(node)
            type_symbol = TypeSymbol(
                name=node.name,
                span=span,
                type_info=TypeInfo(node.name),
                fields=fields,
                is_struct=True
            )

            self.symbol_table.define(type_symbol)

        except Exception as e:
            self.errors.append(TypeError(
                f"Error registering struct '{node.name}': {e}",
                self._get_span(node)
            ))

    def _register_function(self, node: ProcDecl) -> None:
        """Register a function declaration in the symbol table."""
        try:
            span = self._get_span(node)

            # Build parameter symbols
            params = []
            for i, param in enumerate(node.params):
                param_type = self._resolve_type(param.param_type)
                if param_type is None:
                    self.errors.append(TypeError(
                        f"Invalid parameter type for '{param.name}'",
                        self._get_span(param)
                    ))
                    continue

                param_sym = ParamSymbol(
                    name=param.name,
                    span=self._get_span(param),
                    type_info=param_type,
                    position=i
                )
                params.append(param_sym)

            # Resolve return type
            return_type = None
            if node.return_type:
                return_type = self._resolve_type(node.return_type)
                if return_type is None:
                    self.errors.append(TypeError(
                        f"Invalid return type for function '{node.name}'",
                        span
                    ))

            # Create function symbol
            func_symbol = FunctionSymbol(
                name=node.name,
                span=span,
                params=params,
                return_type=return_type
            )

            self.symbol_table.define(func_symbol)

        except Exception as e:
            self.errors.append(TypeError(
                f"Error registering function '{node.name}': {e}",
                self._get_span(node)
            ))

    def _register_extern(self, node: ExternDecl) -> None:
        """Register an external function declaration."""
        try:
            span = self._get_span(node)

            # Build parameter symbols
            params = []
            for i, param in enumerate(node.params):
                param_type = self._resolve_type(param.param_type)
                if param_type is None:
                    self.errors.append(TypeError(
                        f"Invalid parameter type for '{param.name}' in extern '{node.name}'",
                        self._get_span(param)
                    ))
                    continue

                param_sym = ParamSymbol(
                    name=param.name,
                    span=self._get_span(param),
                    type_info=param_type,
                    position=i
                )
                params.append(param_sym)

            # Resolve return type
            return_type = None
            if node.return_type:
                return_type = self._resolve_type(node.return_type)

            # Create extern function symbol
            func_symbol = FunctionSymbol(
                name=node.name,
                span=span,
                params=params,
                return_type=return_type,
                is_extern=True
            )

            self.symbol_table.define(func_symbol)

        except Exception as e:
            self.errors.append(TypeError(
                f"Error registering extern '{node.name}': {e}",
                self._get_span(node)
            ))

    def _check_proc_decl(self, node: ProcDecl) -> None:
        """Check a procedure/function declaration."""
        # Get the function symbol
        func_symbol = self.symbol_table.lookup_optional(node.name)
        if not isinstance(func_symbol, FunctionSymbol):
            return  # Error already reported during registration

        # Enter function scope
        self.symbol_table.push_scope(f"fn_{node.name}")
        old_function = self.current_function
        self.current_function = func_symbol

        try:
            # Add parameters to scope
            for param_sym in func_symbol.params:
                self.symbol_table.define(param_sym)

            # Check function body
            for stmt in node.body:
                self._check_statement(stmt)

            # Check that non-void functions return a value
            if func_symbol.return_type and func_symbol.return_type.name != "void":
                if not self._has_return(node.body):
                    self.errors.append(TypeError(
                        f"Function '{node.name}' must return a value of type {func_symbol.return_type}",
                        self._get_span(node)
                    ))

        finally:
            self.symbol_table.pop_scope()
            self.current_function = old_function

    def _has_return(self, stmts: List[ASTNode]) -> bool:
        """Check if a statement list contains a return statement."""
        for stmt in stmts:
            if isinstance(stmt, ReturnStmt):
                return True
            elif isinstance(stmt, IfStmt):
                # Check if all branches return
                if stmt.else_block:
                    has_then = self._has_return(stmt.then_block)
                    has_else = self._has_return(stmt.else_block)
                    if has_then and has_else:
                        return True
        return False

    def _check_statement(self, node: ASTNode) -> None:
        """Check a statement node."""
        if isinstance(node, VarDecl):
            self._check_var_decl(node)
        elif isinstance(node, Assignment):
            self._check_assignment(node)
        elif isinstance(node, ReturnStmt):
            self._check_return(node)
        elif isinstance(node, IfStmt):
            self._check_if(node)
        elif isinstance(node, WhileStmt):
            self._check_while(node)
        elif isinstance(node, ForStmt):
            self._check_for(node)
        elif isinstance(node, ExprStmt):
            self._check_expr(node.expr)
        elif isinstance(node, BreakStmt):
            self._check_break(node)
        elif isinstance(node, ContinueStmt):
            self._check_continue(node)

    def _check_var_decl(self, node: VarDecl) -> None:
        """Check a variable declaration."""
        # Resolve the declared type
        var_type = self._resolve_type(node.var_type)
        if var_type is None:
            self.errors.append(TypeError(
                f"Invalid type in variable declaration '{node.name}'",
                self._get_span(node)
            ))
            return

        # Check initializer if present
        if node.value:
            value_type = self._check_expr(node.value)
            if value_type and not self._types_compatible(var_type, value_type):
                self.errors.append(TypeError(
                    f"Cannot initialize variable '{node.name}' of type {var_type} "
                    f"with value of type {value_type}",
                    self._get_span(node)
                ))

        # Add variable to symbol table
        try:
            var_symbol = VariableSymbol(
                name=node.name,
                span=self._get_span(node),
                type_info=var_type,
                is_mutable=not node.is_const
            )
            self.symbol_table.define(var_symbol)
        except Exception as e:
            self.errors.append(TypeError(
                f"Error declaring variable '{node.name}': {e}",
                self._get_span(node)
            ))

    def _check_assignment(self, node: Assignment) -> None:
        """Check an assignment statement."""
        # Check target is assignable
        if isinstance(node.target, Identifier):
            symbol = self.symbol_table.lookup_optional(node.target.name)
            if symbol is None:
                self.errors.append(TypeError(
                    f"Undefined variable '{node.target.name}'",
                    self._get_span(node.target)
                ))
                return

            # Check if variable is mutable
            if isinstance(symbol, VariableSymbol) and not symbol.is_mutable:
                self.errors.append(TypeError(
                    f"Cannot assign to immutable variable '{node.target.name}'",
                    self._get_span(node)
                ))
                return

        # Check types match
        target_type = self._check_expr(node.target)
        value_type = self._check_expr(node.value)

        if target_type and value_type:
            if not self._types_compatible(target_type, value_type):
                self.errors.append(TypeError(
                    f"Cannot assign value of type {value_type} to target of type {target_type}",
                    self._get_span(node)
                ))

    def _check_return(self, node: ReturnStmt) -> None:
        """Check a return statement."""
        if not self.current_function:
            self.errors.append(TypeError(
                "Return statement outside of function",
                self._get_span(node)
            ))
            return

        expected_type = self.current_function.return_type

        if node.value is None:
            # Void return
            if expected_type and expected_type.name != "void":
                self.errors.append(TypeError(
                    f"Function must return a value of type {expected_type}",
                    self._get_span(node)
                ))
        else:
            # Value return
            if expected_type is None or expected_type.name == "void":
                self.errors.append(TypeError(
                    "Cannot return a value from void function",
                    self._get_span(node)
                ))
                return

            value_type = self._check_expr(node.value)
            if value_type and not self._types_compatible(expected_type, value_type):
                self.errors.append(TypeError(
                    f"Cannot return value of type {value_type}, expected {expected_type}",
                    self._get_span(node)
                ))

    def _check_if(self, node: IfStmt) -> None:
        """Check an if statement."""
        # Check condition is boolean
        cond_type = self._check_expr(node.condition)
        if cond_type and cond_type.name != "bool":
            self.errors.append(TypeError(
                f"If condition must be bool, got {cond_type}",
                self._get_span(node.condition)
            ))

        # Check then block
        self.symbol_table.push_scope("if_then")
        for stmt in node.then_block:
            self._check_statement(stmt)
        self.symbol_table.pop_scope()

        # Check elif blocks
        if node.elif_blocks:
            for elif_cond, elif_block in node.elif_blocks:
                elif_type = self._check_expr(elif_cond)
                if elif_type and elif_type.name != "bool":
                    self.errors.append(TypeError(
                        f"Elif condition must be bool, got {elif_type}",
                        self._get_span(elif_cond)
                    ))

                self.symbol_table.push_scope("elif")
                for stmt in elif_block:
                    self._check_statement(stmt)
                self.symbol_table.pop_scope()

        # Check else block
        if node.else_block:
            self.symbol_table.push_scope("else")
            for stmt in node.else_block:
                self._check_statement(stmt)
            self.symbol_table.pop_scope()

    def _check_while(self, node: WhileStmt) -> None:
        """Check a while loop."""
        # Check condition is boolean
        cond_type = self._check_expr(node.condition)
        if cond_type and cond_type.name != "bool":
            self.errors.append(TypeError(
                f"While condition must be bool, got {cond_type}",
                self._get_span(node.condition)
            ))

        # Check body
        self.symbol_table.push_scope("while")
        self.in_loop += 1
        try:
            for stmt in node.body:
                self._check_statement(stmt)
        finally:
            self.in_loop -= 1
            self.symbol_table.pop_scope()

    def _check_for(self, node: ForStmt) -> None:
        """Check a for loop."""
        # Check start and end expressions are integers
        start_type = self._check_expr(node.start)
        end_type = self._check_expr(node.end)

        if start_type and not is_integer_type(start_type):
            self.errors.append(TypeError(
                f"For loop start must be integer, got {start_type}",
                self._get_span(node.start)
            ))

        if end_type and not is_integer_type(end_type):
            self.errors.append(TypeError(
                f"For loop end must be integer, got {end_type}",
                self._get_span(node.end)
            ))

        # Create loop variable scope
        self.symbol_table.push_scope("for")
        self.in_loop += 1
        try:
            # Add loop variable (default to int32)
            loop_var_type = start_type if start_type and is_integer_type(start_type) else create_builtin_type("i32")
            var_symbol = VariableSymbol(
                name=node.var,
                span=Span(0, 0, 0),  # No specific span for loop var
                type_info=loop_var_type,
                is_mutable=False
            )
            self.symbol_table.define(var_symbol)

            # Check body
            for stmt in node.body:
                self._check_statement(stmt)
        finally:
            self.in_loop -= 1
            self.symbol_table.pop_scope()

    def _check_break(self, node: BreakStmt) -> None:
        """Check a break statement."""
        if self.in_loop == 0:
            self.errors.append(TypeError(
                "Break statement outside of loop",
                self._get_span(node)
            ))

    def _check_continue(self, node: ContinueStmt) -> None:
        """Check a continue statement."""
        if self.in_loop == 0:
            self.errors.append(TypeError(
                "Continue statement outside of loop",
                self._get_span(node)
            ))

    def _check_expr(self, node: ASTNode) -> Optional[TypeInfo]:
        """
        Check an expression and return its type.

        Returns None if type cannot be determined or there's an error.
        """
        # Check cache
        node_id = id(node)
        if node_id in self.expr_types:
            return self.expr_types[node_id]

        result = None

        if isinstance(node, IntLiteral):
            result = self._check_int_literal(node)
        elif isinstance(node, CharLiteral):
            result = create_builtin_type("char")
        elif isinstance(node, StringLiteral):
            # String is pointer to char
            result = create_pointer_type(create_builtin_type("char"))
        elif isinstance(node, BoolLiteral):
            result = create_builtin_type("bool")
        elif isinstance(node, Identifier):
            result = self._check_identifier(node)
        elif isinstance(node, BinaryExpr):
            result = self._check_binary_expr(node)
        elif isinstance(node, UnaryExpr):
            result = self._check_unary_expr(node)
        elif isinstance(node, CallExpr):
            result = self._check_call_expr(node)
        elif isinstance(node, CastExpr):
            result = self._check_cast_expr(node)
        elif isinstance(node, IndexExpr):
            result = self._check_index_expr(node)
        elif isinstance(node, AddrOfExpr):
            result = self._check_addr_of_expr(node)
        elif isinstance(node, DerefExpr):
            result = self._check_deref_expr(node)
        elif isinstance(node, FieldAccessExpr):
            result = self._check_field_access_expr(node)
        elif isinstance(node, StructLiteral):
            result = self._check_struct_literal(node)
        elif isinstance(node, ArrayLiteral):
            result = self._check_array_literal(node)
        elif isinstance(node, SizeOfExpr):
            result = create_builtin_type("u32")
        elif isinstance(node, ConditionalExpr):
            result = self._check_conditional_expr(node)

        # Cache result
        if result:
            self.expr_types[node_id] = result

        return result

    def _check_int_literal(self, node: IntLiteral) -> TypeInfo:
        """Infer type of integer literal based on value."""
        value = node.value

        # Default to i32 for most integers
        if -2147483648 <= value <= 2147483647:
            return create_builtin_type("i32")
        elif 0 <= value <= 4294967295:
            return create_builtin_type("u32")
        else:
            return create_builtin_type("i64")

    def _check_identifier(self, node: Identifier) -> Optional[TypeInfo]:
        """Check identifier and return its type."""
        symbol = self.symbol_table.lookup_optional(node.name)
        if symbol is None:
            self.errors.append(TypeError(
                f"Undefined identifier '{node.name}'",
                self._get_span(node)
            ))
            return None

        return symbol.type_info

    def _check_binary_expr(self, node: BinaryExpr) -> Optional[TypeInfo]:
        """Check binary expression and return result type."""
        left_type = self._check_expr(node.left)
        right_type = self._check_expr(node.right)

        if not left_type or not right_type:
            return None

        op = node.op

        # Arithmetic operators: +, -, *, /, %
        if op in [BinOp.ADD, BinOp.SUB, BinOp.MUL, BinOp.DIV, BinOp.MOD]:
            if not is_numeric_type(left_type):
                self.errors.append(TypeError(
                    f"Left operand of {op.value} must be numeric, got {left_type}",
                    self._get_span(node.left)
                ))
                return None

            if not is_numeric_type(right_type):
                self.errors.append(TypeError(
                    f"Right operand of {op.value} must be numeric, got {right_type}",
                    self._get_span(node.right)
                ))
                return None

            if not self._types_compatible(left_type, right_type):
                self.errors.append(TypeError(
                    f"Type mismatch in {op.value}: {left_type} and {right_type}",
                    self._get_span(node)
                ))
                return None

            return left_type

        # Comparison operators: ==, !=, <, <=, >, >=
        elif op in [BinOp.EQ, BinOp.NEQ, BinOp.LT, BinOp.LTE, BinOp.GT, BinOp.GTE]:
            if op in [BinOp.LT, BinOp.LTE, BinOp.GT, BinOp.GTE]:
                # Ordering comparisons require numeric types
                if not is_numeric_type(left_type):
                    self.errors.append(TypeError(
                        f"Left operand of {op.value} must be numeric, got {left_type}",
                        self._get_span(node.left)
                    ))
                    return None

                if not is_numeric_type(right_type):
                    self.errors.append(TypeError(
                        f"Right operand of {op.value} must be numeric, got {right_type}",
                        self._get_span(node.right)
                    ))
                    return None

            if not self._types_compatible(left_type, right_type):
                self.errors.append(TypeError(
                    f"Cannot compare {left_type} and {right_type}",
                    self._get_span(node)
                ))
                return None

            return create_builtin_type("bool")

        # Logical operators: and, or
        elif op in [BinOp.AND, BinOp.OR]:
            if left_type.name != "bool":
                self.errors.append(TypeError(
                    f"Left operand of {op.value} must be bool, got {left_type}",
                    self._get_span(node.left)
                ))
                return None

            if right_type.name != "bool":
                self.errors.append(TypeError(
                    f"Right operand of {op.value} must be bool, got {right_type}",
                    self._get_span(node.right)
                ))
                return None

            return create_builtin_type("bool")

        # Bitwise operators: &, |, ^, <<, >>
        elif op in [BinOp.BIT_AND, BinOp.BIT_OR, BinOp.BIT_XOR, BinOp.SHL, BinOp.SHR]:
            if not is_integer_type(left_type):
                self.errors.append(TypeError(
                    f"Left operand of {op.value} must be integer, got {left_type}",
                    self._get_span(node.left)
                ))
                return None

            if not is_integer_type(right_type):
                self.errors.append(TypeError(
                    f"Right operand of {op.value} must be integer, got {right_type}",
                    self._get_span(node.right)
                ))
                return None

            return left_type

        return None

    def _check_unary_expr(self, node: UnaryExpr) -> Optional[TypeInfo]:
        """Check unary expression and return result type."""
        expr_type = self._check_expr(node.expr)
        if not expr_type:
            return None

        if node.op == UnaryOp.NEG:
            if not is_numeric_type(expr_type):
                self.errors.append(TypeError(
                    f"Unary negation requires numeric type, got {expr_type}",
                    self._get_span(node)
                ))
                return None
            return expr_type

        elif node.op == UnaryOp.NOT:
            if expr_type.name != "bool":
                self.errors.append(TypeError(
                    f"Logical not requires bool type, got {expr_type}",
                    self._get_span(node)
                ))
                return None
            return create_builtin_type("bool")

        return None

    def _check_call_expr(self, node: CallExpr) -> Optional[TypeInfo]:
        """Check function call and return result type."""
        # Look up function
        func_symbol = self.symbol_table.lookup_optional(node.func)
        if func_symbol is None:
            self.errors.append(TypeError(
                f"Undefined function '{node.func}'",
                self._get_span(node)
            ))
            return None

        if not isinstance(func_symbol, FunctionSymbol):
            self.errors.append(TypeError(
                f"'{node.func}' is not a function",
                self._get_span(node)
            ))
            return None

        # Check argument count
        if len(node.args) != len(func_symbol.params):
            self.errors.append(TypeError(
                f"Function '{node.func}' expects {len(func_symbol.params)} arguments, "
                f"got {len(node.args)}",
                self._get_span(node)
            ))
            return func_symbol.return_type

        # Check argument types
        for i, (arg, param) in enumerate(zip(node.args, func_symbol.params)):
            arg_type = self._check_expr(arg)
            if arg_type and not self._types_compatible(param.type_info, arg_type):
                self.errors.append(TypeError(
                    f"Argument {i+1} to '{node.func}': expected {param.type_info}, got {arg_type}",
                    self._get_span(arg)
                ))

        return func_symbol.return_type

    def _check_cast_expr(self, node: CastExpr) -> Optional[TypeInfo]:
        """Check cast expression."""
        target_type = self._resolve_type(node.target_type)
        expr_type = self._check_expr(node.expr)

        if not target_type:
            self.errors.append(TypeError(
                "Invalid cast target type",
                self._get_span(node)
            ))
            return None

        # Allow casts between numeric types and pointer types
        # More sophisticated cast validation could be added here

        return target_type

    def _check_index_expr(self, node: IndexExpr) -> Optional[TypeInfo]:
        """Check array/pointer indexing."""
        array_type = self._check_expr(node.array)
        index_type = self._check_expr(node.index)

        if not array_type:
            return None

        # Check index is integer
        if index_type and not is_integer_type(index_type):
            self.errors.append(TypeError(
                f"Array index must be integer, got {index_type}",
                self._get_span(node.index)
            ))

        # Check array_type is indexable (array or pointer)
        if array_type.is_array:
            return array_type.element_type
        elif array_type.is_pointer:
            return array_type.element_type
        else:
            self.errors.append(TypeError(
                f"Cannot index type {array_type}",
                self._get_span(node.array)
            ))
            return None

    def _check_addr_of_expr(self, node: AddrOfExpr) -> Optional[TypeInfo]:
        """Check address-of expression."""
        expr_type = self._check_expr(node.expr)
        if not expr_type:
            return None

        # Check that we're taking address of an lvalue
        if not isinstance(node.expr, (Identifier, IndexExpr, FieldAccessExpr, DerefExpr)):
            self.errors.append(TypeError(
                "Cannot take address of non-lvalue expression",
                self._get_span(node)
            ))
            return None

        return create_pointer_type(expr_type)

    def _check_deref_expr(self, node: DerefExpr) -> Optional[TypeInfo]:
        """Check pointer dereference."""
        expr_type = self._check_expr(node.expr)
        if not expr_type:
            return None

        if not expr_type.is_pointer:
            self.errors.append(TypeError(
                f"Cannot dereference non-pointer type {expr_type}",
                self._get_span(node)
            ))
            return None

        return expr_type.element_type

    def _check_field_access_expr(self, node: FieldAccessExpr) -> Optional[TypeInfo]:
        """Check struct field access."""
        obj_type = self._check_expr(node.object)
        if not obj_type:
            return None

        # Look up the type
        type_symbol = self.symbol_table.lookup_optional(obj_type.name)
        if not isinstance(type_symbol, TypeSymbol):
            self.errors.append(TypeError(
                f"Type {obj_type} is not a struct",
                self._get_span(node.object)
            ))
            return None

        # Check field exists
        if not type_symbol.has_field(node.field_name):
            self.errors.append(TypeError(
                f"Type {obj_type.name} has no field '{node.field_name}'",
                self._get_span(node)
            ))
            return None

        return type_symbol.get_field(node.field_name)

    def _check_struct_literal(self, node: StructLiteral) -> Optional[TypeInfo]:
        """Check struct literal."""
        # Look up struct type
        type_symbol = self.symbol_table.lookup_optional(node.struct_type)
        if not isinstance(type_symbol, TypeSymbol):
            self.errors.append(TypeError(
                f"Undefined struct type '{node.struct_type}'",
                self._get_span(node)
            ))
            return None

        # Check all provided fields exist and have correct types
        for field_name, field_value in node.field_values.items():
            if not type_symbol.has_field(field_name):
                self.errors.append(TypeError(
                    f"Struct '{node.struct_type}' has no field '{field_name}'",
                    self._get_span(node)
                ))
                continue

            expected_type = type_symbol.get_field(field_name)
            value_type = self._check_expr(field_value)

            if value_type and not self._types_compatible(expected_type, value_type):
                self.errors.append(TypeError(
                    f"Field '{field_name}' expects type {expected_type}, got {value_type}",
                    self._get_span(field_value)
                ))

        return TypeInfo(node.struct_type)

    def _check_array_literal(self, node: ArrayLiteral) -> Optional[TypeInfo]:
        """Check array literal."""
        if not node.elements:
            self.errors.append(TypeError(
                "Cannot infer type of empty array literal",
                self._get_span(node)
            ))
            return None

        # Infer element type from first element
        first_type = self._check_expr(node.elements[0])
        if not first_type:
            return None

        # Check all elements have same type
        for i, elem in enumerate(node.elements[1:], 1):
            elem_type = self._check_expr(elem)
            if elem_type and not self._types_compatible(first_type, elem_type):
                self.errors.append(TypeError(
                    f"Array element {i} has type {elem_type}, expected {first_type}",
                    self._get_span(elem)
                ))

        return create_array_type(first_type, len(node.elements))

    def _check_conditional_expr(self, node: ConditionalExpr) -> Optional[TypeInfo]:
        """Check conditional expression (ternary)."""
        cond_type = self._check_expr(node.condition)
        if cond_type and cond_type.name != "bool":
            self.errors.append(TypeError(
                f"Conditional expression condition must be bool, got {cond_type}",
                self._get_span(node.condition)
            ))

        then_type = self._check_expr(node.then_expr)
        else_type = self._check_expr(node.else_expr)

        if then_type and else_type:
            if not self._types_compatible(then_type, else_type):
                self.errors.append(TypeError(
                    f"Conditional expression branches have incompatible types: "
                    f"{then_type} and {else_type}",
                    self._get_span(node)
                ))
                return None

        return then_type if then_type else else_type

    def _resolve_type(self, type_node: Type) -> Optional[TypeInfo]:
        """
        Resolve a type annotation to TypeInfo.

        Handles primitive types, pointers, and arrays.
        """
        if isinstance(type_node, Type):
            # Simple type - look it up
            # Map Brainhair type names to internal names
            type_map = {
                "int": "i32",
                "int8": "i8",
                "int16": "i16",
                "int32": "i32",
                "uint8": "u8",
                "uint16": "u16",
                "uint32": "u32",
                "bool": "bool",
                "char": "char",
                "void": "void"
            }

            type_name = type_map.get(type_node.name, type_node.name)

            # Check if it's a built-in or user-defined type
            type_symbol = self.symbol_table.lookup_optional(type_name)
            if type_symbol:
                return TypeInfo(type_name)

            # Not found
            return None

        elif isinstance(type_node, PointerType):
            base_type = self._resolve_type(type_node.base_type)
            if base_type:
                return create_pointer_type(base_type)
            return None

        elif isinstance(type_node, ArrayType):
            elem_type = self._resolve_type(type_node.element_type)
            if elem_type:
                return create_array_type(elem_type, type_node.size)
            return None

        return None

    def _types_compatible(self, expected: TypeInfo, actual: TypeInfo) -> bool:
        """
        Check if two types are compatible for assignment/comparison.

        This is a simplified version - could be extended with:
        - Implicit conversions
        - Subtyping
        - Generic type matching
        """
        return expected == actual

    def _get_span(self, node: ASTNode) -> Optional[Span]:
        """Get source span from AST node if available."""
        if hasattr(node, 'span') and node.span:
            # Convert parser span to symbol table Span if needed
            if isinstance(node.span, Span):
                return node.span
            # If it's a different span format, convert it
            # This depends on how the parser sets spans
        return None


def check_types(ast: Program) -> List[TypeError]:
    """
    Convenience function to type check a program.

    Args:
        ast: The program AST to check

    Returns:
        List of type errors found (empty if no errors)
    """
    checker = TypeChecker()
    return checker.check(ast)
