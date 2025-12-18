# Brainhair Compiler Test Suite

This directory contains the test infrastructure for the Brainhair compiler.

## Running Tests

### Run all tests
```bash
python3 run_tests.py
```

### Run specific test file
```bash
python3 run_tests.py test_lexer.py
python3 run_tests.py test_parser.py
```

### Run multiple specific test files
```bash
python3 run_tests.py test_lexer.py test_parser.py
```

## Test Structure

The test suite consists of:

- **run_tests.py** - Test runner that discovers and executes all tests
- **test_lexer.py** - Tests for the lexer/tokenizer (27 tests)
- **test_parser.py** - Tests for the parser (44 tests)

## Writing Tests

Tests are Python functions that start with `test_` and use the assertion framework:

```python
def test_my_feature():
    """Test description"""
    # Arrange
    lexer = Lexer("var x: int32")

    # Act
    tokens = lexer.tokenize()

    # Assert
    assert_eq(tokens[0].type, TokenType.VAR, "First token should be VAR")
    assert_true(len(tokens) > 0, "Should have tokens")
```

## Assertion Framework

The test suite includes a simple assertion framework:

### assert_eq(actual, expected, message="")
Asserts that two values are equal.

```python
assert_eq(result, 42, "Result should be 42")
```

### assert_true(condition, message="")
Asserts that a condition is true.

```python
assert_true(x > 0, "X should be positive")
```

### assert_raises(exception_type, callable, message="")
Asserts that calling a function raises a specific exception.

```python
def should_fail():
    parse_code("invalid syntax")

assert_raises(SyntaxError, should_fail, "Should raise SyntaxError")
```

## Exit Codes

- **0** - All tests passed
- **1** - One or more tests failed

This makes it easy to integrate with CI/CD pipelines and build systems.

## Test Coverage

### Lexer Tests (test_lexer.py)
- Integer and hexadecimal literals
- String and character literals with escape sequences
- Keywords (var, const, proc, if, while, etc.)
- Type keywords (int8, int32, ptr, etc.)
- Operators (arithmetic, comparison, logical, bitwise)
- Delimiters and special characters
- Comments
- Error handling (invalid characters, unterminated strings)
- Line and column tracking

### Parser Tests (test_parser.py)
- Variable declarations (var, const, with types)
- Expressions (literals, binary ops, unary ops, function calls)
- Operator precedence and associativity
- Control flow (if/elif/else, while, for, break, continue)
- Function declarations (proc, extern)
- Complex expressions and nested blocks
- Type parsing (basic types, pointer types)
- Error handling
