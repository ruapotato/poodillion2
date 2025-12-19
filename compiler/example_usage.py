"""
Example usage of the error handling system in a compiler pipeline.

This demonstrates how to integrate the error reporter into different
compilation phases (lexer, parser, type checker, etc.).
"""

from errors import (
    ErrorReporter, SourceSpan, LexerError, ParseError,
    TypeError, NameError, OwnershipError, CompilerWarning
)
from typing import Optional


# Mock data structures for demonstration
class Token:
    def __init__(self, type: str, value: str, span: SourceSpan):
        self.type = type
        self.value = value
        self.span = span


class ASTNode:
    def __init__(self, node_type: str, span: SourceSpan):
        self.node_type = node_type
        self.span = span
        self.children = []


# Simulated compiler phases
class Lexer:
    """Tokenizes source code into tokens."""

    def __init__(self, source: str, filename: str, reporter: ErrorReporter):
        self.source = source
        self.filename = filename
        self.reporter = reporter
        self.pos = 0
        self.line = 1
        self.column = 1

    def tokenize(self) -> list[Token]:
        """
        Tokenize the source code.

        Returns a list of tokens, reporting any lexer errors to the reporter.
        """
        tokens = []

        # Simulate finding an invalid character
        if '@' in self.source:
            idx = self.source.index('@')
            span = SourceSpan(
                file=self.filename,
                line=1,
                column=idx + 1,
                end_column=idx + 2,
                source_line=self.source
            )
            error = LexerError.invalid_character('@', span)
            self.reporter.add_error(error)

        # Simulate finding an unterminated string
        if '"hello' in self.source and '"hello"' not in self.source:
            idx = self.source.index('"hello')
            span = SourceSpan(
                file=self.filename,
                line=1,
                column=idx + 1,
                end_column=len(self.source),
                source_line=self.source
            )
            error = LexerError.unterminated_string(span)
            self.reporter.add_error(error)

        # Return mock tokens (in a real lexer, this would be the actual token stream)
        return tokens


class Parser:
    """Parses tokens into an Abstract Syntax Tree."""

    def __init__(self, tokens: list[Token], reporter: ErrorReporter):
        self.tokens = tokens
        self.reporter = reporter
        self.pos = 0

    def parse(self) -> Optional[ASTNode]:
        """
        Parse tokens into an AST.

        Returns the AST root, reporting any parse errors to the reporter.
        """
        # Simulate a missing delimiter error
        span = SourceSpan(
            file="example.bh",
            line=5,
            column=20,
            source_line="fn calculate(x: i32"
        )
        error = ParseError.missing_delimiter(')', span)
        self.reporter.add_error(error)

        # Return mock AST (in a real parser, this would be the actual AST)
        return None


class TypeChecker:
    """Performs type checking on the AST."""

    def __init__(self, ast: ASTNode, reporter: ErrorReporter):
        self.ast = ast
        self.reporter = reporter
        self.symbol_table = {}

    def check(self):
        """
        Type check the AST.

        Reports type errors to the reporter.
        """
        # Simulate a type mismatch
        span = SourceSpan(
            file="example.bh",
            line=10,
            column=14,
            end_column=21,
            source_line='let x: i32 = "hello";'
        )
        error = TypeError.type_mismatch("i32", "str", span)
        self.reporter.add_error(error)

        # Simulate an undefined variable
        span2 = SourceSpan(
            file="example.bh",
            line=15,
            column=13,
            end_column=24,
            source_line='let y = undefined_var;'
        )
        error2 = NameError.undefined_variable("undefined_var", span2)
        self.reporter.add_error(error2)


class WarningAnalyzer:
    """Analyzes code for potential issues."""

    def __init__(self, ast: ASTNode, reporter: ErrorReporter):
        self.ast = ast
        self.reporter = reporter

    def analyze(self):
        """
        Analyze the AST for warnings.

        Reports warnings to the reporter.
        """
        # Simulate an unused variable warning
        span = SourceSpan(
            file="example.bh",
            line=20,
            column=9,
            end_column=14,
            source_line='    let unused = 42;'
        )
        warning = CompilerWarning.unused_variable("unused", span)
        self.reporter.add_warning(warning)


