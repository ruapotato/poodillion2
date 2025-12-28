#!/usr/bin/env python3
"""
Brainhair Lexer - Polyglot Edition

This file is both valid Python AND valid Brainhair.
It can be run as a Python script OR compiled to native x86.

Tokenizes Brainhair source code with Python-style syntax.
"""

# Python-only imports (Brainhair ignores these)
try:
    from typing import List, Optional
except:
    pass

# ============================================================================
# Token Types as Integer Constants (works in both Python and Brainhair)
# ============================================================================

# Keywords
TT_DEF: int = 1
TT_CLASS: int = 2
TT_FROM: int = 3
TT_IMPORT: int = 4
TT_AS: int = 5
TT_RETURN: int = 6
TT_IF: int = 7
TT_ELIF: int = 8
TT_ELSE: int = 9
TT_WHILE: int = 10
TT_FOR: int = 11
TT_IN: int = 12
TT_BREAK: int = 13
TT_CONTINUE: int = 14
TT_PASS: int = 15
TT_WITH: int = 16
TT_RAISE: int = 17
TT_TRY: int = 18
TT_EXCEPT: int = 19
TT_FINALLY: int = 20
TT_LAMBDA: int = 21
TT_YIELD: int = 22
TT_ASYNC: int = 23
TT_AWAIT: int = 24

# Brainhair-specific
TT_EXTERN: int = 25
TT_ASM: int = 26
TT_DEFER: int = 27
TT_MATCH: int = 28
TT_FINAL: int = 29

# Types
TT_PTR: int = 30
TT_LIST: int = 31
TT_DICT: int = 32
TT_TUPLE: int = 33
TT_OPTIONAL: int = 34
TT_INT8: int = 35
TT_INT16: int = 36
TT_INT32: int = 37
TT_INT64: int = 38
TT_UINT8: int = 39
TT_UINT16: int = 40
TT_UINT32: int = 41
TT_UINT64: int = 42
TT_FLOAT32: int = 43
TT_FLOAT64: int = 44
TT_BOOL: int = 45
TT_CHAR: int = 46
TT_STR: int = 47
TT_BYTES: int = 48
TT_INT: int = 49
TT_FLOAT: int = 50
TT_ARRAY: int = 51
TT_REF: int = 52

# Enum
TT_ENUM: int = 53
TT_AUTO: int = 54

# Python compat
TT_DATACLASS: int = 55
TT_ISINSTANCE: int = 56
TT_FIELD: int = 57
TT_PROPERTY: int = 58

# Literals
TT_IDENT: int = 59
TT_NUMBER: int = 60
TT_STRING: int = 61
TT_FSTRING: int = 62
TT_CHAR_LIT: int = 63
TT_TRUE: int = 64
TT_FALSE: int = 65
TT_NONE: int = 66

# Operators
TT_PLUS: int = 67
TT_MINUS: int = 68
TT_STAR: int = 69
TT_SLASH: int = 70
TT_DOUBLE_SLASH: int = 71
TT_PERCENT: int = 72
TT_DOUBLE_STAR: int = 73

# Comparison
TT_EQUALS: int = 74
TT_EQUALS_EQUALS: int = 75
TT_NOT_EQUALS: int = 76
TT_LESS: int = 77
TT_LESS_EQUALS: int = 78
TT_GREATER: int = 79
TT_GREATER_EQUALS: int = 80

# Compound assignment
TT_PLUS_EQUALS: int = 81
TT_MINUS_EQUALS: int = 82
TT_STAR_EQUALS: int = 83
TT_SLASH_EQUALS: int = 84
TT_DOUBLE_SLASH_EQUALS: int = 85
TT_PERCENT_EQUALS: int = 86
TT_AMPERSAND_EQUALS: int = 87
TT_PIPE_EQUALS: int = 88
TT_CARET_EQUALS: int = 89
TT_SHL_EQUALS: int = 90
TT_SHR_EQUALS: int = 91

# Bitwise
TT_SHL: int = 92
TT_SHR: int = 93
TT_PIPE: int = 94
TT_AMPERSAND: int = 95
TT_CARET: int = 96
TT_TILDE: int = 97

