#!/usr/bin/env python3
"""
Brainhair Parser - Python Syntax Edition

Builds AST from tokens using Python-style syntax.
"""

# Python-only imports (Brainhair ignores these)
try:
    from typing import List, Optional, Dict
except:
    pass

# Import token types as integers (works in both Python and Brainhair)
from lexer import Token, TokenType, Lexer, get_keyword_name
# Keywords
from lexer import TT_DEF, TT_CLASS, TT_FROM, TT_IMPORT, TT_AS, TT_RETURN
from lexer import TT_IF, TT_ELIF, TT_ELSE, TT_WHILE, TT_FOR, TT_IN
from lexer import TT_BREAK, TT_CONTINUE, TT_PASS, TT_WITH, TT_RAISE
from lexer import TT_TRY, TT_EXCEPT, TT_FINALLY, TT_LAMBDA, TT_YIELD
from lexer import TT_ASYNC, TT_AWAIT, TT_EXTERN, TT_ASM, TT_DEFER, TT_MATCH, TT_FINAL
# Types
from lexer import TT_PTR, TT_LIST, TT_DICT, TT_TUPLE, TT_OPTIONAL
from lexer import TT_INT8, TT_INT16, TT_INT32, TT_INT64
from lexer import TT_UINT8, TT_UINT16, TT_UINT32, TT_UINT64
from lexer import TT_FLOAT32, TT_FLOAT64, TT_BOOL, TT_CHAR, TT_STR, TT_BYTES
from lexer import TT_INT, TT_FLOAT, TT_ARRAY, TT_REF, TT_ENUM, TT_AUTO
from lexer import TT_DATACLASS, TT_ISINSTANCE, TT_FIELD, TT_PROPERTY
# Literals
from lexer import TT_IDENT, TT_NUMBER, TT_STRING, TT_FSTRING, TT_CHAR_LIT
from lexer import TT_TRUE, TT_FALSE, TT_NONE
# Operators (using actual lexer names)
from lexer import TT_PLUS, TT_MINUS, TT_STAR, TT_SLASH, TT_DOUBLE_SLASH, TT_PERCENT, TT_DOUBLE_STAR
from lexer import TT_AMPERSAND, TT_PIPE, TT_CARET, TT_TILDE, TT_SHL, TT_SHR
from lexer import TT_EQUALS, TT_EQUALS_EQUALS, TT_NOT_EQUALS
from lexer import TT_LESS, TT_LESS_EQUALS, TT_GREATER, TT_GREATER_EQUALS
from lexer import TT_PLUS_EQUALS, TT_MINUS_EQUALS, TT_STAR_EQUALS, TT_SLASH_EQUALS
from lexer import TT_DOUBLE_SLASH_EQUALS, TT_PERCENT_EQUALS
from lexer import TT_AMPERSAND_EQUALS, TT_PIPE_EQUALS, TT_CARET_EQUALS, TT_SHL_EQUALS, TT_SHR_EQUALS
from lexer import TT_AND, TT_OR, TT_NOT, TT_IS, TT_IS_NOT, TT_IN_OP, TT_NOT_IN
# Punctuation
from lexer import TT_LPAREN, TT_RPAREN, TT_LBRACKET, TT_RBRACKET, TT_LBRACE, TT_RBRACE
from lexer import TT_COMMA, TT_DOT, TT_DOTDOT, TT_COLON, TT_ARROW, TT_AT
from lexer import TT_NEWLINE, TT_INDENT, TT_DEDENT, TT_EOF
from lexer import TT_VAR, TT_DISCARD, TT_CONST
from ast_nodes import *

# Compatibility aliases for code that uses short names
TT_EQ = TT_EQUALS_EQUALS
TT_NE = TT_NOT_EQUALS
TT_LT = TT_LESS
TT_LE = TT_LESS_EQUALS
TT_GT = TT_GREATER
TT_GE = TT_GREATER_EQUALS
TT_EQUALS = TT_EQUALS
TT_PLUS_EQ = TT_PLUS_EQUALS
TT_MINUS_EQ = TT_MINUS_EQUALS
TT_STAR_EQ = TT_STAR_EQUALS
TT_SLASH_EQ = TT_SLASH_EQUALS
TT_MOD_EQ = TT_PERCENT_EQUALS
TT_AMP_EQ = TT_AMPERSAND_EQUALS
TT_PIPE_EQ = TT_PIPE_EQUALS
TT_CARET_EQ = TT_CARET_EQUALS
TT_SHL_EQ = TT_SHL_EQUALS
TT_SHR_EQ = TT_SHR_EQUALS
TT_AMP = TT_AMPERSAND

def keyword_name_from_type(tt: int) -> str:
    """Get keyword string from token type. Used for field names in class bodies."""
    if tt == TT_VAR:
        return "var"
    if tt == TT_DEF:
        return "def"
    if tt == TT_CLASS:
        return "class"
    if tt == TT_FROM:
        return "from"
    if tt == TT_IMPORT:
        return "import"
    if tt == TT_AS:
        return "as"
    if tt == TT_RETURN:
        return "return"
    if tt == TT_IF:
        return "if"
    if tt == TT_ELIF:
        return "elif"
    if tt == TT_ELSE:
        return "else"
    if tt == TT_WHILE:
        return "while"
    if tt == TT_FOR:
        return "for"
    if tt == TT_IN:
        return "in"
    if tt == TT_BREAK:
        return "break"
    if tt == TT_CONTINUE:
        return "continue"
    if tt == TT_PASS:
        return "pass"
    if tt == TT_WITH:
        return "with"
    if tt == TT_RAISE:
        return "raise"
    if tt == TT_TRY:
        return "try"
    if tt == TT_EXCEPT:
        return "except"
    if tt == TT_FINALLY:
        return "finally"
    if tt == TT_MATCH:
        return "match"
    if tt == TT_CONST:
        return "const"
    if tt == TT_EXTERN:
        return "extern"
    if tt == TT_ASM:
        return "asm"
    if tt == TT_DEFER:
        return "defer"
    if tt == TT_PTR:
        return "ptr"
    if tt == TT_LIST:
        return "list"
    if tt == TT_DICT:
        return "dict"
    if tt == TT_TUPLE:
        return "tuple"
    if tt == TT_OPTIONAL:
        return "optional"
    if tt == TT_ARRAY:
        return "array"
    if tt == TT_ENUM:
        return "enum"
    if tt == TT_INT:
        return "int"
    if tt == TT_FLOAT:
        return "float"
    if tt == TT_BOOL:
        return "bool"
    if tt == TT_STR:
        return "str"
    if tt == TT_CHAR:
        return "char"
    if tt == TT_BYTES:
        return "bytes"
    return "unknown"

# ============================================================================
# Polyglot Helper Functions
# ============================================================================

def lookup_compound_op(tt: int):
    """Look up compound operator binary op from token type. Returns None if not a compound op."""
    if tt == TT_PLUS_EQUALS:
        return BinOp.ADD
    if tt == TT_MINUS_EQUALS:
        return BinOp.SUB
    if tt == TT_STAR_EQUALS:
        return BinOp.MUL
    if tt == TT_SLASH_EQUALS:
        return BinOp.DIV
    if tt == TT_DOUBLE_SLASH_EQUALS:
        return BinOp.IDIV
    if tt == TT_PERCENT_EQUALS:
        return BinOp.MOD
    if tt == TT_AMPERSAND_EQUALS:
        return BinOp.BIT_AND
    if tt == TT_PIPE_EQUALS:
        return BinOp.BIT_OR
    if tt == TT_CARET_EQUALS:
        return BinOp.BIT_XOR
    if tt == TT_SHL_EQUALS:
        return BinOp.SHL
    if tt == TT_SHR_EQUALS:
        return BinOp.SHR
    return None

def lookup_basic_type(tt: int) -> str:
    """Look up a basic type name from token type. Returns empty string if not a basic type."""
    if tt == TT_INT8:
        return 'int8'
    if tt == TT_INT16:
        return 'int16'
    if tt == TT_INT32:
        return 'int32'
    if tt == TT_INT64:
        return 'int64'
    if tt == TT_UINT8:
        return 'uint8'
    if tt == TT_UINT16:
        return 'uint16'
    if tt == TT_UINT32:
        return 'uint32'
    if tt == TT_UINT64:
        return 'uint64'
    if tt == TT_FLOAT32:
        return 'float32'
    if tt == TT_FLOAT64:
        return 'float64'
    if tt == TT_BOOL:
        return 'bool'
    if tt == TT_CHAR:
        return 'char'
    if tt == TT_STR:
        return 'str'
    if tt == TT_BYTES:
        return 'bytes'
    if tt == TT_INT:
        return 'int32'
    if tt == TT_FLOAT:
        return 'float32'
    return ''


def join_paths(parts: List[str]) -> str:
    """Join a list of path parts with '/' separator."""
    if len(parts) == 0:
        return ""
    result: str = parts[0]
    i: int = 1
    while i < len(parts):
        result = result + "/" + parts[i]
        i = i + 1
    return result


def is_type_keyword(tt: int) -> int:
    """Check if token type is a type keyword. Returns 1 if true, 0 if false."""
    if tt == TT_PTR:
        return 1
    if tt == TT_INT8:
        return 1
    if tt == TT_INT16:
        return 1
    if tt == TT_INT32:
        return 1
    if tt == TT_INT64:
        return 1
    if tt == TT_UINT8:
        return 1
    if tt == TT_UINT16:
        return 1
    if tt == TT_UINT32:
        return 1
    if tt == TT_UINT64:
        return 1
    if tt == TT_FLOAT32:
        return 1
    if tt == TT_FLOAT64:
        return 1
    if tt == TT_BOOL:
        return 1
    if tt == TT_CHAR:
        return 1
    if tt == TT_STR:
        return 1
    return 0

