#!/usr/bin/env python3
"""
Brainhair Lexer - Tokenizes Brainhair source code

Stage 0 compiler (written in Python)
Will be rewritten in Brainhair once compiler is working!
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
    BREAK = auto()
    CONTINUE = auto()
    ASM = auto()
    CAST = auto()
    DISCARD = auto()
    ADDR = auto()
    TYPE = auto()
    OBJECT = auto()
    ENUM = auto()
    MATCH = auto()
    DEFER = auto()
    IMPORT = auto()
    AS = auto()

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
    column: int
    end_line: int = None
    end_column: int = None

    # Backward compatibility - allow .col to work
    @property
    def col(self):
        return self.column

    def __repr__(self):
        if self.value is not None:
            return f"{self.type.name}({self.value})"
        return self.type.name

class Lexer:
    def __init__(self, source: str):
        self.source = source
        self.pos = 0
        self.line = 1
        self.column = 1
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
            'break': TokenType.BREAK,
            'continue': TokenType.CONTINUE,
            'and': TokenType.AND,
            'or': TokenType.OR,
            'not': TokenType.NOT,
            'asm': TokenType.ASM,
            'cast': TokenType.CAST,
            'discard': TokenType.DISCARD,
            'addr': TokenType.ADDR,
            'type': TokenType.TYPE,
            'object': TokenType.OBJECT,
            'enum': TokenType.ENUM,
            'match': TokenType.MATCH,
            'defer': TokenType.DEFER,
            'import': TokenType.IMPORT,
            'as': TokenType.AS,
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
                self.column = 1
            else:
                self.column += 1
            self.pos += 1

    def get_position(self) -> tuple:
        """Return current position as (line, column)"""
        return (self.line, self.column)

    def skip_whitespace(self):
        while self.current_char() in ' \t':
            self.advance()

    def skip_comment(self):
        if self.current_char() == '#':
            while self.current_char() and self.current_char() != '\n':
                self.advance()

    def read_number(self) -> Token:
        start_line, start_col = self.line, self.column
        num_str = ''

        # Hex number
        if self.current_char() == '0' and self.peek_char() in 'xX':
            self.advance()  # 0
            self.advance()  # x
            while self.current_char() and self.current_char() in '0123456789abcdefABCDEF':
                num_str += self.current_char()
                self.advance()
            return Token(TokenType.NUMBER, int(num_str, 16), start_line, start_col,
                        self.line, self.column)

        # Decimal number
        while self.current_char() and self.current_char().isdigit():
            num_str += self.current_char()
            self.advance()

        return Token(TokenType.NUMBER, int(num_str), start_line, start_col,
                    self.line, self.column)

    def read_string(self) -> Token:
        start_line, start_col = self.line, self.column
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
        return Token(TokenType.STRING, string, start_line, start_col,
                    self.line, self.column)

    def read_char(self) -> Token:
        start_line, start_col = self.line, self.column
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
        return Token(TokenType.CHAR_LIT, ch, start_line, start_col,
                    self.line, self.column)

    def read_identifier(self) -> Token:
        start_line, start_col = self.line, self.column
        ident = ''

        while self.current_char() and (self.current_char().isalnum() or self.current_char() == '_'):
            ident += self.current_char()
            self.advance()

        # Check if it's a keyword
        token_type = self.keywords.get(ident, TokenType.IDENT)
        value = None if token_type != TokenType.IDENT else ident

        return Token(token_type, value, start_line, start_col,
                    self.line, self.column)

    def tokenize(self) -> List[Token]:
        while self.pos < len(self.source):
            self.skip_whitespace()

            ch = self.current_char()
            if not ch:
                break

            start_line, start_col = self.line, self.column

            # Comments
            if ch == '#':
                self.skip_comment()
                continue

            # Newlines (significant for indentation)
            if ch == '\n':
                self.advance()
                self.tokens.append(Token(TokenType.NEWLINE, None, start_line, start_col,
                                       self.line, self.column))
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
                self.advance()
                self.tokens.append(Token(TokenType.PLUS, None, start_line, start_col,
                                       self.line, self.column))
            elif ch == '-':
                self.advance()
                self.tokens.append(Token(TokenType.MINUS, None, start_line, start_col,
                                       self.line, self.column))
            elif ch == '*':
                self.advance()
                self.tokens.append(Token(TokenType.STAR, None, start_line, start_col,
                                       self.line, self.column))
            elif ch == '/':
                self.advance()
                self.tokens.append(Token(TokenType.SLASH, None, start_line, start_col,
                                       self.line, self.column))
            elif ch == '%':
                self.advance()
                self.tokens.append(Token(TokenType.PERCENT, None, start_line, start_col,
                                       self.line, self.column))
            elif ch == '=':
                if self.peek_char() == '=':
                    self.advance()
                    self.advance()
                    self.tokens.append(Token(TokenType.EQUALS_EQUALS, None, start_line, start_col,
                                           self.line, self.column))
                else:
                    self.advance()
                    self.tokens.append(Token(TokenType.EQUALS, None, start_line, start_col,
                                           self.line, self.column))
            elif ch == '!':
                if self.peek_char() == '=':
                    self.advance()
                    self.advance()
                    self.tokens.append(Token(TokenType.NOT_EQUALS, None, start_line, start_col,
                                           self.line, self.column))
                else:
                    self.advance()
                    self.tokens.append(Token(TokenType.NOT, None, start_line, start_col,
                                           self.line, self.column))
            elif ch == '<':
                if self.peek_char() == '=':
                    self.advance()
                    self.advance()
                    self.tokens.append(Token(TokenType.LESS_EQUALS, None, start_line, start_col,
                                           self.line, self.column))
                elif self.peek_char() == '<':
                    self.advance()
                    self.advance()
                    self.tokens.append(Token(TokenType.SHL, None, start_line, start_col,
                                           self.line, self.column))
                else:
                    self.advance()
                    self.tokens.append(Token(TokenType.LESS, None, start_line, start_col,
                                           self.line, self.column))
            elif ch == '>':
                if self.peek_char() == '=':
                    self.advance()
                    self.advance()
                    self.tokens.append(Token(TokenType.GREATER_EQUALS, None, start_line, start_col,
                                           self.line, self.column))
                elif self.peek_char() == '>':
                    self.advance()
                    self.advance()
                    self.tokens.append(Token(TokenType.SHR, None, start_line, start_col,
                                           self.line, self.column))
                else:
                    self.advance()
                    self.tokens.append(Token(TokenType.GREATER, None, start_line, start_col,
                                           self.line, self.column))
            elif ch == '(':
                self.advance()
                self.tokens.append(Token(TokenType.LPAREN, None, start_line, start_col,
                                       self.line, self.column))
            elif ch == ')':
                self.advance()
                self.tokens.append(Token(TokenType.RPAREN, None, start_line, start_col,
                                       self.line, self.column))
            elif ch == '[':
                self.advance()
                self.tokens.append(Token(TokenType.LBRACKET, None, start_line, start_col,
                                       self.line, self.column))
            elif ch == ']':
                self.advance()
                self.tokens.append(Token(TokenType.RBRACKET, None, start_line, start_col,
                                       self.line, self.column))
            elif ch == '{':
                self.advance()
                self.tokens.append(Token(TokenType.LBRACE, None, start_line, start_col,
                                       self.line, self.column))
            elif ch == '}':
                self.advance()
                self.tokens.append(Token(TokenType.RBRACE, None, start_line, start_col,
                                       self.line, self.column))
            elif ch == ',':
                self.advance()
                self.tokens.append(Token(TokenType.COMMA, None, start_line, start_col,
                                       self.line, self.column))
            elif ch == ':':
                self.advance()
                self.tokens.append(Token(TokenType.COLON, None, start_line, start_col,
                                       self.line, self.column))
            elif ch == '.':
                if self.peek_char() == '.':
                    self.advance()
                    self.advance()
                    self.tokens.append(Token(TokenType.DOTDOT, None, start_line, start_col,
                                           self.line, self.column))
                else:
                    self.advance()
                    self.tokens.append(Token(TokenType.DOT, None, start_line, start_col,
                                           self.line, self.column))
            elif ch == '|':
                self.advance()
                self.tokens.append(Token(TokenType.PIPE, None, start_line, start_col,
                                       self.line, self.column))
            elif ch == '&':
                self.advance()
                self.tokens.append(Token(TokenType.AMPERSAND, None, start_line, start_col,
                                       self.line, self.column))
            elif ch == '^':
                self.advance()
                self.tokens.append(Token(TokenType.CARET, None, start_line, start_col,
                                       self.line, self.column))
            else:
                raise SyntaxError(f"Unexpected character '{ch}' at line {start_line}, col {start_col}")

        self.tokens.append(Token(TokenType.EOF, None, self.line, self.column,
                                self.line, self.column))
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