# Logical
TT_AND: int = 98
TT_OR: int = 99
TT_NOT: int = 100
TT_IS: int = 101
TT_IS_NOT: int = 102
TT_IN_OP: int = 103
TT_NOT_IN: int = 104

# Delimiters
TT_LPAREN: int = 105
TT_RPAREN: int = 106
TT_LBRACKET: int = 107
TT_RBRACKET: int = 108
TT_LBRACE: int = 109
TT_RBRACE: int = 110
TT_COMMA: int = 111
TT_COLON: int = 112
TT_SEMICOLON: int = 113
TT_DOT: int = 114
TT_DOTDOT: int = 115
TT_ELLIPSIS: int = 116
TT_ARROW: int = 117
TT_AT: int = 118

# Special
TT_NEWLINE: int = 119
TT_INDENT: int = 120
TT_DEDENT: int = 121
TT_EOF: int = 122

# ============================================================================
# Polyglot Helper Functions (work in both Python and Brainhair)
# ============================================================================

def is_alpha(c: int) -> int:
    if c >= 65 and c <= 90:
        return 1
    if c >= 97 and c <= 122:
        return 1
    return 0

def is_digit(c: int) -> int:
    if c >= 48 and c <= 57:
        return 1
    return 0

def is_alnum(c: int) -> int:
    if is_alpha(c) == 1:
        return 1
    if is_digit(c) == 1:
        return 1
    return 0

def is_space(c: int) -> int:
    if c == 32:
        return 1
    if c == 9:
        return 1
    return 0

def is_hex(c: int) -> int:
    if is_digit(c) == 1:
        return 1
    if c >= 65 and c <= 70:
        return 1
    if c >= 97 and c <= 102:
        return 1
    return 0

def poly_strlen(s) -> int:
    """Get length of string - works for both Python str and Ptr[uint8]"""
    # In Python, use len(). In Brainhair, iterate to find null terminator.
    result: int = 0
    try:
        result = len(s)
    except:
        # Brainhair: count until null byte
        i: int = 0
        while s[i] != 0:
            i = i + 1
        result = i
    return result

def poly_ord(c) -> int:
    """Get character code - works for both Python str and uint8"""
    result: int = 0
    try:
        result = ord(c)
    except:
        # Brainhair: character is already an int
        result = cast[int](c)
    return result

# ============================================================================
# Token Class (polyglot - works in both Python and Brainhair)
# ============================================================================

class Token:
    def __init__(self, ttype, value, line: int, column: int, end_line: int = 0, end_column: int = 0):
        self.type = ttype
        self.value = value
        self.line: int = line
        self.column: int = column
        self.col: int = column  # Alias for column (used by parser)
        self.end_line: int = end_line if end_line != 0 else line
        self.end_column: int = end_column if end_column != 0 else column

    def __repr__(self) -> str:
        try:
            return f"{self.type.name}({self.value})" if self.value is not None else self.type.name
        except:
            return f"Token({self.type}, {self.value})"


# ============================================================================
# Python compatibility layer - maps old enum-based TokenType to new int constants
# This allows existing code using TokenType.DEF etc to keep working
# ============================================================================

