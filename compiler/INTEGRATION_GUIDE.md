# Integrating Error Handling into Existing Compiler

This guide shows how to integrate the new error handling system (`errors.py`) into the existing Brainhair compiler components.

## Current State

The existing compiler has these components:
- `lexer.py` - Tokenizes source code
- `parser.py` - Builds AST from tokens
- `type_checker.py` - Performs type checking
- `codegen_x86.py` - Generates x86 assembly

Currently, these components likely use `raise Exception()` or similar for error handling.

## Migration Plan

### Phase 1: Add ErrorReporter to Lexer

#### Before (lexer.py)
```python
class Lexer:
    def tokenize(self, source: str) -> List[Token]:
        # ...
        if invalid_char:
            raise Exception(f"Invalid character: {char}")
```

#### After (with error handling)
```python
from errors import ErrorReporter, LexerError, SourceSpan

class Lexer:
    def __init__(self, source: str, filename: str, reporter: ErrorReporter):
        self.source = source
        self.filename = filename
        self.reporter = reporter
        self.line = 1
        self.column = 1
        # ...

    def create_span(self, start_col: int, end_col: int = None) -> SourceSpan:
        """Helper to create source spans."""
        source_line = self.get_current_line()
        return SourceSpan(
            file=self.filename,
            line=self.line,
            column=start_col,
            end_column=end_col or start_col + 1,
            source_line=source_line
        )

    def get_current_line(self) -> str:
        """Extract the current line from source for error display."""
        lines = self.source.split('\n')
        if self.line <= len(lines):
            return lines[self.line - 1]
        return ""

    def tokenize(self) -> List[Token]:
        tokens = []

        while not self.at_end():
            char = self.current_char()

            if not self.is_valid_char(char):
                span = self.create_span(self.column)
                error = LexerError.invalid_character(char, span)
                self.reporter.add_error(error)
                self.advance()  # Skip invalid char and continue
                continue

            # Continue tokenizing...
            token = self.scan_token()
            tokens.append(token)

        return tokens
```

### Phase 2: Add ErrorReporter to Parser

#### Before (parser.py)
```python
class Parser:
    def parse_statement(self):
        if self.current_token().type != TokenType.EXPECTED:
            raise Exception(f"Expected {TokenType.EXPECTED}, got {self.current_token().type}")
```

#### After (with error handling)
```python
from errors import ErrorReporter, ParseError, SourceSpan

class Parser:
    def __init__(self, tokens: List[Token], reporter: ErrorReporter):
        self.tokens = tokens
        self.reporter = reporter
        self.pos = 0

    def token_to_span(self, token: Token) -> SourceSpan:
        """Convert a token to a source span."""
        # Assumes Token has file, line, column attributes
        return SourceSpan(
            file=token.file,
            line=token.line,
            column=token.column,
            end_column=token.end_column,
            source_line=token.source_line
        )

    def expect(self, expected_type: TokenType) -> Optional[Token]:
        """Expect a specific token type, report error if mismatch."""
        token = self.current_token()

        if token.type != expected_type:
            span = self.token_to_span(token)
            error = ParseError.unexpected_token(
                expected=expected_type.name,
                found=token.type.name,
                span=span
            )
            self.reporter.add_error(error)
            return None

        self.advance()
        return token

    def parse_statement(self) -> Optional[Statement]:
        """Parse a statement, returning None on error."""
        if self.current_token().type == TokenType.VAR:
            return self.parse_var_declaration()
        elif self.current_token().type == TokenType.IF:
            return self.parse_if_statement()
        else:
            span = self.token_to_span(self.current_token())
            error = ParseError.invalid_syntax(
                "unexpected token in statement",
                span
            )
            self.reporter.add_error(error)
            self.synchronize()  # Error recovery
            return None
```

### Phase 3: Add ErrorReporter to Type Checker

#### Before (type_checker.py)
```python
class TypeChecker:
    def check_assignment(self, var_type, value_type):
        if var_type != value_type:
            raise Exception(f"Type mismatch: expected {var_type}, got {value_type}")
```

