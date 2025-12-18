#!/usr/bin/env python3
"""
Brainhair Parser - Builds AST from tokens

Recursive descent parser for Brainhair
"""

from typing import List, Optional
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

    # Type parsing
    def parse_type(self) -> Type:
        token = self.current_token()

        # Basic types
        if token.type in [TokenType.INT8, TokenType.INT16, TokenType.INT32,
                          TokenType.UINT8, TokenType.UINT16, TokenType.UINT32,
                          TokenType.BOOL, TokenType.CHAR]:
            type_name = token.type.name.lower()
            self.advance()
            return Type(type_name)

        # Pointer type: ptr T
        if token.type == TokenType.PTR:
            self.advance()
            base_type = self.parse_type()
            return PointerType(base_type)

        # Array type: array[N, T]
        if token.type == TokenType.IDENT and token.value == 'array':
            self.advance()
            self.expect(TokenType.LBRACKET)

            # Parse size (must be a number literal for now)
            size_token = self.current_token()
            if size_token.type != TokenType.NUMBER:
                raise SyntaxError(f"Array size must be a number at line {size_token.line}")
            size = size_token.value
            self.advance()

            self.expect(TokenType.COMMA)

            # Parse element type
            element_type = self.parse_type()
            self.expect(TokenType.RBRACKET)

            return ArrayType(size, element_type)

        # User-defined type (identifier) - could be struct name
        if token.type == TokenType.IDENT:
            type_name = token.value
            self.advance()
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

        if token.type == TokenType.TRUE:
            self.advance()
            return BoolLiteral(True)

        if token.type == TokenType.FALSE:
            self.advance()
            return BoolLiteral(False)

        # Array literal: [1, 2, 3]
        if token.type == TokenType.LBRACKET:
            self.advance()
            self.skip_newlines()  # Allow newlines after [
            elements = []

            if self.current_token().type != TokenType.RBRACKET:
                elements.append(self.parse_expression())
                while self.current_token().type == TokenType.COMMA:
                    self.advance()
                    self.skip_newlines()  # Allow newlines after comma
                    # Check for trailing comma
                    if self.current_token().type == TokenType.RBRACKET:
                        break
                    elements.append(self.parse_expression())

            self.skip_newlines()  # Allow newlines before ]
            self.expect(TokenType.RBRACKET)
            return ArrayLiteral(elements)

        # Identifier
        if token.type == TokenType.IDENT:
            name = token.value
            self.advance()
            return Identifier(name)

        # Parenthesized expression
        if token.type == TokenType.LPAREN:
            self.advance()
            expr = self.parse_expression()
            self.expect(TokenType.RPAREN)
            return expr

        # Unary operators
        if token.type in [TokenType.MINUS, TokenType.NOT]:
            op = UnaryOp.NEG if token.type == TokenType.MINUS else UnaryOp.NOT
            self.advance()
            return UnaryExpr(op, self.parse_primary())

        raise SyntaxError(f"Unexpected token {token.type} at line {token.line}")

    def parse_primary(self) -> ASTNode:
        """Parse primary expressions with postfix operations (calls, indexing, field access)"""
        token = self.current_token()

        # Handle special prefix expressions first
        # Cast expression: cast[Type](expr)
        if token.type == TokenType.CAST:
            self.advance()
            self.expect(TokenType.LBRACKET)
            target_type = self.parse_type()
            self.expect(TokenType.RBRACKET)
            self.expect(TokenType.LPAREN)
            expr = self.parse_expression()
            self.expect(TokenType.RPAREN)
            expr = CastExpr(target_type, expr)
        # Address-of expression: addr(var)
        elif token.type == TokenType.ADDR:
            self.advance()
            self.expect(TokenType.LPAREN)
            expr = self.parse_expression()
            self.expect(TokenType.RPAREN)
            expr = AddrOfExpr(expr)
        else:
            # Parse atom (literal, identifier, etc.)
            expr = self.parse_atom()

        # Handle postfix operations: calls, indexing, field access
        while True:
            token = self.current_token()

            # Function call or struct literal: foo(...) or Type(field: val)
            if token.type == TokenType.LPAREN:
                # Check if this is a struct literal (identifier followed by named args)
                if isinstance(expr, Identifier):
                    # Peek ahead to see if it's name: value pattern
                    saved_pos = self.pos
                    self.advance()  # Skip (
                    # Skip any newlines to properly detect pattern
                    while self.current_token().type == TokenType.NEWLINE:
                        self.advance()

                    is_struct_literal = False
                    if self.current_token().type == TokenType.IDENT:
                        next_tok = self.peek_token()
                        if next_tok.type == TokenType.COLON:
                            is_struct_literal = True
                    # NOTE: Empty parens foo() is always a function call, not struct literal
                    # Struct literals require at least one field: Type(field: value)

                    # Restore position
                    self.pos = saved_pos

                    if is_struct_literal:
                        # Parse as struct literal
                        struct_name = expr.name
                        self.advance()  # Skip (
                        self.skip_newlines()  # Allow newlines after (
                        field_values = {}

                        if self.current_token().type != TokenType.RPAREN:
                            field_name = self.expect(TokenType.IDENT).value
                            self.expect(TokenType.COLON)
                            field_values[field_name] = self.parse_expression()

                            while self.current_token().type == TokenType.COMMA:
                                self.advance()
                                self.skip_newlines()  # Allow newlines after comma
                                # Check for trailing comma
                                if self.current_token().type == TokenType.RPAREN:
                                    break
                                field_name = self.expect(TokenType.IDENT).value
                                self.expect(TokenType.COLON)
                                field_values[field_name] = self.parse_expression()

                        self.skip_newlines()  # Allow newlines before )
                        self.expect(TokenType.RPAREN)
                        expr = StructLiteral(struct_name, field_values)
                        continue

                # Regular function call
                self.advance()
                self.skip_newlines()  # Allow newlines after (
                args = []

                if self.current_token().type != TokenType.RPAREN:
                    args.append(self.parse_expression())
                    while self.current_token().type == TokenType.COMMA:
                        self.advance()
                        self.skip_newlines()  # Allow newlines after comma
                        # Check for trailing comma
                        if self.current_token().type == TokenType.RPAREN:
                            break
                        args.append(self.parse_expression())

                self.skip_newlines()  # Allow newlines before )
                self.expect(TokenType.RPAREN)
                # If expr is an Identifier, convert to CallExpr with name
                if isinstance(expr, Identifier):
                    expr = CallExpr(expr.name, args)
                else:
                    # This shouldn't happen in valid code, but handle gracefully
                    raise SyntaxError(f"Cannot call non-identifier at line {token.line}")

            # Array/pointer indexing: expr[index]
            elif token.type == TokenType.LBRACKET:
                self.advance()
                index = self.parse_expression()
                self.expect(TokenType.RBRACKET)
                expr = IndexExpr(expr, index)

            # Field access: expr.field
            elif token.type == TokenType.DOT:
                self.advance()
                field_name = self.expect(TokenType.IDENT).value
                expr = FieldAccessExpr(expr, field_name)

            else:
                # No more postfix operations
                break

        return expr

    def parse_multiplicative(self) -> ASTNode:
        left = self.parse_primary()

        while self.current_token().type in [TokenType.STAR, TokenType.SLASH, TokenType.PERCENT]:
            op_token = self.current_token()
            self.advance()

            if op_token.type == TokenType.STAR:
                op = BinOp.MUL
            elif op_token.type == TokenType.SLASH:
                op = BinOp.DIV
            else:
                op = BinOp.MOD

            right = self.parse_primary()
            left = BinaryExpr(left, op, right)

        return left

    def parse_shift(self) -> ASTNode:
        left = self.parse_additive()

        while self.current_token().type in [TokenType.SHL, TokenType.SHR]:
            op_token = self.current_token()
            self.advance()

            op = BinOp.SHL if op_token.type == TokenType.SHL else BinOp.SHR
            right = self.parse_additive()
            left = BinaryExpr(left, op, right)

        return left

    def parse_additive(self) -> ASTNode:
        left = self.parse_multiplicative()

        while self.current_token().type in [TokenType.PLUS, TokenType.MINUS]:
            op_token = self.current_token()
            self.advance()

            op = BinOp.ADD if op_token.type == TokenType.PLUS else BinOp.SUB
            right = self.parse_multiplicative()
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
        left = self.parse_bitwise_or()

        while self.current_token().type in [TokenType.EQUALS_EQUALS, TokenType.NOT_EQUALS,
                                            TokenType.LESS, TokenType.LESS_EQUALS,
                                            TokenType.GREATER, TokenType.GREATER_EQUALS]:
            op_token = self.current_token()
            self.advance()

            op_map = {
                TokenType.EQUALS_EQUALS: BinOp.EQ,
                TokenType.NOT_EQUALS: BinOp.NEQ,
                TokenType.LESS: BinOp.LT,
                TokenType.LESS_EQUALS: BinOp.LTE,
                TokenType.GREATER: BinOp.GT,
                TokenType.GREATER_EQUALS: BinOp.GTE,
            }

            op = op_map[op_token.type]
            right = self.parse_bitwise_or()
            left = BinaryExpr(left, op, right)

        return left

    def parse_logical_and(self) -> ASTNode:
        left = self.parse_comparison()

        while self.current_token().type == TokenType.AND:
            self.advance()
            right = self.parse_comparison()
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
        """Parse conditional expressions: if cond: a else: b"""
        # Check if this is a conditional expression
        if self.current_token().type == TokenType.IF:
            self.advance()
            condition = self.parse_logical_or()
            self.expect(TokenType.COLON)
            then_expr = self.parse_logical_or()
            self.expect(TokenType.ELSE)
            self.expect(TokenType.COLON)
            else_expr = self.parse_logical_or()
            return ConditionalExpr(condition, then_expr, else_expr)

        return self.parse_logical_or()

    def parse_expression(self) -> ASTNode:
        return self.parse_conditional_expr()

    # Statement parsing
    def parse_var_decl(self) -> VarDecl:
        is_const = self.current_token().type == TokenType.CONST
        self.advance()  # Skip var/const

        name = self.expect(TokenType.IDENT).value
        self.expect(TokenType.COLON)
        var_type = self.parse_type()

        value = None
        if self.current_token().type == TokenType.EQUALS:
            self.advance()
            value = self.parse_expression()

        return VarDecl(name, var_type, value, is_const)

    def parse_assignment_or_expr(self) -> ASTNode:
        expr = self.parse_expression()

        # Check for assignment
        if self.current_token().type == TokenType.EQUALS:
            self.advance()
            value = self.parse_expression()
            return Assignment(expr, value)

        return ExprStmt(expr)

    def parse_return_stmt(self) -> ReturnStmt:
        self.advance()  # Skip 'return'

        if self.current_token().type == TokenType.NEWLINE:
            return ReturnStmt()

        value = self.parse_expression()
        return ReturnStmt(value)

    def parse_if_stmt(self) -> IfStmt:
        # Record column of the 'if' keyword for matching else/elif
        if_col = self.current_token().col
        self.advance()  # Skip 'if'

        condition = self.parse_expression()
        self.expect(TokenType.COLON)
        self.skip_newlines()

        # Parse then block
        then_block = self.parse_block()

        # Parse elif blocks - only if at same column as this if
        elif_blocks = []
        while (self.current_token().type == TokenType.ELIF and
               self.current_token().col == if_col):
            self.advance()
            elif_cond = self.parse_expression()
            self.expect(TokenType.COLON)
            self.skip_newlines()
            elif_body = self.parse_block()
            elif_blocks.append((elif_cond, elif_body))

        # Parse else block - only if at same column as this if
        else_block = None
        if (self.current_token().type == TokenType.ELSE and
            self.current_token().col == if_col):
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

    def parse_for_stmt(self) -> ForStmt:
        self.advance()  # Skip 'for'

        var_name = self.expect(TokenType.IDENT).value
        self.expect(TokenType.IN)

        start = self.parse_expression()
        self.expect(TokenType.DOTDOT)
        end = self.parse_expression()

        self.expect(TokenType.COLON)
        self.skip_newlines()

        body = self.parse_block()
        return ForStmt(var_name, start, end, body)

    def parse_statement(self) -> ASTNode:
        token = self.current_token()

        if token.type in [TokenType.VAR, TokenType.CONST]:
            return self.parse_var_decl()

        if token.type == TokenType.RETURN:
            return self.parse_return_stmt()

        if token.type == TokenType.BREAK:
            self.advance()
            return BreakStmt()

        if token.type == TokenType.CONTINUE:
            self.advance()
            return ContinueStmt()

        if token.type == TokenType.IF:
            return self.parse_if_stmt()

        if token.type == TokenType.WHILE:
            return self.parse_while_stmt()

        if token.type == TokenType.FOR:
            return self.parse_for_stmt()

        if token.type == TokenType.DISCARD:
            self.advance()
            return DiscardStmt()

        # Assignment or expression statement
        return self.parse_assignment_or_expr()

    def parse_block(self) -> List[ASTNode]:
        """Parse an indented block of statements"""
        statements = []

        # Track the indentation level of the first statement in the block
        block_indent = None

        # Parse all statements until we hit EOF or a dedent-level keyword
        while True:
            self.skip_newlines()

            token = self.current_token()

            # Stop at end of file
            if token.type == TokenType.EOF:
                break

            # Stop at proc-level keywords (new procedure)
            if token.type == TokenType.PROC and len(statements) > 0:
                break

            # Stop at same-level control flow (elif/else)
            if token.type in [TokenType.ELIF, TokenType.ELSE]:
                break

            # Track indentation of first statement
            if block_indent is None:
                block_indent = token.col
            # If we encounter a statement at LOWER indentation, block is done (dedent)
            elif token.col < block_indent and len(statements) > 0:
                # Exception: elif/else are handled separately above
                break

            # Parse the statement
            stmt = self.parse_statement()
            statements.append(stmt)
            self.skip_newlines()

        return statements

    def parse_proc_decl(self) -> ProcDecl:
        self.advance()  # Skip 'proc'

        name = self.expect(TokenType.IDENT).value
        self.expect(TokenType.LPAREN)

        # Parse parameters
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

        # Parse return type
        return_type = None
        if self.current_token().type == TokenType.COLON:
            self.advance()
            return_type = self.parse_type()

        self.expect(TokenType.EQUALS)
        self.skip_newlines()

        # Parse body
        body = self.parse_block()

        return ProcDecl(name, params, return_type, body)

    def parse_extern_decl(self) -> ExternDecl:
        self.advance()  # Skip 'extern'
        self.expect(TokenType.PROC)

        name = self.expect(TokenType.IDENT).value
        self.expect(TokenType.LPAREN)

        # Parse parameters
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

        # Parse return type
        return_type = None
        if self.current_token().type == TokenType.COLON:
            self.advance()
            return_type = self.parse_type()

        return ExternDecl(name, params, return_type)

    def parse_struct_decl(self) -> StructDecl:
        """Parse struct type declaration: type Name = object ... """
        self.advance()  # Skip 'type'

        name = self.expect(TokenType.IDENT).value
        self.expect(TokenType.EQUALS)
        self.expect(TokenType.OBJECT)
        self.skip_newlines()

        # Parse fields - indented block
        fields = []
        block_indent = None

        while True:
            self.skip_newlines()
            token = self.current_token()

            # Stop at end of file or dedent
            if token.type == TokenType.EOF:
                break

            # Track indentation of first field
            if block_indent is None:
                block_indent = token.col
            # If we encounter a line at LOWER indentation, struct is done
            elif token.col < block_indent:
                break

            # Parse field: name: type
            field_name = self.expect(TokenType.IDENT).value
            self.expect(TokenType.COLON)
            field_type = self.parse_type()

            # Optional default value
            default_value = None
            if self.current_token().type == TokenType.EQUALS:
                self.advance()
                default_value = self.parse_expression()

            fields.append(StructField(field_name, field_type, default_value))
            self.skip_newlines()

        return StructDecl(name, fields)

    def parse(self) -> Program:
        declarations = []

        self.skip_newlines()

        while self.current_token().type != TokenType.EOF:
            token = self.current_token()

            if token.type == TokenType.EXTERN:
                declarations.append(self.parse_extern_decl())
            elif token.type == TokenType.PROC:
                declarations.append(self.parse_proc_decl())
            elif token.type == TokenType.TYPE:
                declarations.append(self.parse_struct_decl())
            elif token.type in [TokenType.VAR, TokenType.CONST]:
                declarations.append(self.parse_var_decl())
            else:
                # Top-level statement
                declarations.append(self.parse_statement())

            self.skip_newlines()

        return Program(declarations)

# Test the parser
if __name__ == '__main__':
    code = """
var x: int32 = 42

proc add(a: int32, b: int32): int32 =
  return a + b

proc main() =
  var result: int32 = add(x, 10)
  if result > 50:
    result = result - 1
"""

    lexer = Lexer(code)
    tokens = lexer.tokenize()

    parser = Parser(tokens)
    ast = parser.parse()

    print("AST:")
    for decl in ast.declarations:
        print(f"  {decl}")
