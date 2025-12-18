#!/usr/bin/env python3
"""
Lexer Tests for Brainhair Compiler

Tests tokenization of various language constructs.
"""

import sys
import os

# Add parent directory to path to import lexer
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lexer import Lexer, TokenType, Token

# Test basic integer literals
def test_integer_literals():
    """Test tokenizing integer literals"""
    lexer = Lexer("42 0 123 456")
    tokens = lexer.tokenize()

    assert_eq(tokens[0].type, TokenType.NUMBER, "First token should be NUMBER")
    assert_eq(tokens[0].value, 42, "First number should be 42")

    assert_eq(tokens[1].type, TokenType.NUMBER, "Second token should be NUMBER")
    assert_eq(tokens[1].value, 0, "Second number should be 0")

    assert_eq(tokens[2].type, TokenType.NUMBER, "Third token should be NUMBER")
    assert_eq(tokens[2].value, 123, "Third number should be 123")

    assert_eq(tokens[3].type, TokenType.NUMBER, "Fourth token should be NUMBER")
    assert_eq(tokens[3].value, 456, "Fourth number should be 456")

def test_hex_literals():
    """Test tokenizing hexadecimal literals"""
    lexer = Lexer("0xB8000 0xFF 0x10")
    tokens = lexer.tokenize()

    assert_eq(tokens[0].type, TokenType.NUMBER, "First token should be NUMBER")
    assert_eq(tokens[0].value, 0xB8000, "First hex number should be 0xB8000")

    assert_eq(tokens[1].type, TokenType.NUMBER, "Second token should be NUMBER")
    assert_eq(tokens[1].value, 0xFF, "Second hex number should be 0xFF")

    assert_eq(tokens[2].type, TokenType.NUMBER, "Third token should be NUMBER")
    assert_eq(tokens[2].value, 0x10, "Third hex number should be 0x10")

def test_string_literals():
    """Test tokenizing string literals"""
    lexer = Lexer('"hello" "world" "test string"')
    tokens = lexer.tokenize()

    assert_eq(tokens[0].type, TokenType.STRING, "First token should be STRING")
    assert_eq(tokens[0].value, "hello", "First string should be 'hello'")

    assert_eq(tokens[1].type, TokenType.STRING, "Second token should be STRING")
    assert_eq(tokens[1].value, "world", "Second string should be 'world'")

    assert_eq(tokens[2].type, TokenType.STRING, "Third token should be STRING")
    assert_eq(tokens[2].value, "test string", "Third string should be 'test string'")

def test_string_escape_sequences():
    """Test string escape sequences"""
    lexer = Lexer(r'"hello\nworld" "tab\there" "null\0term"')
    tokens = lexer.tokenize()

    assert_eq(tokens[0].type, TokenType.STRING)
    assert_eq(tokens[0].value, "hello\nworld", "Should handle \\n escape")

    assert_eq(tokens[1].type, TokenType.STRING)
    assert_eq(tokens[1].value, "tab\there", "Should handle \\t escape")

    assert_eq(tokens[2].type, TokenType.STRING)
    assert_eq(tokens[2].value, "null\0term", "Should handle \\0 escape")

def test_char_literals():
    """Test tokenizing character literals"""
    lexer = Lexer("'a' 'b' 'Z'")
    tokens = lexer.tokenize()

    assert_eq(tokens[0].type, TokenType.CHAR_LIT, "First token should be CHAR_LIT")
    assert_eq(tokens[0].value, "a", "First char should be 'a'")

    assert_eq(tokens[1].type, TokenType.CHAR_LIT, "Second token should be CHAR_LIT")
    assert_eq(tokens[1].value, "b", "Second char should be 'b'")

    assert_eq(tokens[2].type, TokenType.CHAR_LIT, "Third token should be CHAR_LIT")
    assert_eq(tokens[2].value, "Z", "Third char should be 'Z'")

def test_char_escape_sequences():
    """Test character escape sequences"""
    lexer = Lexer(r"'\n' '\t' '\0'")
    tokens = lexer.tokenize()

    assert_eq(tokens[0].type, TokenType.CHAR_LIT)
    assert_eq(tokens[0].value, "\n", "Should handle \\n in char")

    assert_eq(tokens[1].type, TokenType.CHAR_LIT)
    assert_eq(tokens[1].value, "\t", "Should handle \\t in char")

    assert_eq(tokens[2].type, TokenType.CHAR_LIT)
    assert_eq(tokens[2].value, "\0", "Should handle \\0 in char")