#### After (with error handling)
```python
from errors import ErrorReporter, TypeError, NameError, SourceSpan

class TypeChecker:
    def __init__(self, ast: Program, reporter: ErrorReporter):
        self.ast = ast
        self.reporter = reporter
        self.symbol_table = {}

    def check_assignment(self, var_type: str, value_type: str,
                        span: SourceSpan) -> bool:
        """Check type compatibility, return True if valid."""
        if var_type != value_type:
            error = TypeError.type_mismatch(var_type, value_type, span)
            self.reporter.add_error(error)
            return False
        return True

    def check_variable_defined(self, var_name: str, span: SourceSpan) -> bool:
        """Check if variable is defined."""
        if var_name not in self.symbol_table:
            error = NameError.undefined_variable(var_name, span)
            self.reporter.add_error(error)
            return False
        return True

    def check_duplicate_definition(self, name: str, span: SourceSpan) -> bool:
        """Check for duplicate definitions."""
        if name in self.symbol_table:
            first_def = self.symbol_table[name].definition_span
            error = NameError.duplicate_definition(name, span, first_def)
            self.reporter.add_error(error)
            return False
        return True

    def visit_var_declaration(self, node: VarDeclaration):
        """Type check variable declaration."""
        # Check for duplicate
        self.check_duplicate_definition(node.name, node.span)

        # Check type exists
        if not self.is_valid_type(node.type_name):
            error = TypeError.unknown_type(node.type_name, node.type_span)
            self.reporter.add_error(error)

        # Check initializer type if present
        if node.initializer:
            init_type = self.infer_type(node.initializer)
            self.check_assignment(node.type_name, init_type, node.initializer.span)

        # Add to symbol table even if there were errors (for error recovery)
        self.symbol_table[node.name] = SymbolInfo(
            name=node.name,
            type=node.type_name,
            definition_span=node.span
        )
```

### Phase 4: Update Main Compiler Driver

#### Complete Integration (brainhair.py)

```python
#!/usr/bin/env python3
"""
Brainhair Compiler - Main driver
"""

import sys
from errors import ErrorReporter
from lexer import Lexer
from parser import Parser
from type_checker import TypeChecker
from codegen_x86 import CodeGenerator

def compile_file(filename: str) -> int:
    """
    Compile a Brainhair source file.

    Returns:
        0 on success, 1 on error
    """
    # Read source code
    try:
        with open(filename, 'r') as f:
            source_code = f.read()
    except IOError as e:
        print(f"Error reading file: {e}")
        return 1

    # Create error reporter
    reporter = ErrorReporter(use_color=True)

    # Phase 1: Lexical Analysis
    lexer = Lexer(source_code, filename, reporter)
    tokens = lexer.tokenize()

    # Stop if lexer found errors
    if reporter.has_errors():
        print("Compilation failed during lexical analysis:\n")
        reporter.print_report()
        return 1

    # Phase 2: Parsing
    parser = Parser(tokens, reporter)
    ast = parser.parse()

    # Stop if parser found errors
    if reporter.has_errors():
        print("Compilation failed during parsing:\n")
        reporter.print_report()
        return 1

    # Phase 3: Type Checking
    type_checker = TypeChecker(ast, reporter)
    type_checker.check()

    # Stop if type checker found errors
    if reporter.has_errors():
        print("Compilation failed during type checking:\n")
        reporter.print_report()
        return 1

    # Phase 4: Code Generation
    codegen = CodeGenerator(ast, reporter)
    asm_code = codegen.generate()

    # Report warnings (but don't stop compilation)
    if reporter.has_warnings():
        print("Compilation succeeded with warnings:\n")
        reporter.print_report()
        print()

    # Write output
    output_filename = filename.replace('.bh', '.asm')
    try:
        with open(output_filename, 'w') as f:
            f.write(asm_code)
        print(f"Successfully compiled {filename} -> {output_filename}")
        return 0
    except IOError as e:
        print(f"Error writing output file: {e}")
        return 1


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: brainhair.py <source_file.bh>")
        sys.exit(1)

    exit_code = compile_file(sys.argv[1])
    sys.exit(exit_code)
```