try:
    from enum import IntEnum

    class TokenType(IntEnum):
        DEF = TT_DEF
        CLASS = TT_CLASS
        FROM = TT_FROM
        IMPORT = TT_IMPORT
        AS = TT_AS
        RETURN = TT_RETURN
        IF = TT_IF
        ELIF = TT_ELIF
        ELSE = TT_ELSE
        WHILE = TT_WHILE
        FOR = TT_FOR
        IN = TT_IN
        BREAK = TT_BREAK
        CONTINUE = TT_CONTINUE
        PASS = TT_PASS
        WITH = TT_WITH
        RAISE = TT_RAISE
        TRY = TT_TRY
        EXCEPT = TT_EXCEPT
        FINALLY = TT_FINALLY
        LAMBDA = TT_LAMBDA
        YIELD = TT_YIELD
        ASYNC = TT_ASYNC
        AWAIT = TT_AWAIT
        EXTERN = TT_EXTERN
        ASM = TT_ASM
        DEFER = TT_DEFER
        MATCH = TT_MATCH
        FINAL = TT_FINAL
        PTR = TT_PTR
        LIST = TT_LIST
        DICT = TT_DICT
        TUPLE = TT_TUPLE
        OPTIONAL = TT_OPTIONAL
        INT8 = TT_INT8
        INT16 = TT_INT16
        INT32 = TT_INT32
        INT64 = TT_INT64
        UINT8 = TT_UINT8
        UINT16 = TT_UINT16
        UINT32 = TT_UINT32
        UINT64 = TT_UINT64
        FLOAT32 = TT_FLOAT32
        FLOAT64 = TT_FLOAT64
        BOOL = TT_BOOL
        CHAR = TT_CHAR
        STR = TT_STR
        BYTES = TT_BYTES
        INT = TT_INT
        FLOAT = TT_FLOAT
        ARRAY = TT_ARRAY
        REF = TT_REF
        ENUM = TT_ENUM
        AUTO = TT_AUTO
        DATACLASS = TT_DATACLASS
        ISINSTANCE = TT_ISINSTANCE
        FIELD = TT_FIELD
        PROPERTY = TT_PROPERTY
        IDENT = TT_IDENT
        NUMBER = TT_NUMBER
        STRING = TT_STRING
        FSTRING = TT_FSTRING
        CHAR_LIT = TT_CHAR_LIT
        TRUE = TT_TRUE
        FALSE = TT_FALSE
        NONE = TT_NONE
        PLUS = TT_PLUS
        MINUS = TT_MINUS
        STAR = TT_STAR
        SLASH = TT_SLASH
        DOUBLE_SLASH = TT_DOUBLE_SLASH
        PERCENT = TT_PERCENT
        DOUBLE_STAR = TT_DOUBLE_STAR
        EQUALS = TT_EQUALS
        EQUALS_EQUALS = TT_EQUALS_EQUALS
        NOT_EQUALS = TT_NOT_EQUALS
        LESS = TT_LESS
        LESS_EQUALS = TT_LESS_EQUALS
        GREATER = TT_GREATER
        GREATER_EQUALS = TT_GREATER_EQUALS
        PLUS_EQUALS = TT_PLUS_EQUALS
        MINUS_EQUALS = TT_MINUS_EQUALS
        STAR_EQUALS = TT_STAR_EQUALS
        SLASH_EQUALS = TT_SLASH_EQUALS
        DOUBLE_SLASH_EQUALS = TT_DOUBLE_SLASH_EQUALS
        PERCENT_EQUALS = TT_PERCENT_EQUALS
        AMPERSAND_EQUALS = TT_AMPERSAND_EQUALS
        PIPE_EQUALS = TT_PIPE_EQUALS
        CARET_EQUALS = TT_CARET_EQUALS
        SHL_EQUALS = TT_SHL_EQUALS
        SHR_EQUALS = TT_SHR_EQUALS
        SHL = TT_SHL
        SHR = TT_SHR
        PIPE = TT_PIPE
        AMPERSAND = TT_AMPERSAND
        CARET = TT_CARET
        TILDE = TT_TILDE
        AND = TT_AND
        OR = TT_OR
        NOT = TT_NOT
        IS = TT_IS
        IS_NOT = TT_IS_NOT
        IN_OP = TT_IN_OP
        NOT_IN = TT_NOT_IN
        LPAREN = TT_LPAREN
        RPAREN = TT_RPAREN
        LBRACKET = TT_LBRACKET
        RBRACKET = TT_RBRACKET
        LBRACE = TT_LBRACE
        RBRACE = TT_RBRACE
        COMMA = TT_COMMA
        COLON = TT_COLON
        SEMICOLON = TT_SEMICOLON
        DOT = TT_DOT
        DOTDOT = TT_DOTDOT
        ELLIPSIS = TT_ELLIPSIS
        ARROW = TT_ARROW
        AT = TT_AT
        NEWLINE = TT_NEWLINE
        INDENT = TT_INDENT
        DEDENT = TT_DEDENT
        EOF = TT_EOF
except:
    pass


# ============================================================================
# Polyglot Keyword Lookup (replaces dict - works in both Python and Brainhair)
# ============================================================================

