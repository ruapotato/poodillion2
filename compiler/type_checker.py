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
    create_builtin_type, create_pointer_type, create_array_type, create_slice_type,
    create_list_type, create_any_type,
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
            elif isinstance(decl, EnumDecl):
                self._register_enum(decl)
            elif isinstance(decl, ProcDecl):
                self._register_function(decl)
            elif isinstance(decl, MethodDecl):
                self._register_method(decl)
            elif isinstance(decl, ExternDecl):
                self._register_extern(decl)

        # Second pass: check function bodies and global variables
        for decl in node.declarations:
            if isinstance(decl, ProcDecl):
                self._check_proc_decl(decl)
            elif isinstance(decl, MethodDecl):
                self._check_method_decl(decl)
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

    def _register_enum(self, node: EnumDecl) -> None:
        """Register an enum type in the symbol table."""
        try:
            span = self._get_span(node)

            # Build variant info as "fields" where name -> payload type
            # For unit variants (no payload), use a void/unit type
            variants = {}
            for variant in node.variants:
                if variant.payload_types:
                    # For now, only support single-value payloads
                    variant_type = self._resolve_type(variant.payload_types[0])
                    variants[variant.name] = variant_type
                else:
                    # Unit variant - no payload
                    variants[variant.name] = None

            # Create type symbol
            type_symbol = TypeSymbol(
                name=node.name,
                span=span,
                type_info=TypeInfo(node.name),
                fields=variants,  # Store variants as fields
                is_struct=False,
                is_enum=True
            )

            self.symbol_table.define(type_symbol)

            # Also register constructor functions for each variant
            for variant in node.variants:
                if variant.payload_types:
                    # Variant with payload: Some(int32) -> function Some(int32): Option
                    params = []
                    for i, ptype in enumerate(variant.payload_types):
                        param_type = self._resolve_type(ptype)
                        if param_type:
                            param_sym = ParamSymbol(
                                name=f"_arg{i}",
                                span=span,
                                type_info=param_type,
                                position=i
                            )
                            params.append(param_sym)

                    func_symbol = FunctionSymbol(
                        name=variant.name,
                        span=span,
                        params=params,
                        return_type=TypeInfo(node.name)
                    )
                    self.symbol_table.define(func_symbol)
                else:
                    # Unit variant: None is a constant of type Option
                    # Register as a variable/constant
                    var_symbol = VariableSymbol(
                        name=variant.name,
                        span=span,
                        type_info=TypeInfo(node.name),
                        is_mutable=False
                    )
                    self.symbol_table.define(var_symbol)

        except Exception as e:
            self.errors.append(TypeError(
                f"Error registering enum '{node.name}': {e}",
                self._get_span(node)
            ))

    def _register_function(self, node: ProcDecl) -> None:
        """Register a function declaration in the symbol table."""
        try:
            span = self._get_span(node)

            # Build parameter symbols
            params = []
            for i, param in enumerate(node.params):
                param_type = self._resolve_type(param.param_type) if param.param_type else None
                if param_type is None:
                    # Use 'any' type for untyped parameters (Python compatibility)
                    param_type = create_any_type()

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

    def _register_method(self, node: MethodDecl) -> None:
        """Register a method declaration in the symbol table."""
        try:
            span = self._get_span(node)

            # Get the type name from receiver type
            receiver_type = node.receiver_type
            if isinstance(receiver_type, PointerType):
                type_name = receiver_type.base_type.name
            else:
                type_name = receiver_type.name

            # Mangled name: TypeName_methodName
            mangled_name = f"{type_name}_{node.name}"

            # Resolve receiver type
            receiver_type_info = self._resolve_type(node.receiver_type)

            # Build parameter symbols (self is first parameter)
            params = []

            # Add self parameter
            if receiver_type_info:
                self_param = ParamSymbol(
                    name=node.receiver_name,
                    span=span,
                    type_info=receiver_type_info,
                    position=0
                )
                params.append(self_param)

            # Add explicit parameters
            for i, param in enumerate(node.params):
                param_type = self._resolve_type(param.param_type) if param.param_type else None
                if param_type is None:
                    # Use 'any' type for untyped parameters (Python compatibility)
                    param_type = create_any_type()

                param_sym = ParamSymbol(
                    name=param.name,
                    span=self._get_span(param),
                    type_info=param_type,
                    position=i + 1  # +1 because self is position 0
                )
                params.append(param_sym)

            # Resolve return type
            return_type = None
            if node.return_type:
                return_type = self._resolve_type(node.return_type)
                if return_type is None:
                    self.errors.append(TypeError(
                        f"Invalid return type for method '{node.name}'",
                        span
                    ))

            # Create function symbol with mangled name
            func_symbol = FunctionSymbol(
                name=mangled_name,
                span=span,
                params=params,
                return_type=return_type
            )

            self.symbol_table.define(func_symbol)

        except Exception as e:
            self.errors.append(TypeError(
                f"Error registering method '{node.name}': {e}",
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

    def _check_method_decl(self, node: MethodDecl) -> None:
        """Check a method declaration."""
        # Get the type name from receiver type
        receiver_type = node.receiver_type
        if isinstance(receiver_type, PointerType):
            type_name = receiver_type.base_type.name
        else:
            type_name = receiver_type.name

        mangled_name = f"{type_name}_{node.name}"

        # Get the function symbol
        func_symbol = self.symbol_table.lookup_optional(mangled_name)
        if not isinstance(func_symbol, FunctionSymbol):
            return  # Error already reported during registration

        # Enter method scope
        self.symbol_table.push_scope(f"method_{mangled_name}")
        old_function = self.current_function
        self.current_function = func_symbol

        try:
            # Add parameters to scope (including self)
            for param_sym in func_symbol.params:
                self.symbol_table.define(param_sym)

            # Check method body
            for stmt in node.body:
                self._check_statement(stmt)

            # Check that non-void methods return a value
            if func_symbol.return_type and func_symbol.return_type.name != "void":
                if not self._has_return(node.body):
                    self.errors.append(TypeError(
                        f"Method '{node.name}' must return a value of type {func_symbol.return_type}",
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
        elif isinstance(node, ForEachStmt):
            self._check_foreach(node)
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
                # Python-style: auto-declare variable on first assignment
                value_type = self._check_expr(node.value)
                if value_type:
                    var_symbol = VariableSymbol(
                        name=node.target.name,
                        span=self._get_span(node.target),
                        type_info=value_type,
                        is_mutable=True
                    )
                    try:
                        self.symbol_table.define(var_symbol)
                    except:
                        pass  # Ignore redefinition errors
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
            # For Python compatibility, if no return type specified (expected_type is None),
            # allow any return type
            if expected_type is not None and expected_type.name == "void":
                self.errors.append(TypeError(
                    "Cannot return a value from void function",
                    self._get_span(node)
                ))
                return

            value_type = self._check_expr(node.value)
            if expected_type is not None and value_type and not self._types_compatible(expected_type, value_type):
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

    def _check_foreach(self, node: ForEachStmt) -> None:
        """Check a for-each loop (for item in array)."""
        # Check iterable expression is an array
        iterable_type = self._check_expr(node.iterable)

        if iterable_type is None:
            return

        if not iterable_type.is_array:
            self.errors.append(TypeError(
                f"For-each requires array type, got {iterable_type}",
                self._get_span(node.iterable)
            ))
            return

        # Get element type from array
        element_type = iterable_type.element_type

        # Create loop variable scope
        self.symbol_table.push_scope("foreach")
        self.in_loop += 1
        try:
            # Add loop variable with element type
            var_symbol = VariableSymbol(
                name=node.var,
                span=Span(0, 0, 0),
                type_info=element_type,
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
            # String is pointer to u8 (compatible with C strings and syscalls)
            result = create_pointer_type(create_builtin_type("u8"))
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
        elif isinstance(node, MethodCallExpr):
            result = self._check_method_call_expr(node)
        elif isinstance(node, CastExpr):
            result = self._check_cast_expr(node)
        elif isinstance(node, IndexExpr):
            result = self._check_index_expr(node)
        elif isinstance(node, SliceExpr):
            result = self._check_slice_expr(node)
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
        elif isinstance(node, MatchExpr):
            result = self._check_match_expr(node)

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
            # For Python compatibility, allow undefined identifiers as 'any' type
            # This handles variables that are conditionally assigned or defined elsewhere
            return create_any_type()

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
            # Special case: string concatenation with +
            if op == BinOp.ADD:
                is_left_string = left_type.name in ("str", "any") or (left_type.is_pointer and left_type.element_type and left_type.element_type.name in ("u8", "char"))
                is_right_string = right_type.name in ("str", "any") or (right_type.is_pointer and right_type.element_type and right_type.element_type.name in ("u8", "char"))
                if is_left_string or is_right_string:
                    # String concatenation returns string
                    return create_builtin_type("str")

            # 'any' type is allowed for flexibility
            if left_type.name == "any" or right_type.name == "any":
                return create_any_type()

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
                # Ordering comparisons - allow numeric types, strings, chars, and 'any'
                is_left_orderable = is_numeric_type(left_type) or left_type.name in ("str", "char", "any")
                is_right_orderable = is_numeric_type(right_type) or right_type.name in ("str", "char", "any")

                if not is_left_orderable:
                    self.errors.append(TypeError(
                        f"Left operand of {op.value} must be numeric or string, got {left_type}",
                        self._get_span(node.left)
                    ))
                    return None

                if not is_right_orderable:
                    self.errors.append(TypeError(
                        f"Right operand of {op.value} must be numeric or string, got {right_type}",
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
            # Allow bool or any type for Python truthy/falsy semantics
            if left_type.name not in ("bool", "any"):
                self.errors.append(TypeError(
                    f"Left operand of {op.value} must be bool, got {left_type}",
                    self._get_span(node.left)
                ))
                return None

            if right_type.name not in ("bool", "any"):
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
            # Allow bool or any type for logical not (Python truthy/falsy semantics)
            if expr_type.name not in ("bool", "any"):
                self.errors.append(TypeError(
                    f"Logical not requires bool type, got {expr_type}",
                    self._get_span(node)
                ))
                return None
            return create_builtin_type("bool")

        return None

    def _check_call_expr(self, node: CallExpr) -> Optional[TypeInfo]:
        """Check function call and return result type."""
        # Check for built-in functions
        if node.func == "len" and len(node.args) == 1:
            arg_type = self._check_expr(node.args[0])
            if arg_type:
                # Allow len() on slices, arrays, and strings
                if arg_type.is_slice or arg_type.is_array or arg_type.name in ("str", "any"):
                    return create_builtin_type("i32")
                else:
                    self.errors.append(TypeError(
                        f"len() expects slice, array, or string, got {arg_type}",
                        self._get_span(node)
                    ))
            return create_builtin_type("i32")

        # Python builtin functions
        if node.func == "chr":
            # chr(i) -> str (single character)
            return create_builtin_type("char")
        if node.func == "ord":
            # ord(c) -> int
            return create_builtin_type("i32")
        if node.func == "str":
            # str(x) -> str
            return create_builtin_type("str")
        if node.func == "int":
            # int(x) -> int
            return create_builtin_type("i32")
        if node.func == "bool":
            # bool(x) -> bool
            return create_builtin_type("bool")
        if node.func == "float":
            # float(x) -> float
            return create_builtin_type("f32")
        if node.func == "range":
            # range() -> iterable (treat as any for now)
            return create_any_type()
        if node.func == "enumerate":
            # enumerate() -> iterable
            return create_any_type()
        if node.func == "zip":
            # zip() -> iterable
            return create_any_type()
        if node.func == "list":
            # list() -> list
            return create_any_type()
        if node.func == "dict":
            # dict() -> dict
            return create_any_type()
        if node.func == "set":
            # set() -> set
            return create_any_type()
        if node.func == "tuple":
            # tuple() -> tuple
            return create_any_type()
        if node.func == "print":
            # print() -> None
            return create_builtin_type("void")
        if node.func == "open":
            # open() -> file object
            return create_any_type()
        if node.func == "isinstance":
            return create_builtin_type("bool")
        if node.func == "hasattr":
            return create_builtin_type("bool")
        if node.func == "getattr":
            return create_any_type()
        if node.func == "setattr":
            return create_builtin_type("void")
        if node.func == "type":
            return create_any_type()
        if node.func == "id":
            return create_builtin_type("i32")
        if node.func == "hex":
            return create_builtin_type("str")
        if node.func == "bin":
            return create_builtin_type("str")
        if node.func == "oct":
            return create_builtin_type("str")
        if node.func == "abs":
            return create_builtin_type("i32")
        if node.func == "min":
            return create_any_type()
        if node.func == "max":
            return create_any_type()
        if node.func == "sum":
            return create_builtin_type("i32")
        if node.func == "sorted":
            return create_any_type()
        if node.func == "reversed":
            return create_any_type()
        if node.func == "map":
            return create_any_type()
        if node.func == "filter":
            return create_any_type()
        if node.func == "any":
            return create_builtin_type("bool")
        if node.func == "all":
            return create_builtin_type("bool")
        if node.func == "repr":
            return create_builtin_type("str")
        if node.func == "format":
            return create_builtin_type("str")

        # Look up function
        func_symbol = self.symbol_table.lookup_optional(node.func)
        if func_symbol is None:
            self.errors.append(TypeError(
                f"Undefined function '{node.func}'",
                self._get_span(node)
            ))
            return None

        # Handle TypeSymbol as constructor (for @dataclass classes)
        if isinstance(func_symbol, TypeSymbol):
            if func_symbol.is_struct:
                # This is a dataclass/struct constructor call
                # Return the type being constructed
                return TypeInfo(func_symbol.name)
            else:
                self.errors.append(TypeError(
                    f"'{node.func}' is not callable",
                    self._get_span(node)
                ))
                return None

        if not isinstance(func_symbol, FunctionSymbol):
            self.errors.append(TypeError(
                f"'{node.func}' is not a function",
                self._get_span(node)
            ))
            return None

        # Check argument count (allow fewer for Python functions with default parameters)
        if len(node.args) > len(func_symbol.params):
            self.errors.append(TypeError(
                f"Function '{node.func}' expects at most {len(func_symbol.params)} arguments, "
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

    def _check_method_call_expr(self, node: MethodCallExpr) -> Optional[TypeInfo]:
        """Check method call and return result type."""
        # Get object type
        obj_type = self._check_expr(node.object)
        if obj_type is None:
            return None

        # Get the type name for method lookup
        type_name = obj_type.name
        if obj_type.is_pointer and obj_type.element_type:
            type_name = obj_type.element_type.name

        # Handle built-in list methods
        if obj_type.is_array or type_name.startswith("List["):
            method = node.method_name
            if method == "append":
                # append() returns None/void
                return create_builtin_type("void")
            elif method == "pop":
                # pop() returns element type
                if obj_type.element_type:
                    return obj_type.element_type
                return create_any_type()
            elif method == "insert":
                return create_builtin_type("void")
            elif method == "remove":
                return create_builtin_type("void")
            elif method == "clear":
                return create_builtin_type("void")
            elif method == "extend":
                return create_builtin_type("void")
            elif method == "copy":
                return obj_type
            elif method == "index":
                return create_builtin_type("i32")
            elif method == "count":
                return create_builtin_type("i32")
            elif method == "sort":
                return create_builtin_type("void")
            elif method == "reverse":
                return create_builtin_type("void")

        # Handle built-in string methods
        if type_name in ("str", "any") or (obj_type.is_pointer and obj_type.element_type and obj_type.element_type.name in ("u8", "char")):
            method = node.method_name
            if method in ("upper", "lower", "strip", "lstrip", "rstrip", "capitalize", "title"):
                return create_builtin_type("str")
            elif method in ("split", "splitlines"):
                return create_any_type()  # Returns list
            elif method in ("join",):
                return create_builtin_type("str")
            elif method in ("find", "rfind", "index", "rindex", "count"):
                return create_builtin_type("i32")
            elif method in ("startswith", "endswith", "isdigit", "isalpha", "isalnum", "isspace"):
                return create_builtin_type("bool")
            elif method in ("replace", "format"):
                return create_builtin_type("str")
            elif method == "encode":
                return create_any_type()  # Returns bytes

        # Handle dict methods
        if type_name == "any" or type_name.startswith("Dict["):
            method = node.method_name
            if method == "get":
                return create_any_type()
            elif method == "keys":
                return create_any_type()
            elif method == "values":
                return create_any_type()
            elif method == "items":
                return create_any_type()
            elif method == "pop":
                return create_any_type()
            elif method == "update":
                return create_builtin_type("void")
            elif method == "clear":
                return create_builtin_type("void")

        # Build mangled name
        mangled_name = f"{type_name}_{node.method_name}"

        # Look up method by mangled name
        func_symbol = self.symbol_table.lookup_optional(mangled_name)
        if func_symbol is None:
            self.errors.append(TypeError(
                f"No method '{node.method_name}' for type '{type_name}'",
                self._get_span(node)
            ))
            return None

        if not isinstance(func_symbol, FunctionSymbol):
            self.errors.append(TypeError(
                f"'{mangled_name}' is not a method",
                self._get_span(node)
            ))
            return None

        # Check argument count (excluding self)
        # Allow fewer arguments for Python methods with default parameters
        expected_args = len(func_symbol.params) - 1  # -1 for self
        if len(node.args) > expected_args:
            self.errors.append(TypeError(
                f"Method '{node.method_name}' expects at most {expected_args} arguments, "
                f"got {len(node.args)}",
                self._get_span(node)
            ))
            return func_symbol.return_type

        # Check argument types (skip self parameter at position 0)
        for i, arg in enumerate(node.args):
            param = func_symbol.params[i + 1]  # +1 to skip self
            arg_type = self._check_expr(arg)
            if arg_type and not self._types_compatible(param.type_info, arg_type):
                self.errors.append(TypeError(
                    f"Argument {i+1} to '{node.method_name}': expected {param.type_info}, got {arg_type}",
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

        # Check index is integer (allow 'any' or 'str' for dict-like access)
        if index_type and not is_integer_type(index_type) and index_type.name not in ("any", "str"):
            # Only require integer index for arrays, not for 'any' type (which could be a dict)
            if array_type.name != "any":
                self.errors.append(TypeError(
                    f"Array index must be integer, got {index_type}",
                    self._get_span(node.index)
                ))

        # Check array_type is indexable (array, pointer, slice, or string)
        if array_type.is_array:
            return array_type.element_type
        elif array_type.is_pointer:
            return array_type.element_type
        elif array_type.is_slice:
            return array_type.element_type
        elif array_type.name in ("str", "any"):
            # String indexing returns a character
            return create_builtin_type("char")
        else:
            self.errors.append(TypeError(
                f"Cannot index type {array_type}",
                self._get_span(node.array)
            ))
            return None

    def _check_slice_expr(self, node: SliceExpr) -> Optional[TypeInfo]:
        """Check slice expression: arr[start..end]"""
        array_type = self._check_expr(node.array)
        start_type = self._check_expr(node.start)
        end_type = self._check_expr(node.end)

        if not array_type:
            return None

        # Check start and end are integers
        if start_type and not is_integer_type(start_type):
            self.errors.append(TypeError(
                f"Slice start must be integer, got {start_type}",
                self._get_span(node.start)
            ))

        if end_type and not is_integer_type(end_type):
            self.errors.append(TypeError(
                f"Slice end must be integer, got {end_type}",
                self._get_span(node.end)
            ))

        # Check array_type is sliceable (array, pointer, or slice)
        if array_type.is_array:
            return create_slice_type(array_type.element_type)
        elif array_type.is_pointer:
            return create_slice_type(array_type.element_type)
        elif array_type.is_slice:
            return create_slice_type(array_type.element_type)
        else:
            self.errors.append(TypeError(
                f"Cannot slice type {array_type}",
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
        """Check struct field access (works for both direct struct and ptr-to-struct)."""
        obj_type = self._check_expr(node.object)
        if not obj_type:
            return None

        # Handle 'any' type - allow any field access
        if obj_type.name == "any":
            return create_any_type()

        # Handle pointer-to-struct: extract base type
        struct_type_name = obj_type.name
        if obj_type.is_pointer and obj_type.element_type:
            struct_type_name = obj_type.element_type.name

        # Look up the struct type
        type_symbol = self.symbol_table.lookup_optional(struct_type_name)

        # Check if it's an enum and accessing .name property
        if isinstance(type_symbol, TypeSymbol) and type_symbol.is_enum:
            if node.field_name == "name":
                # Enum .name property returns the variant name as a string
                return create_builtin_type("str")
            elif node.field_name == "value":
                # Enum .value property returns the value
                return create_builtin_type("i32")

        if not isinstance(type_symbol, TypeSymbol):
            self.errors.append(TypeError(
                f"Type {struct_type_name} is not a struct",
                self._get_span(node.object)
            ))
            return None

        # Check field exists
        if not type_symbol.has_field(node.field_name):
            self.errors.append(TypeError(
                f"Type {struct_type_name} has no field '{node.field_name}'",
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
            # Empty array literal - use 'any' element type for flexibility
            return create_array_type(create_any_type(), 0)

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

    def _check_match_expr(self, node: MatchExpr) -> Optional[TypeInfo]:
        """Check match expression and return result type."""
        # Check the expression being matched
        expr_type = self._check_expr(node.expr)
        if not expr_type:
            return None

        # Look up the enum type
        type_symbol = self.symbol_table.lookup_optional(expr_type.name)
        if not type_symbol or not isinstance(type_symbol, TypeSymbol) or not type_symbol.is_enum:
            self.errors.append(TypeError(
                f"Match expression requires enum type, got {expr_type}",
                self._get_span(node.expr)
            ))
            return None

        # Get the enum variants
        variants = type_symbol.fields  # variant name -> payload type

        # Check each arm
        arm_types = []
        matched_variants = set()

        for arm in node.arms:
            variant_name = arm.pattern.variant_name

            # Check variant exists
            if variant_name not in variants:
                self.errors.append(TypeError(
                    f"Unknown variant '{variant_name}' for enum {expr_type.name}",
                    self._get_span(arm)
                ))
                continue

            # Track which variants we've matched
            matched_variants.add(variant_name)

            # Check arm body with bindings in scope
            self.symbol_table.push_scope(f"match_arm_{variant_name}")
            try:
                # If variant has payload and pattern has bindings, add them
                payload_type = variants[variant_name]
                if payload_type and arm.pattern.bindings:
                    for i, binding in enumerate(arm.pattern.bindings):
                        var_symbol = VariableSymbol(
                            name=binding,
                            span=self._get_span(arm),
                            type_info=payload_type,
                            is_mutable=False
                        )
                        self.symbol_table.define(var_symbol)

                # Check arm body
                for stmt in arm.body:
                    self._check_statement(stmt)

                # Try to determine return type from return statements
                for stmt in arm.body:
                    if isinstance(stmt, ReturnStmt) and stmt.value:
                        arm_type = self._check_expr(stmt.value)
                        if arm_type:
                            arm_types.append(arm_type)
                            break

            finally:
                self.symbol_table.pop_scope()

        # Check exhaustiveness
        missing_variants = set(variants.keys()) - matched_variants
        if missing_variants:
            self.errors.append(TypeError(
                f"Non-exhaustive match: missing variants {missing_variants}",
                self._get_span(node)
            ))

        # Return the common type of all arms (simplified - just use first)
        if arm_types:
            return arm_types[0]
        return create_builtin_type("void")

    def _resolve_type(self, type_node: Type) -> Optional[TypeInfo]:
        """
        Resolve a type annotation to TypeInfo.

        Handles primitive types, pointers, arrays, lists, dicts, and 'any'.
        """
        if isinstance(type_node, ListType):
            elem_type = self._resolve_type(type_node.element_type)
            if elem_type:
                return create_list_type(elem_type)
            return create_list_type(create_any_type())  # Default to List[any]

        elif isinstance(type_node, DictType):
            # Dicts are treated as 'any' for now
            return create_any_type()

        elif isinstance(type_node, Type):
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
                "void": "void",
                "str": "str",
                "any": "any"
            }

            type_name = type_map.get(type_node.name, type_node.name)

            # Handle 'any' type specially
            if type_name == "any":
                return create_any_type()

            # Check if it's a built-in or user-defined type
            type_symbol = self.symbol_table.lookup_optional(type_name)
            if type_symbol:
                return TypeInfo(type_name)

            # For unknown types, treat as 'any' to allow flexibility
            return create_any_type()

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

        elif isinstance(type_node, SliceType):
            elem_type = self._resolve_type(type_node.element_type)
            if elem_type:
                return create_slice_type(elem_type)
            return None

        elif isinstance(type_node, GenericInstanceType):
            # Handle generic type instantiations like Optional[str], List[int]
            base = type_node.base_type
            if base == "Optional":
                # Optional[T] -> treat as 'any' for flexibility (could be T or None)
                if type_node.type_args:
                    inner = self._resolve_type(type_node.type_args[0])
                    # For type checking, treat Optional[T] as 'any' to allow None
                    return create_any_type()
                return create_any_type()
            elif base == "List":
                if type_node.type_args:
                    elem_type = self._resolve_type(type_node.type_args[0])
                    return create_list_type(elem_type or create_any_type())
                return create_list_type(create_any_type())
            elif base == "Dict":
                # Treat Dict as 'any' for flexibility
                return create_any_type()
            else:
                # Unknown generic type - treat as 'any'
                return create_any_type()

        return None

    def _types_compatible(self, expected: TypeInfo, actual: TypeInfo) -> bool:
        """
        Check if two types are compatible for assignment/comparison.

        Supports implicit integer conversions (C-like behavior):
        - Any integer type can be assigned to any other integer type
        - Signedness and size differences are allowed (may truncate)
        """
        if expected == actual:
            return True

        # Allow implicit conversions between integer types
        if is_integer_type(expected) and is_integer_type(actual):
            return True

        # 'any' type is compatible with everything
        if expected.name == "any" or actual.name == "any":
            return True

        # char is compatible with string/pointer types (for comparisons)
        char_types = {"char", "u8", "i8"}
        string_types = {"str"}
        if expected.name in char_types and actual.name in string_types:
            return True
        if actual.name in char_types and expected.name in string_types:
            return True
        if expected.name in char_types and actual.is_pointer:
            return True
        if actual.name in char_types and expected.is_pointer:
            return True

        # Allow str comparison with integers (Python comparison semantics)
        if (expected.name == "str" and is_integer_type(actual)) or \
           (actual.name == "str" and is_integer_type(expected)):
            return True

        # str is compatible with *u8/*char (string types)
        if expected.name == "str" and actual.is_pointer:
            return True
        if actual.name == "str" and expected.is_pointer:
            return True

        # Same pointer types are compatible
        if expected.is_pointer and actual.is_pointer:
            if expected.element_type and actual.element_type:
                return self._types_compatible(expected.element_type, actual.element_type)
            return True

        # Array types with 'any' element type are compatible with list types
        # (for empty array literal [] assigned to List[T])
        if expected.is_array and actual.is_array:
            if actual.element_type and actual.element_type.name == "any":
                return True  # Empty array [] is compatible with any list type
            if expected.element_type and actual.element_type:
                return self._types_compatible(expected.element_type, actual.element_type)

        return False

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
