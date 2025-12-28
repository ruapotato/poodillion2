#!/usr/bin/env python3
"""
AST Node Definitions for Brainhair

All the different types of nodes in our Abstract Syntax Tree
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum

class BinOp(Enum):
    ADD = '+'
    SUB = '-'
    MUL = '*'
    DIV = '/'
    IDIV = '//'  # Integer division
    MOD = '%'
    POW = '**'   # Power/exponentiation
    EQ = '=='
    NEQ = '!='
    LT = '<'
    LTE = '<='
    GT = '>'
    GTE = '>='
    AND = 'and'
    OR = 'or'
    IN = 'in'      # Membership test (Python compatibility)
    NOT_IN = 'not in'  # Negative membership test
    # Bitwise operators
    BIT_OR = '|'
    BIT_AND = '&'
    BIT_XOR = '^'
    SHL = '<<'
    SHR = '>>'

class UnaryOp(Enum):
    NEG = '-'
    NOT = '!'
    BIT_NOT = '~'  # Bitwise NOT

# Base class for all AST nodes
class ASTNode:
    """Base AST node with optional source span tracking"""

    def __init__(self):
        self.span = None  # Set by parser for error reporting

    def with_span(self, span):
        """Set span and return self for chaining"""
        self.span = span
        return self


# Mixin to add span support to dataclasses (Python-only)
try:
    def _add_span_support(cls):
        """Decorator to add span tracking to dataclass nodes"""
        original_init = cls.__init__
        def new_init(self, *args, **kwargs):
            original_init(self, *args, **kwargs)
            if not hasattr(self, 'span'):
                self.span = None
        cls.__init__ = new_init
        cls.with_span = lambda self, span: (setattr(self, 'span', span), self)[1]
        return cls
except:
    pass

# Types
@dataclass
class Type(ASTNode):
    name: str

@dataclass
class PointerType(ASTNode):
    base_type: Type

    @property
    def name(self):
        return f"ptr {self.base_type.name}"


@dataclass
class ArrayType(ASTNode):
    """Array type with compile-time known size: array[N, T]"""
    size: int  # Compile-time size
    element_type: 'Type'

    @property
    def name(self):
        return f"array[{self.size}, {self.element_type.name}]"


@dataclass
class SliceType(ASTNode):
    """Slice type: []T - fat pointer (ptr + len)"""
    element_type: 'Type'

    @property
    def name(self):
        return f"[]{self.element_type.name}"


@dataclass
class ListType(ASTNode):
    """List type: List[T] - dynamic growable array"""
    element_type: 'Type'

    @property
    def name(self):
        return f"List[{self.element_type.name}]"


@dataclass
class DictType(ASTNode):
    """Dict type: Dict[K, V] - hash map"""
    key_type: 'Type'
    value_type: 'Type'

    @property
    def name(self):
        return f"Dict[{self.key_type.name}, {self.value_type.name}]"


@dataclass
class GenericType(ASTNode):
    """Generic type parameter: T in proc foo[T](x: T)"""
    name: str
    constraints: List[str] = field(default_factory=list)  # Future: type constraints


@dataclass
class GenericInstanceType(ASTNode):
    """Instantiated generic type: Vec[int32]"""
    base_type: str  # Name of generic type
    type_args: List['Type'] = field(default_factory=list)

    @property
    def name(self):
        args = ", ".join(t.name for t in self.type_args)
        return f"{self.base_type}[{args}]"


@dataclass
class StructField(ASTNode):
    """Field in a struct definition"""
    name: str
    field_type: 'Type'
    default_value: Optional['ASTNode'] = None


@dataclass
class StructDecl(ASTNode):
    """Struct type definition: class Foo: ... or type Foo = object ..."""
    name: str
    fields: List[StructField] = field(default_factory=list)
    generic_params: List[str] = field(default_factory=list)  # For generic structs
    is_packed: bool = False  # For @packed decorator


# Expressions
@dataclass
class IntLiteral(ASTNode):
    value: int

@dataclass
class CharLiteral(ASTNode):
    value: str

@dataclass
class StringLiteral(ASTNode):
    value: str

@dataclass
class FStringLiteral(ASTNode):
    """F-string literal: f"Hello {name}" - format string with interpolation"""
    value: str  # Raw string, interpolation parsed at compile time

@dataclass
class BoolLiteral(ASTNode):
    value: bool

@dataclass
class NoneLiteral(ASTNode):
    """None literal"""
    pass

@dataclass
class Identifier(ASTNode):
    name: str

@dataclass
class BinaryExpr(ASTNode):
    left: ASTNode
    op: BinOp
    right: ASTNode

@dataclass
class UnaryExpr(ASTNode):
    op: UnaryOp
    expr: ASTNode

@dataclass
class CallExpr(ASTNode):
    func: str
    args: List[ASTNode]
    type_args: List['Type'] = field(default_factory=list)  # Generic type arguments

@dataclass
class CastExpr(ASTNode):
    target_type: Type
    expr: ASTNode

@dataclass
class IsInstanceExpr(ASTNode):
    """isinstance(expr, Type) - type check expression"""
    expr: ASTNode
    check_type: str  # Type name to check against

@dataclass
class IndexExpr(ASTNode):
    array: ASTNode
    index: ASTNode

@dataclass
class AddrOfExpr(ASTNode):
    """Address-of operator - gets the address of a variable"""
    expr: ASTNode


@dataclass
class FieldAccessExpr(ASTNode):
    """Field access: obj.field"""
    object: ASTNode
    field_name: str


@dataclass
class StructLiteral(ASTNode):
    """Struct instantiation: Foo(field1: val1, field2: val2)"""
    struct_type: str
    field_values: Dict[str, ASTNode] = field(default_factory=dict)


@dataclass
class ArrayLiteral(ASTNode):
    """Array literal: [1, 2, 3]"""
    elements: List[ASTNode] = field(default_factory=list)


@dataclass
class DictLiteral(ASTNode):
    """Dict literal: {"key": value, ...}"""
    pairs: List[tuple] = field(default_factory=list)  # List of (key, value) pairs


@dataclass
class TupleLiteral(ASTNode):
    """Tuple literal: (a, b, c)"""
    elements: List[ASTNode] = field(default_factory=list)


@dataclass
class SizeOfExpr(ASTNode):
    """sizeof(Type) - get size of type in bytes"""
    target_type: 'Type'


@dataclass
class DerefExpr(ASTNode):
    """Pointer dereference: ptr[]"""
    expr: ASTNode


@dataclass
class SliceExpr(ASTNode):
    """Slice creation: arr[start..end] - creates a fat pointer"""
    array: ASTNode
    start: ASTNode
    end: ASTNode


# Statements
@dataclass
class VarDecl(ASTNode):
    name: str
    var_type: Type
    value: Optional[ASTNode] = None
    is_const: bool = False
    is_extern: bool = False

@dataclass
class Assignment(ASTNode):
    target: ASTNode
    value: ASTNode
    type_hint: Optional[Type] = None  # Type annotation if present (e.g., self.x: int = 0)

@dataclass
class ReturnStmt(ASTNode):
    value: Optional[ASTNode] = None

@dataclass
class IfStmt(ASTNode):
    condition: ASTNode
    then_block: List[ASTNode]
    elif_blocks: List[tuple] = None  # List of (condition, block) tuples
    else_block: Optional[List[ASTNode]] = None

@dataclass
class WhileStmt(ASTNode):
    condition: ASTNode
    body: List[ASTNode]

@dataclass
class ForStmt(ASTNode):
    """For loop over range: for i in start..end"""
    var: str
    start: ASTNode
    end: ASTNode
    body: List[ASTNode]

@dataclass
class ForEachStmt(ASTNode):
    """For-each loop over array: for item in array or for a, b in pairs"""
    vars: List[str]  # List of variable names (supports tuple unpacking)
    iterable: ASTNode
    body: List[ASTNode]

@dataclass
class ExprStmt(ASTNode):
    expr: ASTNode

@dataclass
class DiscardStmt(ASTNode):
    pass

@dataclass
class BreakStmt(ASTNode):
    pass

@dataclass
class ContinueStmt(ASTNode):
    pass

@dataclass
class DeferStmt(ASTNode):
    """Defer statement: defer expr - executes expr when function returns"""
    stmt: ASTNode  # The statement to defer (usually a function call)


@dataclass
class PassStmt(ASTNode):
    """Pass statement - no-op placeholder"""
    pass


@dataclass
class WithStmt(ASTNode):
    """With statement for context managers: with expr as name: body"""
    context: ASTNode  # The context manager expression
    var_name: Optional[str]  # Optional binding name
    body: List[ASTNode] = field(default_factory=list)


@dataclass
class RaiseStmt(ASTNode):
    """Raise statement for exceptions (Python compatibility)"""
    exception: Optional[ASTNode] = None  # The exception expression


@dataclass
class TryExceptStmt(ASTNode):
    """Try/except statement for polyglot code.
    In Brainhair, we execute the except_body (Brainhair-compatible code).
    In Python, the try_body runs first and except_body only on exception."""
    try_body: List[ASTNode] = field(default_factory=list)
    except_body: List[ASTNode] = field(default_factory=list)
    finally_body: List[ASTNode] = field(default_factory=list)


@dataclass
class RangeExpr(ASTNode):
    """Range expression: range(start, end, step)"""
    start: ASTNode
    end: Optional[ASTNode] = None
    step: Optional[ASTNode] = None


@dataclass
class AsmExpr(ASTNode):
    """Inline assembly: asm("instruction")"""
    instruction: str


@dataclass
class ConditionalExpr(ASTNode):
    """Conditional expression: if cond: a else: b"""
    condition: ASTNode
    then_expr: ASTNode
    else_expr: ASTNode

# Procedures
@dataclass
class Parameter(ASTNode):
    name: str
    param_type: Type
    default_value: ASTNode = None  # Optional default value for Python compatibility

@dataclass
class ProcDecl(ASTNode):
    name: str
    params: List[Parameter]
    return_type: Optional[Type]
    body: List[ASTNode]
    is_inline: bool = False
    type_params: List['GenericType'] = field(default_factory=list)  # Generic type parameters

@dataclass
class MethodDecl(ASTNode):
    """Method declaration: proc (self: ptr Type) name(params): return_type"""
    receiver_type: Type  # The type this method belongs to (e.g., Point)
    receiver_name: str   # Usually "self"
    name: str
    params: List[Parameter]
    return_type: Optional[Type]
    body: List[ASTNode]

@dataclass
class MethodCallExpr(ASTNode):
    """Method call: obj.method(args)"""
    object: ASTNode
    method_name: str
    args: List[ASTNode] = field(default_factory=list)

@dataclass
class ExternDecl(ASTNode):
    """External function declaration (implemented in assembly)"""
    name: str
    params: List[Parameter]
    return_type: Optional[Type]


# Enums and Pattern Matching
@dataclass
class EnumVariant(ASTNode):
    """A variant of an enum type: Some(T) or None"""
    name: str
    payload_types: List['Type'] = field(default_factory=list)  # Types for payload, empty for unit variants


@dataclass
class EnumDecl(ASTNode):
    """Enum type definition: type Option = enum Some(T) | None"""
    name: str
    variants: List[EnumVariant] = field(default_factory=list)
    generic_params: List[str] = field(default_factory=list)  # For generic enums like Option[T]


@dataclass
class MatchArm(ASTNode):
    """A single arm of a match expression: Pattern => body"""
    pattern: 'Pattern'
    body: List[ASTNode]


@dataclass
class Pattern(ASTNode):
    """A pattern for matching: VariantName(binding1, binding2) or just VariantName"""
    variant_name: str
    bindings: List[str] = field(default_factory=list)  # Variable names to bind payload values


@dataclass
class MatchExpr(ASTNode):
    """Match expression: match expr: arms"""
    expr: ASTNode
    arms: List[MatchArm] = field(default_factory=list)


# Import
@dataclass
class ImportDecl(ASTNode):
    """Import declaration.

    Supports:
    - from lib.syscalls import *
    - from lib.syscalls import func1, func2
    - import lib.math
    - import lib.math as m
    """
    path: str  # The import path (e.g., "lib/syscalls")
    alias: Optional[str] = None  # Optional alias for 'import x as y'
    import_names: List[str] = field(default_factory=list)  # Names imported with 'from x import y, z'


# Program
@dataclass
class Program(ASTNode):
    declarations: List[ASTNode]
    imports: List[ImportDecl] = field(default_factory=list)  # Import declarations

    def __repr__(self):
        return f"Program({len(self.declarations)} declarations, {len(self.imports)} imports)"
