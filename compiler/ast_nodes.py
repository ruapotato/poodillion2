#!/usr/bin/env python3
"""
AST Node Definitions for Mini-Nim

All the different types of nodes in our Abstract Syntax Tree
"""

from dataclasses import dataclass
from typing import List, Optional
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
@dataclass
class ASTNode:
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

@dataclass
class CastExpr(ASTNode):
    target_type: Type
    expr: ASTNode

@dataclass
class IndexExpr(ASTNode):
    array: ASTNode
    index: ASTNode

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
