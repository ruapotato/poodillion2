#!/usr/bin/env python3
"""
Brainhair Lexer - Polyglot Edition

This file is both valid Python AND valid Brainhair.
It can be run as a Python script OR compiled to native x86.

Tokenizes Brainhair source code with Python-style syntax.
"""

# Python-only imports and type aliases (Brainhair ignores these)
try:
    from typing import List, Optional
    # In Python, 'char' is just a string - define alias for compatibility
    char = str
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

# Brainhair native syntax
TT_VAR: int = 123
TT_DISCARD: int = 124
TT_CONST: int = 125

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
        VAR = TT_VAR
        DISCARD = TT_DISCARD
        CONST = TT_CONST
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
    if str_eq(word, "Array") == 1 or str_eq(word, "array") == 1:
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
    # Brainhair native keywords
    if str_eq(word, "var") == 1:
        return TT_VAR
    if str_eq(word, "discard") == 1:
        return TT_DISCARD
    if str_eq(word, "const") == 1:
        return TT_CONST
    # Not a keyword
    return 0


def get_keyword_name(tt: int) -> str:
    """Get the keyword name for a token type, or empty string if not a keyword."""
    # Python keywords
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
    if tt == TT_LAMBDA:
        return "lambda"
    if tt == TT_YIELD:
        return "yield"
    if tt == TT_ASYNC:
        return "async"
    if tt == TT_AWAIT:
        return "await"
    if tt == TT_AND:
        return "and"
    if tt == TT_OR:
        return "or"
    if tt == TT_NOT:
        return "not"
    if tt == TT_IS:
        return "is"
    if tt == TT_TRUE:
        return "true"
    if tt == TT_FALSE:
        return "false"
    if tt == TT_NONE:
        return "none"
    # Brainhair-specific
    if tt == TT_EXTERN:
        return "extern"
    if tt == TT_ASM:
        return "asm"
    if tt == TT_DEFER:
        return "defer"
    if tt == TT_MATCH:
        return "match"
    # Type keywords (these can be used as names in some contexts)
    if tt == TT_FINAL:
        return "final"
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
    if tt == TT_ENUM:
        return "enum"
    if tt == TT_AUTO:
        return "auto"
    if tt == TT_ARRAY:
        return "array"
    if tt == TT_REF:
        return "ref"
    if tt == TT_DATACLASS:
        return "dataclass"
    if tt == TT_ISINSTANCE:
        return "isinstance"
    # Primitive types
    if tt == TT_INT8:
        return "int8"
    if tt == TT_INT16:
        return "int16"
    if tt == TT_INT32:
        return "int32"
    if tt == TT_INT64:
        return "int64"
    if tt == TT_UINT8:
        return "uint8"
    if tt == TT_UINT16:
        return "uint16"
    if tt == TT_UINT32:
        return "uint32"
    if tt == TT_UINT64:
        return "uint64"
    if tt == TT_FLOAT32:
        return "float32"
    if tt == TT_FLOAT64:
        return "float64"
    if tt == TT_BOOL:
        return "bool"
    if tt == TT_CHAR:
        return "char"
    if tt == TT_STR:
        return "str"
    if tt == TT_BYTES:
        return "bytes"
    if tt == TT_INT:
        return "int"
    if tt == TT_FLOAT:
        return "float"
    if tt == TT_VAR:
        return "var"
    if tt == TT_DISCARD:
        return "discard"
    if tt == TT_CONST:
        return "const"
    if tt == TT_PROPERTY:
        return "property"
    if tt == TT_FIELD:
        return "field"
    # Not a keyword
    return ""