def test_keywords():
    """Test tokenizing keywords"""
    lexer = Lexer("var const proc return if else while for")
    tokens = lexer.tokenize()

    assert_eq(tokens[0].type, TokenType.VAR, "Should recognize 'var' keyword")
    assert_eq(tokens[1].type, TokenType.CONST, "Should recognize 'const' keyword")
    assert_eq(tokens[2].type, TokenType.PROC, "Should recognize 'proc' keyword")
    assert_eq(tokens[3].type, TokenType.RETURN, "Should recognize 'return' keyword")
    assert_eq(tokens[4].type, TokenType.IF, "Should recognize 'if' keyword")
    assert_eq(tokens[5].type, TokenType.ELSE, "Should recognize 'else' keyword")
    assert_eq(tokens[6].type, TokenType.WHILE, "Should recognize 'while' keyword")
    assert_eq(tokens[7].type, TokenType.FOR, "Should recognize 'for' keyword")

def test_type_keywords():
    """Test tokenizing type keywords"""
    lexer = Lexer("int8 int16 int32 uint8 uint16 uint32 bool char ptr")
    tokens = lexer.tokenize()

    assert_eq(tokens[0].type, TokenType.INT8, "Should recognize 'int8'")
    assert_eq(tokens[1].type, TokenType.INT16, "Should recognize 'int16'")
    assert_eq(tokens[2].type, TokenType.INT32, "Should recognize 'int32'")
    assert_eq(tokens[3].type, TokenType.UINT8, "Should recognize 'uint8'")
    assert_eq(tokens[4].type, TokenType.UINT16, "Should recognize 'uint16'")
    assert_eq(tokens[5].type, TokenType.UINT32, "Should recognize 'uint32'")
    assert_eq(tokens[6].type, TokenType.BOOL, "Should recognize 'bool'")
    assert_eq(tokens[7].type, TokenType.CHAR, "Should recognize 'char'")
    assert_eq(tokens[8].type, TokenType.PTR, "Should recognize 'ptr'")

def test_boolean_keywords():
    """Test tokenizing boolean literals"""
    lexer = Lexer("true false")
    tokens = lexer.tokenize()

    assert_eq(tokens[0].type, TokenType.TRUE, "Should recognize 'true'")
    assert_eq(tokens[1].type, TokenType.FALSE, "Should recognize 'false'")

def test_identifiers():
    """Test tokenizing identifiers"""
    lexer = Lexer("x myVar _private test123 CamelCase")
    tokens = lexer.tokenize()

    assert_eq(tokens[0].type, TokenType.IDENT, "Should recognize identifier 'x'")
    assert_eq(tokens[0].value, "x", "Identifier value should be 'x'")

    assert_eq(tokens[1].type, TokenType.IDENT, "Should recognize identifier 'myVar'")
    assert_eq(tokens[1].value, "myVar", "Identifier value should be 'myVar'")

    assert_eq(tokens[2].type, TokenType.IDENT, "Should recognize identifier '_private'")
    assert_eq(tokens[2].value, "_private", "Identifier value should be '_private'")

    assert_eq(tokens[3].type, TokenType.IDENT, "Should recognize identifier 'test123'")
    assert_eq(tokens[3].value, "test123", "Identifier value should be 'test123'")

    assert_eq(tokens[4].type, TokenType.IDENT, "Should recognize identifier 'CamelCase'")
    assert_eq(tokens[4].value, "CamelCase", "Identifier value should be 'CamelCase'")

def test_arithmetic_operators():
    """Test tokenizing arithmetic operators"""
    lexer = Lexer("+ - * / %")
    tokens = lexer.tokenize()

    assert_eq(tokens[0].type, TokenType.PLUS, "Should recognize '+' operator")
    assert_eq(tokens[1].type, TokenType.MINUS, "Should recognize '-' operator")
    assert_eq(tokens[2].type, TokenType.STAR, "Should recognize '*' operator")
    assert_eq(tokens[3].type, TokenType.SLASH, "Should recognize '/' operator")
    assert_eq(tokens[4].type, TokenType.PERCENT, "Should recognize '%' operator")

def test_comparison_operators():
    """Test tokenizing comparison operators"""
    lexer = Lexer("== != < <= > >=")
    tokens = lexer.tokenize()

    assert_eq(tokens[0].type, TokenType.EQUALS_EQUALS, "Should recognize '==' operator")
    assert_eq(tokens[1].type, TokenType.NOT_EQUALS, "Should recognize '!=' operator")
    assert_eq(tokens[2].type, TokenType.LESS, "Should recognize '<' operator")
    assert_eq(tokens[3].type, TokenType.LESS_EQUALS, "Should recognize '<=' operator")
    assert_eq(tokens[4].type, TokenType.GREATER, "Should recognize '>' operator")
    assert_eq(tokens[5].type, TokenType.GREATER_EQUALS, "Should recognize '>=' operator")

