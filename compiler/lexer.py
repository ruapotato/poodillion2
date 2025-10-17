#!/usr/bin/env python3
"""
Mini-Nim Lexer - Tokenizes Mini-Nim source code

Stage 0 compiler (written in Python)
Will be rewritten in Mini-Nim once compiler is working!
"""

from enum import Enum, auto
from dataclasses import dataclass
from typing import List, Optional

class TokenType(Enum):
    # Keywords
    VAR = auto()
    CONST = auto()
    PROC = auto()
    EXTERN = auto()
    RETURN = auto()
    IF = auto()
    ELIF = auto()
    ELSE = auto()
    WHILE = auto()
    FOR = auto()
    IN = auto()
    ASM = auto()
    CAST = auto()
    DISCARD = auto()

    # Types
    INT8 = auto()
    INT16 = auto()
    INT32 = auto()
    UINT8 = auto()
    UINT16 = auto()
    UINT32 = auto()
    BOOL = auto()
    CHAR = auto()
    PTR = auto()

    # Literals
    IDENT = auto()
    NUMBER = auto()
    STRING = auto()
    CHAR_LIT = auto()
    TRUE = auto()
    FALSE = auto()

    # Operators
    PLUS = auto()
    MINUS = auto()
    STAR = auto()
    SLASH = auto()
    PERCENT = auto()
    EQUALS = auto()
    EQUALS_EQUALS = auto()
    NOT_EQUALS = auto()
    LESS = auto()
    LESS_EQUALS = auto()
    GREATER = auto()
    GREATER_EQUALS = auto()
    SHL = auto()  # <<
    SHR = auto()  # >>
    AND = auto()
    OR = auto()
    NOT = auto()
    # Bitwise operators
    PIPE = auto()      # |
    AMPERSAND = auto() # &
    CARET = auto()     # ^

    # Delimiters
    LPAREN = auto()
    RPAREN = auto()
    LBRACKET = auto()
    RBRACKET = auto()
    LBRACE = auto()
    RBRACE = auto()
    COMMA = auto()
    COLON = auto()
    DOT = auto()
    DOTDOT = auto()

    # Special
    NEWLINE = auto()
    INDENT = auto()
    DEDENT = auto()
    EOF = auto()

@dataclass
class Token:
    type: TokenType
    value: any
    line: int
    col: int

    def __repr__(self):
        if self.value is not None:
            return f"{self.type.name}({self.value})"
        return self.type.name