class Lexer:
    def __init__(self, source: str):
        self.source = source
        self.pos = 0
        self.line = 1
        self.column = 1
        self.tokens: List[Token] = []

        # Track indentation for Python-style blocks
        self.indent_stack: List[int] = [0]
        self.at_line_start: bool = True

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
                'auto': TokenType.AUTO, 'Array': TokenType.ARRAY, 'array': TokenType.ARRAY,
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
                'var': TokenType.VAR, 'discard': TokenType.DISCARD,
                'const': TokenType.CONST,
            }
        except:
            self.keywords = {}

    def at_end(self) -> bool:
        """Return True if at end of input."""
        return self.pos >= len(self.source)

    def current_char(self) -> char:
        """Return current character. Check at_end() before calling."""
        return self.source[self.pos]

    def peek_char(self, offset: int = 1) -> char:
        """Return character at offset. Returns space if out of bounds."""
        pos: int = self.pos + offset
        if pos >= len(self.source):
            return ' '
        return self.source[pos]

    def peek_valid(self, offset: int = 1) -> bool:
        """Return True if peek offset is valid."""
        return self.pos + offset < len(self.source)

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
        while not self.at_end():
            ch: char = self.current_char()
            if ch == ' ' or ch == '\t':
                self.advance()
            else:
                break

    def skip_comment(self):
        if self.current_char() == '#':
            while not self.at_end() and self.current_char() != '\n':
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
        if self.current_char() == '0' and self.peek_valid() and (pk == 'x' or pk == 'X'):
            self.advance()  # 0
            self.advance()  # x
            ch = self.current_char()
            while not self.at_end() and (is_hex(ord(ch)) == 1 or ch == '_'):
                if ch != '_':
                    num_str += ch
                self.advance()
                if self.at_end():
                    break
                ch = self.current_char()
            return Token(TT_NUMBER, int(num_str, 16), start_line, start_col,
                        self.line, self.column)

        # Binary number
        pk = self.peek_char()
        if self.current_char() == '0' and self.peek_valid() and (pk == 'b' or pk == 'B'):
            self.advance()  # 0
            self.advance()  # b
            ch = self.current_char()
            while not self.at_end() and (ch == '0' or ch == '1' or ch == '_'):
                if ch != '_':
                    num_str += ch
                self.advance()
                if self.at_end():
                    break
                ch = self.current_char()
            return Token(TT_NUMBER, int(num_str, 2), start_line, start_col,
                        self.line, self.column)

        # Octal number
        pk = self.peek_char()
        if self.current_char() == '0' and self.peek_valid() and (pk == 'o' or pk == 'O'):
            self.advance()  # 0
            self.advance()  # o
            ch = self.current_char()
            while not self.at_end() and ((ord(ch) >= 48 and ord(ch) <= 55) or ch == '_'):
                if ch != '_':
                    num_str += ch
                self.advance()
                if self.at_end():
                    break
                ch = self.current_char()
            return Token(TT_NUMBER, int(num_str, 8), start_line, start_col,
                        self.line, self.column)

        # Decimal number (with optional underscores)
        ch = self.current_char()
        while not self.at_end() and (is_digit(ord(ch)) == 1 or ch == '_'):
            if ch != '_':
                num_str += ch
            self.advance()
            if self.at_end():
                break
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
            ch: char = self.current_char()
            if self.at_end():
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

        while not self.at_end():
            ch = self.current_char()
            if is_alnum(ord(ch)) == 1 or ch == '_':
                ident += ch
                self.advance()
            else:
                break

        # Check if it's a keyword - use lookup_keyword directly
        # (Native code doesn't support try/except with dict access)
        token_type: int = lookup_keyword(ident)
        if token_type == 0:
            token_type = TT_IDENT
        value = None if token_type != TT_IDENT else ident

        return Token(token_type, value, start_line, start_col,
                    self.line, self.column)

    def tokenize(self) -> List[Token]:
        while not self.at_end():
            ch: char = self.current_char()

            start_line: int = self.line
            start_col: int = self.column

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

            # Strings (double quotes and single quotes)
            # In Python-compatible mode, single quotes are strings too
            if ch == '"':
                self.tokens.append(self.read_string())
                continue
            if ch == "'":
                # Check if it's a single char followed by closing quote (char literal)
                # or a multi-char string
                next_char = self.peek_char()
                if self.peek_valid():
                    # Save position for lookahead
                    pos = self.pos
                    saved_col = self.column
                    self.advance()  # skip opening '

                    if next_char == '\\':
                        # Escape sequence: '\n', '\t', etc - pattern is '\x'
                        self.advance()  # skip backslash
                        if not self.at_end():
                            self.advance()  # skip escape char
                            if not self.at_end() and self.current_char() == "'":
                                # It's a char literal with escape sequence
                                self.pos = pos
                                self.column = saved_col
                                self.tokens.append(self.read_char())
                                continue
                    else:
                        # Regular char: 'x' pattern
                        c = self.current_char()
                        self.advance()  # skip char
                        if not self.at_end() and self.current_char() == "'":
                            # It's a char literal like 'x'
                            self.pos = pos
                            self.column = saved_col
                            self.tokens.append(self.read_char())
                            continue

                    # Restore position
                    self.pos = pos
                    self.column = saved_col

                # Otherwise treat as string
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

# Brainhair native entry point - tests the lexer
def main() -> int:
    print("Lexer test\n")

    print("Creating code\n")
    code: str = "x: int = 42"
    print("Creating lexer\n")
    lexer: Lexer = Lexer(code)
    print("Created\n")
    print("Tokenizing\n")
    tokens: List[Token] = lexer.tokenize()
    print("Done tokenizing\n")

    # Print token count
    n: int = len(tokens)
    print("Token count: ")
    # Simple int printing (digit by digit)
    if n >= 10:
        d: int = n // 10
        c: char = chr(48 + d)
        print(c)
    c2: char = chr(48 + (n % 10))
    print(c2)
    print("\n")

    print("Done!\n")
    return 0

# Python-only test (Brainhair ignores try/except at module level)
try:
    if __name__ == '__main__':
        code = "x: int = 42 + y"
        lexer = Lexer(code)
        tokens = lexer.tokenize()
        print("Tokens:")
        for token in tokens:
            print(f"  {token}")
except:
    pass