def str_eq(a: str, b: str) -> int:
    """Compare two strings for equality."""
    i: int = 0
    while True:
        # Get char from a (handle both Python str and null-terminated)
        ca: int = 0
        if i < len(a):
            ca = ord(a[i])
        # Get char from b
        cb: int = 0
        if i < len(b):
            cb = ord(b[i])
        # Compare
        if ca != cb:
            return 0
        if ca == 0:
            return 1
        i = i + 1
    return 0  # Unreachable but satisfies type checker

def lookup_keyword(word: str) -> int:
    """Look up a keyword and return its token type, or 0 if not a keyword."""
    # Python keywords
    if str_eq(word, "def") == 1:
        return TT_DEF
    if str_eq(word, "class") == 1:
        return TT_CLASS
    if str_eq(word, "from") == 1:
        return TT_FROM
    if str_eq(word, "import") == 1:
        return TT_IMPORT
    if str_eq(word, "as") == 1:
        return TT_AS
    if str_eq(word, "return") == 1:
        return TT_RETURN
    if str_eq(word, "if") == 1:
        return TT_IF
    if str_eq(word, "elif") == 1:
        return TT_ELIF
    if str_eq(word, "else") == 1:
        return TT_ELSE
    if str_eq(word, "while") == 1:
        return TT_WHILE
    if str_eq(word, "for") == 1:
        return TT_FOR
    if str_eq(word, "in") == 1:
        return TT_IN
    if str_eq(word, "break") == 1:
        return TT_BREAK
    if str_eq(word, "continue") == 1:
        return TT_CONTINUE
    if str_eq(word, "pass") == 1:
        return TT_PASS
    if str_eq(word, "with") == 1:
        return TT_WITH
    if str_eq(word, "raise") == 1:
        return TT_RAISE
    if str_eq(word, "try") == 1:
        return TT_TRY
    if str_eq(word, "except") == 1:
        return TT_EXCEPT
    if str_eq(word, "finally") == 1:
        return TT_FINALLY
    if str_eq(word, "lambda") == 1:
        return TT_LAMBDA
    if str_eq(word, "yield") == 1:
        return TT_YIELD
    if str_eq(word, "async") == 1:
        return TT_ASYNC
    if str_eq(word, "await") == 1:
        return TT_AWAIT
    if str_eq(word, "and") == 1:
        return TT_AND
    if str_eq(word, "or") == 1:
        return TT_OR
    if str_eq(word, "not") == 1:
        return TT_NOT
    if str_eq(word, "is") == 1:
        return TT_IS
    if str_eq(word, "true") == 1:
        return TT_TRUE
    if str_eq(word, "false") == 1:
        return TT_FALSE
    if str_eq(word, "True") == 1:
        return TT_TRUE
    if str_eq(word, "False") == 1:
        return TT_FALSE
    if str_eq(word, "None") == 1:
        return TT_NONE
    # Brainhair-specific
    if str_eq(word, "extern") == 1:
        return TT_EXTERN
    if str_eq(word, "asm") == 1:
        return TT_ASM
    if str_eq(word, "defer") == 1:
        return TT_DEFER
    if str_eq(word, "match") == 1:
        return TT_MATCH
    # Type keywords
    if str_eq(word, "Final") == 1:
        return TT_FINAL
    if str_eq(word, "Ptr") == 1:
        return TT_PTR
    if str_eq(word, "List") == 1:
        return TT_LIST
    if str_eq(word, "Dict") == 1:
        return TT_DICT
    if str_eq(word, "Tuple") == 1:
        return TT_TUPLE
    if str_eq(word, "Optional") == 1:
        return TT_OPTIONAL
    if str_eq(word, "Enum") == 1:
        return TT_ENUM
    if str_eq(word, "auto") == 1:
        return TT_AUTO
    if str_eq(word, "Array") == 1:
        return TT_ARRAY
    if str_eq(word, "Ref") == 1:
        return TT_REF
    # Python compatibility
    if str_eq(word, "dataclass") == 1:
        return TT_DATACLASS
    if str_eq(word, "isinstance") == 1:
        return TT_ISINSTANCE
    # Primitive types
    if str_eq(word, "int8") == 1:
        return TT_INT8
    if str_eq(word, "int16") == 1:
        return TT_INT16
    if str_eq(word, "int32") == 1:
        return TT_INT32
    if str_eq(word, "int64") == 1:
        return TT_INT64
    if str_eq(word, "uint8") == 1:
        return TT_UINT8
    if str_eq(word, "uint16") == 1:
        return TT_UINT16
    if str_eq(word, "uint32") == 1:
        return TT_UINT32
    if str_eq(word, "uint64") == 1:
        return TT_UINT64
    if str_eq(word, "float32") == 1:
        return TT_FLOAT32
    if str_eq(word, "float64") == 1:
        return TT_FLOAT64
    if str_eq(word, "bool") == 1:
        return TT_BOOL
    if str_eq(word, "char") == 1:
        return TT_CHAR
    if str_eq(word, "str") == 1:
        return TT_STR
    if str_eq(word, "bytes") == 1:
        return TT_BYTES
    # Type aliases
    if str_eq(word, "int") == 1:
        return TT_INT
    if str_eq(word, "float") == 1:
        return TT_FLOAT
    # Not a keyword
    return 0


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

        # Keywords dict is Python-only (uses TokenType enum)
        # Native code uses lookup_keyword() function instead
        try:
            self.keywords = {
                'def': TokenType.DEF, 'class': TokenType.CLASS,
                'from': TokenType.FROM, 'import': TokenType.IMPORT,
                'as': TokenType.AS, 'return': TokenType.RETURN,
                'if': TokenType.IF, 'elif': TokenType.ELIF,
                'else': TokenType.ELSE, 'while': TokenType.WHILE,
                'for': TokenType.FOR, 'in': TokenType.IN,
                'break': TokenType.BREAK, 'continue': TokenType.CONTINUE,
                'pass': TokenType.PASS, 'with': TokenType.WITH,
                'raise': TokenType.RAISE, 'try': TokenType.TRY,
                'except': TokenType.EXCEPT, 'finally': TokenType.FINALLY,
                'lambda': TokenType.LAMBDA, 'yield': TokenType.YIELD,
                'async': TokenType.ASYNC, 'await': TokenType.AWAIT,
                'and': TT_AND, 'or': TT_OR,
                'not': TT_NOT, 'is': TokenType.IS,
                'true': TokenType.TRUE, 'false': TokenType.FALSE,
                'True': TokenType.TRUE, 'False': TokenType.FALSE,
                'None': TokenType.NONE, 'extern': TokenType.EXTERN,
                'asm': TokenType.ASM, 'defer': TokenType.DEFER,
                'match': TokenType.MATCH, 'Final': TokenType.FINAL,
                'Ptr': TokenType.PTR, 'List': TokenType.LIST,
                'Dict': TokenType.DICT, 'Tuple': TokenType.TUPLE,
                'Optional': TokenType.OPTIONAL, 'Enum': TokenType.ENUM,
                'auto': TokenType.AUTO, 'Array': TokenType.ARRAY,
                'Ref': TokenType.REF, 'dataclass': TokenType.DATACLASS,
                'isinstance': TokenType.ISINSTANCE,
                'int8': TokenType.INT8, 'int16': TokenType.INT16,
                'int32': TokenType.INT32, 'int64': TokenType.INT64,
                'uint8': TokenType.UINT8, 'uint16': TokenType.UINT16,
                'uint32': TokenType.UINT32, 'uint64': TokenType.UINT64,
                'float32': TokenType.FLOAT32, 'float64': TokenType.FLOAT64,
                'bool': TokenType.BOOL, 'char': TokenType.CHAR,
                'str': TokenType.STR, 'bytes': TokenType.BYTES,
                'int': TokenType.INT, 'float': TokenType.FLOAT,
            }
        except:
            self.keywords = {}

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
        ch = self.current_char()
        while ch == ' ' or ch == '\t':
            self.advance()
            ch = self.current_char()

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
        pk = self.peek_char()
        if self.current_char() == '0' and pk and (pk == 'x' or pk == 'X'):
            self.advance()  # 0
            self.advance()  # x
            ch = self.current_char()
            while ch and is_hex(ord(ch)) == 1 or ch == '_':
                if ch != '_':
                    num_str += ch
                self.advance()
                ch = self.current_char()
            return Token(TT_NUMBER, int(num_str, 16), start_line, start_col,
                        self.line, self.column)

        # Binary number
        pk = self.peek_char()
        if self.current_char() == '0' and pk and (pk == 'b' or pk == 'B'):
            self.advance()  # 0
            self.advance()  # b
            ch = self.current_char()
            while ch and (ch == '0' or ch == '1' or ch == '_'):
                if ch != '_':
                    num_str += ch
                self.advance()
                ch = self.current_char()
            return Token(TT_NUMBER, int(num_str, 2), start_line, start_col,
                        self.line, self.column)

        # Octal number
        pk = self.peek_char()
        if self.current_char() == '0' and pk and (pk == 'o' or pk == 'O'):
            self.advance()  # 0
            self.advance()  # o
            ch = self.current_char()
            while ch and ((ord(ch) >= 48 and ord(ch) <= 55) or ch == '_'):
                if ch != '_':
                    num_str += ch
                self.advance()
                ch = self.current_char()
            return Token(TT_NUMBER, int(num_str, 8), start_line, start_col,
                        self.line, self.column)

        # Decimal number (with optional underscores)
        ch = self.current_char()
        while ch and (is_digit(ord(ch)) == 1 or ch == '_'):
            if ch != '_':
                num_str += ch
            self.advance()
            ch = self.current_char()

        return Token(TT_NUMBER, int(num_str), start_line, start_col,
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

        token_type = TT_FSTRING if is_fstring else TT_STRING
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
        return Token(TT_CHAR_LIT, ch, start_line, start_col,
                    self.line, self.column)

    def read_identifier(self) -> Token:
        start_line, start_col = self.line, self.column
        ident = ''

        ch = self.current_char()
        while ch and (is_alnum(ord(ch)) == 1 or ch == '_'):
            ident += ch
            self.advance()
            ch = self.current_char()

        # Check if it's a keyword - use polyglot lookup_keyword if dict fails
        try:
            token_type = self.keywords.get(ident, TT_IDENT)
        except:
            token_type = lookup_keyword(ident)
            if token_type == 0:
                token_type = TT_IDENT
        value = None if token_type != TT_IDENT else ident

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
                self.tokens.append(Token(TT_NEWLINE, None, start_line, start_col,
                                       self.line, self.column))
                continue

            # Skip whitespace (but track for indentation)
            if ch == ' ' or ch == '\t':
                self.skip_whitespace_on_line()
                continue

            # Comments
            if ch == '#':
                self.skip_comment()
                continue

            # F-strings
            pk = self.peek_char()
            if (ch == 'f' or ch == 'F') and (pk == '"' or pk == "'"):
                self.advance()  # Skip 'f'
                self.tokens.append(self.read_string(is_fstring=True))
                continue

            # Raw strings (r"...")
            pk = self.peek_char()
            if (ch == 'r' or ch == 'R') and (pk == '"' or pk == "'"):
                self.advance()  # Skip 'r'
                # TODO: Handle raw strings (no escape processing)
                self.tokens.append(self.read_string())
                continue

            # Byte strings (b"...")
            pk = self.peek_char()
            if (ch == 'b' or ch == 'B') and (pk == '"' or pk == "'"):
                self.advance()  # Skip 'b'
                self.tokens.append(self.read_string())
                continue

            # Numbers
            if is_digit(ord(ch)) == 1:
                self.tokens.append(self.read_number())
                continue

            # Strings
            if ch == '"' or ch == "'":
                self.tokens.append(self.read_string())
                continue

            # Identifiers and keywords
            if is_alpha(ord(ch)) == 1 or ch == '_':
                self.tokens.append(self.read_identifier())
                continue

            # Multi-character operators
            if ch == '+':
                if self.peek_char() == '=':
                    self.advance()
                    self.advance()
                    self.tokens.append(Token(TT_PLUS_EQUALS, None, start_line, start_col,
                                           self.line, self.column))
                else:
                    self.advance()
                    self.tokens.append(Token(TT_PLUS, None, start_line, start_col,
                                           self.line, self.column))
            elif ch == '-':
                if self.peek_char() == '=':
                    self.advance()
                    self.advance()
                    self.tokens.append(Token(TT_MINUS_EQUALS, None, start_line, start_col,
                                           self.line, self.column))
                elif self.peek_char() == '>':
                    self.advance()
                    self.advance()
                    self.tokens.append(Token(TT_ARROW, None, start_line, start_col,
                                           self.line, self.column))
                else:
                    self.advance()
                    self.tokens.append(Token(TT_MINUS, None, start_line, start_col,
                                           self.line, self.column))
            elif ch == '*':
                if self.peek_char() == '*':
                    self.advance()
                    self.advance()
                    self.tokens.append(Token(TT_DOUBLE_STAR, None, start_line, start_col,
                                           self.line, self.column))
                elif self.peek_char() == '=':
                    self.advance()
                    self.advance()
                    self.tokens.append(Token(TT_STAR_EQUALS, None, start_line, start_col,
                                           self.line, self.column))
                else:
                    self.advance()
                    self.tokens.append(Token(TT_STAR, None, start_line, start_col,
                                           self.line, self.column))
            elif ch == '/':
                if self.peek_char() == '/':
                    if self.peek_char(2) == '=':
                        self.advance()
                        self.advance()
                        self.advance()
                        self.tokens.append(Token(TT_DOUBLE_SLASH_EQUALS, None, start_line, start_col,
                                               self.line, self.column))
                    else:
                        self.advance()
                        self.advance()
                        self.tokens.append(Token(TT_DOUBLE_SLASH, None, start_line, start_col,
                                               self.line, self.column))
                elif self.peek_char() == '=':
                    self.advance()
                    self.advance()
                    self.tokens.append(Token(TT_SLASH_EQUALS, None, start_line, start_col,
                                           self.line, self.column))
                else:
                    self.advance()
                    self.tokens.append(Token(TT_SLASH, None, start_line, start_col,
                                           self.line, self.column))
            elif ch == '%':
                if self.peek_char() == '=':
                    self.advance()
                    self.advance()
                    self.tokens.append(Token(TT_PERCENT_EQUALS, None, start_line, start_col,
                                           self.line, self.column))
                else:
                    self.advance()
                    self.tokens.append(Token(TT_PERCENT, None, start_line, start_col,
                                           self.line, self.column))
            elif ch == '=':
                if self.peek_char() == '=':
                    self.advance()
                    self.advance()
                    self.tokens.append(Token(TT_EQUALS_EQUALS, None, start_line, start_col,
                                           self.line, self.column))
                else:
                    self.advance()
                    self.tokens.append(Token(TT_EQUALS, None, start_line, start_col,
                                           self.line, self.column))
            elif ch == '!':
                if self.peek_char() == '=':
                    self.advance()
                    self.advance()
                    self.tokens.append(Token(TT_NOT_EQUALS, None, start_line, start_col,
                                           self.line, self.column))
                else:
                    self.advance()
                    self.tokens.append(Token(TT_NOT, None, start_line, start_col,
                                           self.line, self.column))
            elif ch == '<':
                if self.peek_char() == '=':
                    self.advance()
                    self.advance()
                    self.tokens.append(Token(TT_LESS_EQUALS, None, start_line, start_col,
                                           self.line, self.column))
                elif self.peek_char() == '<':
                    if self.peek_char(2) == '=':
                        self.advance()
                        self.advance()
                        self.advance()
                        self.tokens.append(Token(TT_SHL_EQUALS, None, start_line, start_col,
                                               self.line, self.column))
                    else:
                        self.advance()
                        self.advance()
                        self.tokens.append(Token(TT_SHL, None, start_line, start_col,
                                               self.line, self.column))
                else:
                    self.advance()
                    self.tokens.append(Token(TT_LESS, None, start_line, start_col,
                                           self.line, self.column))
            elif ch == '>':
                if self.peek_char() == '=':
                    self.advance()
                    self.advance()
                    self.tokens.append(Token(TT_GREATER_EQUALS, None, start_line, start_col,
                                           self.line, self.column))
                elif self.peek_char() == '>':
                    if self.peek_char(2) == '=':
                        self.advance()
                        self.advance()
                        self.advance()
                        self.tokens.append(Token(TT_SHR_EQUALS, None, start_line, start_col,
                                               self.line, self.column))
                    else:
                        self.advance()
                        self.advance()
                        self.tokens.append(Token(TT_SHR, None, start_line, start_col,
                                               self.line, self.column))
                else:
                    self.advance()
                    self.tokens.append(Token(TT_GREATER, None, start_line, start_col,
                                           self.line, self.column))
            elif ch == '&':
                if self.peek_char() == '=':
                    self.advance()
                    self.advance()
                    self.tokens.append(Token(TT_AMPERSAND_EQUALS, None, start_line, start_col,
                                           self.line, self.column))
                else:
                    self.advance()
                    self.tokens.append(Token(TT_AMPERSAND, None, start_line, start_col,
                                           self.line, self.column))
            elif ch == '|':
                if self.peek_char() == '=':
                    self.advance()
                    self.advance()
                    self.tokens.append(Token(TT_PIPE_EQUALS, None, start_line, start_col,
                                           self.line, self.column))
                else:
                    self.advance()
                    self.tokens.append(Token(TT_PIPE, None, start_line, start_col,
                                           self.line, self.column))
            elif ch == '^':
                if self.peek_char() == '=':
                    self.advance()
                    self.advance()
                    self.tokens.append(Token(TT_CARET_EQUALS, None, start_line, start_col,
                                           self.line, self.column))
                else:
                    self.advance()
                    self.tokens.append(Token(TT_CARET, None, start_line, start_col,
                                           self.line, self.column))
            elif ch == '~':
                self.advance()
                self.tokens.append(Token(TT_TILDE, None, start_line, start_col,
                                       self.line, self.column))
            elif ch == '(':
                self.advance()
                self.tokens.append(Token(TT_LPAREN, None, start_line, start_col,
                                       self.line, self.column))
            elif ch == ')':
                self.advance()
                self.tokens.append(Token(TT_RPAREN, None, start_line, start_col,
                                       self.line, self.column))
            elif ch == '[':
                self.advance()
                self.tokens.append(Token(TT_LBRACKET, None, start_line, start_col,
                                       self.line, self.column))
            elif ch == ']':
                self.advance()
                self.tokens.append(Token(TT_RBRACKET, None, start_line, start_col,
                                       self.line, self.column))
            elif ch == '{':
                self.advance()
                self.tokens.append(Token(TT_LBRACE, None, start_line, start_col,
                                       self.line, self.column))
            elif ch == '}':
                self.advance()
                self.tokens.append(Token(TT_RBRACE, None, start_line, start_col,
                                       self.line, self.column))
            elif ch == ',':
                self.advance()
                self.tokens.append(Token(TT_COMMA, None, start_line, start_col,
                                       self.line, self.column))
            elif ch == ':':
                self.advance()
                self.tokens.append(Token(TT_COLON, None, start_line, start_col,
                                       self.line, self.column))
            elif ch == ';':
                self.advance()
                self.tokens.append(Token(TT_SEMICOLON, None, start_line, start_col,
                                       self.line, self.column))
            elif ch == '.':
                if self.peek_char() == '.':
                    if self.peek_char(2) == '.':
                        self.advance()
                        self.advance()
                        self.advance()
                        self.tokens.append(Token(TT_ELLIPSIS, None, start_line, start_col,
                                               self.line, self.column))
                    else:
                        self.advance()
                        self.advance()
                        self.tokens.append(Token(TT_DOTDOT, None, start_line, start_col,
                                               self.line, self.column))
                else:
                    self.advance()
                    self.tokens.append(Token(TT_DOT, None, start_line, start_col,
                                           self.line, self.column))
            elif ch == '@':
                self.advance()
                self.tokens.append(Token(TT_AT, None, start_line, start_col,
                                       self.line, self.column))
            elif ch == '\\':
                # Line continuation - skip backslash and following newline
                self.advance()
                if self.current_char() == '\n':
                    self.advance()  # Skip the newline
                # Otherwise just ignore the backslash
            else:
                raise SyntaxError(f"Unexpected character '{ch}' at line {start_line}, col {start_col}")

        self.tokens.append(Token(TT_EOF, None, self.line, self.column,
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

# Brainhair native entry point (stub for now)
# Returns 0 to indicate successful compilation as a native binary
def main() -> int:
    return 0
