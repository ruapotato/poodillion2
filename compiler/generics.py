#!/usr/bin/env python3
"""
Generics and Monomorphization for Brainhair Compiler

This module handles generic types and functions through monomorphization:
- Generic functions are instantiated at each unique call site
- Generic types create concrete versions for each type argument
- No runtime cost - everything resolved at compile time

Example:
    proc swap[T](a: ptr T, b: ptr T) =
        var tmp: T = a[0]
        a[0] = b[0]
        b[0] = tmp

    # Called as:
    swap[int32](addr(x), addr(y))  # Generates swap$int32
    swap[Point](addr(p1), addr(p2))  # Generates swap$Point
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Any
from copy import deepcopy

from ast_nodes import *

# Polyglot: get reference to Python's str type using type("") trick
try:
    _str_type = type("")
    _to_str = _str_type
except:
    _str_type = None
    def _to_str(x):
        return ""


@dataclass
class GenericParam:
    """A generic type parameter."""
    name: str
    constraints: List[str] = field(default_factory=list)


@dataclass
class GenericFunction:
    """A generic function awaiting monomorphization."""
    name: str
    type_params: List[GenericParam]
    proc_decl: 'ProcDecl'
    instantiations: Dict = field(default_factory=dict)


@dataclass
class GenericStruct:
    """A generic struct type awaiting monomorphization."""
    name: str
    type_params: List[GenericParam]
    struct_decl: 'StructDecl'
    instantiations: Dict = field(default_factory=dict)


def mangle_name(base_name: str, type_args: List[str]) -> str:
    """
    Mangle a generic name with type arguments.

    Examples:
        swap + [int32] -> swap$int32
        Vec + [Point] -> Vec$Point
        HashMap + [string, int32] -> HashMap$string_int32
    """
    if not type_args:
        return base_name
    args_str = "_".join(t.replace(' ', '_').replace('*', 'ptr_') for t in type_args)
    return f"{base_name}${args_str}"


def demangle_name(mangled: str) -> Tuple[str, List[str]]:
    """
    Demangle a name back to base name and type arguments.

    Examples:
        swap$int32 -> (swap, [int32])
        Vec$Point -> (Vec, [Point])
    """
    if '$' not in mangled:
        return mangled, []
    base, args_str = mangled.split('$', 1)
    args = args_str.split('_')
    return base, args


class GenericCollector:
    """
    First pass: collect generic function and type definitions.
    """

    def __init__(self):
        self.generic_functions: Dict[str, GenericFunction] = {}
        self.generic_structs: Dict[str, GenericStruct] = {}

    def collect(self, program: Program) -> None:
        """Collect all generic definitions from program."""
        for decl in program.declarations:
            if isinstance(decl, ProcDecl):
                if hasattr(decl, 'type_params') and decl.type_params:
                    self._collect_generic_proc(decl)
            elif isinstance(decl, StructDecl):
                if hasattr(decl, 'type_params') and decl.type_params:
                    self._collect_generic_struct(decl)

    def _collect_generic_proc(self, proc: ProcDecl) -> None:
        """Collect a generic procedure."""
        params = []
        for p in proc.type_params:
            param_name = p.name if hasattr(p, 'name') else _to_str(p)
            params.append(GenericParam(name=param_name))
        self.generic_functions[proc.name] = GenericFunction(
            name=proc.name,
            type_params=params,
            proc_decl=proc
        )

    def _collect_generic_struct(self, struct: StructDecl) -> None:
        """Collect a generic struct."""
        params = []
        for p in struct.type_params:
            param_name = p.name if hasattr(p, 'name') else _to_str(p)
            params.append(GenericParam(name=param_name))
        self.generic_structs[struct.name] = GenericStruct(
            name=struct.name,
            type_params=params,
            struct_decl=struct
        )


class Monomorphizer:
    """
    Monomorphization pass: instantiate generic functions and types.

    This creates concrete versions of generic code by substituting
    actual types for type parameters.
    """

    def __init__(self, collector: GenericCollector):
        self.collector = collector
        self.instantiated_procs: List[ProcDecl] = []
        self.instantiated_structs: List[StructDecl] = []
        self.pending_instantiations: List[Tuple[str, List[str]]] = []

    def monomorphize(self, program: Program) -> Program:
        """
        Monomorphize the entire program.

        Returns a new program with generic definitions replaced by
        their concrete instantiations.
        """
        # First collect all generic definitions
        self.collector.collect(program)

        # Find all instantiation sites
        self._find_instantiation_sites(program)

        # Process pending instantiations
        while self.pending_instantiations:
            name, type_args = self.pending_instantiations.pop(0)
            self._instantiate(name, type_args)

        # Build new program with monomorphized code
        new_decls = []

        # Add non-generic declarations
        for decl in program.declarations:
            if isinstance(decl, ProcDecl):
                if not hasattr(decl, 'type_params') or not decl.type_params:
                    # Rewrite any generic calls in non-generic functions
                    new_decl = self._rewrite_calls(decl)
                    new_decls.append(new_decl)
            elif isinstance(decl, StructDecl):
                if not hasattr(decl, 'type_params') or not decl.type_params:
                    new_decls.append(decl)
            else:
                new_decls.append(decl)

        # Add instantiated declarations
        new_decls.extend(self.instantiated_structs)
        new_decls.extend(self.instantiated_procs)

        return Program(declarations=new_decls)

    def _find_instantiation_sites(self, program: Program) -> None:
        """Find all places where generic functions/types are used."""
        for decl in program.declarations:
            if isinstance(decl, ProcDecl):
                self._find_in_proc(decl)

    def _find_in_proc(self, proc: ProcDecl) -> None:
        """Find generic usage in a procedure."""
        for stmt in proc.body:
            self._find_in_stmt(stmt)

    def _find_in_stmt(self, stmt: ASTNode) -> None:
        """Find generic usage in a statement."""
        if isinstance(stmt, VarDecl):
            self._find_in_type(stmt.var_type)
            if stmt.value:
                self._find_in_expr(stmt.value)
        elif isinstance(stmt, Assignment):
            self._find_in_expr(stmt.value)
        elif isinstance(stmt, ReturnStmt):
            if stmt.value:
                self._find_in_expr(stmt.value)
        elif isinstance(stmt, IfStmt):
            self._find_in_expr(stmt.condition)
            for s in stmt.then_block:
                self._find_in_stmt(s)
            if stmt.else_block:
                for s in stmt.else_block:
                    self._find_in_stmt(s)
        elif isinstance(stmt, WhileStmt):
            self._find_in_expr(stmt.condition)
            for s in stmt.body:
                self._find_in_stmt(s)
        elif isinstance(stmt, ForStmt):
            self._find_in_expr(stmt.start)
            self._find_in_expr(stmt.end)
            for s in stmt.body:
                self._find_in_stmt(s)
        elif isinstance(stmt, ExprStmt):
            self._find_in_expr(stmt.expr)

    def _find_in_expr(self, expr: ASTNode) -> None:
        """Find generic usage in an expression."""
        if isinstance(expr, CallExpr):
            # Check if this is a generic call
            if hasattr(expr, 'type_args') and expr.type_args:
                type_arg_names = []
                for t in expr.type_args:
                    type_arg_names.append(self._type_to_string(t))
                already_pending = False
                for p in self.pending_instantiations:
                    if p[0] == expr.func and tuple(p[1]) == tuple(type_arg_names):
                        already_pending = True
                        break
                if not already_pending:
                    self.pending_instantiations.append((expr.func, type_arg_names))
            for arg in expr.args:
                self._find_in_expr(arg)
        elif isinstance(expr, BinaryExpr):
            self._find_in_expr(expr.left)
            self._find_in_expr(expr.right)
        elif isinstance(expr, UnaryExpr):
            self._find_in_expr(expr.expr)
        elif isinstance(expr, CastExpr):
            self._find_in_type(expr.target_type)
            self._find_in_expr(expr.expr)
        elif isinstance(expr, IndexExpr):
            self._find_in_expr(expr.base)
            self._find_in_expr(expr.index)
        elif isinstance(expr, AddrOfExpr):
            self._find_in_expr(expr.expr)
        elif isinstance(expr, DerefExpr):
            self._find_in_expr(expr.expr)

    def _find_in_type(self, ty) -> None:
        """Find generic usage in a type."""
        if isinstance(ty, GenericInstanceType):
            type_arg_names = []
            for t in ty.type_args:
                type_arg_names.append(self._type_to_string(t))
            already_pending = False
            for p in self.pending_instantiations:
                if p[0] == ty.base_type and tuple(p[1]) == tuple(type_arg_names):
                    already_pending = True
                    break
            if not already_pending:
                self.pending_instantiations.append((ty.base_type, type_arg_names))
        elif isinstance(ty, PointerType):
            self._find_in_type(ty.base_type)
        elif isinstance(ty, ArrayType):
            self._find_in_type(ty.element_type)

    def _type_to_string(self, ty) -> str:
        """Convert a type to string representation."""
        if isinstance(ty, Type):
            return ty.name
        elif isinstance(ty, PointerType):
            return f"ptr_{self._type_to_string(ty.base_type)}"
        elif isinstance(ty, ArrayType):
            return f"array_{ty.size}_{self._type_to_string(ty.element_type)}"
        elif _str_type is not None and isinstance(ty, _str_type):
            return ty
        return _to_str(ty)

    def _instantiate(self, name: str, type_args: List[str]) -> None:
        """Instantiate a generic function or struct."""
        type_args_tuple = tuple(type_args)

        # Check if it's a generic function
        if name in self.collector.generic_functions:
            gf = self.collector.generic_functions[name]
            if type_args_tuple not in gf.instantiations:
                mangled = mangle_name(name, type_args)
                new_proc = self._instantiate_proc(gf, type_args, mangled)
                gf.instantiations[type_args_tuple] = new_proc
                self.instantiated_procs.append(new_proc)

        # Check if it's a generic struct
        elif name in self.collector.generic_structs:
            gs = self.collector.generic_structs[name]
            if type_args_tuple not in gs.instantiations:
                mangled = mangle_name(name, type_args)
                new_struct = self._instantiate_struct(gs, type_args, mangled)
                gs.instantiations[type_args_tuple] = new_struct
                self.instantiated_structs.append(new_struct)

    def _instantiate_proc(self, gf: GenericFunction, type_args: List[str],
                          mangled_name: str) -> ProcDecl:
        """Create a concrete instantiation of a generic procedure."""
        # Build substitution map
        subst = {}
        for i, param in enumerate(gf.type_params):
            if i < len(type_args):
                subst[param.name] = type_args[i]

        # Deep copy and substitute
        new_proc = deepcopy(gf.proc_decl)
        new_proc.name = mangled_name
        new_proc.type_params = []  # No longer generic

        # Substitute in parameters
        new_proc.params = [self._subst_param(p, subst) for p in new_proc.params]

        # Substitute in return type
        new_proc.return_type = self._subst_type(new_proc.return_type, subst)

        # Substitute in body
        new_proc.body = [self._subst_stmt(s, subst) for s in new_proc.body]

        return new_proc

    def _instantiate_struct(self, gs: GenericStruct, type_args: List[str],
                            mangled_name: str) -> StructDecl:
        """Create a concrete instantiation of a generic struct."""
        # Build substitution map
        subst = {}
        for i, param in enumerate(gs.type_params):
            if i < len(type_args):
                subst[param.name] = type_args[i]

        # Deep copy and substitute
        new_struct = deepcopy(gs.struct_decl)
        new_struct.name = mangled_name
        new_struct.type_params = []  # No longer generic

        # Substitute in fields
        for field in new_struct.fields:
            field.field_type = self._subst_type(field.field_type, subst)

        return new_struct

    def _subst_param(self, param, subst: Dict[str, str]):
        """Substitute types in a parameter."""
        new_param = deepcopy(param)
        new_param.param_type = self._subst_type(param.param_type, subst)
        return new_param

    def _subst_type(self, ty, subst: Dict[str, str]):
        """Substitute type parameters with concrete types."""
        if ty is None:
            return None

        if isinstance(ty, Type):
            if ty.name in subst:
                return Type(name=subst[ty.name])
            return ty

        if isinstance(ty, PointerType):
            new_base = self._subst_type(ty.base_type, subst)
            return PointerType(base_type=new_base)

        if isinstance(ty, ArrayType):
            new_elem = self._subst_type(ty.element_type, subst)
            return ArrayType(size=ty.size, element_type=new_elem)

        if isinstance(ty, GenericInstanceType):
            new_args = [self._subst_type(t, subst) for t in ty.type_args]
            return GenericInstanceType(base_type=ty.base_type, type_args=new_args)

        return ty

    def _subst_stmt(self, stmt: ASTNode, subst: Dict[str, str]) -> ASTNode:
        """Substitute types in a statement."""
        if isinstance(stmt, VarDecl):
            new_stmt = deepcopy(stmt)
            new_stmt.var_type = self._subst_type(stmt.var_type, subst)
            if stmt.value:
                new_stmt.value = self._subst_expr(stmt.value, subst)
            return new_stmt

        elif isinstance(stmt, Assignment):
            new_stmt = deepcopy(stmt)
            new_stmt.value = self._subst_expr(stmt.value, subst)
            return new_stmt

        elif isinstance(stmt, ReturnStmt):
            new_stmt = deepcopy(stmt)
            if stmt.value:
                new_stmt.value = self._subst_expr(stmt.value, subst)
            return new_stmt

        elif isinstance(stmt, IfStmt):
            new_stmt = deepcopy(stmt)
            new_stmt.condition = self._subst_expr(stmt.condition, subst)
            new_stmt.then_block = [self._subst_stmt(s, subst) for s in stmt.then_block]
            if stmt.else_block:
                new_stmt.else_block = [self._subst_stmt(s, subst) for s in stmt.else_block]
            return new_stmt

        elif isinstance(stmt, WhileStmt):
            new_stmt = deepcopy(stmt)
            new_stmt.condition = self._subst_expr(stmt.condition, subst)
            new_stmt.body = [self._subst_stmt(s, subst) for s in stmt.body]
            return new_stmt

        elif isinstance(stmt, ForStmt):
            new_stmt = deepcopy(stmt)
            new_stmt.start = self._subst_expr(stmt.start, subst)
            new_stmt.end = self._subst_expr(stmt.end, subst)
            new_stmt.body = [self._subst_stmt(s, subst) for s in stmt.body]
            return new_stmt

        elif isinstance(stmt, ExprStmt):
            new_stmt = deepcopy(stmt)
            new_stmt.expr = self._subst_expr(stmt.expr, subst)
            return new_stmt

        return stmt

    def _subst_expr(self, expr: ASTNode, subst: Dict[str, str]) -> ASTNode:
        """Substitute types in an expression."""
        if isinstance(expr, CastExpr):
            new_expr = deepcopy(expr)
            new_expr.target_type = self._subst_type(expr.target_type, subst)
            new_expr.expr = self._subst_expr(expr.expr, subst)
            return new_expr

        elif isinstance(expr, CallExpr):
            new_expr = deepcopy(expr)
            new_expr.args = [self._subst_expr(a, subst) for a in expr.args]
            # If this is a generic call, rewrite to mangled name
            if hasattr(expr, 'type_args') and expr.type_args:
                type_arg_names = [self._type_to_string(self._subst_type(t, subst))
                                  for t in expr.type_args]
                new_expr.func = mangle_name(expr.func, type_arg_names)
                new_expr.type_args = []  # Clear type args
            return new_expr

        elif isinstance(expr, BinaryExpr):
            new_expr = deepcopy(expr)
            new_expr.left = self._subst_expr(expr.left, subst)
            new_expr.right = self._subst_expr(expr.right, subst)
            return new_expr

        elif isinstance(expr, UnaryExpr):
            new_expr = deepcopy(expr)
            new_expr.expr = self._subst_expr(expr.expr, subst)
            return new_expr

        elif isinstance(expr, IndexExpr):
            new_expr = deepcopy(expr)
            new_expr.base = self._subst_expr(expr.base, subst)
            new_expr.index = self._subst_expr(expr.index, subst)
            return new_expr

        elif isinstance(expr, AddrOfExpr):
            new_expr = deepcopy(expr)
            new_expr.expr = self._subst_expr(expr.expr, subst)
            return new_expr

        elif isinstance(expr, DerefExpr):
            new_expr = deepcopy(expr)
            new_expr.expr = self._subst_expr(expr.expr, subst)
            return new_expr

        return expr

    def _rewrite_calls(self, proc: ProcDecl) -> ProcDecl:
        """Rewrite generic calls in a non-generic procedure to use mangled names."""
        new_proc = deepcopy(proc)
        new_proc.body = [self._rewrite_stmt(s) for s in proc.body]
        return new_proc

    def _rewrite_stmt(self, stmt: ASTNode) -> ASTNode:
        """Rewrite generic calls in a statement."""
        if isinstance(stmt, VarDecl):
            new_stmt = deepcopy(stmt)
            if stmt.value:
                new_stmt.value = self._rewrite_expr(stmt.value)
            return new_stmt

        elif isinstance(stmt, Assignment):
            new_stmt = deepcopy(stmt)
            new_stmt.value = self._rewrite_expr(stmt.value)
            return new_stmt

        elif isinstance(stmt, ReturnStmt):
            new_stmt = deepcopy(stmt)
            if stmt.value:
                new_stmt.value = self._rewrite_expr(stmt.value)
            return new_stmt

        elif isinstance(stmt, IfStmt):
            new_stmt = deepcopy(stmt)
            new_stmt.condition = self._rewrite_expr(stmt.condition)
            new_stmt.then_block = [self._rewrite_stmt(s) for s in stmt.then_block]
            if stmt.else_block:
                new_stmt.else_block = [self._rewrite_stmt(s) for s in stmt.else_block]
            return new_stmt

        elif isinstance(stmt, WhileStmt):
            new_stmt = deepcopy(stmt)
            new_stmt.condition = self._rewrite_expr(stmt.condition)
            new_stmt.body = [self._rewrite_stmt(s) for s in stmt.body]
            return new_stmt

        elif isinstance(stmt, ForStmt):
            new_stmt = deepcopy(stmt)
            new_stmt.start = self._rewrite_expr(stmt.start)
            new_stmt.end = self._rewrite_expr(stmt.end)
            new_stmt.body = [self._rewrite_stmt(s) for s in stmt.body]
            return new_stmt

        elif isinstance(stmt, ExprStmt):
            new_stmt = deepcopy(stmt)
            new_stmt.expr = self._rewrite_expr(stmt.expr)
            return new_stmt

        return stmt

    def _rewrite_expr(self, expr: ASTNode) -> ASTNode:
        """Rewrite generic calls in an expression."""
        if isinstance(expr, CallExpr):
            new_expr = deepcopy(expr)
            new_expr.args = [self._rewrite_expr(a) for a in expr.args]
            # If this is a generic call, rewrite to mangled name
            if hasattr(expr, 'type_args') and expr.type_args:
                type_arg_names = [self._type_to_string(t) for t in expr.type_args]
                new_expr.func = mangle_name(expr.func, type_arg_names)
                new_expr.type_args = []
            return new_expr

        elif isinstance(expr, BinaryExpr):
            new_expr = deepcopy(expr)
            new_expr.left = self._rewrite_expr(expr.left)
            new_expr.right = self._rewrite_expr(expr.right)
            return new_expr

        elif isinstance(expr, UnaryExpr):
            new_expr = deepcopy(expr)
            new_expr.expr = self._rewrite_expr(expr.expr)
            return new_expr

        elif isinstance(expr, IndexExpr):
            new_expr = deepcopy(expr)
            new_expr.base = self._rewrite_expr(expr.base)
            new_expr.index = self._rewrite_expr(expr.index)
            return new_expr

        elif isinstance(expr, AddrOfExpr):
            new_expr = deepcopy(expr)
            new_expr.expr = self._rewrite_expr(expr.expr)
            return new_expr

        elif isinstance(expr, DerefExpr):
            new_expr = deepcopy(expr)
            new_expr.expr = self._rewrite_expr(expr.expr)
            return new_expr

        elif isinstance(expr, CastExpr):
            new_expr = deepcopy(expr)
            new_expr.expr = self._rewrite_expr(expr.expr)
            return new_expr

        return expr


def monomorphize(program: Program) -> Program:
    """
    Convenience function to monomorphize a program.

    Args:
        program: The AST program node

    Returns:
        New program with generic code replaced by concrete instantiations
    """
    collector = GenericCollector()
    mono = Monomorphizer(collector)
    return mono.monomorphize(program)


# ============================================================================
# Test
# ============================================================================

if __name__ == "__main__":
    # Test name mangling
    print("=== Name Mangling ===")
    print(f"swap + [int32] -> {mangle_name('swap', ['int32'])}")
    print(f"Vec + [Point] -> {mangle_name('Vec', ['Point'])}")
    print(f"HashMap + [string, int32] -> {mangle_name('HashMap', ['string', 'int32'])}")

    # Test demangling
    print("\n=== Demangling ===")
    print(f"swap$int32 -> {demangle_name('swap$int32')}")
    print(f"Vec$Point -> {demangle_name('Vec$Point')}")
    print(f"HashMap$string_int32 -> {demangle_name('HashMap$string_int32')}")

    print("\n=== Monomorphizer Created ===")
    print("Ready for integration with parser for generic syntax")
