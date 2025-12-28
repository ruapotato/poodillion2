#!/usr/bin/env python3
"""
Brainhair Lexer - Python Syntax Edition

Tokenizes Brainhair source code with Python-style syntax.
"""

from enum import Enum, auto
from dataclasses import dataclass
from typing import List, Optional

class TokenType(Enum):
    # Python-style keywords
    DEF = auto()          # def (replaces proc)
    CLASS = auto()        # class (replaces type ... = object)
    FROM = auto()         # from (for imports)
    IMPORT = auto()       # import
    AS = auto()           # as (for imports and with)
    RETURN = auto()
    IF = auto()
    ELIF = auto()
    ELSE = auto()
    WHILE = auto()
    FOR = auto()
    IN = auto()
    BREAK = auto()
    CONTINUE = auto()
    PASS = auto()         # pass statement
    WITH = auto()         # context managers
    RAISE = auto()        # raise exceptions (future)
    TRY = auto()          # try blocks (future)
    EXCEPT = auto()       # except blocks (future)
    FINALLY = auto()      # finally blocks (future)
    LAMBDA = auto()       # lambda expressions (future)
    YIELD = auto()        # generators (future)
    ASYNC = auto()        # async (future)
    AWAIT = auto()        # await (future)

    # Brainhair-specific keywords (systems programming)
    EXTERN = auto()       # external functions
    ASM = auto()          # inline assembly
    DEFER = auto()        # defer statement (RAII)
    MATCH = auto()        # pattern matching

    # Type system keywords
    FINAL = auto()        # Final[T] for constants (replaces const)

    # Python-style types (capitalized)
    PTR = auto()          # Ptr[T] - raw pointer
    LIST = auto()         # List[T] - growable array
    DICT = auto()         # Dict[K, V] - hash map
    TUPLE = auto()        # Tuple[A, B, ...] - fixed tuples
    OPTIONAL = auto()     # Optional[T] - T | None

    # Primitive types (keep explicit sizes)
    INT8 = auto()
    INT16 = auto()
    INT32 = auto()
    INT64 = auto()
    UINT8 = auto()
    UINT16 = auto()
    UINT32 = auto()
    UINT64 = auto()
    FLOAT32 = auto()
    FLOAT64 = auto()
    BOOL = auto()
    CHAR = auto()
    STR = auto()          # str type
    BYTES = auto()        # bytes type

    # Type aliases
    INT = auto()          # int = int32
    FLOAT = auto()        # float = float32

    # Enum keyword
    ENUM = auto()
    AUTO = auto()         # auto() for enum values

    # Python compatibility
    DATACLASS = auto()    # @dataclass decorator
    ISINSTANCE = auto()   # isinstance() builtin
    FIELD = auto()        # field() for dataclass
    PROPERTY = auto()     # @property decorator

    # Literals
    IDENT = auto()
    NUMBER = auto()
    STRING = auto()
    FSTRING = auto()      # f"..." format strings
    CHAR_LIT = auto()
    TRUE = auto()
    FALSE = auto()
    NONE = auto()         # None literal

    # Operators
    PLUS = auto()           # +
    MINUS = auto()          # -
    STAR = auto()           # *
    SLASH = auto()          # /
    DOUBLE_SLASH = auto()   # // (integer division)
    PERCENT = auto()        # %
    DOUBLE_STAR = auto()    # ** (power)

    # Comparison
    EQUALS = auto()         # =
    EQUALS_EQUALS = auto()  # ==
    NOT_EQUALS = auto()     # !=
    LESS = auto()           # <
    LESS_EQUALS = auto()    # <=
    GREATER = auto()        # >
    GREATER_EQUALS = auto() # >=

    # Compound assignment
    PLUS_EQUALS = auto()    # +=
    MINUS_EQUALS = auto()   # -=
    STAR_EQUALS = auto()    # *=
    SLASH_EQUALS = auto()   # /=
    DOUBLE_SLASH_EQUALS = auto()  # //=
    PERCENT_EQUALS = auto() # %=
    AMPERSAND_EQUALS = auto()  # &=
    PIPE_EQUALS = auto()    # |=
    CARET_EQUALS = auto()   # ^=
    SHL_EQUALS = auto()     # <<=
    SHR_EQUALS = auto()     # >>=

    # Bitwise
    SHL = auto()            # <<
    SHR = auto()            # >>
    PIPE = auto()           # |
    AMPERSAND = auto()      # &
    CARET = auto()          # ^
    TILDE = auto()          # ~ (bitwise not)

    # Logical (keywords)
    AND = auto()            # and
    OR = auto()             # or
    NOT = auto()            # not
    IS = auto()             # is (identity)
    IS_NOT = auto()         # is not
    IN_OP = auto()          # in (membership test)
    NOT_IN = auto()         # not in

    # Delimiters
    LPAREN = auto()         # (
    RPAREN = auto()         # )
    LBRACKET = auto()       # [
    RBRACKET = auto()       # ]
    LBRACE = auto()         # {
    RBRACE = auto()         # }
    COMMA = auto()          # ,
    COLON = auto()          # :
    SEMICOLON = auto()      # ;
    DOT = auto()            # .
    DOTDOT = auto()         # .. (range)
    ELLIPSIS = auto()       # ...
    ARROW = auto()          # -> (return type annotation)
    AT = auto()             # @ (decorators)

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
        self.at_line_start = True

        # Keywords - Python style
        self.keywords = {
            # Python keywords
            'def': TokenType.DEF,
            'class': TokenType.CLASS,
            'from': TokenType.FROM,
            'import': TokenType.IMPORT,
            'as': TokenType.AS,
            'return': TokenType.RETURN,
            'if': TokenType.IF,
            'elif': TokenType.ELIF,
            'else': TokenType.ELSE,
            'while': TokenType.WHILE,
            'for': TokenType.FOR,
            'in': TokenType.IN,
            'break': TokenType.BREAK,
            'continue': TokenType.CONTINUE,
            'pass': TokenType.PASS,
            'with': TokenType.WITH,
            'raise': TokenType.RAISE,
            'try': TokenType.TRY,
            'except': TokenType.EXCEPT,
            'finally': TokenType.FINALLY,
            'lambda': TokenType.LAMBDA,
            'yield': TokenType.YIELD,
            'async': TokenType.ASYNC,
            'await': TokenType.AWAIT,
            'and': TokenType.AND,
            'or': TokenType.OR,
            'not': TokenType.NOT,
            'is': TokenType.IS,
            'true': TokenType.TRUE,
            'false': TokenType.FALSE,
            'True': TokenType.TRUE,
            'False': TokenType.FALSE,
            'None': TokenType.NONE,

            # Brainhair-specific
            'extern': TokenType.EXTERN,
            'asm': TokenType.ASM,
            'defer': TokenType.DEFER,
            'match': TokenType.MATCH,

            # Type keywords
            'Final': TokenType.FINAL,
            'Ptr': TokenType.PTR,
            'List': TokenType.LIST,
            'Dict': TokenType.DICT,
            'Tuple': TokenType.TUPLE,
            'Optional': TokenType.OPTIONAL,
            'Enum': TokenType.ENUM,
            'auto': TokenType.AUTO,

            # Python compatibility
            'dataclass': TokenType.DATACLASS,
            'isinstance': TokenType.ISINSTANCE,
            # Note: 'field' and 'property' are kept as identifiers to avoid breaking existing code

            # Primitive types
            'int8': TokenType.INT8,
            'int16': TokenType.INT16,
            'int32': TokenType.INT32,
            'int64': TokenType.INT64,
            'uint8': TokenType.UINT8,
            'uint16': TokenType.UINT16,
            'uint32': TokenType.UINT32,
            'uint64': TokenType.UINT64,
            'float32': TokenType.FLOAT32,
            'float64': TokenType.FLOAT64,
            'bool': TokenType.BOOL,
            'char': TokenType.CHAR,
            'str': TokenType.STR,
            'bytes': TokenType.BYTES,

            # Type aliases
            'int': TokenType.INT,
            'float': TokenType.FLOAT,
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
                self.at_line_start = True
            else:
                self.column += 1
            self.pos += 1

    def get_position(self) -> tuple:
        return (self.line, self.column)

    def skip_whitespace_on_line(self):
        """Skip spaces and tabs but not newlines."""
        while self.current_char() in ' \t':
            self.advance()

    def skip_comment(self):
        if self.current_char() == '#':
            while self.current_char() and self.current_char() != '\n':
                self.advance()

    def count_indent(self) -> int:
        """Count indentation at start of line (spaces only, tab = 4 spaces)."""
        indent = 0
        pos = self.pos
        while pos < len(self.source):
            ch = self.source[pos]
            if ch == ' ':
                indent += 1
                pos += 1
            elif ch == '\t':
                indent += 4
                pos += 1
            else:
                break
        return indent

    def read_number(self) -> Token:
        start_line, start_col = self.line, self.column
        num_str = ''

        # Hex number
        if self.current_char() == '0' and self.peek_char() and self.peek_char() in 'xX':
            self.advance()  # 0
            self.advance()  # x
            while self.current_char() and self.current_char() in '0123456789abcdefABCDEF_':
                if self.current_char() != '_':
                    num_str += self.current_char()
                self.advance()
            return Token(TokenType.NUMBER, int(num_str, 16), start_line, start_col,
                        self.line, self.column)

        # Binary number
        if self.current_char() == '0' and self.peek_char() and self.peek_char() in 'bB':
            self.advance()  # 0
            self.advance()  # b
            while self.current_char() and self.current_char() in '01_':
                if self.current_char() != '_':
                    num_str += self.current_char()
                self.advance()
            return Token(TokenType.NUMBER, int(num_str, 2), start_line, start_col,
                        self.line, self.column)

        # Octal number
        if self.current_char() == '0' and self.peek_char() and self.peek_char() in 'oO':
            self.advance()  # 0
            self.advance()  # o
            while self.current_char() and self.current_char() in '01234567_':
                if self.current_char() != '_':
                    num_str += self.current_char()
                self.advance()
            return Token(TokenType.NUMBER, int(num_str, 8), start_line, start_col,
                        self.line, self.column)

        # Decimal number (with optional underscores)
        while self.current_char() and (self.current_char().isdigit() or self.current_char() == '_'):
            if self.current_char() != '_':
                num_str += self.current_char()
            self.advance()

        return Token(TokenType.NUMBER, int(num_str), start_line, start_col,
                    self.line, self.column)

    def read_string(self, is_fstring: bool = False) -> Token:
        start_line, start_col = self.line, self.column
        quote = self.current_char()
        self.advance()  # Skip opening quote

        # Check for triple quote
        triple = False
        if self.current_char() == quote and self.peek_char() == quote:
            triple = True
            self.advance()
            self.advance()

        string = ''
        while True:
            ch = self.current_char()
            if ch is None:
                raise SyntaxError(f"Unterminated string at line {start_line}")

            if triple:
                # Triple quoted string
                if ch == quote and self.peek_char() == quote and self.peek_char(2) == quote:
                    self.advance()
                    self.advance()
                    self.advance()
                    break
                string += ch
                self.advance()
            else:
                # Single quoted string
                if ch == quote:
                    self.advance()
                    break
                if ch == '\n':
                    raise SyntaxError(f"Newline in single-quoted string at line {self.line}")
                if ch == '\\':
                    self.advance()
                    esc = self.current_char()
                    if esc == 'n':
                        string += '\n'
                    elif esc == 't':
                        string += '\t'
                    elif esc == 'r':
                        string += '\r'
                    elif esc == '0':
                        string += '\0'
                    elif esc == '\\':
                        string += '\\'
                    elif esc == quote:
                        string += quote
                    elif esc == 'x':
                        # Hex escape \xNN
                        self.advance()
                        hex_chars = self.current_char()
                        self.advance()
                        hex_chars += self.current_char()
                        string += chr(int(hex_chars, 16))
                    else:
                        string += esc
                    self.advance()
                else:
                    string += ch
                    self.advance()

        token_type = TokenType.FSTRING if is_fstring else TokenType.STRING
        return Token(token_type, string, start_line, start_col, self.line, self.column)

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
            elif esc == 'r':
                ch = '\r'
            elif esc == '0':
                ch = '\0'
            elif esc == '\\':
                ch = '\\'
            elif esc == "'":
                ch = "'"
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
            ch = self.current_char()
            if not ch:
                break

            start_line, start_col = self.line, self.column

            # Handle newlines
            if ch == '\n':
                self.advance()
                self.tokens.append(Token(TokenType.NEWLINE, None, start_line, start_col,
                                       self.line, self.column))
                continue

            # Skip whitespace (but track for indentation)
            if ch in ' \t':
                self.skip_whitespace_on_line()
                continue

            # Comments
            if ch == '#':
                self.skip_comment()
                continue

            # F-strings
            if ch in 'fF' and self.peek_char() in '"\'':
                self.advance()  # Skip 'f'
                self.tokens.append(self.read_string(is_fstring=True))
                continue

            # Raw strings (r"...")
            if ch in 'rR' and self.peek_char() in '"\'':
                self.advance()  # Skip 'r'
                # TODO: Handle raw strings (no escape processing)
                self.tokens.append(self.read_string())
                continue

            # Byte strings (b"...")
            if ch in 'bB' and self.peek_char() in '"\'':
                self.advance()  # Skip 'b'
                self.tokens.append(self.read_string())
                continue

            # Numbers
            if ch.isdigit():
                self.tokens.append(self.read_number())
                continue

            # Strings
            if ch == '"' or ch == "'":
                self.tokens.append(self.read_string())
                continue

            # Identifiers and keywords
            if ch.isalpha() or ch == '_':
                self.tokens.append(self.read_identifier())
                continue

            # Multi-character operators
            if ch == '+':
                if self.peek_char() == '=':
                    self.advance()
                    self.advance()
                    self.tokens.append(Token(TokenType.PLUS_EQUALS, None, start_line, start_col,
                                           self.line, self.column))
                else:
                    self.advance()
                    self.tokens.append(Token(TokenType.PLUS, None, start_line, start_col,
                                           self.line, self.column))
            elif ch == '-':
                if self.peek_char() == '=':
                    self.advance()
                    self.advance()
                    self.tokens.append(Token(TokenType.MINUS_EQUALS, None, start_line, start_col,
                                           self.line, self.column))
                elif self.peek_char() == '>':
                    self.advance()
                    self.advance()
                    self.tokens.append(Token(TokenType.ARROW, None, start_line, start_col,
                                           self.line, self.column))
                else:
                    self.advance()
                    self.tokens.append(Token(TokenType.MINUS, None, start_line, start_col,
                                           self.line, self.column))
            elif ch == '*':
                if self.peek_char() == '*':
                    self.advance()
                    self.advance()
                    self.tokens.append(Token(TokenType.DOUBLE_STAR, None, start_line, start_col,
                                           self.line, self.column))
                elif self.peek_char() == '=':
                    self.advance()
                    self.advance()
                    self.tokens.append(Token(TokenType.STAR_EQUALS, None, start_line, start_col,
                                           self.line, self.column))
                else:
                    self.advance()
                    self.tokens.append(Token(TokenType.STAR, None, start_line, start_col,
                                           self.line, self.column))
            elif ch == '/':
                if self.peek_char() == '/':
                    if self.peek_char(2) == '=':
                        self.advance()
                        self.advance()
                        self.advance()
                        self.tokens.append(Token(TokenType.DOUBLE_SLASH_EQUALS, None, start_line, start_col,
                                               self.line, self.column))
                    else:
                        self.advance()
                        self.advance()
                        self.tokens.append(Token(TokenType.DOUBLE_SLASH, None, start_line, start_col,
                                               self.line, self.column))
                elif self.peek_char() == '=':
                    self.advance()
                    self.advance()
                    self.tokens.append(Token(TokenType.SLASH_EQUALS, None, start_line, start_col,
                                           self.line, self.column))
                else:
                    self.advance()
                    self.tokens.append(Token(TokenType.SLASH, None, start_line, start_col,
                                           self.line, self.column))
            elif ch == '%':
                if self.peek_char() == '=':
                    self.advance()
                    self.advance()
                    self.tokens.append(Token(TokenType.PERCENT_EQUALS, None, start_line, start_col,
                                           self.line, self.column))
                else:
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
                    if self.peek_char(2) == '=':
                        self.advance()
                        self.advance()
                        self.advance()
                        self.tokens.append(Token(TokenType.SHL_EQUALS, None, start_line, start_col,
                                               self.line, self.column))
                    else:
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
                    if self.peek_char(2) == '=':
                        self.advance()
                        self.advance()
                        self.advance()
                        self.tokens.append(Token(TokenType.SHR_EQUALS, None, start_line, start_col,
                                               self.line, self.column))
                    else:
                        self.advance()
                        self.advance()
                        self.tokens.append(Token(TokenType.SHR, None, start_line, start_col,
                                               self.line, self.column))
                else:
                    self.advance()
                    self.tokens.append(Token(TokenType.GREATER, None, start_line, start_col,
                                           self.line, self.column))
            elif ch == '&':
                if self.peek_char() == '=':
                    self.advance()
                    self.advance()
                    self.tokens.append(Token(TokenType.AMPERSAND_EQUALS, None, start_line, start_col,
                                           self.line, self.column))
                else:
                    self.advance()
                    self.tokens.append(Token(TokenType.AMPERSAND, None, start_line, start_col,
                                           self.line, self.column))
            elif ch == '|':
                if self.peek_char() == '=':
                    self.advance()
                    self.advance()
                    self.tokens.append(Token(TokenType.PIPE_EQUALS, None, start_line, start_col,
                                           self.line, self.column))
                else:
                    self.advance()
                    self.tokens.append(Token(TokenType.PIPE, None, start_line, start_col,
                                           self.line, self.column))
            elif ch == '^':
                if self.peek_char() == '=':
                    self.advance()
                    self.advance()
                    self.tokens.append(Token(TokenType.CARET_EQUALS, None, start_line, start_col,
                                           self.line, self.column))
                else:
                    self.advance()
                    self.tokens.append(Token(TokenType.CARET, None, start_line, start_col,
                                           self.line, self.column))
            elif ch == '~':
                self.advance()
                self.tokens.append(Token(TokenType.TILDE, None, start_line, start_col,
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
            elif ch == ';':
                self.advance()
                self.tokens.append(Token(TokenType.SEMICOLON, None, start_line, start_col,
                                       self.line, self.column))
            elif ch == '.':
                if self.peek_char() == '.':
                    if self.peek_char(2) == '.':
                        self.advance()
                        self.advance()
                        self.advance()
                        self.tokens.append(Token(TokenType.ELLIPSIS, None, start_line, start_col,
                                               self.line, self.column))
                    else:
                        self.advance()
                        self.advance()
                        self.tokens.append(Token(TokenType.DOTDOT, None, start_line, start_col,
                                               self.line, self.column))
                else:
                    self.advance()
                    self.tokens.append(Token(TokenType.DOT, None, start_line, start_col,
                                           self.line, self.column))
            elif ch == '@':
                self.advance()
                self.tokens.append(Token(TokenType.AT, None, start_line, start_col,
                                       self.line, self.column))
            elif ch == '\\':
                # Line continuation - skip backslash and following newline
                self.advance()
                if self.current_char() == '\n':
                    self.advance()  # Skip the newline
                # Otherwise just ignore the backslash
            else:
                raise SyntaxError(f"Unexpected character '{ch}' at line {start_line}, col {start_col}")

        self.tokens.append(Token(TokenType.EOF, None, self.line, self.column,
                                self.line, self.column))
        return self.tokens

# Test the lexer
if __name__ == '__main__':
    code = """
from lib.syscalls import *

# Constants
SYS_EXIT: Final[int32] = 1

@inline
def add(a: int32, b: int32) -> int32:
    return a + b

class Point:
    x: int32
    y: int32

    def move(self, dx: int32):
        self.x += dx

def main() -> int32:
    p: Ptr[int32] = Ptr[int32](0xB8000)
    p[0] = 0x0F41
    return 0
"""

    lexer = Lexer(code)
    tokens = lexer.tokenize()

    print("Tokens:")
    for token in tokens:
        print(f"  {token}")
