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
    MOD = '%'
    EQ = '=='
    NEQ = '!='
    LT = '<'
    LTE = '<='
    GT = '>'
    GTE = '>='
    AND = 'and'
    OR = 'or'
    # Bitwise operators
    BIT_OR = '|'
    BIT_AND = '&'
    BIT_XOR = '^'
    SHL = '<<'
    SHR = '>>'

class UnaryOp(Enum):
    NEG = '-'
    NOT = '!'

# Base class for all AST nodes
class ASTNode:
    """Base AST node with optional source span tracking"""

    def __init__(self):
        self.span = None  # Set by parser for error reporting

    def with_span(self, span):
        """Set span and return self for chaining"""
        self.span = span
        return self


# Mixin to add span support to dataclasses
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
    """Struct type definition: type Foo = object ... end"""
    name: str
    fields: List[StructField] = field(default_factory=list)
    generic_params: List[str] = field(default_factory=list)  # For generic structs


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
class BoolLiteral(ASTNode):
    value: bool

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
class SizeOfExpr(ASTNode):
    """sizeof(Type) - get size of type in bytes"""
    target_type: 'Type'


@dataclass
class DerefExpr(ASTNode):
    """Pointer dereference: ptr[]"""
    expr: ASTNode


# Statements
@dataclass
class VarDecl(ASTNode):
    name: str
    var_type: Type
    value: Optional[ASTNode] = None
    is_const: bool = False

@dataclass
class Assignment(ASTNode):
    target: ASTNode
    value: ASTNode

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
    var: str
    start: ASTNode
    end: ASTNode
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

@dataclass
class ProcDecl(ASTNode):
    name: str
    params: List[Parameter]
    return_type: Optional[Type]
    body: List[ASTNode]
    is_inline: bool = False
    type_params: List['GenericType'] = field(default_factory=list)  # Generic type parameters

@dataclass
class ExternDecl(ASTNode):
    """External function declaration (implemented in assembly)"""
    name: str
    params: List[Parameter]
    return_type: Optional[Type]

# Program
@dataclass
class Program(ASTNode):
    declarations: List[ASTNode]

    def __repr__(self):
        return f"Program({len(self.declarations)} declarations)"