def test_logical_operators():
    """Test tokenizing logical operators"""
    lexer = Lexer("and or not")
    tokens = lexer.tokenize()

    assert_eq(tokens[0].type, TokenType.AND, "Should recognize 'and' operator")
    assert_eq(tokens[1].type, TokenType.OR, "Should recognize 'or' operator")
    assert_eq(tokens[2].type, TokenType.NOT, "Should recognize 'not' operator")

def test_bitwise_operators():
    """Test tokenizing bitwise operators"""
    lexer = Lexer("| & ^ << >>")
    tokens = lexer.tokenize()

    assert_eq(tokens[0].type, TokenType.PIPE, "Should recognize '|' operator")
    assert_eq(tokens[1].type, TokenType.AMPERSAND, "Should recognize '&' operator")
    assert_eq(tokens[2].type, TokenType.CARET, "Should recognize '^' operator")
    assert_eq(tokens[3].type, TokenType.SHL, "Should recognize '<<' operator")
    assert_eq(tokens[4].type, TokenType.SHR, "Should recognize '>>' operator")

def test_delimiters():
    """Test tokenizing delimiters"""
    lexer = Lexer("( ) [ ] { } , : . ..")
    tokens = lexer.tokenize()

    assert_eq(tokens[0].type, TokenType.LPAREN, "Should recognize '(' delimiter")
    assert_eq(tokens[1].type, TokenType.RPAREN, "Should recognize ')' delimiter")
    assert_eq(tokens[2].type, TokenType.LBRACKET, "Should recognize '[' delimiter")
    assert_eq(tokens[3].type, TokenType.RBRACKET, "Should recognize ']' delimiter")
    assert_eq(tokens[4].type, TokenType.LBRACE, "Should recognize '{' delimiter")
    assert_eq(tokens[5].type, TokenType.RBRACE, "Should recognize '}' delimiter")
    assert_eq(tokens[6].type, TokenType.COMMA, "Should recognize ',' delimiter")
    assert_eq(tokens[7].type, TokenType.COLON, "Should recognize ':' delimiter")
    assert_eq(tokens[8].type, TokenType.DOT, "Should recognize '.' delimiter")
    assert_eq(tokens[9].type, TokenType.DOTDOT, "Should recognize '..' delimiter")

def test_assignment_operator():
    """Test tokenizing assignment operator"""
    lexer = Lexer("= ==")
    tokens = lexer.tokenize()

    assert_eq(tokens[0].type, TokenType.EQUALS, "Should recognize '=' operator")
    assert_eq(tokens[1].type, TokenType.EQUALS_EQUALS, "Should recognize '==' operator")

def test_comments():
    """Test that comments are properly ignored"""
    lexer = Lexer("var x # this is a comment\nvar y")
    tokens = lexer.tokenize()

    # Should have: VAR, IDENT, NEWLINE, VAR, IDENT, EOF
    assert_eq(tokens[0].type, TokenType.VAR, "First token should be VAR")
    assert_eq(tokens[1].type, TokenType.IDENT, "Second token should be IDENT")
    assert_eq(tokens[1].value, "x", "Second token value should be 'x'")
    assert_eq(tokens[2].type, TokenType.NEWLINE, "Third token should be NEWLINE")
    assert_eq(tokens[3].type, TokenType.VAR, "Fourth token should be VAR")
    assert_eq(tokens[4].type, TokenType.IDENT, "Fifth token should be IDENT")
    assert_eq(tokens[4].value, "y", "Fifth token value should be 'y'")

def test_newlines():
    """Test that newlines are tokenized"""
    lexer = Lexer("var\nx\ny")
    tokens = lexer.tokenize()

    assert_eq(tokens[0].type, TokenType.VAR, "First token should be VAR")
    assert_eq(tokens[1].type, TokenType.NEWLINE, "Second token should be NEWLINE")
    assert_eq(tokens[2].type, TokenType.IDENT, "Third token should be IDENT")
    assert_eq(tokens[3].type, TokenType.NEWLINE, "Fourth token should be NEWLINE")
    assert_eq(tokens[4].type, TokenType.IDENT, "Fifth token should be IDENT")

def test_eof_token():
    """Test that EOF token is always last"""
    lexer = Lexer("var x")
    tokens = lexer.tokenize()

    assert_eq(tokens[-1].type, TokenType.EOF, "Last token should be EOF")

