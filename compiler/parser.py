#!/usr/bin/env python3
"""
Brainhair Parser - Python Syntax Edition

Builds AST from tokens using Python-style syntax.
"""

from typing import List, Optional, Dict
from lexer import Token, TokenType, Lexer
from ast_nodes import *

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
        while self.current_token().type == TokenType.NEWLINE:
            self.advance()

    def match(self, *types) -> bool:
        """Check if current token matches any of the given types."""
        return self.current_token().type in types

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
        if token.type == TokenType.STRING:
            type_name = token.value
            self.advance()
            return Type(type_name)

        # Basic primitive types
        basic_types = {
            TokenType.INT8: 'int8',
            TokenType.INT16: 'int16',
            TokenType.INT32: 'int32',
            TokenType.INT64: 'int64',
            TokenType.UINT8: 'uint8',
            TokenType.UINT16: 'uint16',
            TokenType.UINT32: 'uint32',
            TokenType.UINT64: 'uint64',
            TokenType.FLOAT32: 'float32',
            TokenType.FLOAT64: 'float64',
            TokenType.BOOL: 'bool',
            TokenType.CHAR: 'char',
            TokenType.STR: 'str',
            TokenType.BYTES: 'bytes',
            TokenType.INT: 'int32',  # int is alias for int32
            TokenType.FLOAT: 'float32',  # float is alias for float32
        }

        if token.type in basic_types:
            type_name = basic_types[token.type]
            self.advance()
            return Type(type_name)

        # Ptr[T] - pointer type
        if token.type == TokenType.PTR:
            self.advance()
            self.expect(TokenType.LBRACKET)
            base_type = self.parse_type()
            self.expect(TokenType.RBRACKET)
            return PointerType(base_type)

        # List[T] - dynamic list
        if token.type == TokenType.LIST:
            self.advance()
            self.expect(TokenType.LBRACKET)
            element_type = self.parse_type()
            self.expect(TokenType.RBRACKET)
            return ListType(element_type)

        # Dict[K, V] - hash map
        if token.type == TokenType.DICT:
            self.advance()
            self.expect(TokenType.LBRACKET)
            key_type = self.parse_type()
            self.expect(TokenType.COMMA)
            value_type = self.parse_type()
            self.expect(TokenType.RBRACKET)
            return DictType(key_type, value_type)

        # Optional[T]
        if token.type == TokenType.OPTIONAL:
            self.advance()
            self.expect(TokenType.LBRACKET)
            inner_type = self.parse_type()
            self.expect(TokenType.RBRACKET)
            return GenericInstanceType('Optional', [inner_type])

        # Tuple[A, B, ...]
        if token.type == TokenType.TUPLE:
            self.advance()
            self.expect(TokenType.LBRACKET)
            types = [self.parse_type()]
            while self.current_token().type == TokenType.COMMA:
                self.advance()
                types.append(self.parse_type())
            self.expect(TokenType.RBRACKET)
            return GenericInstanceType('Tuple', types)

        # Final[T] - constant type (for type annotation only)
        if token.type == TokenType.FINAL:
            self.advance()
            self.expect(TokenType.LBRACKET)
            inner_type = self.parse_type()
            self.expect(TokenType.RBRACKET)
            return inner_type  # Final is handled at declaration level

        # Legacy slice type: []T
        if token.type == TokenType.LBRACKET:
            self.advance()
            self.expect(TokenType.RBRACKET)
            element_type = self.parse_type()
            return SliceType(element_type)

        # User-defined type (identifier) - could be struct name or generic
        if token.type == TokenType.IDENT:
            type_name = token.value
            self.advance()

            # Special case: Array[N, T] where N is a number
            if type_name == 'Array' and self.current_token().type == TokenType.LBRACKET:
                self.advance()  # Skip '['
                size = self.expect(TokenType.NUMBER).value
                self.expect(TokenType.COMMA)
                element_type = self.parse_type()
                self.expect(TokenType.RBRACKET)
                return ArrayType(size, element_type)

            # Check for generic instantiation: Type[Args]
            if self.current_token().type == TokenType.LBRACKET:
                self.advance()
                type_args = [self.parse_type()]
                while self.current_token().type == TokenType.COMMA:
                    self.advance()
                    type_args.append(self.parse_type())
                self.expect(TokenType.RBRACKET)
                return GenericInstanceType(type_name, type_args)

            return Type(type_name)

        raise SyntaxError(f"Expected type, got {token.type} at line {token.line}")

    # Expression parsing (with precedence)
    def parse_atom(self) -> ASTNode:
        """Parse atomic expressions (literals, identifiers, parenthesized exprs)"""
        token = self.current_token()

        # Literals
        if token.type == TokenType.NUMBER:
            self.advance()
            return IntLiteral(token.value)

        if token.type == TokenType.CHAR_LIT:
            self.advance()
            return CharLiteral(token.value)

        if token.type == TokenType.STRING:
            self.advance()
            return StringLiteral(token.value)

        if token.type == TokenType.FSTRING:
            self.advance()
            return FStringLiteral(token.value)

        if token.type == TokenType.TRUE:
            self.advance()
            return BoolLiteral(True)

        if token.type == TokenType.FALSE:
            self.advance()
            return BoolLiteral(False)

        if token.type == TokenType.NONE:
            self.advance()
            return NoneLiteral()

        # List/array literal: [1, 2, 3] or list comprehension: [expr for x in iterable]
        if token.type == TokenType.LBRACKET:
            self.advance()
            self.skip_newlines()
            elements = []

            if self.current_token().type != TokenType.RBRACKET:
                first_expr = self.parse_expression()

                # Check for list comprehension: [expr for var in iterable]
                if self.current_token().type == TokenType.FOR:
                    self.advance()  # skip 'for'
                    var_name = self.expect(TokenType.IDENT).value
                    self.expect(TokenType.IN)
                    iterable = self.parse_expression()
                    self.skip_newlines()
                    self.expect(TokenType.RBRACKET)
                    # Return as ForEachStmt wrapped in special node, or just return empty for now
                    # For compilation, we'll treat this as runtime loop - return placeholder
                    return ArrayLiteral([])  # TODO: proper list comprehension support

                elements.append(first_expr)
                while self.current_token().type == TokenType.COMMA:
                    self.advance()
                    self.skip_newlines()
                    if self.current_token().type == TokenType.RBRACKET:
                        break
                    elements.append(self.parse_expression())

            self.skip_newlines()
            self.expect(TokenType.RBRACKET)
            return ArrayLiteral(elements)

        # Dict literal: {key: value, ...} or set comprehension: {expr for x in iterable}
        if token.type == TokenType.LBRACE:
            self.advance()
            self.skip_newlines()
            pairs = []

            if self.current_token().type != TokenType.RBRACE:
                first_expr = self.parse_expression()

                # Check for set comprehension: {expr for var in iterable}
                if self.current_token().type == TokenType.FOR:
                    self.advance()  # skip 'for'
                    var_name = self.expect(TokenType.IDENT).value
                    self.expect(TokenType.IN)
                    iterable = self.parse_expression()
                    self.skip_newlines()
                    self.expect(TokenType.RBRACE)
                    # Return empty set/dict as placeholder for now
                    return DictLiteral([])  # TODO: proper set comprehension support

                # It's a dict literal - expect colon
                self.expect(TokenType.COLON)
                value = self.parse_expression()
                pairs.append((first_expr, value))

                while self.current_token().type == TokenType.COMMA:
                    self.advance()
                    self.skip_newlines()
                    if self.current_token().type == TokenType.RBRACE:
                        break
                    key = self.parse_expression()
                    self.expect(TokenType.COLON)
                    value = self.parse_expression()
                    pairs.append((key, value))

            self.skip_newlines()
            self.expect(TokenType.RBRACE)
            return DictLiteral(pairs)

        # Ptr[T](value) - pointer cast/construction
        if token.type == TokenType.PTR:
            self.advance()
            self.expect(TokenType.LBRACKET)
            target_type = self.parse_type()
            self.expect(TokenType.RBRACKET)
            self.expect(TokenType.LPAREN)
            expr = self.parse_expression()
            self.expect(TokenType.RPAREN)
            return CastExpr(PointerType(target_type), expr)

        # Identifier or function call
        if token.type == TokenType.IDENT:
            name = token.value
            self.advance()
            return Identifier(name)

        # Keywords used as identifiers (when not followed by their special syntax)
        # This handles cases like: asm = [], match = {}, etc.
        keyword_as_ident = [TokenType.ASM, TokenType.MATCH, TokenType.DEFER]
        if token.type in keyword_as_ident:
            name = token.type.name.lower()
            self.advance()
            return Identifier(name)

        # Parenthesized expression or tuple
        if token.type == TokenType.LPAREN:
            self.advance()
            self.skip_newlines()

            # Empty tuple
            if self.current_token().type == TokenType.RPAREN:
                self.advance()
                return TupleLiteral([])

            expr = self.parse_expression()

            # Check if it's a tuple
            if self.current_token().type == TokenType.COMMA:
                elements = [expr]
                while self.current_token().type == TokenType.COMMA:
                    self.advance()
                    self.skip_newlines()
                    if self.current_token().type == TokenType.RPAREN:
                        break
                    elements.append(self.parse_expression())
                self.expect(TokenType.RPAREN)
                return TupleLiteral(elements)

            self.expect(TokenType.RPAREN)
            return expr

        # Unary operators
        if token.type == TokenType.MINUS:
            self.advance()
            return UnaryExpr(UnaryOp.NEG, self.parse_unary())

        if token.type == TokenType.NOT:
            self.advance()
            return UnaryExpr(UnaryOp.NOT, self.parse_unary())

        if token.type == TokenType.TILDE:
            self.advance()
            return UnaryExpr(UnaryOp.BIT_NOT, self.parse_unary())

        raise SyntaxError(f"Unexpected token {token.type} at line {token.line}")

    def parse_unary(self) -> ASTNode:
        """Parse unary expressions."""
        token = self.current_token()

        if token.type == TokenType.MINUS:
            self.advance()
            return UnaryExpr(UnaryOp.NEG, self.parse_unary())

        if token.type == TokenType.NOT:
            self.advance()
            return UnaryExpr(UnaryOp.NOT, self.parse_unary())

        if token.type == TokenType.TILDE:
            self.advance()
            return UnaryExpr(UnaryOp.BIT_NOT, self.parse_unary())

        return self.parse_primary()

    def parse_primary(self) -> ASTNode:
        """Parse primary expressions with postfix operations."""
        token = self.current_token()

        # Lambda expression: lambda args: expr (parse and return None placeholder)
        if token.type == TokenType.LAMBDA:
            self.advance()
            # Skip parameters until colon
            while self.current_token().type != TokenType.COLON:
                self.advance()
            self.advance()  # Skip colon
            # Parse the lambda body expression
            self.parse_expression()
            # Return None as placeholder (lambdas not fully supported yet)
            return NoneLiteral()

        # addr(expr) - address-of (only if followed by LPAREN)
        is_addr = token.type == TokenType.IDENT and token.value == 'addr'
        if is_addr and self.peek_token().type == TokenType.LPAREN:
            self.advance()
            self.expect(TokenType.LPAREN)
            expr = self.parse_expression()
            self.expect(TokenType.RPAREN)
            return AddrOfExpr(expr)

        # cast[Type](expr) - type cast (only if followed by LBRACKET)
        is_cast = token.type == TokenType.IDENT and token.value == 'cast'
        if is_cast and self.peek_token().type == TokenType.LBRACKET:
            self.advance()
            self.expect(TokenType.LBRACKET)
            target_type = self.parse_type()
            self.expect(TokenType.RBRACKET)
            self.expect(TokenType.LPAREN)
            expr = self.parse_expression()
            self.expect(TokenType.RPAREN)
            return CastExpr(target_type, expr)

        # isinstance(expr, Type) - type check (Python compatibility)
        # Handle both keyword and identifier tokenization
        is_isinstance = token.type == TokenType.ISINSTANCE
        is_isinstance = is_isinstance or (token.type == TokenType.IDENT and token.value == 'isinstance')
        if is_isinstance and self.peek_token().type == TokenType.LPAREN:
            self.advance()
            self.expect(TokenType.LPAREN)
            expr = self.parse_expression()
            self.expect(TokenType.COMMA)
            # Parse the type - could be single name or tuple of types: (Type1, Type2)
            if self.current_token().type == TokenType.LPAREN:
                # Tuple of types - skip the whole tuple and use first type
                self.advance()  # skip (
                type_name = self.expect(TokenType.IDENT).value
                while self.current_token().type == TokenType.DOT:
                    self.advance()
                    type_name += '.' + self.expect(TokenType.IDENT).value
                # Skip remaining types in tuple
                while self.current_token().type == TokenType.COMMA:
                    self.advance()
                    self.expect(TokenType.IDENT)
                    while self.current_token().type == TokenType.DOT:
                        self.advance()
                        self.expect(TokenType.IDENT)
                self.expect(TokenType.RPAREN)  # close tuple
            else:
                # Single type name
                type_name = self.expect(TokenType.IDENT).value
                while self.current_token().type == TokenType.DOT:
                    self.advance()
                    type_name += '.' + self.expect(TokenType.IDENT).value
            self.expect(TokenType.RPAREN)
            return IsInstanceExpr(expr, type_name)

        # int(expr, base) or int(expr) - type conversions
        # Handle both when 'int' is a keyword (TokenType.INT) or identifier
        is_int_call = token.type == TokenType.INT or (token.type == TokenType.IDENT and token.value == 'int')
        if is_int_call and self.peek_token().type == TokenType.LPAREN:
            self.advance()
            self.expect(TokenType.LPAREN)
            args: List[ASTNode] = [self.parse_expression()]
            while self.current_token().type == TokenType.COMMA:
                self.advance()
                args.append(self.parse_expression())
            self.expect(TokenType.RPAREN)
            # For BH, int() is a cast to int32, ignore base argument
            return CastExpr(Type('int32'), args[0])

        # str(expr) - string conversion
        is_str_call = token.type == TokenType.STR or (token.type == TokenType.IDENT and token.value == 'str')
        if is_str_call and self.peek_token().type == TokenType.LPAREN:
            self.advance()
            self.expect(TokenType.LPAREN)
            expr = self.parse_expression()
            self.expect(TokenType.RPAREN)
            # Treat str() as a call for now
            return CallExpr('str', [expr])

        # len(expr) - length function (only if followed by parenthesis)
        is_len = token.type == TokenType.IDENT and token.value == 'len'
        if is_len and self.peek_token() and self.peek_token().type == TokenType.LPAREN:
            self.advance()
            self.expect(TokenType.LPAREN)
            expr = self.parse_expression()
            self.expect(TokenType.RPAREN)
            return CallExpr('len', [expr])

        # sizeof(Type) - size of type (only if followed by LPAREN)
        is_sizeof = token.type == TokenType.IDENT and token.value == 'sizeof'
        if is_sizeof and self.peek_token().type == TokenType.LPAREN:
            self.advance()
            self.expect(TokenType.LPAREN)
            target_type = self.parse_type()
            self.expect(TokenType.RPAREN)
            return SizeOfExpr(target_type)

        # range(start, end) - range function (only if followed by LPAREN)
        is_range = token.type == TokenType.IDENT and token.value == 'range'
        if is_range and self.peek_token().type == TokenType.LPAREN:
            self.advance()
            self.expect(TokenType.LPAREN)
            start = self.parse_expression()
            end = None
            step = None
            if self.current_token().type == TokenType.COMMA:
                self.advance()
                end = self.parse_expression()
                if self.current_token().type == TokenType.COMMA:
                    self.advance()
                    step = self.parse_expression()
            self.expect(TokenType.RPAREN)
            return RangeExpr(start, end, step)

        # asm("instruction") - inline assembly (only if followed by LPAREN)
        if token.type == TokenType.ASM and self.peek_token().type == TokenType.LPAREN:
            self.advance()
            self.expect(TokenType.LPAREN)
            asm_str = self.expect(TokenType.STRING).value
            self.expect(TokenType.RPAREN)
            return AsmExpr(asm_str)

        # match expression
        if token.type == TokenType.MATCH:
            return self.parse_match_expr()

        # Parse atom first
        expr = self.parse_atom()

        # Handle postfix operations
        while True:
            token = self.current_token()

            # Function call: expr(args) or generic call: expr[types](args)
            if token.type == TokenType.LPAREN:
                if isinstance(expr, Identifier):
                    # Check if previous was a struct literal pattern
                    saved_pos = self.pos
                    self.advance()  # Skip (
                    self.skip_newlines()

                    is_struct_literal = False
                    if self.current_token().type == TokenType.IDENT:
                        next_tok = self.peek_token()
                        if next_tok.type == TokenType.COLON:
                            is_struct_literal = True

                    self.pos = saved_pos

                    if is_struct_literal:
                        # Struct literal: Type(field: val, ...)
                        struct_name = expr.name
                        self.advance()  # Skip (
                        self.skip_newlines()
                        field_values = {}

                        if self.current_token().type != TokenType.RPAREN:
                            field_name = self.expect(TokenType.IDENT).value
                            self.expect(TokenType.COLON)
                            field_values[field_name] = self.parse_expression()

                            while self.current_token().type == TokenType.COMMA:
                                self.advance()
                                self.skip_newlines()
                                if self.current_token().type == TokenType.RPAREN:
                                    break
                                field_name = self.expect(TokenType.IDENT).value
                                self.expect(TokenType.COLON)
                                field_values[field_name] = self.parse_expression()

                        self.skip_newlines()
                        self.expect(TokenType.RPAREN)
                        expr = StructLiteral(struct_name, field_values)
                        continue

                # Regular function call
                self.advance()
                self.skip_newlines()
                args: List[ASTNode] = []

                while self.current_token().type != TokenType.RPAREN:
                    # Handle *args and **kwargs unpacking (skip them)
                    cur_type = self.current_token().type
                    if cur_type == TokenType.STAR or cur_type == TokenType.DOUBLE_STAR:
                        self.advance()
                        if self.current_token().type == TokenType.STAR:
                            self.advance()
                        # Parse the expression being unpacked
                        self.parse_expression()
                        if self.current_token().type == TokenType.COMMA:
                            self.advance()
                        self.skip_newlines()
                        continue

                    # Parse argument (handles keyword args and generator expressions)
                    arg_expr = self.parse_expression()

                    # Handle generator expression: expr for var in iterable [if cond]
                    if self.current_token().type == TokenType.FOR:
                        # Skip the generator expression, tracking nested parens
                        paren_depth = 1
                        while paren_depth > 0:
                            self.advance()
                            if self.current_token().type == TokenType.LPAREN:
                                paren_depth = paren_depth + 1
                            elif self.current_token().type == TokenType.RPAREN:
                                paren_depth = paren_depth - 1
                        # Return empty list as placeholder
                        args.append(ArrayLiteral([]))
                        break

                    if self.current_token().type == TokenType.EQUALS:
                        self.advance()
                        arg_expr = self.parse_expression()
                    args.append(arg_expr)
                    if self.current_token().type == TokenType.COMMA:
                        self.advance()
                        self.skip_newlines()
                    else:
                        break

                self.skip_newlines()
                self.expect(TokenType.RPAREN)

                if isinstance(expr, Identifier):
                    expr = CallExpr(expr.name, args)
                else:
                    raise SyntaxError(f"Cannot call non-identifier at line {token.line}")

            # Generic call: expr[types](args)
            elif token.type == TokenType.LBRACKET:
                if isinstance(expr, Identifier):
                    # Could be generic call or array indexing
                    saved_pos = self.pos
                    self.advance()

                    # Try to detect if this is a type list
                    type_keywords = set()
                    type_keywords.add(TokenType.INT8)
                    type_keywords.add(TokenType.INT16)
                    type_keywords.add(TokenType.INT32)
                    type_keywords.add(TokenType.INT64)
                    type_keywords.add(TokenType.UINT8)
                    type_keywords.add(TokenType.UINT16)
                    type_keywords.add(TokenType.UINT32)
                    type_keywords.add(TokenType.UINT64)
                    type_keywords.add(TokenType.BOOL)
                    type_keywords.add(TokenType.CHAR)
                    type_keywords.add(TokenType.PTR)
                    type_keywords.add(TokenType.LIST)
                    type_keywords.add(TokenType.DICT)
                    type_keywords.add(TokenType.OPTIONAL)
                    type_keywords.add(TokenType.TUPLE)
                    type_keywords.add(TokenType.INT)
                    type_keywords.add(TokenType.FLOAT)
                    type_keywords.add(TokenType.STR)
                    type_keywords.add(TokenType.BYTES)

                    first_tok = self.current_token().type
                    is_type_start = first_tok == TokenType.IDENT or first_tok in type_keywords

                    if is_type_start:
                        # Scan to see if followed by ]( pattern
                        scan_pos = self.pos
                        is_generic_call = False
                        while scan_pos < len(self.tokens):
                            tok = self.tokens[scan_pos]
                            if tok.type == TokenType.RBRACKET:
                                has_next = scan_pos + 1 < len(self.tokens)
                                if has_next and self.tokens[scan_pos + 1].type == TokenType.LPAREN:
                                    is_generic_call = True
                                break
                            elif tok.type in (TokenType.IDENT, TokenType.COMMA) or tok.type in type_keywords:
                                scan_pos += 1
                            else:
                                break

                        if is_generic_call:
                            # Parse as generic call
                            type_args = [self.parse_type()]
                            while self.current_token().type == TokenType.COMMA:
                                self.advance()
                                type_args.append(self.parse_type())
                            self.expect(TokenType.RBRACKET)
                            self.expect(TokenType.LPAREN)
                            self.skip_newlines()
                            args = []
                            if self.current_token().type != TokenType.RPAREN:
                                args.append(self.parse_expression())
                                while self.current_token().type == TokenType.COMMA:
                                    self.advance()
                                    self.skip_newlines()
                                    if self.current_token().type == TokenType.RPAREN:
                                        break
                                    args.append(self.parse_expression())
                            self.skip_newlines()
                            self.expect(TokenType.RPAREN)
                            expr = CallExpr(expr.name, args, type_args=type_args)
                            continue

                    # Restore position and treat as array indexing
                    self.pos = saved_pos

                # Array/pointer indexing or slicing
                self.advance()

                # Check for slice starting with : (e.g., [:4])
                if self.current_token().type == TokenType.COLON:
                    self.advance()
                    # Slice from beginning: [:end]
                    if self.current_token().type == TokenType.RBRACKET:
                        # [:] - full slice (return as-is for now)
                        self.advance()
                        expr = expr  # No change, just skip
                    else:
                        end = self.parse_expression()
                        self.expect(TokenType.RBRACKET)
                        expr = SliceExpr(expr, IntLiteral(0), end)
                else:
                    index = self.parse_expression()

                    # Check for slice: arr[start..end] or arr[start:end] or arr[start:]
                    if self.current_token().type == TokenType.DOTDOT:
                        self.advance()
                        end = self.parse_expression()
                        self.expect(TokenType.RBRACKET)
                        expr = SliceExpr(expr, index, end)
                    elif self.current_token().type == TokenType.COLON:
                        self.advance()
                        # Python-style slice: arr[start:end] or arr[start:]
                        if self.current_token().type == TokenType.RBRACKET:
                            # arr[start:] - slice to end (use large number as placeholder)
                            self.advance()
                            expr = SliceExpr(expr, index, IntLiteral(999999999))
                        else:
                            end = self.parse_expression()
                            self.expect(TokenType.RBRACKET)
                            expr = SliceExpr(expr, index, end)
                    else:
                        self.expect(TokenType.RBRACKET)
                        expr = IndexExpr(expr, index)

            # Field access or method call: expr.field or expr.method()
            elif token.type == TokenType.DOT:
                self.advance()
                # Field/method name can be IDENT or keyword (like 'match', 'type', etc.)
                tok = self.current_token()
                if tok.type == TokenType.IDENT:
                    field_name = tok.value
                    self.advance()
                elif tok.type.name.isupper():
                    field_name = tok.type.name.lower()
                    self.advance()
                else:
                    raise SyntaxError(f"Expected field name, got {tok.type} at line {tok.line}")

                if self.current_token().type == TokenType.LPAREN:
                    # Method call
                    self.advance()
                    args: List[ASTNode] = []

                    while self.current_token().type != TokenType.RPAREN:
                        # Handle *args and **kwargs unpacking (skip them)
                        cur_type = self.current_token().type
                        if cur_type == TokenType.STAR or cur_type == TokenType.DOUBLE_STAR:
                            self.advance()
                            if self.current_token().type == TokenType.STAR:
                                self.advance()
                            self.parse_expression()
                            if self.current_token().type == TokenType.COMMA:
                                self.advance()
                            continue

                        # Parse argument
                        arg_expr = self.parse_expression()

                        # Handle generator expression: expr for var in iterable [if cond]
                        if self.current_token().type == TokenType.FOR:
                            paren_depth = 1
                            while paren_depth > 0:
                                self.advance()
                                if self.current_token().type == TokenType.LPAREN:
                                    paren_depth = paren_depth + 1
                                elif self.current_token().type == TokenType.RPAREN:
                                    paren_depth = paren_depth - 1
                            args.append(ArrayLiteral([]))
                            break

                        if self.current_token().type == TokenType.EQUALS:
                            self.advance()
                            arg_expr = self.parse_expression()
                        args.append(arg_expr)
                        if self.current_token().type == TokenType.COMMA:
                            self.advance()
                        else:
                            break
                    self.expect(TokenType.RPAREN)
                    expr = MethodCallExpr(expr, field_name, args)
                else:
                    expr = FieldAccessExpr(expr, field_name)

            else:
                break

        return expr

    def parse_power(self) -> ASTNode:
        """Parse power expressions: a ** b (right associative)"""
        left = self.parse_unary()

        if self.current_token().type == TokenType.DOUBLE_STAR:
            self.advance()
            right = self.parse_power()  # Right associative
            left = BinaryExpr(left, BinOp.POW, right)

        return left

    def parse_multiplicative(self) -> ASTNode:
        left = self.parse_power()

        while self.match(TokenType.STAR, TokenType.SLASH, TokenType.DOUBLE_SLASH, TokenType.PERCENT):
            op_token = self.current_token()
            self.advance()

            op_map = {
                TokenType.STAR: BinOp.MUL,
                TokenType.SLASH: BinOp.DIV,
                TokenType.DOUBLE_SLASH: BinOp.IDIV,
                TokenType.PERCENT: BinOp.MOD,
            }
            op = op_map[op_token.type]
            right = self.parse_power()
            left = BinaryExpr(left, op, right)

        return left

    def parse_additive(self) -> ASTNode:
        left = self.parse_multiplicative()

        while self.match(TokenType.PLUS, TokenType.MINUS):
            op_token = self.current_token()
            self.advance()

            op = BinOp.ADD if op_token.type == TokenType.PLUS else BinOp.SUB
            right = self.parse_multiplicative()
            left = BinaryExpr(left, op, right)

        return left

    def parse_shift(self) -> ASTNode:
        left = self.parse_additive()

        while self.match(TokenType.SHL, TokenType.SHR):
            op_token = self.current_token()
            self.advance()

            op = BinOp.SHL if op_token.type == TokenType.SHL else BinOp.SHR
            right = self.parse_additive()
            left = BinaryExpr(left, op, right)

        return left

    def parse_bitwise_and(self) -> ASTNode:
        left = self.parse_shift()

        while self.current_token().type == TokenType.AMPERSAND:
            self.advance()
            right = self.parse_shift()
            left = BinaryExpr(left, BinOp.BIT_AND, right)

        return left

    def parse_bitwise_xor(self) -> ASTNode:
        left = self.parse_bitwise_and()

        while self.current_token().type == TokenType.CARET:
            self.advance()
            right = self.parse_bitwise_and()
            left = BinaryExpr(left, BinOp.BIT_XOR, right)

        return left

    def parse_bitwise_or(self) -> ASTNode:
        left = self.parse_bitwise_xor()

        while self.current_token().type == TokenType.PIPE:
            self.advance()
            right = self.parse_bitwise_xor()
            left = BinaryExpr(left, BinOp.BIT_OR, right)

        return left

    def parse_comparison(self) -> ASTNode:
        """Parse comparison with chaining support: a < b < c"""
        left = self.parse_bitwise_or()

        comp_tokens = {
            TokenType.EQUALS_EQUALS: BinOp.EQ,
            TokenType.NOT_EQUALS: BinOp.NEQ,
            TokenType.LESS: BinOp.LT,
            TokenType.LESS_EQUALS: BinOp.LTE,
            TokenType.GREATER: BinOp.GT,
            TokenType.GREATER_EQUALS: BinOp.GTE,
            TokenType.IS: BinOp.EQ,  # 'is' treated as equality for None checks
            TokenType.IS_NOT: BinOp.NEQ,  # 'is not' treated as inequality
            TokenType.IN: BinOp.IN,  # 'in' membership test
        }

        # Handle comparison chaining: 0 <= x < 100 -> (0 <= x) and (x < 100)
        comparisons = []
        while True:
            cur_type = self.current_token().type
            is_comp = cur_type in comp_tokens
            is_is_not = cur_type == TokenType.IS and self.peek_token().type == TokenType.NOT
            is_not_in = cur_type == TokenType.NOT and self.peek_token().type == TokenType.IN
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
            if self.current_token().type == TokenType.IS:
                self.advance()
                if self.current_token().type == TokenType.NOT:
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
        if self.current_token().type == TokenType.NOT:
            self.advance()
            return UnaryExpr(UnaryOp.NOT, self.parse_not())
        return self.parse_comparison()

    def parse_logical_and(self) -> ASTNode:
        left = self.parse_not()

        while self.current_token().type == TokenType.AND:
            self.advance()
            right = self.parse_not()
            left = BinaryExpr(left, BinOp.AND, right)

        return left

    def parse_logical_or(self) -> ASTNode:
        left = self.parse_logical_and()

        while self.current_token().type == TokenType.OR:
            self.advance()
            right = self.parse_logical_and()
            left = BinaryExpr(left, BinOp.OR, right)

        return left

    def parse_conditional_expr(self) -> ASTNode:
        """Parse conditional expressions: a if cond else b"""
        expr = self.parse_logical_or()

        # Python-style ternary: value if condition else other
        if self.current_token().type == TokenType.IF:
            self.advance()
            condition = self.parse_logical_or()
            self.expect(TokenType.ELSE)
            else_expr = self.parse_conditional_expr()
            return ConditionalExpr(condition, expr, else_expr)

        return expr

    def parse_expression(self) -> ASTNode:
        return self.parse_conditional_expr()

    def parse_match_expr(self) -> MatchExpr:
        """Parse match expression."""
        self.advance()  # Skip 'match'
        match_expr = self.parse_expression()
        self.expect(TokenType.COLON)
        self.skip_newlines()

        arms = []
        block_indent = None

        while True:
            self.skip_newlines()
            token = self.current_token()

            if token.type == TokenType.EOF:
                break

            if block_indent is None:
                block_indent = token.col
            elif token.col < block_indent:
                break

            # Parse pattern
            variant_name = self.expect(TokenType.IDENT).value
            bindings = []

            if self.current_token().type == TokenType.LPAREN:
                self.advance()
                if self.current_token().type != TokenType.RPAREN:
                    bindings.append(self.expect(TokenType.IDENT).value)
                    while self.current_token().type == TokenType.COMMA:
                        self.advance()
                        bindings.append(self.expect(TokenType.IDENT).value)
                self.expect(TokenType.RPAREN)

            pattern = Pattern(variant_name, bindings)

            self.expect(TokenType.COLON)
            self.skip_newlines()

            body = self.parse_block()
            arms.append(MatchArm(pattern, body))

        return MatchExpr(match_expr, arms)

    # Statement parsing

    def parse_var_decl(self, is_final: bool = False) -> VarDecl:
        """Parse variable declaration: name: Type = value or name = value"""
        name = self.expect(TokenType.IDENT).value
        self.expect(TokenType.COLON)

        # Check if type starts with Final[
        var_type = None
        if self.current_token().type == TokenType.FINAL:
            is_final = True
            self.advance()
            self.expect(TokenType.LBRACKET)
            var_type = self.parse_type()
            self.expect(TokenType.RBRACKET)
        else:
            var_type = self.parse_type()

        value = None
        if self.current_token().type == TokenType.EQUALS:
            self.advance()
            value = self.parse_expression()

        return VarDecl(name, var_type, value, is_const=is_final)

    def parse_assignment_or_expr(self) -> ASTNode:
        """Parse assignment (including compound) or expression statement."""
        expr = self.parse_expression()

        # Handle tuple unpacking: a, b = x, y (Python compatibility)
        if self.current_token().type == TokenType.COMMA:
            targets = [expr]
            while self.current_token().type == TokenType.COMMA:
                self.advance()
                targets.append(self.parse_expression())

            if self.current_token().type == TokenType.EQUALS:
                self.advance()
                # Parse the right side (could be a tuple)
                value = self.parse_expression()
                values = [value]
                while self.current_token().type == TokenType.COMMA:
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

        # Compound assignment operators
        compound_ops = {
            TokenType.PLUS_EQUALS: BinOp.ADD,
            TokenType.MINUS_EQUALS: BinOp.SUB,
            TokenType.STAR_EQUALS: BinOp.MUL,
            TokenType.SLASH_EQUALS: BinOp.DIV,
            TokenType.DOUBLE_SLASH_EQUALS: BinOp.IDIV,
            TokenType.PERCENT_EQUALS: BinOp.MOD,
            TokenType.AMPERSAND_EQUALS: BinOp.BIT_AND,
            TokenType.PIPE_EQUALS: BinOp.BIT_OR,
            TokenType.CARET_EQUALS: BinOp.BIT_XOR,
            TokenType.SHL_EQUALS: BinOp.SHL,
            TokenType.SHR_EQUALS: BinOp.SHR,
        }

        if self.current_token().type in compound_ops:
            op = compound_ops[self.current_token().type]
            self.advance()
            value = self.parse_expression()
            # Desugar x += y to x = x + y
            return Assignment(expr, BinaryExpr(expr, op, value))

        # Type-annotated assignment for expressions like self.field: Type = value
        if self.current_token().type == TokenType.COLON:
            self.advance()
            var_type = self.parse_type()
            if self.current_token().type == TokenType.EQUALS:
                self.advance()
                value = self.parse_expression()
                return Assignment(expr, value, type_hint=var_type)  # Preserve type annotation
            # Type annotation without assignment - treat as no-op
            return ExprStmt(expr)

        # Simple assignment
        if self.current_token().type == TokenType.EQUALS:
            self.advance()
            value = self.parse_expression()
            return Assignment(expr, value)

        return ExprStmt(expr)

    def parse_annotated_assignment(self) -> ASTNode:
        """Parse: name: Type = value (variable with type annotation)"""
        # This is called when we see IDENT followed by COLON
        name = self.expect(TokenType.IDENT).value
        self.expect(TokenType.COLON)

        # Check for Final[T]
        is_final = False
        if self.current_token().type == TokenType.FINAL:
            is_final = True
            self.advance()
            self.expect(TokenType.LBRACKET)
            var_type = self.parse_type()
            self.expect(TokenType.RBRACKET)
        else:
            var_type = self.parse_type()

        value = None
        if self.current_token().type == TokenType.EQUALS:
            self.advance()
            value = self.parse_expression()

        return VarDecl(name, var_type, value, is_const=is_final)

    def parse_return_stmt(self) -> ReturnStmt:
        self.advance()  # Skip 'return'

        if self.current_token().type == TokenType.NEWLINE:
            return ReturnStmt()

        # Parse expression, check for tuple return (comma-separated values)
        value = self.parse_expression()
        if self.current_token().type == TokenType.COMMA:
            # Tuple return: return a, b, c
            elements: List[ASTNode] = [value]
            while self.current_token().type == TokenType.COMMA:
                self.advance()
                elements.append(self.parse_expression())
            value = TupleLiteral(elements)
        return ReturnStmt(value)

    def parse_if_stmt(self) -> IfStmt:
        if_col = self.current_token().col
        self.advance()  # Skip 'if'

        condition = self.parse_expression()
        self.expect(TokenType.COLON)
        self.skip_newlines()

        then_block = self.parse_block()

        elif_blocks: List[tuple] = []
        while True:
            cur = self.current_token()
            is_elif = cur.type == TokenType.ELIF and cur.col == if_col
            if not is_elif:
                break
            self.advance()
            elif_cond = self.parse_expression()
            self.expect(TokenType.COLON)
            self.skip_newlines()
            elif_body = self.parse_block()
            elif_blocks.append((elif_cond, elif_body))

        else_block = None
        cur = self.current_token()
        is_else = cur.type == TokenType.ELSE and cur.col == if_col
        if is_else:
            self.advance()
            self.expect(TokenType.COLON)
            self.skip_newlines()
            else_block = self.parse_block()

        return IfStmt(condition, then_block, elif_blocks if elif_blocks else None, else_block)

    def parse_while_stmt(self) -> WhileStmt:
        self.advance()  # Skip 'while'

        condition = self.parse_expression()
        self.expect(TokenType.COLON)
        self.skip_newlines()

        body = self.parse_block()
        return WhileStmt(condition, body)

    def parse_for_stmt(self):
        """Parse for loop: for i in range(n) or for item in iterable or for a, b in pairs"""
        self.advance()  # Skip 'for'

        # Parse variable names (supports tuple unpacking: for a, b in ... or for i, (a, b) in ...)
        var_names: List[str] = []
        var_names.append(self.expect(TokenType.IDENT).value)
        while self.current_token().type == TokenType.COMMA:
            self.advance()  # Skip comma
            if self.current_token().type == TokenType.LPAREN:
                # Nested tuple like (a, b) - parse and flatten
                self.advance()  # skip (
                var_names.append(self.expect(TokenType.IDENT).value)
                while self.current_token().type == TokenType.COMMA:
                    self.advance()
                    var_names.append(self.expect(TokenType.IDENT).value)
                self.expect(TokenType.RPAREN)
            else:
                var_names.append(self.expect(TokenType.IDENT).value)

        var_name = var_names[0]  # For ForStmt compatibility
        self.expect(TokenType.IN)

        # Check for range() call
        if self.current_token().type == TokenType.IDENT and self.current_token().value == 'range':
            self.advance()
            self.expect(TokenType.LPAREN)

            # Parse range arguments
            first = self.parse_expression()
            start = IntLiteral(0)
            end = first
            step = None

            if self.current_token().type == TokenType.COMMA:
                self.advance()
                start = first
                end = self.parse_expression()

                if self.current_token().type == TokenType.COMMA:
                    self.advance()
                    step = self.parse_expression()

            self.expect(TokenType.RPAREN)
            self.expect(TokenType.COLON)
            self.skip_newlines()
            body = self.parse_block()
            return ForStmt(var_name, start, end, body)

        # Check for start..end range syntax
        first_expr = self.parse_expression()
        if self.current_token().type == TokenType.DOTDOT:
            self.advance()
            end = self.parse_expression()
            self.expect(TokenType.COLON)
            self.skip_newlines()
            body = self.parse_block()
            return ForStmt(var_name, first_expr, end, body)

        # For-each over iterable
        self.expect(TokenType.COLON)
        self.skip_newlines()
        body = self.parse_block()
        return ForEachStmt(var_names, first_expr, body)

    def parse_with_stmt(self) -> WithStmt:
        """Parse with statement (context manager)"""
        self.advance()  # Skip 'with'

        context = self.parse_expression()
        var_name = None
        if self.current_token().type == TokenType.AS:
            self.advance()
            var_name = self.expect(TokenType.IDENT).value

        self.expect(TokenType.COLON)
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
        if token.type == TokenType.IDENT:
            if self.peek_token().type == TokenType.COLON:
                return self.parse_annotated_assignment()

        if token.type == TokenType.RETURN:
            return self.parse_return_stmt()

        if token.type == TokenType.BREAK:
            self.advance()
            return BreakStmt()

        if token.type == TokenType.CONTINUE:
            self.advance()
            return ContinueStmt()

        if token.type == TokenType.PASS:
            self.advance()
            return PassStmt()

        if token.type == TokenType.IF:
            return self.parse_if_stmt()

        if token.type == TokenType.WHILE:
            return self.parse_while_stmt()

        if token.type == TokenType.FOR:
            return self.parse_for_stmt()

        if token.type == TokenType.WITH:
            return self.parse_with_stmt()

        if token.type == TokenType.DEFER:
            return self.parse_defer_stmt()

        if token.type == TokenType.RAISE:
            self.advance()
            # Parse the exception expression
            if self.current_token().type in (TokenType.NEWLINE, TokenType.EOF):
                return RaiseStmt(None)
            exception = self.parse_expression()
            return RaiseStmt(exception)

        # Try/except block (parse but simplify to just the try body for now)
        if token.type == TokenType.TRY:
            self.advance()
            self.expect(TokenType.COLON)
            self.skip_newlines()
            try_body = self.parse_block()

            # Parse except clauses
            while self.current_token().type == TokenType.EXCEPT:
                self.advance()
                # Skip exception type and 'as name' if present
                if self.current_token().type != TokenType.COLON:
                    self.parse_expression()  # Exception type
                    if self.current_token().type == TokenType.AS:
                        self.advance()
                        self.expect(TokenType.IDENT)
                self.expect(TokenType.COLON)
                self.skip_newlines()
                self.parse_block()  # Except body (ignored for now)

            # Parse optional finally
            if self.current_token().type == TokenType.FINALLY:
                self.advance()
                self.expect(TokenType.COLON)
                self.skip_newlines()
                self.parse_block()

            # For simplicity, return just the try body statements
            # A proper implementation would need a TryStmt AST node
            if len(try_body) == 1:
                return try_body[0]
            # Return first statement (not ideal but works for parsing)
            return try_body[0] if try_body else PassStmt()

        # Import inside a block (Python allows this)
        if token.type in (TokenType.FROM, TokenType.IMPORT):
            # Skip the import and return a pass statement
            self.parse_import()
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

            if token.type == TokenType.EOF:
                break

            # Stop at these keywords at base level
            if token.type in [TokenType.DEF, TokenType.CLASS, TokenType.ELIF, TokenType.ELSE]:
                break

            if block_indent is None:
                block_indent = token.col
            elif token.col < block_indent and len(statements) > 0:
                break

            stmt = self.parse_statement()
            statements.append(stmt)
            self.skip_newlines()

        return statements

    def parse_decorator(self) -> str:
        """Parse a decorator: @name or @name(args)"""
        self.expect(TokenType.AT)
        # Decorator name can be IDENT or a keyword like DATACLASS, PROPERTY
        token = self.current_token()
        if token.type == TokenType.IDENT:
            name = token.value
            self.advance()
        elif token.type == TokenType.DATACLASS:
            name = 'dataclass'
            self.advance()
        elif token.type == TokenType.PROPERTY:
            name = 'property'
            self.advance()
        else:
            raise SyntaxError(f"Expected decorator name, got {token.type} at line {token.line}")

        args = None
        if self.current_token().type == TokenType.LPAREN:
            self.advance()
            args = []
            if self.current_token().type != TokenType.RPAREN:
                args.append(self.parse_expression())
                while self.current_token().type == TokenType.COMMA:
                    self.advance()
                    args.append(self.parse_expression())
            self.expect(TokenType.RPAREN)

        return (name, args)

    def parse_def(self, decorators=None) -> ProcDecl:
        """Parse function definition: def name(params) -> ReturnType:"""
        self.advance()  # Skip 'def'

        name = self.expect(TokenType.IDENT).value

        # Parse optional generic type parameters: def foo[T, U](...)
        type_params = []
        if self.current_token().type == TokenType.LBRACKET:
            self.advance()
            if self.current_token().type != TokenType.RBRACKET:
                type_name = self.expect(TokenType.IDENT).value
                type_params.append(GenericType(name=type_name))

                while self.current_token().type == TokenType.COMMA:
                    self.advance()
                    type_name = self.expect(TokenType.IDENT).value
                    type_params.append(GenericType(name=type_name))

            self.expect(TokenType.RBRACKET)

        self.expect(TokenType.LPAREN)

        # Parse parameters
        params: List[Parameter] = []
        self.skip_newlines()
        while self.current_token().type != TokenType.RPAREN:
            # Handle *args and **kwargs (skip them)
            cur_type = self.current_token().type
            if cur_type == TokenType.STAR or cur_type == TokenType.DOUBLE_STAR:
                self.advance()
                if self.current_token().type == TokenType.STAR:
                    self.advance()  # ** as two stars
                if self.current_token().type == TokenType.IDENT:
                    self.advance()  # Skip the parameter name
                # Skip comma if present
                if self.current_token().type == TokenType.COMMA:
                    self.advance()
                self.skip_newlines()
                continue

            # Parse parameter: name: Type = default or name = default
            param_name = self.expect(TokenType.IDENT).value
            param_type = None
            default_value = None
            if self.current_token().type == TokenType.COLON:
                self.advance()
                param_type = self.parse_type()
            if self.current_token().type == TokenType.EQUALS:
                self.advance()
                default_value = self.parse_expression()
            params.append(Parameter(param_name, param_type, default_value))

            if self.current_token().type == TokenType.COMMA:
                self.advance()
                self.skip_newlines()
            else:
                break

        self.skip_newlines()
        self.expect(TokenType.RPAREN)

        # Parse return type: -> Type
        return_type = None
        if self.current_token().type == TokenType.ARROW:
            self.advance()
            return_type = self.parse_type()

        self.expect(TokenType.COLON)
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

    def _infer_fields_from_init(self, methods: List[MethodDecl], existing_fields: List[StructField]) -> List[StructField]:
        """Infer class fields from self.field = value assignments in __init__.

        This enables Python-style class definitions where fields are defined
        in __init__ rather than explicitly declared.
        """
        # Find __init__ method
        init_method = None
        for m in methods:
            if m.name == '__init__':
                init_method = m
                break

        if init_method is None:
            return []

        # Build a map of parameter names to their types
        param_types: Dict[str, Type] = {}
        for param in init_method.params:
            param_types[param.name] = param.param_type

        # Track existing field names to avoid duplicates
        existing_names = {f.name for f in existing_fields}

        # Scan the body for self.field = value assignments
        inferred_fields: List[StructField] = []
        seen_fields = set()

        def infer_type_from_expr(expr: ASTNode) -> Type:
            """Infer type from an expression."""
            if isinstance(expr, IntLiteral):
                return Type('int32')
            elif isinstance(expr, BoolLiteral):
                return Type('bool')
            elif isinstance(expr, StringLiteral) or isinstance(expr, FStringLiteral):
                return PointerType(Type('uint8'))
            elif isinstance(expr, CharLiteral):
                return Type('char')
            elif isinstance(expr, ArrayLiteral):
                return Type('any')  # Can't easily infer element type
            elif isinstance(expr, DictLiteral):
                return Type('any')
            elif isinstance(expr, Identifier):
                # Check if it's a parameter
                if expr.name in param_types and param_types[expr.name] is not None:
                    return param_types[expr.name]
                return Type('any')
            elif isinstance(expr, NoneLiteral):
                return Type('any')  # None could be any pointer type
            else:
                return Type('any')  # Default fallback

        def scan_body(stmts: List[ASTNode]):
            for stmt in stmts:
                if isinstance(stmt, Assignment):
                    # Check if target is self.field
                    if isinstance(stmt.target, FieldAccessExpr):
                        if isinstance(stmt.target.object, Identifier) and stmt.target.object.name == 'self':
                            field_name = stmt.target.field_name
                            if field_name not in existing_names and field_name not in seen_fields:
                                # Use type hint if available, otherwise infer from value
                                if hasattr(stmt, 'type_hint') and stmt.type_hint is not None:
                                    field_type = stmt.type_hint
                                else:
                                    field_type = infer_type_from_expr(stmt.value)
                                inferred_fields.append(StructField(field_name, field_type, None))
                                seen_fields.add(field_name)
                # Recurse into blocks
                elif isinstance(stmt, IfStmt):
                    scan_body(stmt.then_body)
                    if stmt.else_body:
                        scan_body(stmt.else_body)
                elif isinstance(stmt, WhileStmt):
                    scan_body(stmt.body)
                elif isinstance(stmt, ForRangeStmt):
                    scan_body(stmt.body)
                elif isinstance(stmt, ForEachStmt):
                    scan_body(stmt.body)

        scan_body(init_method.body)
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

        name = self.expect(TokenType.IDENT).value

        # Check for inheritance or Enum
        parent = None
        is_enum = False
        if self.current_token().type == TokenType.LPAREN:
            self.advance()
            # Parent can be IDENT or the ENUM keyword (for 'class Foo(Enum):')
            if self.current_token().type == TokenType.ENUM:
                self.advance()
                is_enum = True
            else:
                parent_name = self.expect(TokenType.IDENT).value
                if parent_name == 'Enum':
                    is_enum = True
                else:
                    parent = parent_name
            self.expect(TokenType.RPAREN)

        self.expect(TokenType.COLON)
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

            if token.type == TokenType.EOF:
                break

            if block_indent is None:
                block_indent = token.col
            elif token.col < block_indent:
                break

            # Parse decorators
            inner_decorators = []
            while token.type == TokenType.AT:
                inner_decorators.append(self.parse_decorator())
                self.skip_newlines()
                token = self.current_token()

            # Method definition
            if token.type == TokenType.DEF:
                method = self.parse_method(name, inner_decorators)
                methods.append(method)
            # Pass statement
            elif token.type == TokenType.PASS:
                self.advance()
            # Field definition: name: Type or name: Type = default
            # Or class variable: name = value (no type annotation)
            elif token.type == TokenType.IDENT:
                field_name = token.value
                self.advance()

                if self.current_token().type == TokenType.COLON:
                    # Typed field: name: Type = default
                    self.advance()
                    field_type = self.parse_type()
                    default_value = None
                    if self.current_token().type == TokenType.EQUALS:
                        self.advance()
                        default_value = self.parse_expression()
                    fields.append(StructField(field_name, field_type, default_value))
                elif self.current_token().type == TokenType.EQUALS:
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
        if token.type == TokenType.IDENT:
            method_name = token.value
            self.advance()
        elif token.type.name.isupper():
            # Allow keywords as method names (match, etc.)
            method_name = token.type.name.lower()
            self.advance()
        else:
            raise SyntaxError(f"Expected method name, got {token.type} at line {token.line}")

        self.expect(TokenType.LPAREN)

        # First parameter should be 'self'
        params = []
        receiver_name = None
        receiver_type = None

        if self.current_token().type != TokenType.RPAREN:
            first_param = self.expect(TokenType.IDENT).value
            if first_param == 'self':
                receiver_name = 'self'
                receiver_type = PointerType(Type(class_name))

                if self.current_token().type == TokenType.COMMA:
                    self.advance()
            else:
                # First param isn't self - could be a static method
                param_type = None
                if self.current_token().type == TokenType.COLON:
                    self.advance()
                    param_type = self.parse_type()
                params.append(Parameter(first_param, param_type))

            # Parse remaining parameters
            while self.current_token().type != TokenType.RPAREN:
                if self.current_token().type == TokenType.COMMA:
                    self.advance()
                    self.skip_newlines()  # Handle multi-line parameters
                if self.current_token().type == TokenType.RPAREN:
                    break

                # Handle *args and **kwargs (variadic parameters)
                cur_type = self.current_token().type
                if cur_type == TokenType.STAR or cur_type == TokenType.DOUBLE_STAR:
                    self.advance()
                    if self.current_token().type == TokenType.STAR:
                        self.advance()  # ** as two stars
                    if self.current_token().type == TokenType.IDENT:
                        self.advance()  # Skip the parameter name
                    continue

                param_name = self.expect(TokenType.IDENT).value
                param_type = None
                default_value = None
                if self.current_token().type == TokenType.COLON:
                    self.advance()
                    param_type = self.parse_type()
                if self.current_token().type == TokenType.EQUALS:
                    self.advance()
                    default_value = self.parse_expression()
                params.append(Parameter(param_name, param_type, default_value))

        self.expect(TokenType.RPAREN)

        # Return type
        return_type = None
        if self.current_token().type == TokenType.ARROW:
            self.advance()
            return_type = self.parse_type()

        self.expect(TokenType.COLON)
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

            if token.type == TokenType.EOF:
                break

            if block_indent is None:
                block_indent = token.col
            elif token.col < block_indent:
                break

            if token.type == TokenType.PASS:
                self.advance()
                continue

            # Parse variant: Name or Name(Type1, Type2, ...) or Name = auto() or Name = value
            # For Python compatibility, allow keywords as enum variant names (like DEF, CLASS, etc.)
            token = self.current_token()
            if token.type == TokenType.IDENT:
                variant_name = token.value
                self.advance()
            elif token.type.name.isupper():
                # Allow keyword tokens as enum variant names (DEF, CLASS, etc.)
                variant_name = token.type.name
                self.advance()
            else:
                raise SyntaxError(f"Expected enum variant name, got {token.type} at line {token.line}")
            payload_types = []

            # Python-style: NAME = auto() or NAME = value
            if self.current_token().type == TokenType.EQUALS:
                self.advance()
                # Check for auto() - can be AUTO token or IDENT with value 'auto'
                cur = self.current_token()
                if cur.type == TokenType.AUTO or (cur.type == TokenType.IDENT and cur.value == 'auto'):
                    self.advance()
                    self.expect(TokenType.LPAREN)
                    self.expect(TokenType.RPAREN)
                    # auto() just increments, no payload
                    auto_value += 1
                elif self.current_token().type == TokenType.NUMBER:
                    # Explicit value - skip it, BH enums are just sequential
                    self.advance()
                    auto_value += 1
                else:
                    # Some other expression, just parse and ignore
                    self.parse_expression()
                    auto_value += 1
            # Brainhair-style: Name(Type1, Type2, ...)
            elif self.current_token().type == TokenType.LPAREN:
                self.advance()
                if self.current_token().type != TokenType.RPAREN:
                    payload_types.append(self.parse_type())
                    while self.current_token().type == TokenType.COMMA:
                        self.advance()
                        payload_types.append(self.parse_type())
                self.expect(TokenType.RPAREN)

            variants.append(EnumVariant(variant_name, payload_types))

        return EnumDecl(name, variants)

    def parse_extern_decl(self):
        """Parse extern declaration: extern def func(params) -> Type OR extern name: Type"""
        self.advance()  # Skip 'extern'

        # Check for 'def' keyword (function declaration)
        if self.current_token().type == TokenType.DEF:
            self.advance()
            name = self.expect(TokenType.IDENT).value
            self.expect(TokenType.LPAREN)
        else:
            # Could be variable or function
            name = self.expect(TokenType.IDENT).value

            # Check if it's a variable declaration (name: Type)
            if self.current_token().type == TokenType.COLON:
                self.advance()  # Skip ':'
                var_type = self.parse_type()
                # Return as VarDecl with is_extern flag (or ExternVarDecl)
                return VarDecl(name, var_type, None, is_const=False, is_extern=True)

            # Otherwise it's a function declaration
            self.expect(TokenType.LPAREN)

        params = []
        if self.current_token().type != TokenType.RPAREN:
            param_name = self.expect(TokenType.IDENT).value
            self.expect(TokenType.COLON)
            param_type = self.parse_type()
            params.append(Parameter(param_name, param_type))

            while self.current_token().type == TokenType.COMMA:
                self.advance()
                param_name = self.expect(TokenType.IDENT).value
                self.expect(TokenType.COLON)
                param_type = self.parse_type()
                params.append(Parameter(param_name, param_type))

        self.expect(TokenType.RPAREN)

        return_type = None
        if self.current_token().type == TokenType.ARROW:
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
        if self.current_token().type == TokenType.FROM:
            self.advance()

            # Parse module path: lib.syscalls -> lib/syscalls
            first_part = self.expect(TokenType.IDENT).value

            # Skip Python stdlib imports
            if first_part in ('typing', 'enum', 'dataclasses', 'copy'):
                # Skip the rest of the import statement
                while self.current_token().type not in (TokenType.NEWLINE, TokenType.EOF):
                    self.advance()
                return None  # Signal to skip this import

            path_parts = [first_part]
            while self.current_token().type == TokenType.DOT:
                self.advance()
                path_parts.append(self.expect(TokenType.IDENT).value)

            path = '/'.join(path_parts)

            self.expect(TokenType.IMPORT)

            # Parse imported names
            names = []
            if self.current_token().type == TokenType.STAR:
                self.advance()
                names = ['*']
            else:
                names.append(self.expect(TokenType.IDENT).value)
                while self.current_token().type == TokenType.COMMA:
                    self.advance()
                    names.append(self.expect(TokenType.IDENT).value)

            return ImportDecl(path, import_names=names)

        else:
            self.advance()  # Skip 'import'

            # Parse module path
            path_parts = [self.expect(TokenType.IDENT).value]
            while self.current_token().type == TokenType.DOT:
                self.advance()
                path_parts.append(self.expect(TokenType.IDENT).value)

            path = '/'.join(path_parts)

            alias = None
            if self.current_token().type == TokenType.AS:
                self.advance()
                alias = self.expect(TokenType.IDENT).value

            return ImportDecl(path, alias)

    def parse(self) -> Program:
        imports = []
        declarations = []
        methods = []  # Collect methods from classes

        self.skip_newlines()

        # Skip module docstring (string literal at start of file)
        if self.current_token().type == TokenType.STRING:
            self.advance()
            self.skip_newlines()

        # Parse imports first (imports can be interspersed with docstrings/comments)
        while self.match(TokenType.FROM, TokenType.IMPORT):
            imp = self.parse_import()
            if imp is not None:  # Skip Python stdlib imports
                imports.append(imp)
            self.skip_newlines()

        # Parse declarations
        while self.current_token().type != TokenType.EOF:
            # Allow imports anywhere in the file (Python compatibility)
            if self.match(TokenType.FROM, TokenType.IMPORT):
                imp = self.parse_import()
                if imp is not None:
                    imports.append(imp)
                self.skip_newlines()
                continue
            # Parse decorators
            decorators = []
            while self.current_token().type == TokenType.AT:
                decorators.append(self.parse_decorator())
                self.skip_newlines()

            token = self.current_token()

            if token.type == TokenType.EXTERN:
                declarations.append(self.parse_extern_decl())
            elif token.type == TokenType.DEF:
                declarations.append(self.parse_def(decorators))
            elif token.type == TokenType.CLASS:
                result = self.parse_class(decorators)
                if isinstance(result, tuple):
                    struct, class_methods = result
                    declarations.append(struct)
                    methods.extend(class_methods)
                else:
                    declarations.append(result)
            elif token.type == TokenType.IDENT:
                # Top-level variable with type annotation
                if self.peek_token().type == TokenType.COLON:
                    declarations.append(self.parse_annotated_assignment())
                else:
                    declarations.append(self.parse_statement())
            else:
                declarations.append(self.parse_statement())

            self.skip_newlines()

        # Add methods to declarations
        declarations.extend(methods)

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