class Lexer:
    def __init__(self, source: str):
        self.source = source
        self.pos = 0
        self.line = 1
        self.col = 1
        self.tokens: List[Token] = []

        # Track indentation for Python-style blocks
        self.indent_stack = [0]

        # Keywords
        self.keywords = {
            'var': TokenType.VAR,
            'const': TokenType.CONST,
            'proc': TokenType.PROC,
            'extern': TokenType.EXTERN,
            'return': TokenType.RETURN,
            'if': TokenType.IF,
            'elif': TokenType.ELIF,
            'else': TokenType.ELSE,
            'while': TokenType.WHILE,
            'for': TokenType.FOR,
            'in': TokenType.IN,
            'asm': TokenType.ASM,
            'cast': TokenType.CAST,
            'discard': TokenType.DISCARD,
            'true': TokenType.TRUE,
            'false': TokenType.FALSE,
            # Types
            'int8': TokenType.INT8,
            'int16': TokenType.INT16,
            'int32': TokenType.INT32,
            'uint8': TokenType.UINT8,
            'uint16': TokenType.UINT16,
            'uint32': TokenType.UINT32,
            'bool': TokenType.BOOL,
            'char': TokenType.CHAR,
            'ptr': TokenType.PTR,
        }

    def current_char(self) -> Optional[str]:
        if self.pos >= len(self.source):
            return None
        return self.source[self.pos]

    def peek_char(self, offset=1) -> Optional[str]:
        pos = self.pos + offset
        if pos >= len(self.source):
            return None
        return self.source[pos]

    def advance(self):
        if self.pos < len(self.source):
            if self.source[self.pos] == '\n':
                self.line += 1
                self.col = 1
            else:
                self.col += 1
            self.pos += 1

    def skip_whitespace(self):
        while self.current_char() in ' \t':
            self.advance()

    def skip_comment(self):
        if self.current_char() == '#':
            while self.current_char() and self.current_char() != '\n':
                self.advance()

    def read_number(self) -> Token:
        line, col = self.line, self.col
        num_str = ''

        # Hex number
        if self.current_char() == '0' and self.peek_char() in 'xX':
            self.advance()  # 0
            self.advance()  # x
            while self.current_char() and self.current_char() in '0123456789abcdefABCDEF':
                num_str += self.current_char()
                self.advance()
            return Token(TokenType.NUMBER, int(num_str, 16), line, col)

        # Decimal number
        while self.current_char() and self.current_char().isdigit():
            num_str += self.current_char()
            self.advance()

        return Token(TokenType.NUMBER, int(num_str), line, col)

    def read_string(self) -> Token:
        line, col = self.line, self.col
        quote = self.current_char()
        self.advance()  # Skip opening quote

        string = ''
        while self.current_char() and self.current_char() != quote:
            if self.current_char() == '\\':
                self.advance()
                # Handle escape sequences
                esc = self.current_char()
                if esc == 'n':
                    string += '\n'
                elif esc == 't':
                    string += '\t'
                elif esc == '0':
                    string += '\0'
                else:
                    string += esc
                self.advance()
            else:
                string += self.current_char()
                self.advance()

        self.advance()  # Skip closing quote
        return Token(TokenType.STRING, string, line, col)

    def read_char(self) -> Token:
        line, col = self.line, self.col
        self.advance()  # Skip opening '

        ch = self.current_char()
        if ch == '\\':
            self.advance()
            esc = self.current_char()
            if esc == 'n':
                ch = '\n'
            elif esc == 't':
                ch = '\t'
            elif esc == '0':
                ch = '\0'
            else:
                ch = esc

        self.advance()
        self.advance()  # Skip closing '
        return Token(TokenType.CHAR_LIT, ch, line, col)

    def read_identifier(self) -> Token:
        line, col = self.line, self.col
        ident = ''

        while self.current_char() and (self.current_char().isalnum() or self.current_char() == '_'):
            ident += self.current_char()
            self.advance()

        # Check if it's a keyword
        token_type = self.keywords.get(ident, TokenType.IDENT)
        value = None if token_type != TokenType.IDENT else ident

        return Token(token_type, value, line, col)

    def tokenize(self) -> List[Token]:
        while self.pos < len(self.source):
            self.skip_whitespace()

            ch = self.current_char()
            if not ch:
                break

            line, col = self.line, self.col

            # Comments
            if ch == '#':
                self.skip_comment()
                continue

            # Newlines (significant for indentation)
            if ch == '\n':
                self.tokens.append(Token(TokenType.NEWLINE, None, line, col))
                self.advance()
                continue

            # Numbers
            if ch.isdigit():
                self.tokens.append(self.read_number())
                continue

            # Strings
            if ch == '"':
                self.tokens.append(self.read_string())
                continue

            # Characters
            if ch == "'":
                self.tokens.append(self.read_char())
                continue

            # Identifiers and keywords
            if ch.isalpha() or ch == '_':
                self.tokens.append(self.read_identifier())
                continue

            # Operators and delimiters
            if ch == '+':
                self.tokens.append(Token(TokenType.PLUS, None, line, col))
                self.advance()
            elif ch == '-':
                self.tokens.append(Token(TokenType.MINUS, None, line, col))
                self.advance()
            elif ch == '*':
                self.tokens.append(Token(TokenType.STAR, None, line, col))
                self.advance()
            elif ch == '/':
                self.tokens.append(Token(TokenType.SLASH, None, line, col))
                self.advance()
            elif ch == '%':
                self.tokens.append(Token(TokenType.PERCENT, None, line, col))
                self.advance()
            elif ch == '=':
                if self.peek_char() == '=':
                    self.tokens.append(Token(TokenType.EQUALS_EQUALS, None, line, col))
                    self.advance()
                    self.advance()
                else:
                    self.tokens.append(Token(TokenType.EQUALS, None, line, col))
                    self.advance()
            elif ch == '!':
                if self.peek_char() == '=':
                    self.tokens.append(Token(TokenType.NOT_EQUALS, None, line, col))
                    self.advance()
                    self.advance()
                else:
                    self.tokens.append(Token(TokenType.NOT, None, line, col))
                    self.advance()
            elif ch == '<':
                if self.peek_char() == '=':
                    self.tokens.append(Token(TokenType.LESS_EQUALS, None, line, col))
                    self.advance()
                    self.advance()
                elif self.peek_char() == '<':
                    self.tokens.append(Token(TokenType.SHL, None, line, col))
                    self.advance()
                    self.advance()
                else:
                    self.tokens.append(Token(TokenType.LESS, None, line, col))
                    self.advance()
            elif ch == '>':
                if self.peek_char() == '=':
                    self.tokens.append(Token(TokenType.GREATER_EQUALS, None, line, col))
                    self.advance()
                    self.advance()
                elif self.peek_char() == '>':
                    self.tokens.append(Token(TokenType.SHR, None, line, col))
                    self.advance()
                    self.advance()
                else:
                    self.tokens.append(Token(TokenType.GREATER, None, line, col))
                    self.advance()
            elif ch == '(':
                self.tokens.append(Token(TokenType.LPAREN, None, line, col))
                self.advance()
            elif ch == ')':
                self.tokens.append(Token(TokenType.RPAREN, None, line, col))
                self.advance()
            elif ch == '[':
                self.tokens.append(Token(TokenType.LBRACKET, None, line, col))
                self.advance()
            elif ch == ']':
                self.tokens.append(Token(TokenType.RBRACKET, None, line, col))
                self.advance()
            elif ch == '{':
                self.tokens.append(Token(TokenType.LBRACE, None, line, col))
                self.advance()
            elif ch == '}':
                self.tokens.append(Token(TokenType.RBRACE, None, line, col))
                self.advance()
            elif ch == ',':
                self.tokens.append(Token(TokenType.COMMA, None, line, col))
                self.advance()
            elif ch == ':':
                self.tokens.append(Token(TokenType.COLON, None, line, col))
                self.advance()
            elif ch == '.':
                if self.peek_char() == '.':
                    self.tokens.append(Token(TokenType.DOTDOT, None, line, col))
                    self.advance()
                    self.advance()
                else:
                    self.tokens.append(Token(TokenType.DOT, None, line, col))
                    self.advance()
            elif ch == '|':
                self.tokens.append(Token(TokenType.PIPE, None, line, col))
                self.advance()
            elif ch == '&':
                self.tokens.append(Token(TokenType.AMPERSAND, None, line, col))
                self.advance()
            elif ch == '^':
                self.tokens.append(Token(TokenType.CARET, None, line, col))
                self.advance()
            else:
                raise SyntaxError(f"Unexpected character '{ch}' at line {line}, col {col}")

        self.tokens.append(Token(TokenType.EOF, None, self.line, self.col))
        return self.tokens

# Test the lexer
if __name__ == '__main__':
    code = """
var x: int32 = 42
var msg: ptr uint8 = cast[ptr uint8](0xB8000)

proc add(a, b: int32): int32 =
  return a + b

if x > 0:
  x = x + 1
"""

    lexer = Lexer(code)
    tokens = lexer.tokenize()

    print("Tokens:")
    for token in tokens:
        print(f"  {token}")