class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0

    def current_token(self) -> Token:
        if self.pos >= len(self.tokens):
            return self.tokens[-1]  # EOF
        return self.tokens[self.pos]

    def peek_token(self, offset=1) -> Token:
        pos = self.pos + offset
        if pos >= len(self.tokens):
            return self.tokens[-1]
        return self.tokens[pos]

    def advance(self):
        if self.pos < len(self.tokens) - 1:
            self.pos += 1

    def expect(self, token_type: TokenType) -> Token:
        token = self.current_token()
        if token.type != token_type:
            raise SyntaxError(f"Expected {token_type}, got {token.type} at line {token.line}")
        self.advance()
        return token

    def skip_newlines(self):
        while self.current_token().type == TT_NEWLINE:
            self.advance()

    def match(self, *types) -> bool:
        """Check if current token matches any of the given types."""
        tt = self.current_token().type
        for t in types:
            if tt == t:
                return True
        return False

    # Type parsing
    def parse_type(self) -> Type:
        """Parse a type annotation.

        Supports:
        - Basic types: int32, bool, str
        - Pointer types: Ptr[T]
        - List types: List[T]
        - Dict types: Dict[K, V]
        - Optional types: Optional[T]
        - Tuple types: Tuple[A, B]
        - Final types: Final[T]
        - Array types: Array[N, T]
        - Slice types: List[T] (or []T legacy)
        - Forward references: 'TypeName' (string-quoted)
        """
        token = self.current_token()

        # Forward reference: 'TypeName' (string-quoted type)
        if token.type == TT_STRING:
            type_name = token.value
            self.advance()
            return Type(type_name)

        # None type (Python-style void/unit return type)
        if token.type == TT_NONE:
            self.advance()
            return Type('None')

        # Basic primitive types - use polyglot lookup
        type_name = lookup_basic_type(token.type)
        if type_name != '':
            self.advance()
            return Type(type_name)

        # Ptr[T] or ptr T - pointer type
        if token.type == TT_PTR:
            self.advance()
            # Support both Ptr[T] and ptr T syntax
            if self.current_token().type == TT_LBRACKET:
                self.advance()
                base_type = self.parse_type()
                self.expect(TT_RBRACKET)
            else:
                # C-style: ptr uint8 (without brackets)
                base_type = self.parse_type()
            return PointerType(base_type)

        # *T - C-style pointer type
        if token.type == TT_STAR:
            self.advance()
            base_type = self.parse_type()
            return PointerType(base_type)

        # List[T] - dynamic list (or just List for unparameterized)
        if token.type == TT_LIST:
            self.advance()
            if self.current_token().type == TT_LBRACKET:
                self.advance()
                element_type = self.parse_type()
                self.expect(TT_RBRACKET)
                return ListType(element_type)
            return Type('List')

        # Dict[K, V] - hash map (or just Dict for unparameterized)
        if token.type == TT_DICT:
            self.advance()
            if self.current_token().type == TT_LBRACKET:
                self.advance()
                key_type = self.parse_type()
                self.expect(TT_COMMA)
                value_type = self.parse_type()
                self.expect(TT_RBRACKET)
                return DictType(key_type, value_type)
            return Type('Dict')

        # Optional[T]
        if token.type == TT_OPTIONAL:
            self.advance()
            self.expect(TT_LBRACKET)
            inner_type = self.parse_type()
            self.expect(TT_RBRACKET)
            return GenericInstanceType('Optional', [inner_type])

        # Tuple[A, B, ...]
        if token.type == TT_TUPLE:
            self.advance()
            self.expect(TT_LBRACKET)
            types = [self.parse_type()]
            while self.current_token().type == TT_COMMA:
                self.advance()
                types.append(self.parse_type())
            self.expect(TT_RBRACKET)
            return GenericInstanceType('Tuple', types)

        # Final[T] - constant type (for type annotation only)
        if token.type == TT_FINAL:
            self.advance()
            self.expect(TT_LBRACKET)
            inner_type = self.parse_type()
            self.expect(TT_RBRACKET)
            return inner_type  # Final is handled at declaration level

        # Array[N, T] - fixed-size array type
        if token.type == TT_ARRAY:
            self.advance()
            self.expect(TT_LBRACKET)
            size = self.expect(TT_NUMBER).value
            self.expect(TT_COMMA)
            element_type = self.parse_type()
            self.expect(TT_RBRACKET)
            return ArrayType(size, element_type)

        # Legacy slice type: []T
        if token.type == TT_LBRACKET:
            self.advance()
            self.expect(TT_RBRACKET)
            element_type = self.parse_type()
            return SliceType(element_type)

        # User-defined type (identifier) - could be struct name or generic
        if token.type == TT_IDENT:
            type_name = token.value
            self.advance()

            # Special case: Array[N, T] where N is a number
            if type_name == 'Array' and self.current_token().type == TT_LBRACKET:
                self.advance()  # Skip '['
                size = self.expect(TT_NUMBER).value
                self.expect(TT_COMMA)
                element_type = self.parse_type()
                self.expect(TT_RBRACKET)
                return ArrayType(size, element_type)

            # Check for generic instantiation: Type[Args]
            if self.current_token().type == TT_LBRACKET:
                self.advance()
                type_args = [self.parse_type()]
                while self.current_token().type == TT_COMMA:
                    self.advance()
                    type_args.append(self.parse_type())
                self.expect(TT_RBRACKET)
                return GenericInstanceType(type_name, type_args)

            return Type(type_name)

        raise SyntaxError(f"Expected type, got {token.type} at line {token.line}")

    # Expression parsing (with precedence)
    def parse_atom(self) -> ASTNode:
        """Parse atomic expressions (literals, identifiers, parenthesized exprs)"""
        token = self.current_token()

        # Literals
        if token.type == TT_NUMBER:
            self.advance()
            return IntLiteral(token.value)

        if token.type == TT_CHAR_LIT:
            self.advance()
            return CharLiteral(token.value)

        if token.type == TT_STRING:
            self.advance()
            return StringLiteral(token.value)

        if token.type == TT_FSTRING:
            self.advance()
            return FStringLiteral(token.value)

        if token.type == TT_TRUE:
            self.advance()
            return BoolLiteral(True)

        if token.type == TT_FALSE:
            self.advance()
            return BoolLiteral(False)

        if token.type == TT_NONE:
            self.advance()
            return NoneLiteral()

        # List/array literal: [1, 2, 3] or list comprehension: [expr for x in iterable]
        if token.type == TT_LBRACKET:
            self.advance()
            self.skip_newlines()
            elements = []

            if self.current_token().type != TT_RBRACKET:
                first_expr = self.parse_expression()

                # Check for list comprehension: [expr for var in iterable]
                if self.current_token().type == TT_FOR:
                    self.advance()  # skip 'for'
                    var_name = self.expect(TT_IDENT).value
                    self.expect(TT_IN)
                    iterable = self.parse_expression()
                    self.skip_newlines()
                    self.expect(TT_RBRACKET)
                    # Return as ForEachStmt wrapped in special node, or just return empty for now
                    # For compilation, we'll treat this as runtime loop - return placeholder
                    return ArrayLiteral([])  # TODO: proper list comprehension support

                elements.append(first_expr)
                while self.current_token().type == TT_COMMA:
                    self.advance()
                    self.skip_newlines()
                    if self.current_token().type == TT_RBRACKET:
                        break
                    elements.append(self.parse_expression())

            self.skip_newlines()
            self.expect(TT_RBRACKET)
            return ArrayLiteral(elements)

        # Dict literal: {key: value, ...} or set literal: {a, b, c}
        if token.type == TT_LBRACE:
            self.advance()
            self.skip_newlines()

            # Empty dict/set
            if self.current_token().type == TT_RBRACE:
                self.advance()
                return DictLiteral([])

            first_expr = self.parse_expression()

            # Check for set comprehension: {expr for var in iterable}
            if self.current_token().type == TT_FOR:
                self.advance()  # skip 'for'
                var_name = self.expect(TT_IDENT).value
                self.expect(TT_IN)
                iterable = self.parse_expression()
                self.skip_newlines()
                self.expect(TT_RBRACE)
                return SetLiteral([first_expr])  # Placeholder

            # Check if it's a set literal (comma after first expr) or dict (colon)
            if self.current_token().type == TT_COMMA:
                # Set literal: {a, b, c}
                elements = [first_expr]
                while self.current_token().type == TT_COMMA:
                    self.advance()
                    self.skip_newlines()
                    if self.current_token().type == TT_RBRACE:
                        break
                    elements.append(self.parse_expression())
                self.skip_newlines()
                self.expect(TT_RBRACE)
                return SetLiteral(elements)

            if self.current_token().type == TT_RBRACE:
                # Single element set: {a}
                self.advance()
                return SetLiteral([first_expr])

            # Dict literal - expect colon
            self.expect(TT_COLON)
            value = self.parse_expression()
            pairs = [(first_expr, value)]

            while self.current_token().type == TT_COMMA:
                self.advance()
                self.skip_newlines()
                if self.current_token().type == TT_RBRACE:
                    break
                key = self.parse_expression()
                self.expect(TT_COLON)
                value = self.parse_expression()
                pairs.append((key, value))

            self.skip_newlines()
            self.expect(TT_RBRACE)
            return DictLiteral(pairs)

        # Ptr[T](value) - pointer cast/construction
        if token.type == TT_PTR:
            self.advance()
            self.expect(TT_LBRACKET)
            target_type = self.parse_type()
            self.expect(TT_RBRACKET)
            self.expect(TT_LPAREN)
            expr = self.parse_expression()
            self.expect(TT_RPAREN)
            return CastExpr(PointerType(target_type), expr)

        # Identifier or function call
        if token.type == TT_IDENT:
            name = token.value
            self.advance()
            return Identifier(name)

        # Keywords used as identifiers (when not followed by their special syntax)
        # This handles cases like: var = x, asm = [], match = {}, etc.
        # Python allows these as variable names, so we need to support them
        name = keyword_name_from_type(token.type)
        if name != "unknown":
            self.advance()
            return Identifier(name)

        # Parenthesized expression or tuple
        if token.type == TT_LPAREN:
            self.advance()
            self.skip_newlines()

            # Empty tuple
            if self.current_token().type == TT_RPAREN:
                self.advance()
                return TupleLiteral([])

            expr = self.parse_expression()

            # Check if it's a tuple
            if self.current_token().type == TT_COMMA:
                elements = [expr]
                while self.current_token().type == TT_COMMA:
                    self.advance()
                    self.skip_newlines()
                    if self.current_token().type == TT_RPAREN:
                        break
                    elements.append(self.parse_expression())
                self.expect(TT_RPAREN)
                return TupleLiteral(elements)

            self.expect(TT_RPAREN)
            return expr

        # Unary operators
        if token.type == TT_MINUS:
            self.advance()
            return UnaryExpr(UnaryOp.NEG, self.parse_unary())

        if token.type == TT_NOT:
            self.advance()
            return UnaryExpr(UnaryOp.NOT, self.parse_unary())

        if token.type == TT_TILDE:
            self.advance()
            return UnaryExpr(UnaryOp.BIT_NOT, self.parse_unary())

        raise SyntaxError(f"Unexpected token {token.type} at line {token.line}")

    def parse_unary(self) -> ASTNode:
        """Parse unary expressions."""
        token = self.current_token()

        if token.type == TT_MINUS:
            self.advance()
            return UnaryExpr(UnaryOp.NEG, self.parse_unary())

        if token.type == TT_NOT:
            self.advance()
            return UnaryExpr(UnaryOp.NOT, self.parse_unary())

        if token.type == TT_TILDE:
            self.advance()
            return UnaryExpr(UnaryOp.BIT_NOT, self.parse_unary())

        # Dereference operator: *ptr
        if token.type == TT_STAR:
            self.advance()
            return UnaryExpr(UnaryOp.DEREF, self.parse_unary())

        return self.parse_primary()

    def parse_primary(self) -> ASTNode:
        """Parse primary expressions with postfix operations."""
        token = self.current_token()

        # Lambda expression: lambda args: expr (parse and return None placeholder)
        if token.type == TT_LAMBDA:
            self.advance()
            # Skip parameters until colon
            while self.current_token().type != TT_COLON:
                self.advance()
            self.advance()  # Skip colon
            # Parse the lambda body expression
            self.parse_expression()
            # Return None as placeholder (lambdas not fully supported yet)
            return NoneLiteral()

        # addr(expr) - address-of (only if followed by LPAREN)
        is_addr = token.type == TT_IDENT and token.value == 'addr'
        if is_addr and self.peek_token().type == TT_LPAREN:
            self.advance()
            self.expect(TT_LPAREN)
            expr = self.parse_expression()
            self.expect(TT_RPAREN)
            return AddrOfExpr(expr)

        # cast[Type](expr) - type cast (only if followed by LBRACKET)
        is_cast = token.type == TT_IDENT and token.value == 'cast'
        if is_cast and self.peek_token().type == TT_LBRACKET:
            self.advance()
            self.expect(TT_LBRACKET)
            target_type = self.parse_type()
            self.expect(TT_RBRACKET)
            self.expect(TT_LPAREN)
            expr = self.parse_expression()
            self.expect(TT_RPAREN)
            return CastExpr(target_type, expr)

        # isinstance(expr, Type) - type check (Python compatibility)
        # Handle both keyword and identifier tokenization
        is_isinstance = token.type == TT_ISINSTANCE
        is_isinstance = is_isinstance or (token.type == TT_IDENT and token.value == 'isinstance')
        if is_isinstance and self.peek_token().type == TT_LPAREN:
            self.advance()
            self.expect(TT_LPAREN)
            expr = self.parse_expression()
            self.expect(TT_COMMA)
            # Parse the type - could be single name or tuple of types: (Type1, Type2)
            if self.current_token().type == TT_LPAREN:
                # Tuple of types - skip the whole tuple and use first type
                self.advance()  # skip (
                type_name = self.expect(TT_IDENT).value
                while self.current_token().type == TT_DOT:
                    self.advance()
                    type_name += '.' + self.expect(TT_IDENT).value
                # Skip remaining types in tuple
                while self.current_token().type == TT_COMMA:
                    self.advance()
                    self.expect(TT_IDENT)
                    while self.current_token().type == TT_DOT:
                        self.advance()
                        self.expect(TT_IDENT)
                self.expect(TT_RPAREN)  # close tuple
            else:
                # Single type name
                type_name = self.expect(TT_IDENT).value
                while self.current_token().type == TT_DOT:
                    self.advance()
                    type_name += '.' + self.expect(TT_IDENT).value
            self.expect(TT_RPAREN)
            return IsInstanceExpr(expr, type_name)

        # int(expr, base) or int(expr) - type conversions
        # Handle both when 'int' is a keyword (TT_INT) or identifier
        is_int_call = token.type == TT_INT or (token.type == TT_IDENT and token.value == 'int')
        if is_int_call and self.peek_token().type == TT_LPAREN:
            self.advance()
            self.expect(TT_LPAREN)
            args: List[ASTNode] = [self.parse_expression()]
            while self.current_token().type == TT_COMMA:
                self.advance()
                args.append(self.parse_expression())
            self.expect(TT_RPAREN)
            # For BH, int() is a cast to int32, ignore base argument
            return CastExpr(Type('int32'), args[0])

        # str(expr) - string conversion
        is_str_call = token.type == TT_STR or (token.type == TT_IDENT and token.value == 'str')
        if is_str_call and self.peek_token().type == TT_LPAREN:
            self.advance()
            self.expect(TT_LPAREN)
            expr = self.parse_expression()
            self.expect(TT_RPAREN)
            # Treat str() as a call for now
            return CallExpr('str', [expr])

        # len(expr) - length function (only if followed by parenthesis)
        is_len = token.type == TT_IDENT and token.value == 'len'
        if is_len and self.peek_token() and self.peek_token().type == TT_LPAREN:
            self.advance()
            self.expect(TT_LPAREN)
            expr = self.parse_expression()
            self.expect(TT_RPAREN)
            return CallExpr('len', [expr])

        # sizeof(Type) - size of type (only if followed by LPAREN)
        is_sizeof = token.type == TT_IDENT and token.value == 'sizeof'
        if is_sizeof and self.peek_token().type == TT_LPAREN:
            self.advance()
            self.expect(TT_LPAREN)
            target_type = self.parse_type()
            self.expect(TT_RPAREN)
            return SizeOfExpr(target_type)

        # range(start, end) - range function (only if followed by LPAREN)
        is_range = token.type == TT_IDENT and token.value == 'range'
        if is_range and self.peek_token().type == TT_LPAREN:
            self.advance()
            self.expect(TT_LPAREN)
            start = self.parse_expression()
            end = None
            step = None
            if self.current_token().type == TT_COMMA:
                self.advance()
                end = self.parse_expression()
                if self.current_token().type == TT_COMMA:
                    self.advance()
                    step = self.parse_expression()
            self.expect(TT_RPAREN)
            return RangeExpr(start, end, step)

        # asm("instruction") or asm "instruction" - inline assembly
        if token.type == TT_ASM:
            self.advance()
            if self.current_token().type == TT_LPAREN:
                self.advance()  # Skip (
                asm_str = self.expect(TT_STRING).value
                self.expect(TT_RPAREN)
            else:
                # asm "instruction" syntax (no parentheses)
                asm_str = self.expect(TT_STRING).value
            return AsmExpr(asm_str)

        # match expression
        if token.type == TT_MATCH:
            return self.parse_match_expr()

        # Parse atom first
        expr = self.parse_atom()

        # Handle postfix operations
        while True:
            token = self.current_token()

            # Function call: expr(args) or generic call: expr[types](args)
            if token.type == TT_LPAREN:
                if isinstance(expr, Identifier):
                    # Check if previous was a struct literal pattern
                    saved_pos = self.pos
                    self.advance()  # Skip (
                    self.skip_newlines()

                    is_struct_literal = False
                    if self.current_token().type == TT_IDENT:
                        next_tok = self.peek_token()
                        if next_tok.type == TT_COLON:
                            is_struct_literal = True

                    self.pos = saved_pos

                    if is_struct_literal:
                        # Struct literal: Type(field: val, ...)
                        struct_name = expr.name
                        self.advance()  # Skip (
                        self.skip_newlines()
                        field_values = {}

                        if self.current_token().type != TT_RPAREN:
                            field_name = self.expect(TT_IDENT).value
                            self.expect(TT_COLON)
                            field_values[field_name] = self.parse_expression()

                            while self.current_token().type == TT_COMMA:
                                self.advance()
                                self.skip_newlines()
                                if self.current_token().type == TT_RPAREN:
                                    break
                                field_name = self.expect(TT_IDENT).value
                                self.expect(TT_COLON)
                                field_values[field_name] = self.parse_expression()

                        self.skip_newlines()
                        self.expect(TT_RPAREN)
                        expr = StructLiteral(struct_name, field_values)
                        continue

                # Regular function call
                self.advance()
                self.skip_newlines()
                args: List[ASTNode] = []

                while self.current_token().type != TT_RPAREN:
                    # Handle *args and **kwargs unpacking (skip them)
                    cur_type = self.current_token().type
                    if cur_type == TT_STAR or cur_type == TT_DOUBLE_STAR:
                        self.advance()
                        if self.current_token().type == TT_STAR:
                            self.advance()
                        # Parse the expression being unpacked
                        self.parse_expression()
                        if self.current_token().type == TT_COMMA:
                            self.advance()
                        self.skip_newlines()
                        continue

                    # Parse argument (handles keyword args and generator expressions)
                    arg_expr = self.parse_expression()

                    # Handle generator expression: expr for var in iterable [if cond]
                    if self.current_token().type == TT_FOR:
                        # Skip the generator expression, tracking nested parens
                        paren_depth = 1
                        while paren_depth > 0:
                            self.advance()
                            if self.current_token().type == TT_LPAREN:
                                paren_depth = paren_depth + 1
                            elif self.current_token().type == TT_RPAREN:
                                paren_depth = paren_depth - 1
                        # Return empty list as placeholder
                        args.append(ArrayLiteral([]))
                        break

                    if self.current_token().type == TT_EQUALS:
                        self.advance()
                        arg_expr = self.parse_expression()
                    args.append(arg_expr)
                    if self.current_token().type == TT_COMMA:
                        self.advance()
                        self.skip_newlines()
                    else:
                        break

                self.skip_newlines()
                self.expect(TT_RPAREN)

                if isinstance(expr, Identifier):
                    expr = CallExpr(expr.name, args)
                else:
                    raise SyntaxError(f"Cannot call non-identifier at line {token.line}")

            # Generic call: expr[types](args)
            elif token.type == TT_LBRACKET:
                if isinstance(expr, Identifier):
                    # Could be generic call or array indexing
                    saved_pos = self.pos
                    self.advance()

                    # Try to detect if this is a type list
                    type_keywords = set()
                    type_keywords.add(TT_INT8)
                    type_keywords.add(TT_INT16)
                    type_keywords.add(TT_INT32)
                    type_keywords.add(TT_INT64)
                    type_keywords.add(TT_UINT8)
                    type_keywords.add(TT_UINT16)
                    type_keywords.add(TT_UINT32)
                    type_keywords.add(TT_UINT64)
                    type_keywords.add(TT_BOOL)
                    type_keywords.add(TT_CHAR)
                    type_keywords.add(TT_PTR)
                    type_keywords.add(TT_LIST)
                    type_keywords.add(TT_DICT)
                    type_keywords.add(TT_OPTIONAL)
                    type_keywords.add(TT_TUPLE)
                    type_keywords.add(TT_INT)
                    type_keywords.add(TT_FLOAT)
                    type_keywords.add(TT_STR)
                    type_keywords.add(TT_BYTES)

                    first_tok = self.current_token().type
                    is_type_start = first_tok == TT_IDENT or first_tok in type_keywords

                    if is_type_start:
                        # Scan to see if followed by ]( pattern
                        scan_pos = self.pos
                        is_generic_call = False
                        while scan_pos < len(self.tokens):
                            tok = self.tokens[scan_pos]
                            if tok.type == TT_RBRACKET:
                                has_next = scan_pos + 1 < len(self.tokens)
                                if has_next and self.tokens[scan_pos + 1].type == TT_LPAREN:
                                    is_generic_call = True
                                break
                            elif tok.type in (TT_IDENT, TT_COMMA) or tok.type in type_keywords:
                                scan_pos += 1
                            else:
                                break

                        if is_generic_call:
                            # Parse as generic call
                            type_args = [self.parse_type()]
                            while self.current_token().type == TT_COMMA:
                                self.advance()
                                type_args.append(self.parse_type())
                            self.expect(TT_RBRACKET)
                            self.expect(TT_LPAREN)
                            self.skip_newlines()
                            args = []
                            if self.current_token().type != TT_RPAREN:
                                args.append(self.parse_expression())
                                while self.current_token().type == TT_COMMA:
                                    self.advance()
                                    self.skip_newlines()
                                    if self.current_token().type == TT_RPAREN:
                                        break
                                    args.append(self.parse_expression())
                            self.skip_newlines()
                            self.expect(TT_RPAREN)
                            expr = CallExpr(expr.name, args, type_args=type_args)
                            continue

                    # Restore position and treat as array indexing
                    self.pos = saved_pos

                # Array/pointer indexing or slicing
                self.advance()

                # Check for slice starting with : (e.g., [:4])
                if self.current_token().type == TT_COLON:
                    self.advance()
                    # Slice from beginning: [:end]
                    if self.current_token().type == TT_RBRACKET:
                        # [:] - full slice (return as-is for now)
                        self.advance()
                        expr = expr  # No change, just skip
                    else:
                        end = self.parse_expression()
                        self.expect(TT_RBRACKET)
                        expr = SliceExpr(expr, IntLiteral(0), end)
                else:
                    index = self.parse_expression()

                    # Check for slice: arr[start..end] or arr[start:end] or arr[start:]
                    if self.current_token().type == TT_DOTDOT:
                        self.advance()
                        end = self.parse_expression()
                        self.expect(TT_RBRACKET)
                        expr = SliceExpr(expr, index, end)
                    elif self.current_token().type == TT_COLON:
                        self.advance()
                        # Python-style slice: arr[start:end] or arr[start:]
                        if self.current_token().type == TT_RBRACKET:
                            # arr[start:] - slice to end (use large number as placeholder)
                            self.advance()
                            expr = SliceExpr(expr, index, IntLiteral(999999999))
                        else:
                            end = self.parse_expression()
                            self.expect(TT_RBRACKET)
                            expr = SliceExpr(expr, index, end)
                    else:
                        self.expect(TT_RBRACKET)
                        expr = IndexExpr(expr, index)

            # Field access or method call: expr.field or expr.method()
            elif token.type == TT_DOT:
                self.advance()
                # Field/method name can be IDENT or keyword (like 'match', 'type', etc.)
                tok = self.current_token()
                if tok.type == TT_IDENT:
                    field_name = tok.value
                    self.advance()
                elif get_keyword_name(tok.type) != "":
                    field_name = get_keyword_name(tok.type)
                    self.advance()
                else:
                    raise SyntaxError(f"Expected field name, got {tok.type} at line {tok.line}")

                if self.current_token().type == TT_LPAREN:
                    # Method call
                    self.advance()
                    args: List[ASTNode] = []

                    while self.current_token().type != TT_RPAREN:
                        # Handle *args and **kwargs unpacking (skip them)
                        cur_type = self.current_token().type
                        if cur_type == TT_STAR or cur_type == TT_DOUBLE_STAR:
                            self.advance()
                            if self.current_token().type == TT_STAR:
                                self.advance()
                            self.parse_expression()
                            if self.current_token().type == TT_COMMA:
                                self.advance()
                            continue

                        # Parse argument
                        arg_expr = self.parse_expression()

                        # Handle generator expression: expr for var in iterable [if cond]
                        if self.current_token().type == TT_FOR:
                            paren_depth = 1
                            while paren_depth > 0:
                                self.advance()
                                if self.current_token().type == TT_LPAREN:
                                    paren_depth = paren_depth + 1
                                elif self.current_token().type == TT_RPAREN:
                                    paren_depth = paren_depth - 1
                            args.append(ArrayLiteral([]))
                            break

                        if self.current_token().type == TT_EQUALS:
                            self.advance()
                            arg_expr = self.parse_expression()
                        args.append(arg_expr)
                        if self.current_token().type == TT_COMMA:
                            self.advance()
                        else:
                            break
                    self.expect(TT_RPAREN)
                    expr = MethodCallExpr(expr, field_name, args)
                else:
                    expr = FieldAccessExpr(expr, field_name)

            else:
                break

        return expr

    def parse_power(self) -> ASTNode:
        """Parse power expressions: a ** b (right associative)"""
        left = self.parse_unary()

        if self.current_token().type == TT_DOUBLE_STAR:
            self.advance()
            right = self.parse_power()  # Right associative
            left = BinaryExpr(left, BinOp.POW, right)

        return left

    def parse_multiplicative(self) -> ASTNode:
        left = self.parse_power()

        while self.match(TT_STAR, TT_SLASH, TT_DOUBLE_SLASH, TT_PERCENT):
            op_token = self.current_token()
            self.advance()

            op_map = {
                TT_STAR: BinOp.MUL,
                TT_SLASH: BinOp.DIV,
                TT_DOUBLE_SLASH: BinOp.IDIV,
                TT_PERCENT: BinOp.MOD,
            }
            op = op_map[op_token.type]
            right = self.parse_power()
            left = BinaryExpr(left, op, right)

        return left

    def parse_additive(self) -> ASTNode:
        left = self.parse_multiplicative()

        while self.match(TT_PLUS, TT_MINUS):
            op_token = self.current_token()
            self.advance()

            op = BinOp.ADD if op_token.type == TT_PLUS else BinOp.SUB
            right = self.parse_multiplicative()
            left = BinaryExpr(left, op, right)

        return left

    def parse_shift(self) -> ASTNode:
        left = self.parse_additive()

        while self.match(TT_SHL, TT_SHR):
            op_token = self.current_token()
            self.advance()

            op = BinOp.SHL if op_token.type == TT_SHL else BinOp.SHR
            right = self.parse_additive()
            left = BinaryExpr(left, op, right)

        return left

    def parse_bitwise_and(self) -> ASTNode:
        left = self.parse_shift()

        while self.current_token().type == TT_AMPERSAND:
            self.advance()
            right = self.parse_shift()
            left = BinaryExpr(left, BinOp.BIT_AND, right)

        return left

    def parse_bitwise_xor(self) -> ASTNode:
        left = self.parse_bitwise_and()

        while self.current_token().type == TT_CARET:
            self.advance()
            right = self.parse_bitwise_and()
            left = BinaryExpr(left, BinOp.BIT_XOR, right)

        return left

    def parse_bitwise_or(self) -> ASTNode:
        left = self.parse_bitwise_xor()

        while self.current_token().type == TT_PIPE:
            self.advance()
            right = self.parse_bitwise_xor()
            left = BinaryExpr(left, BinOp.BIT_OR, right)

        return left

    def parse_comparison(self) -> ASTNode:
        """Parse comparison with chaining support: a < b < c"""
        left = self.parse_bitwise_or()

        comp_tokens = {
            TT_EQUALS_EQUALS: BinOp.EQ,
            TT_NOT_EQUALS: BinOp.NEQ,
            TT_LESS: BinOp.LT,
            TT_LESS_EQUALS: BinOp.LTE,
            TT_GREATER: BinOp.GT,
            TT_GREATER_EQUALS: BinOp.GTE,
            TT_IS: BinOp.EQ,  # 'is' treated as equality for None checks
            TT_IS_NOT: BinOp.NEQ,  # 'is not' treated as inequality
            TT_IN: BinOp.IN,  # 'in' membership test
        }

        # Handle comparison chaining: 0 <= x < 100 -> (0 <= x) and (x < 100)
        comparisons = []
        while True:
            cur_type = self.current_token().type
            is_comp = cur_type in comp_tokens
            is_is_not = cur_type == TT_IS and self.peek_token().type == TT_NOT
            is_not_in = cur_type == TT_NOT and self.peek_token().type == TT_IN
            if not (is_comp or is_is_not or is_not_in):
                break
            # Handle 'not in' as a two-token operator
            if is_not_in:
                self.advance()  # Skip 'not'
                self.advance()  # Skip 'in'
                right = self.parse_bitwise_or()
                comparisons.append((left, BinOp.NOT_IN, right))
                left = right
                continue
            # Handle 'is not' as a two-token operator
            if self.current_token().type == TT_IS:
                self.advance()
                if self.current_token().type == TT_NOT:
                    self.advance()
                    op = BinOp.NEQ
                else:
                    op = BinOp.EQ
                right = self.parse_bitwise_or()
                comparisons.append((left, op, right))
                left = right
                continue
            op = comp_tokens[self.current_token().type]
            self.advance()
            right = self.parse_bitwise_or()
            comparisons.append((left, op, right))
            left = right

        if not comparisons:
            return left

        # Build chained comparison
        if len(comparisons) == 1:
            cmp0 = comparisons[0]
            return BinaryExpr(cmp0[0], cmp0[1], cmp0[2])

        # Multiple comparisons: chain with 'and'
        exprs: List[ASTNode] = []
        i = 0
        while i < len(comparisons):
            cmp_tuple = comparisons[i]
            exprs.append(BinaryExpr(cmp_tuple[0], cmp_tuple[1], cmp_tuple[2]))
            i = i + 1

        result = exprs[0]
        j = 1
        while j < len(exprs):
            result = BinaryExpr(result, BinOp.AND, exprs[j])
            j = j + 1
        return result

    def parse_not(self) -> ASTNode:
        """Parse 'not' expressions"""
        if self.current_token().type == TT_NOT:
            self.advance()
            return UnaryExpr(UnaryOp.NOT, self.parse_not())
        return self.parse_comparison()

    def parse_logical_and(self) -> ASTNode:
        left = self.parse_not()

        while self.current_token().type == TT_AND:
            self.advance()
            right = self.parse_not()
            left = BinaryExpr(left, BinOp.AND, right)

        return left

    def parse_logical_or(self) -> ASTNode:
        left = self.parse_logical_and()

        while self.current_token().type == TT_OR:
            self.advance()
            right = self.parse_logical_and()
            left = BinaryExpr(left, BinOp.OR, right)

        return left

    def parse_conditional_expr(self) -> ASTNode:
        """Parse conditional expressions: a if cond else b"""
        expr = self.parse_logical_or()

        # Python-style ternary: value if condition else other
        if self.current_token().type == TT_IF:
            self.advance()
            condition = self.parse_logical_or()
            self.expect(TT_ELSE)
            else_expr = self.parse_conditional_expr()
            return ConditionalExpr(condition, expr, else_expr)

        return expr

    def parse_expression(self) -> ASTNode:
        return self.parse_conditional_expr()

    def parse_match_expr(self) -> MatchExpr:
        """Parse match expression."""
        self.advance()  # Skip 'match'
        match_expr = self.parse_expression()
        self.expect(TT_COLON)
        self.skip_newlines()

        arms = []
        block_indent = None

        while True:
            self.skip_newlines()
            token = self.current_token()

            if token.type == TT_EOF:
                break

            if block_indent is None:
                block_indent = token.col
            elif token.col < block_indent:
                break

            # Parse pattern
            variant_name = self.expect(TT_IDENT).value
            bindings = []

            if self.current_token().type == TT_LPAREN:
                self.advance()
                if self.current_token().type != TT_RPAREN:
                    bindings.append(self.expect(TT_IDENT).value)
                    while self.current_token().type == TT_COMMA:
                        self.advance()
                        bindings.append(self.expect(TT_IDENT).value)
                self.expect(TT_RPAREN)

            pattern = Pattern(variant_name, bindings)

            self.expect(TT_COLON)
            self.skip_newlines()

            body = self.parse_block()
            arms.append(MatchArm(pattern, body))

        return MatchExpr(match_expr, arms)

    # Statement parsing

    def parse_var_decl(self, is_final: bool = False) -> VarDecl:
        """Parse variable declaration: name: Type = value or name = value"""
        name = self.expect(TT_IDENT).value
        self.expect(TT_COLON)

        # Check if type starts with Final[
        var_type = None
        if self.current_token().type == TT_FINAL:
            is_final = True
            self.advance()
            self.expect(TT_LBRACKET)
            var_type = self.parse_type()
            self.expect(TT_RBRACKET)
        else:
            var_type = self.parse_type()

        value = None
        if self.current_token().type == TT_EQUALS:
            self.advance()
            value = self.parse_expression()

        return VarDecl(name, var_type, value, is_const=is_final)

    def parse_assignment_or_expr(self) -> ASTNode:
        """Parse assignment (including compound) or expression statement."""
        expr = self.parse_expression()

        # Handle tuple unpacking: a, b = x, y (Python compatibility)
        if self.current_token().type == TT_COMMA:
            targets = [expr]
            while self.current_token().type == TT_COMMA:
                self.advance()
                targets.append(self.parse_expression())

            if self.current_token().type == TT_EQUALS:
                self.advance()
                # Parse the right side (could be a tuple)
                value = self.parse_expression()
                values = [value]
                while self.current_token().type == TT_COMMA:
                    self.advance()
                    values.append(self.parse_expression())

                # Create TupleLiteral for both sides for proper tuple unpacking
                # The codegen handles TupleLiteral targets
                if len(values) == 1 and isinstance(values[0], TupleLiteral):
                    # Assigning from a tuple literal, use its elements
                    value_tuple = values[0]
                else:
                    value_tuple = TupleLiteral(values)

                target_tuple = TupleLiteral(targets)
                return Assignment(target_tuple, value_tuple)

            # Not an assignment, return as tuple expression
            return TupleLiteral(targets)

        # Compound assignment operators - use polyglot lookup
        compound_op = lookup_compound_op(self.current_token().type)
        if compound_op is not None:
            self.advance()
            value = self.parse_expression()
            # Desugar x += y to x = x + y
            return Assignment(expr, BinaryExpr(expr, compound_op, value))

        # Type-annotated assignment for expressions like self.field: Type = value
        if self.current_token().type == TT_COLON:
            self.advance()
            var_type = self.parse_type()
            if self.current_token().type == TT_EQUALS:
                self.advance()
                value = self.parse_expression()
                return Assignment(expr, value, type_hint=var_type)  # Preserve type annotation
            # Type annotation without assignment - treat as no-op
            return ExprStmt(expr)

        # Simple assignment
        if self.current_token().type == TT_EQUALS:
            self.advance()
            value = self.parse_expression()
            return Assignment(expr, value)

        return ExprStmt(expr)

    def parse_annotated_assignment(self) -> ASTNode:
        """Parse: name: Type = value (variable with type annotation)"""
        # This is called when we see IDENT followed by COLON
        name = self.expect(TT_IDENT).value
        self.expect(TT_COLON)

        # Check for Final[T]
        is_final = False
        if self.current_token().type == TT_FINAL:
            is_final = True
            self.advance()
            self.expect(TT_LBRACKET)
            var_type = self.parse_type()
            self.expect(TT_RBRACKET)
        else:
            var_type = self.parse_type()

        value = None
        if self.current_token().type == TT_EQUALS:
            self.advance()
            value = self.parse_expression()

        return VarDecl(name, var_type, value, is_const=is_final)

    def parse_var_stmt(self) -> VarDecl:
        """Parse Brainhair native: var name: Type = value"""
        self.advance()  # Skip 'var'
        name = self.expect(TT_IDENT).value
        self.expect(TT_COLON)
        var_type = self.parse_type()

        value = None
        if self.current_token().type == TT_EQUALS:
            self.advance()
            value = self.parse_expression()

        return VarDecl(name, var_type, value, is_const=False)

    def parse_const_stmt(self) -> VarDecl:
        """Parse Brainhair native: const name: Type = value"""
        self.advance()  # Skip 'const'
        name = self.expect(TT_IDENT).value
        self.expect(TT_COLON)
        var_type = self.parse_type()

        value = None
        if self.current_token().type == TT_EQUALS:
            self.advance()
            value = self.parse_expression()

        return VarDecl(name, var_type, value, is_const=True)

    def parse_return_stmt(self) -> ReturnStmt:
        self.advance()  # Skip 'return'

        if self.current_token().type == TT_NEWLINE:
            return ReturnStmt()

        # Parse expression, check for tuple return (comma-separated values)
        value = self.parse_expression()
        if self.current_token().type == TT_COMMA:
            # Tuple return: return a, b, c
            elements: List[ASTNode] = [value]
            while self.current_token().type == TT_COMMA:
                self.advance()
                elements.append(self.parse_expression())
            value = TupleLiteral(elements)
        return ReturnStmt(value)

    def parse_if_stmt(self) -> IfStmt:
        if_col = self.current_token().col
        self.advance()  # Skip 'if'

        condition = self.parse_expression()
        self.expect(TT_COLON)
        self.skip_newlines()

        then_block = self.parse_block()

        elif_blocks: List[tuple] = []
        while True:
            cur = self.current_token()
            is_elif = cur.type == TT_ELIF and cur.col == if_col
            if not is_elif:
                break
            self.advance()
            elif_cond = self.parse_expression()
            self.expect(TT_COLON)
            self.skip_newlines()
            elif_body = self.parse_block()
            elif_blocks.append((elif_cond, elif_body))

        else_block = None
        cur = self.current_token()
        is_else = cur.type == TT_ELSE and cur.col == if_col
        if is_else:
            self.advance()
            self.expect(TT_COLON)
            self.skip_newlines()
            else_block = self.parse_block()

        return IfStmt(condition, then_block, elif_blocks if elif_blocks else None, else_block)

    def parse_while_stmt(self) -> WhileStmt:
        self.advance()  # Skip 'while'

        condition = self.parse_expression()
        self.expect(TT_COLON)
        self.skip_newlines()

        body = self.parse_block()
        return WhileStmt(condition, body)

    def parse_var_name(self) -> str:
        """Parse a variable name - could be an identifier or a keyword used as a name"""
        token = self.current_token()
        if token.type == TT_IDENT:
            name = token.value
            self.advance()
            return name
        # Keywords can be used as variable names in Python-style code
        # Check if next token indicates this is being used as a name (followed by 'in', ':', '=', etc.)
        name = keyword_name_from_type(token.type)
        if name != "unknown":
            self.advance()
            return name
        raise SyntaxError(f"Expected identifier, got {token.type} at line {token.line}")

    def parse_for_stmt(self):
        """Parse for loop: for i in range(n) or for item in iterable or for a, b in pairs"""
        self.advance()  # Skip 'for'

        # Parse variable names (supports tuple unpacking: for a, b in ... or for i, (a, b) in ...)
        var_names: List[str] = []
        var_names.append(self.parse_var_name())
        while self.current_token().type == TT_COMMA:
            self.advance()  # Skip comma
            if self.current_token().type == TT_LPAREN:
                # Nested tuple like (a, b) - parse and flatten
                self.advance()  # skip (
                var_names.append(self.parse_var_name())
                while self.current_token().type == TT_COMMA:
                    self.advance()
                    var_names.append(self.parse_var_name())
                self.expect(TT_RPAREN)
            else:
                var_names.append(self.parse_var_name())

        var_name = var_names[0]  # For ForStmt compatibility
        self.expect(TT_IN)

        # Check for range() call
        if self.current_token().type == TT_IDENT and self.current_token().value == 'range':
            self.advance()
            self.expect(TT_LPAREN)

            # Parse range arguments
            first = self.parse_expression()
            start = IntLiteral(0)
            end = first
            step = None

            if self.current_token().type == TT_COMMA:
                self.advance()
                start = first
                end = self.parse_expression()

                if self.current_token().type == TT_COMMA:
                    self.advance()
                    step = self.parse_expression()

            self.expect(TT_RPAREN)
            self.expect(TT_COLON)
            self.skip_newlines()
            body = self.parse_block()
            return ForStmt(var_name, start, end, body)

        # Check for start..end range syntax
        first_expr = self.parse_expression()
        if self.current_token().type == TT_DOTDOT:
            self.advance()
            end = self.parse_expression()
            self.expect(TT_COLON)
            self.skip_newlines()
            body = self.parse_block()
            return ForStmt(var_name, first_expr, end, body)

        # For-each over iterable
        self.expect(TT_COLON)
        self.skip_newlines()
        body = self.parse_block()
        return ForEachStmt(var_names, first_expr, body)

    def parse_with_stmt(self) -> WithStmt:
        """Parse with statement (context manager)"""
        self.advance()  # Skip 'with'

        context = self.parse_expression()
        var_name = None
        if self.current_token().type == TT_AS:
            self.advance()
            var_name = self.expect(TT_IDENT).value

        self.expect(TT_COLON)
        self.skip_newlines()
        body = self.parse_block()

        return WithStmt(context, var_name, body)

    def parse_defer_stmt(self) -> DeferStmt:
        self.advance()  # Skip 'defer'
        expr = self.parse_expression()
        return DeferStmt(ExprStmt(expr))

    def parse_statement(self) -> ASTNode:
        token = self.current_token()

        # Check for annotated assignment: name: Type = value
        if token.type == TT_IDENT:
            if self.peek_token().type == TT_COLON:
                return self.parse_annotated_assignment()

        if token.type == TT_RETURN:
            return self.parse_return_stmt()

        if token.type == TT_BREAK:
            self.advance()
            return BreakStmt()

        if token.type == TT_CONTINUE:
            self.advance()
            return ContinueStmt()

        if token.type == TT_PASS:
            self.advance()
            return PassStmt()

        # Brainhair native: var name: Type = value
        if token.type == TT_VAR:
            return self.parse_var_stmt()

        # Brainhair native: const name: Type = value
        if token.type == TT_CONST:
            return self.parse_const_stmt()

        # Brainhair native: discard expression
        if token.type == TT_DISCARD:
            self.advance()
            expr = self.parse_expression()
            return ExprStmt(expr)  # Just evaluate and discard

        if token.type == TT_IF:
            return self.parse_if_stmt()

        if token.type == TT_WHILE:
            return self.parse_while_stmt()

        if token.type == TT_FOR:
            return self.parse_for_stmt()

        if token.type == TT_WITH:
            return self.parse_with_stmt()

        if token.type == TT_DEFER:
            return self.parse_defer_stmt()

        if token.type == TT_RAISE:
            self.advance()
            # Parse the exception expression
            if self.current_token().type in (TT_NEWLINE, TT_EOF):
                return RaiseStmt(None)
            exception = self.parse_expression()
            return RaiseStmt(exception)

        # Try/except block - for polyglot code
        # Pattern: try: Python-only code; except: Brainhair-compatible code
        if token.type == TT_TRY:
            self.advance()
            self.expect(TT_COLON)
            self.skip_newlines()
            try_body = self.parse_block()

            # Parse except clauses and capture the body for Brainhair execution
            except_body = []
            while self.current_token().type == TT_EXCEPT:
                self.advance()
                # Skip exception type and 'as name' if present
                if self.current_token().type != TT_COLON:
                    self.parse_expression()  # Exception type
                    if self.current_token().type == TT_AS:
                        self.advance()
                        self.expect(TT_IDENT)
                self.expect(TT_COLON)
                self.skip_newlines()
                except_body = self.parse_block()  # Capture except body for Brainhair

            # Parse optional finally
            finally_body = []
            if self.current_token().type == TT_FINALLY:
                self.advance()
                self.expect(TT_COLON)
                self.skip_newlines()
                finally_body = self.parse_block()

            # Return TryExceptStmt - codegen will use except_body for Brainhair
            return TryExceptStmt(try_body, except_body, finally_body)

        # Import inside a block (Python allows this)
        if token.type in (TT_FROM, TT_IMPORT):
            # Return the import so it can be collected for polyglot code
            imp = self.parse_import()
            if imp is not None:
                return imp
            return PassStmt()

        # Assignment or expression
        return self.parse_assignment_or_expr()

    def parse_block(self) -> List[ASTNode]:
        """Parse an indented block of statements."""
        statements = []
        block_indent = None

        while True:
            self.skip_newlines()
            token = self.current_token()

            if token.type == TT_EOF:
                break

            # Stop at these keywords at base level (but not inside try blocks)
            # EXCEPT and FINALLY handled by try/except parsing
            if token.type in [TT_ELIF, TT_ELSE, TT_EXCEPT, TT_FINALLY]:
                break

            if block_indent is None:
                block_indent = token.col
            elif token.col < block_indent and len(statements) > 0:
                break

            # Handle class and def inside blocks (e.g., in try blocks)
            if token.type == TT_CLASS:
                # Parse class as a statement (skip it for try blocks)
                result = self.parse_class([])
                if isinstance(result, tuple):
                    struct, class_methods = result
                    statements.append(struct)
                    statements.extend(class_methods)
                else:
                    statements.append(result)
            elif token.type == TT_DEF:
                statements.append(self.parse_def([]))
            else:
                stmt = self.parse_statement()
                statements.append(stmt)
            self.skip_newlines()

        return statements

    def parse_decorator(self) -> str:
        """Parse a decorator: @name or @name(args)"""
        self.expect(TT_AT)
        # Decorator name can be IDENT or a keyword like DATACLASS, PROPERTY
        token = self.current_token()
        if token.type == TT_IDENT:
            name = token.value
            self.advance()
        elif token.type == TT_DATACLASS:
            name = 'dataclass'
            self.advance()
        elif token.type == TT_PROPERTY:
            name = 'property'
            self.advance()
        else:
            raise SyntaxError(f"Expected decorator name, got {token.type} at line {token.line}")

        args = None
        if self.current_token().type == TT_LPAREN:
            self.advance()
            args = []
            if self.current_token().type != TT_RPAREN:
                args.append(self.parse_expression())
                while self.current_token().type == TT_COMMA:
                    self.advance()
                    args.append(self.parse_expression())
            self.expect(TT_RPAREN)

        return (name, args)

    def parse_def(self, decorators=None) -> ProcDecl:
        """Parse function definition: def name(params) -> ReturnType:"""
        self.advance()  # Skip 'def'

        name = self.expect(TT_IDENT).value

        # Parse optional generic type parameters: def foo[T, U](...)
        type_params = []
        if self.current_token().type == TT_LBRACKET:
            self.advance()
            if self.current_token().type != TT_RBRACKET:
                type_name = self.expect(TT_IDENT).value
                type_params.append(GenericType(name=type_name))

                while self.current_token().type == TT_COMMA:
                    self.advance()
                    type_name = self.expect(TT_IDENT).value
                    type_params.append(GenericType(name=type_name))

            self.expect(TT_RBRACKET)

        self.expect(TT_LPAREN)

        # Parse parameters
        params: List[Parameter] = []
        self.skip_newlines()
        while self.current_token().type != TT_RPAREN:
            # Handle *args and **kwargs (skip them)
            cur_type = self.current_token().type
            if cur_type == TT_STAR or cur_type == TT_DOUBLE_STAR:
                self.advance()
                if self.current_token().type == TT_STAR:
                    self.advance()  # ** as two stars
                if self.current_token().type == TT_IDENT:
                    self.advance()  # Skip the parameter name
                # Skip comma if present
                if self.current_token().type == TT_COMMA:
                    self.advance()
                self.skip_newlines()
                continue

            # Parse parameter: name: Type = default or name = default
            param_name = self.expect(TT_IDENT).value
            param_type = None
            default_value = None
            if self.current_token().type == TT_COLON:
                self.advance()
                param_type = self.parse_type()
            if self.current_token().type == TT_EQUALS:
                self.advance()
                default_value = self.parse_expression()
            params.append(Parameter(param_name, param_type, default_value))

            if self.current_token().type == TT_COMMA:
                self.advance()
                self.skip_newlines()
            else:
                break

        self.skip_newlines()
        self.expect(TT_RPAREN)

        # Parse return type: -> Type or : Type (for proc syntax)
        return_type = None
        if self.current_token().type == TT_ARROW:
            self.advance()
            return_type = self.parse_type()
            self.expect(TT_COLON)
        elif self.current_token().type == TT_EQUALS:
            # proc syntax with no return type: name() = body
            self.advance()  # Skip '='
        elif self.current_token().type == TT_COLON:
            # Could be Python-style body start OR proc-style return type
            self.advance()
            next_tok = self.current_token().type
            # If next token is a type keyword, it's a return type
            if is_type_keyword(next_tok) == 1 or next_tok == TT_IDENT:
                return_type = self.parse_type()
                # Expect = for proc syntax
                if self.current_token().type == TT_EQUALS:
                    # proc syntax: name(): Type = body
                    self.advance()  # Skip '='

        self.skip_newlines()

        # Parse body
        body = self.parse_block()

        # Check for @inline decorator
        is_inline = False
        if decorators:
            for dec_name, dec_args in decorators:
                if dec_name == 'inline':
                    is_inline = True

        return ProcDecl(name, params, return_type, body, is_inline=is_inline, type_params=type_params)

    def _infer_type_from_expr(self, expr: ASTNode, param_types) -> Type:
        """Infer type from an expression (helper for _infer_fields_from_init)."""
        if isinstance(expr, IntLiteral):
            return Type('int32')
        if isinstance(expr, BoolLiteral):
            return Type('bool')
        if isinstance(expr, StringLiteral):
            return PointerType(Type('uint8'))
        if isinstance(expr, FStringLiteral):
            return PointerType(Type('uint8'))
        if isinstance(expr, CharLiteral):
            return Type('char')
        if isinstance(expr, ArrayLiteral):
            return Type('any')
        if isinstance(expr, DictLiteral):
            return Type('any')
        if isinstance(expr, Identifier):
            if expr.name in param_types:
                if param_types[expr.name] is not None:
                    return param_types[expr.name]
            return Type('any')
        if isinstance(expr, NoneLiteral):
            return Type('any')
        return Type('any')

    def _scan_body_for_fields(self, stmts, existing_names, seen_fields, param_types, inferred_fields):
        """Scan statement body for self.field assignments (helper for _infer_fields_from_init)."""
        for stmt in stmts:
            if isinstance(stmt, Assignment):
                if isinstance(stmt.target, FieldAccessExpr):
                    if isinstance(stmt.target.object, Identifier):
                        if stmt.target.object.name == 'self':
                            field_name: str = stmt.target.field_name
                            if field_name not in existing_names:
                                if field_name not in seen_fields:
                                    # Use explicit type hint if present, otherwise infer from value
                                    if hasattr(stmt, 'type_hint') and stmt.type_hint is not None:
                                        field_type: Type = stmt.type_hint
                                    else:
                                        field_type: Type = self._infer_type_from_expr(stmt.value, param_types)
                                    inferred_fields.append(StructField(field_name, field_type, None))
                                    seen_fields.add(field_name)
            if isinstance(stmt, IfStmt):
                self._scan_body_for_fields(stmt.then_block, existing_names, seen_fields, param_types, inferred_fields)
                if stmt.else_block:
                    self._scan_body_for_fields(stmt.else_block, existing_names, seen_fields, param_types, inferred_fields)
            if isinstance(stmt, WhileStmt):
                self._scan_body_for_fields(stmt.body, existing_names, seen_fields, param_types, inferred_fields)
            if isinstance(stmt, ForStmt):
                self._scan_body_for_fields(stmt.body, existing_names, seen_fields, param_types, inferred_fields)
            if isinstance(stmt, ForEachStmt):
                self._scan_body_for_fields(stmt.body, existing_names, seen_fields, param_types, inferred_fields)

    def _infer_fields_from_init(self, methods, existing_fields):
        """Infer class fields from self.field = value assignments in __init__."""
        init_method = None
        for m in methods:
            if m.name == '__init__':
                init_method = m
                break

        if init_method is None:
            return []

        param_types = {}
        for param in init_method.params:
            param_types[param.name] = param.param_type

        existing_names = set()
        for f in existing_fields:
            existing_names.add(f.name)

        inferred_fields = []
        seen_fields = set()

        self._scan_body_for_fields(init_method.body, existing_names, seen_fields, param_types, inferred_fields)
        return inferred_fields

    def parse_class(self, decorators=None) -> StructDecl:
        """Parse class definition.

        class Name:
            field: Type
            field2: Type = default

            def method(self, ...):
                ...
        """
        self.advance()  # Skip 'class'

        name = self.expect(TT_IDENT).value

        # Check for inheritance or Enum
        parent = None
        is_enum = False
        if self.current_token().type == TT_LPAREN:
            self.advance()
            # Parent can be IDENT or the ENUM keyword (for 'class Foo(Enum):')
            if self.current_token().type == TT_ENUM:
                self.advance()
                is_enum = True
            else:
                parent_name = self.expect(TT_IDENT).value
                if parent_name == 'Enum':
                    is_enum = True
                else:
                    parent = parent_name
            self.expect(TT_RPAREN)

        self.expect(TT_COLON)
        self.skip_newlines()

        if is_enum:
            return self.parse_enum_body(name, decorators)

        # Parse class body
        fields = []
        methods = []
        block_indent = None

        while True:
            self.skip_newlines()
            token = self.current_token()

            if token.type == TT_EOF:
                break

            if block_indent is None:
                block_indent = token.col
            elif token.col < block_indent:
                break

            # Parse decorators
            inner_decorators = []
            while token.type == TT_AT:
                inner_decorators.append(self.parse_decorator())
                self.skip_newlines()
                token = self.current_token()

            # Method definition
            if token.type == TT_DEF:
                method = self.parse_method(name, inner_decorators)
                methods.append(method)
            # Pass statement
            elif token.type == TT_PASS:
                self.advance()
            # Docstring - skip it
            elif token.type == TT_STRING:
                self.advance()
            # Field definition: name: Type or name: Type = default
            # Or class variable: name = value (no type annotation)
            # Keywords can also be field names (e.g., 'var: str' in Python classes)
            elif token.type == TT_IDENT or self.peek_token().type == TT_COLON:
                # Get field name - use token.value for IDENT, or keyword name for keywords
                if token.type == TT_IDENT:
                    field_name = token.value
                else:
                    # It's a keyword being used as a field name
                    field_name = keyword_name_from_type(token.type)
                self.advance()

                if self.current_token().type == TT_COLON:
                    # Typed field: name: Type = default
                    self.advance()
                    field_type = self.parse_type()
                    default_value = None
                    if self.current_token().type == TT_EQUALS:
                        self.advance()
                        default_value = self.parse_expression()
                    fields.append(StructField(field_name, field_type, default_value))
                elif self.current_token().type == TT_EQUALS:
                    # Untyped class variable: name = value (skip it)
                    self.advance()
                    self.parse_expression()
                    # Don't add to fields - this is just a class-level constant
                else:
                    # Just an identifier, skip it
                    pass
            else:
                break

        # Infer fields from __init__ self.field = value assignments (Python-style)
        inferred_fields = self._infer_fields_from_init(methods, fields)
        fields.extend(inferred_fields)

        struct = StructDecl(name, fields)

        # Handle decorators like @packed, @dataclass (no-op)
        if decorators:
            for dec_name, dec_args in decorators:
                if dec_name == 'packed':
                    struct.is_packed = True
                # @dataclass is a no-op in BH - classes already work like dataclasses
                elif dec_name == 'dataclass':
                    pass

        return struct, methods

    def parse_method(self, class_name: str, decorators=None) -> MethodDecl:
        """Parse method definition inside a class."""
        self.advance()  # Skip 'def'

        # Method name can be an identifier or a keyword (Python allows 'match' as method name)
        token = self.current_token()
        if token.type == TT_IDENT:
            method_name = token.value
            self.advance()
        elif get_keyword_name(token.type) != "":
            # Allow keywords as method names (match, etc.)
            method_name = get_keyword_name(token.type)
            self.advance()
        else:
            raise SyntaxError(f"Expected method name, got {token.type} at line {token.line}")

        self.expect(TT_LPAREN)

        # First parameter should be 'self'
        params = []
        receiver_name = None
        receiver_type = None

        if self.current_token().type != TT_RPAREN:
            first_param = self.expect(TT_IDENT).value
            if first_param == 'self':
                receiver_name = 'self'
                receiver_type = PointerType(Type(class_name))

                if self.current_token().type == TT_COMMA:
                    self.advance()
            else:
                # First param isn't self - could be a static method
                param_type = None
                if self.current_token().type == TT_COLON:
                    self.advance()
                    param_type = self.parse_type()
                params.append(Parameter(first_param, param_type))

            # Parse remaining parameters
            while self.current_token().type != TT_RPAREN:
                if self.current_token().type == TT_COMMA:
                    self.advance()
                    self.skip_newlines()  # Handle multi-line parameters
                if self.current_token().type == TT_RPAREN:
                    break

                # Handle *args and **kwargs (variadic parameters)
                cur_type = self.current_token().type
                if cur_type == TT_STAR or cur_type == TT_DOUBLE_STAR:
                    self.advance()
                    if self.current_token().type == TT_STAR:
                        self.advance()  # ** as two stars
                    if self.current_token().type == TT_IDENT:
                        self.advance()  # Skip the parameter name
                    continue

                param_name = self.expect(TT_IDENT).value
                param_type = None
                default_value = None
                if self.current_token().type == TT_COLON:
                    self.advance()
                    param_type = self.parse_type()
                if self.current_token().type == TT_EQUALS:
                    self.advance()
                    default_value = self.parse_expression()
                params.append(Parameter(param_name, param_type, default_value))

        self.expect(TT_RPAREN)

        # Return type
        return_type = None
        if self.current_token().type == TT_ARROW:
            self.advance()
            return_type = self.parse_type()

        self.expect(TT_COLON)
        self.skip_newlines()

        body = self.parse_block()

        if receiver_name:
            return MethodDecl(receiver_type, receiver_name, method_name, params, return_type, body)
        else:
            # Static method - treat as regular function
            return ProcDecl(f"{class_name}_{method_name}", params, return_type, body)

    def parse_enum_body(self, name: str, decorators=None) -> EnumDecl:
        """Parse enum body after 'class Name(Enum):'

        Supports both Brainhair-style and Python-style enums:

        Brainhair-style:
            class MyEnum(Enum):
                Variant1
                Variant2(Type)

        Python-style:
            class MyEnum(Enum):
                VARIANT1 = auto()
                VARIANT2 = 1
        """
        variants = []
        block_indent = None
        auto_value = 0

        while True:
            self.skip_newlines()
            token = self.current_token()

            if token.type == TT_EOF:
                break

            if block_indent is None:
                block_indent = token.col
            elif token.col < block_indent:
                break

            if token.type == TT_PASS:
                self.advance()
                continue

            # Parse variant: Name or Name(Type1, Type2, ...) or Name = auto() or Name = value
            # For Python compatibility, allow keywords as enum variant names (like DEF, CLASS, etc.)
            token = self.current_token()
            if token.type == TT_IDENT:
                variant_name = token.value
                self.advance()
            else:
                # Try to use the token value as variant name for keyword tokens
                if hasattr(token, 'value') and token.value:
                    variant_name = token.value
                    self.advance()
                else:
                    raise SyntaxError(f"Expected enum variant name, got {token.type} at line {token.line}")
            payload_types = []

            # Python-style: NAME = auto() or NAME = value
            if self.current_token().type == TT_EQUALS:
                self.advance()
                # Check for auto() - can be AUTO token or IDENT with value 'auto'
                cur = self.current_token()
                if cur.type == TT_AUTO or (cur.type == TT_IDENT and cur.value == 'auto'):
                    self.advance()
                    self.expect(TT_LPAREN)
                    self.expect(TT_RPAREN)
                    # auto() just increments, no payload
                    auto_value += 1
                elif self.current_token().type == TT_NUMBER:
                    # Explicit value - skip it, BH enums are just sequential
                    self.advance()
                    auto_value += 1
                else:
                    # Some other expression, just parse and ignore
                    self.parse_expression()
                    auto_value += 1
            # Brainhair-style: Name(Type1, Type2, ...)
            elif self.current_token().type == TT_LPAREN:
                self.advance()
                if self.current_token().type != TT_RPAREN:
                    payload_types.append(self.parse_type())
                    while self.current_token().type == TT_COMMA:
                        self.advance()
                        payload_types.append(self.parse_type())
                self.expect(TT_RPAREN)

            variants.append(EnumVariant(variant_name, payload_types))

        return EnumDecl(name, variants)

    def parse_extern_decl(self):
        """Parse extern declaration: extern def func(params) -> Type OR extern name: Type"""
        self.advance()  # Skip 'extern'

        # Check for 'def' or 'proc' keyword (function declaration)
        token = self.current_token()
        if token.type == TT_DEF or (token.type == TT_IDENT and token.value == 'proc'):
            self.advance()  # Skip 'def' or 'proc'
            name = self.expect(TT_IDENT).value
            self.expect(TT_LPAREN)
        else:
            # Could be variable or function
            name = self.expect(TT_IDENT).value

            # Check if it's a variable declaration (name: Type)
            if self.current_token().type == TT_COLON:
                self.advance()  # Skip ':'
                var_type = self.parse_type()
                # Return as VarDecl with is_extern flag (or ExternVarDecl)
                return VarDecl(name, var_type, None, is_const=False, is_extern=True)

            # Otherwise it's a function declaration
            self.expect(TT_LPAREN)

        params = []
        if self.current_token().type != TT_RPAREN:
            param_name = self.expect(TT_IDENT).value
            self.expect(TT_COLON)
            param_type = self.parse_type()
            params.append(Parameter(param_name, param_type))

            while self.current_token().type == TT_COMMA:
                self.advance()
                param_name = self.expect(TT_IDENT).value
                self.expect(TT_COLON)
                param_type = self.parse_type()
                params.append(Parameter(param_name, param_type))

        self.expect(TT_RPAREN)

        return_type = None
        # Accept both -> Type and : Type for return type (for Brainhair-native syntax)
        if self.current_token().type == TT_ARROW or self.current_token().type == TT_COLON:
            self.advance()
            return_type = self.parse_type()

        return ExternDecl(name, params, return_type)

    def parse_import(self) -> ImportDecl:
        """Parse import statements.

        Supports:
        - from lib.syscalls import *
        - from lib.syscalls import func1, func2
        - import lib.math
        - import lib.math as m

        Python stdlib imports (typing, enum, dataclasses) are skipped.
        """
        if self.current_token().type == TT_FROM:
            self.advance()

            # Parse module path: lib.syscalls -> lib/syscalls
            first_part = self.expect(TT_IDENT).value

            # Skip Python stdlib imports
            if first_part in ('typing', 'enum', 'dataclasses', 'copy', 'sys', 'os', 'pathlib', 'subprocess'):
                # Skip the rest of the import statement
                while self.current_token().type not in (TT_NEWLINE, TT_EOF):
                    self.advance()
                return None  # Signal to skip this import

            path_parts = [first_part]
            while self.current_token().type == TT_DOT:
                self.advance()
                path_parts.append(self.expect(TT_IDENT).value)

            path = join_paths(path_parts)

            self.expect(TT_IMPORT)

            # Parse imported names (supports 'as' aliases: from X import Y as Z)
            names = []
            if self.current_token().type == TT_STAR:
                self.advance()
                names = ['*']
            else:
                name = self.expect(TT_IDENT).value
                # Skip 'as alias' if present
                if self.current_token().type == TT_AS:
                    self.advance()
                    self.expect(TT_IDENT)  # Skip the alias
                names.append(name)
                while self.current_token().type == TT_COMMA:
                    self.advance()
                    name = self.expect(TT_IDENT).value
                    if self.current_token().type == TT_AS:
                        self.advance()
                        self.expect(TT_IDENT)  # Skip the alias
                    names.append(name)

            return ImportDecl(path, import_names=names)

        else:
            self.advance()  # Skip 'import'

            # Parse module path
            first_part = self.expect(TT_IDENT).value

            # Skip Python stdlib imports
            if first_part in ('typing', 'enum', 'dataclasses', 'copy', 'sys', 'os', 'pathlib', 'subprocess'):
                while self.current_token().type not in (TT_NEWLINE, TT_EOF):
                    self.advance()
                return None

            path_parts = [first_part]
            while self.current_token().type == TT_DOT:
                self.advance()
                path_parts.append(self.expect(TT_IDENT).value)

            path = join_paths(path_parts)

            alias = None
            if self.current_token().type == TT_AS:
                self.advance()
                alias = self.expect(TT_IDENT).value

            return ImportDecl(path, alias)

    def parse(self) -> Program:
        imports = []
        declarations = []
        methods = []  # Collect methods from classes

        self.skip_newlines()

        # Skip module docstring (string literal at start of file)
        if self.current_token().type == TT_STRING:
            self.advance()
            self.skip_newlines()

        # Parse imports first (imports can be interspersed with docstrings/comments)
        while self.match(TT_FROM, TT_IMPORT):
            imp = self.parse_import()
            if imp is not None:  # Skip Python stdlib imports
                imports.append(imp)
            self.skip_newlines()

        # Parse declarations
        while self.current_token().type != TT_EOF:
            # Allow imports anywhere in the file (Python compatibility)
            if self.match(TT_FROM, TT_IMPORT):
                imp = self.parse_import()
                if imp is not None:
                    imports.append(imp)
                self.skip_newlines()
                continue
            # Parse decorators
            decorators = []
            while self.current_token().type == TT_AT:
                decorators.append(self.parse_decorator())
                self.skip_newlines()

            token = self.current_token()

            if token.type == TT_EXTERN:
                declarations.append(self.parse_extern_decl())
            elif token.type == TT_CONST:
                # Top-level constant declaration
                declarations.append(self.parse_const_stmt())
            elif token.type == TT_DEF or (token.type == TT_IDENT and token.value == 'proc'):
                declarations.append(self.parse_def(decorators))
            elif token.type == TT_CLASS:
                result = self.parse_class(decorators)
                if isinstance(result, tuple):
                    struct, class_methods = result
                    declarations.append(struct)
                    methods.extend(class_methods)
                else:
                    declarations.append(result)
            elif token.type == TT_IDENT:
                # Top-level variable with type annotation
                if self.peek_token().type == TT_COLON:
                    declarations.append(self.parse_annotated_assignment())
                else:
                    declarations.append(self.parse_statement())
            else:
                declarations.append(self.parse_statement())

            self.skip_newlines()

        # Add methods to declarations
        declarations.extend(methods)

        # Extract imports from TryExceptStmt bodies (for polyglot code)
        def extract_imports_from_stmt(stmt):
            extracted = []
            if hasattr(stmt, 'try_body'):
                for s in stmt.try_body:
                    if isinstance(s, ImportDecl):
                        extracted.append(s)
                    else:
                        extracted.extend(extract_imports_from_stmt(s))
            if hasattr(stmt, 'except_body'):
                for s in stmt.except_body:
                    if isinstance(s, ImportDecl):
                        extracted.append(s)
                    else:
                        extracted.extend(extract_imports_from_stmt(s))
            return extracted

        for decl in declarations:
            imports.extend(extract_imports_from_stmt(decl))

        return Program(declarations, imports)


# Test the parser
if __name__ == '__main__':
    code = """
from lib.syscalls import *

SYS_EXIT: Final[int32] = 1

@inline
def add(a: int32, b: int32) -> int32:
    return a + b

class Point:
    x: int32
    y: int32

    def move(self, dx: int32):
        self.x += dx

class Option(Enum):
    Some(int32)
    None

def main() -> int32:
    p: Ptr[int32] = Ptr[int32](0xB8000)
    p[0] = 0x0F41

    for i in range(10):
        print_int(i)

    return 0
"""

    lexer = Lexer(code)
    tokens = lexer.tokenize()

    parser = Parser(tokens)
    ast = parser.parse()

    print("AST:")
    print(f"Imports: {len(ast.imports)}")
    for imp in ast.imports:
        print(f"  {imp}")

    print(f"Declarations: {len(ast.declarations)}")
    for decl in ast.declarations:
        print(f"  {decl}")