## Error Recovery Strategies

### Lexer Recovery

When the lexer encounters an error, it should:
1. Report the error
2. Skip the invalid character
3. Continue tokenizing

```python
def scan_token(self) -> Optional[Token]:
    # Try to scan a token
    if self.current_char() == '@':
        span = self.create_span(self.column)
        error = LexerError.invalid_character('@', span)
        self.reporter.add_error(error)
        self.advance()  # Skip it
        return None  # Signal to caller to try next token
    # ...
```

### Parser Recovery

Use synchronization points to recover from parse errors:

```python
def synchronize(self):
    """
    Synchronize parser after error by skipping to next statement.
    """
    self.advance()

    while not self.at_end():
        # Stop at statement boundaries
        if self.current_token().type in [
            TokenType.VAR, TokenType.CONST, TokenType.PROC,
            TokenType.IF, TokenType.WHILE, TokenType.RETURN
        ]:
            return

        self.advance()

def parse_program(self) -> Program:
    """Parse entire program with error recovery."""
    statements = []

    while not self.at_end():
        stmt = self.parse_statement()
        if stmt is not None:
            statements.append(stmt)
        elif self.reporter.has_errors():
            # Error already reported, synchronize
            self.synchronize()

    return Program(statements)
```

### Type Checker Recovery

Continue checking even after errors to find multiple issues:

```python
def check(self):
    """
    Type check the entire AST.

    Continues checking even after errors to find all type issues.
    """
    for statement in self.ast.statements:
        self.visit_statement(statement)
        # Don't stop on error - keep checking
```

## Token Updates

Update the `Token` class to include span information:

```python
# In lexer.py
@dataclass
class Token:
    type: TokenType
    value: str
    file: str
    line: int
    column: int
    end_column: int
    source_line: str  # The actual line of source code

    def to_span(self) -> SourceSpan:
        """Convert token to source span for error reporting."""
        return SourceSpan(
            file=self.file,
            line=self.line,
            column=self.column,
            end_column=self.end_column,
            source_line=self.source_line
        )
```

## Testing the Integration

Create a test file with intentional errors:

```brainhair
// test_errors.bh

var x: i32 = "hello";  // Type error: expected i32, got str

proc calculate(y: i32 {  // Parse error: missing )
    var z: unknown_type = 5;  // Type error: unknown type

    println(undefined_var);  // Name error: undefined variable

    var temp = 42;  // Warning: unused variable

    return y * 2;
}
```

Run compiler:
```bash
python3 brainhair.py test_errors.bh
```

Expected output with our error system:
```
Compilation failed during parsing:

error[P002]: missing ')'
  --> test_errors.bh:5:23

  5 | proc calculate(y: i32 {
                           ^
```

## Benefits of This Integration

1. **Better Error Messages**: Users see exactly where errors occur with source context
2. **Multiple Errors**: All errors in a phase are shown, not just the first
3. **Error Recovery**: Compiler continues after errors to find more issues
4. **Warnings**: Non-fatal issues can be reported without stopping compilation
5. **Consistency**: All error messages follow the same format
6. **Color Coding**: Errors in red, warnings in yellow for better visibility
7. **Error Codes**: Each error type has a code for documentation lookup
8. **Helpful Notes**: Suggestions and context help users fix issues

## Next Steps

1. Update `Token` class to include span information
2. Modify `Lexer` to accept `ErrorReporter` and report errors instead of raising exceptions
3. Modify `Parser` to accept `ErrorReporter` and implement error recovery
4. Modify `TypeChecker` to accept `ErrorReporter` and continue after errors
5. Update main compiler driver to use `ErrorReporter` throughout
6. Add comprehensive tests for error cases
7. Document all error codes in user documentation