def compile_file(filename: str, source_code: str) -> bool:
    """
    Compile a source file through all phases.

    Returns True if compilation succeeded (no errors), False otherwise.
    """
    print(f"Compiling {filename}...")
    print()

    # Create error reporter
    reporter = ErrorReporter(use_color=True)

    # Phase 1: Lexical Analysis
    print("Phase 1: Lexical Analysis")
    lexer = Lexer(source_code, filename, reporter)
    tokens = lexer.tokenize()

    # Check for lexer errors before continuing
    if reporter.has_errors():
        print("  Errors detected in lexer phase")
    else:
        print("  No errors")
    print()

    # Phase 2: Parsing
    print("Phase 2: Parsing")
    parser = Parser(tokens, reporter)
    ast = parser.parse()

    if reporter.error_count() > 0:
        print(f"  Errors detected in parser phase")
    else:
        print("  No errors")
    print()

    # Phase 3: Type Checking (only if we have an AST)
    print("Phase 3: Type Checking")
    if ast is not None:
        type_checker = TypeChecker(ast, reporter)
        type_checker.check()

    if reporter.error_count() > 0:
        print("  Errors detected in type checker phase")
    else:
        print("  No errors")
    print()

    # Phase 4: Warning Analysis
    print("Phase 4: Warning Analysis")
    if ast is not None:
        analyzer = WarningAnalyzer(ast, reporter)
        analyzer.analyze()

    if reporter.has_warnings():
        print(f"  {reporter.warning_count()} warning(s) detected")
    else:
        print("  No warnings")
    print()

    # Report all diagnostics
    print("=" * 60)
    print("COMPILATION REPORT")
    print("=" * 60)
    print()

    if reporter.has_errors() or reporter.has_warnings():
        reporter.print_report()
    else:
        print("Compilation successful! No errors or warnings.")

    print()
    print("=" * 60)

    # Return success status
    return not reporter.has_errors()


def example_1_clean_compilation():
    """Example of successful compilation with no errors."""
    print("\n" + "=" * 60)
    print("EXAMPLE 1: Clean Compilation")
    print("=" * 60 + "\n")

    source = """
    fn main() {
        let x: i32 = 42;
        println(x);
    }
    """

    reporter = ErrorReporter()
    # No errors reported
    print(reporter.report() or "No errors or warnings!")
    print()


def example_2_with_errors():
    """Example of compilation with multiple errors."""
    print("\n" + "=" * 60)
    print("EXAMPLE 2: Compilation with Errors")
    print("=" * 60 + "\n")

    source = 'let x: i32 = "hello"; // type mismatch'

    success = compile_file("example.bh", source)

    if success:
        print("\nCompilation succeeded!")
    else:
        print("\nCompilation failed!")


def example_3_error_recovery():
    """Example showing how to continue compilation after errors."""
    print("\n" + "=" * 60)
    print("EXAMPLE 3: Error Recovery")
    print("=" * 60 + "\n")

    reporter = ErrorReporter()

    # Collect multiple errors without stopping
    errors = [
        TypeError.type_mismatch("i32", "str", SourceSpan("test.bh", 1, 5)),
        NameError.undefined_variable("foo", SourceSpan("test.bh", 2, 10)),
        ParseError.missing_delimiter(')', SourceSpan("test.bh", 3, 15))
    ]

    for error in errors:
        reporter.add_error(error)
        # Continue processing instead of stopping

    print(f"Collected {reporter.error_count()} errors")
    print()
    reporter.print_report()


def example_4_warnings_only():
    """Example with only warnings (compilation succeeds)."""
    print("\n" + "=" * 60)
    print("EXAMPLE 4: Warnings Only")
    print("=" * 60 + "\n")

    reporter = ErrorReporter()

    warnings = [
        CompilerWarning.unused_variable("temp", SourceSpan("test.bh", 5, 9)),
        CompilerWarning.unreachable_code(SourceSpan("test.bh", 10, 5))
    ]

    for warning in warnings:
        reporter.add_warning(warning)

    print(f"Has errors: {reporter.has_errors()}")
    print(f"Has warnings: {reporter.has_warnings()}")
    print()

    reporter.print_report()

    print("\nCompilation succeeded with warnings!")


def example_5_detailed_context():
    """Example showing errors with rich context."""
    print("\n" + "=" * 60)
    print("EXAMPLE 5: Rich Error Context")
    print("=" * 60 + "\n")

    reporter = ErrorReporter()

    # Error with source line context
    span = SourceSpan(
        file="ownership.bh",
        line=42,
        column=5,
        end_column=9,
        source_line="    println(data);"
    )

    moved_span = SourceSpan(
        file="ownership.bh",
        line=40,
        column=5
    )

    error = OwnershipError.use_after_move("data", span, moved_span)
    reporter.add_error(error)

    reporter.print_report()


if __name__ == "__main__":
    # Run all examples
    example_1_clean_compilation()
    example_2_with_errors()
    example_3_error_recovery()
    example_4_warnings_only()
    example_5_detailed_context()

    print("\n" + "=" * 60)
    print("All examples completed!")
    print("=" * 60)