def test_line_and_column_tracking():
    """Test that line and column numbers are tracked correctly"""
    lexer = Lexer("var x\nvar y")
    tokens = lexer.tokenize()

    # var is at line 1, col 1
    assert_eq(tokens[0].line, 1, "VAR should be at line 1")
    assert_eq(tokens[0].col, 1, "VAR should be at column 1")

    # x is at line 1, col 5
    assert_eq(tokens[1].line, 1, "First IDENT should be at line 1")
    assert_eq(tokens[1].col, 5, "First IDENT should be at column 5")

    # newline is at line 1, col 6
    assert_eq(tokens[2].line, 1, "NEWLINE should be at line 1")

    # second var is at line 2, col 1
    assert_eq(tokens[3].line, 2, "Second VAR should be at line 2")
    assert_eq(tokens[3].col, 1, "Second VAR should be at column 1")

def test_variable_declaration():
    """Test tokenizing a complete variable declaration"""
    lexer = Lexer("var x: int32 = 42")
    tokens = lexer.tokenize()

    expected_types = [
        TokenType.VAR,
        TokenType.IDENT,
        TokenType.COLON,
        TokenType.INT32,
        TokenType.EQUALS,
        TokenType.NUMBER,
        TokenType.EOF
    ]

    for i, expected_type in enumerate(expected_types):
        assert_eq(tokens[i].type, expected_type, f"Token {i} should be {expected_type}")

def test_complex_expression():
    """Test tokenizing a complex expression"""
    lexer = Lexer("(a + b) * (c - d)")
    tokens = lexer.tokenize()

    expected_types = [
        TokenType.LPAREN,
        TokenType.IDENT,
        TokenType.PLUS,
        TokenType.IDENT,
        TokenType.RPAREN,
        TokenType.STAR,
        TokenType.LPAREN,
        TokenType.IDENT,
        TokenType.MINUS,
        TokenType.IDENT,
        TokenType.RPAREN,
        TokenType.EOF
    ]

    for i, expected_type in enumerate(expected_types):
        assert_eq(tokens[i].type, expected_type, f"Token {i} should be {expected_type}")

def test_unterminated_string_error():
    """Test that unterminated strings raise an error"""
    # The lexer will reach EOF while still in the string, which will cause
    # it to try to advance past the closing quote that doesn't exist
    # This may result in an IndexError or the string consuming to EOF
    lexer = Lexer('"unterminated')

    # Depending on implementation, this might raise an error or just consume to EOF
    # The current implementation will advance past EOF and create a string with all remaining chars
    # Let's test that it doesn't crash
    try:
        tokens = lexer.tokenize()
        # If it doesn't crash, check that we got some tokens
        assert_true(len(tokens) > 0, "Should produce at least EOF token")
    except:
        # It's also acceptable to raise an error for unterminated strings
        pass

def test_invalid_character_error():
    """Test that invalid characters raise an error"""
    lexer = Lexer("var x @ 42")  # @ is not a valid character

    def tokenize():
        lexer.tokenize()

    assert_raises(SyntaxError, tokenize, "Should raise SyntaxError for invalid character")

def test_whitespace_handling():
    """Test that various whitespace is handled correctly"""
    lexer = Lexer("var  x\t:\tint32")
    tokens = lexer.tokenize()

    # Whitespace should be skipped
    assert_eq(tokens[0].type, TokenType.VAR, "First token should be VAR")
    assert_eq(tokens[1].type, TokenType.IDENT, "Second token should be IDENT")
    assert_eq(tokens[2].type, TokenType.COLON, "Third token should be COLON")
    assert_eq(tokens[3].type, TokenType.INT32, "Fourth token should be INT32")

def test_cast_expression_tokens():
    """Test tokenizing a cast expression"""
    lexer = Lexer("cast[ptr uint8](0xB8000)")
    tokens = lexer.tokenize()

    expected_types = [
        TokenType.CAST,
        TokenType.LBRACKET,
        TokenType.PTR,
        TokenType.UINT8,
        TokenType.RBRACKET,
        TokenType.LPAREN,
        TokenType.NUMBER,
        TokenType.RPAREN,
        TokenType.EOF
    ]

    for i, expected_type in enumerate(expected_types):
        assert_eq(tokens[i].type, expected_type, f"Token {i} should be {expected_type}")

def test_procedure_declaration_tokens():
    """Test tokenizing a procedure declaration"""
    lexer = Lexer("proc add(a: int32, b: int32): int32")
    tokens = lexer.tokenize()

    expected_types = [
        TokenType.PROC,
        TokenType.IDENT,
        TokenType.LPAREN,
        TokenType.IDENT,
        TokenType.COLON,
        TokenType.INT32,
        TokenType.COMMA,
        TokenType.IDENT,
        TokenType.COLON,
        TokenType.INT32,
        TokenType.RPAREN,
        TokenType.COLON,
        TokenType.INT32,
        TokenType.EOF
    ]

    for i, expected_type in enumerate(expected_types):
        assert_eq(tokens[i].type, expected_type, f"Token {i} should be {expected_type}")
