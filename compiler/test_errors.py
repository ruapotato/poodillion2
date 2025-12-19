"""
Test and demonstration file for the error handling system.

This file shows how to use the error reporting system with various
error types and scenarios.
"""

from errors import (
    SourceSpan, CompilerError, LexerError, ParseError, TypeError,
    OwnershipError, NameError, CompilerWarning, ErrorReporter
)


def demo_lexer_errors():
    """Demonstrate lexer error reporting."""
    print("=" * 60)
    print("LEXER ERROR EXAMPLES")
    print("=" * 60)
    print()

    reporter = ErrorReporter()

    # Invalid character
    span1 = SourceSpan(
        file="example.bh",
        line=5,
        column=12,
        end_column=13,
        source_line="let x = @invalid;"
    )
    error1 = LexerError.invalid_character('@', span1)
    reporter.add_error(error1)

    # Unterminated string
    span2 = SourceSpan(
        file="example.bh",
        line=10,
        column=13,
        end_column=25,
        source_line='let msg = "hello world;'
    )
    error2 = LexerError.unterminated_string(span2)
    reporter.add_error(error2)

    # Invalid escape sequence
    span3 = SourceSpan(
        file="example.bh",
        line=15,
        column=15,
        end_column=17,
        source_line='let path = "C:\\x70\\x61\\x74\\x68";'
    )
    error3 = LexerError.invalid_escape_sequence('x', span3)
    reporter.add_error(error3)

    reporter.print_report()
    print()


def demo_parse_errors():
    """Demonstrate parse error reporting."""
    print("=" * 60)
    print("PARSE ERROR EXAMPLES")
    print("=" * 60)
    print()

    reporter = ErrorReporter()

    # Unexpected token
    span1 = SourceSpan(
        file="test.bh",
        line=3,
        column=15,
        end_column=16,
        source_line="if x == 5 { println(x) ]"
    )
    error1 = ParseError.unexpected_token("'}'", "']'", span1)
    reporter.add_error(error1)

    # Missing delimiter
    span2 = SourceSpan(
        file="test.bh",
        line=8,
        column=20,
        source_line="fn calculate(a: i32"
    )
    error2 = ParseError.missing_delimiter(')', span2)
    reporter.add_error(error2)

    reporter.print_report()
    print()


def demo_type_errors():
    """Demonstrate type error reporting."""
    print("=" * 60)
    print("TYPE ERROR EXAMPLES")
    print("=" * 60)
    print()

    reporter = ErrorReporter()

    # Type mismatch
    span1 = SourceSpan(
        file="types.bh",
        line=12,
        column=9,
        end_column=15,
        source_line='let x: i32 = "hello";'
    )
    error1 = TypeError.type_mismatch("i32", "str", span1)
    reporter.add_error(error1)

    # Unknown type
    span2 = SourceSpan(
        file="types.bh",
        line=18,
        column=8,
        end_column=17,
        source_line="let y: MyCustomType = get_value();"
    )
    error2 = TypeError.unknown_type("MyCustomType", span2)
    reporter.add_error(error2)

    # Invalid operation
    span3 = SourceSpan(
        file="types.bh",
        line=25,
        column=13,
        end_column=18,
        source_line='let result = "hello" + 42;'
    )
    error3 = TypeError.invalid_operation("+", "str", "i32", span3)
    reporter.add_error(error3)

    reporter.print_report()
    print()


def demo_ownership_errors():
    """Demonstrate ownership error reporting."""
    print("=" * 60)
    print("OWNERSHIP ERROR EXAMPLES")
    print("=" * 60)
    print()

    reporter = ErrorReporter()

    # Use after move
    moved_span = SourceSpan(
        file="ownership.bh",
        line=10,
        column=5,
        source_line="    take_ownership(data);"
    )
    use_span = SourceSpan(
        file="ownership.bh",
        line=12,
        column=5,
        end_column=9,
        source_line="    println(data);"
    )
    error1 = OwnershipError.use_after_move("data", use_span, moved_span)
    reporter.add_error(error1)

    # Mutable borrow conflict
    first_borrow = SourceSpan(
        file="ownership.bh",
        line=20,
        column=9,
        source_line="    let ref1 = &mut vec;"
    )
    second_borrow = SourceSpan(
        file="ownership.bh",
        line=21,
        column=9,
        end_column=17,
        source_line="    let ref2 = &mut vec;"
    )
    error2 = OwnershipError.mutable_borrow_conflict("vec", second_borrow, first_borrow)
    reporter.add_error(error2)

    reporter.print_report()
    print()


def demo_name_errors():
    """Demonstrate name resolution error reporting."""
    print("=" * 60)
    print("NAME ERROR EXAMPLES")
    print("=" * 60)
    print()

    reporter = ErrorReporter()

    # Undefined variable
    span1 = SourceSpan(
        file="names.bh",
        line=5,
        column=9,
        end_column=20,
        source_line="let x = undefined_var + 10;"
    )
    error1 = NameError.undefined_variable("undefined_var", span1)
    reporter.add_error(error1)

    # Duplicate definition
    first_def = SourceSpan(
        file="names.bh",
        line=10,
        column=5,
        source_line="    fn process(x: i32) -> i32 {"
    )
    duplicate_def = SourceSpan(
        file="names.bh",
        line=15,
        column=5,
        end_column=12,
        source_line="    fn process(x: str) -> str {"
    )
    error2 = NameError.duplicate_definition("process", duplicate_def, first_def)
    reporter.add_error(error2)

    reporter.print_report()
    print()


def demo_warnings():
    """Demonstrate compiler warnings."""
    print("=" * 60)
    print("WARNING EXAMPLES")
    print("=" * 60)
    print()

    reporter = ErrorReporter()

    # Unused variable
    span1 = SourceSpan(
        file="warnings.bh",
        line=8,
        column=9,
        end_column=14,
        source_line="    let unused = calculate_value();"
    )
    warning1 = CompilerWarning.unused_variable("unused", span1)
    reporter.add_warning(warning1)

    # Unreachable code
    span2 = SourceSpan(
        file="warnings.bh",
        line=15,
        column=5,
        end_column=28,
        source_line="    println('Never reached');"
    )
    warning2 = CompilerWarning.unreachable_code(span2)
    reporter.add_warning(warning2)

    # Deprecated feature
    span3 = SourceSpan(
        file="warnings.bh",
        line=22,
        column=5,
        end_column=17,
        source_line="    old_function(x);"
    )
    warning3 = CompilerWarning.deprecated_feature("old_function", "new_function", span3)
    reporter.add_warning(warning3)

    reporter.print_report()
    print()


def demo_mixed_diagnostics():
    """Demonstrate mixed errors and warnings."""
    print("=" * 60)
    print("MIXED ERRORS AND WARNINGS")
    print("=" * 60)
    print()

    reporter = ErrorReporter()

    # Add some warnings
    span1 = SourceSpan(
        file="mixed.bh",
        line=5,
        column=9,
        source_line="    let temp = 42;"
    )
    reporter.add_warning(CompilerWarning.unused_variable("temp", span1))

    # Add an error
    span2 = SourceSpan(
        file="mixed.bh",
        line=10,
        column=9,
        end_column=17,
        source_line='let x: i32 = "invalid";'
    )
    reporter.add_error(TypeError.type_mismatch("i32", "str", span2))

    # Add another warning
    span3 = SourceSpan(
        file="mixed.bh",
        line=15,
        column=5,
        source_line="    return x;"
    )
    reporter.add_warning(CompilerWarning.unreachable_code(span3))

    # Add another error
    span4 = SourceSpan(
        file="mixed.bh",
        line=20,
        column=5,
        end_column=16,
        source_line="    println(unknown);"
    )
    reporter.add_error(NameError.undefined_variable("unknown", span4))

    print(f"Has errors: {reporter.has_errors()}")
    print(f"Has warnings: {reporter.has_warnings()}")
    print(f"Error count: {reporter.error_count()}")
    print(f"Warning count: {reporter.warning_count()}")
    print()

    reporter.print_report()
    print()


def demo_colorless_output():
    """Demonstrate output without colors."""
    print("=" * 60)
    print("COLORLESS OUTPUT EXAMPLE")
    print("=" * 60)
    print()

    reporter = ErrorReporter(use_color=False)

    span = SourceSpan(
        file="example.bh",
        line=10,
        column=9,
        end_column=17,
        source_line='let x: i32 = "hello";'
    )
    error = TypeError.type_mismatch("i32", "str", span)
    reporter.add_error(error)

    reporter.print_report()
    print()


if __name__ == "__main__":
    # Run all demos
    demo_lexer_errors()
    demo_parse_errors()
    demo_type_errors()
    demo_ownership_errors()
    demo_name_errors()
    demo_warnings()
    demo_mixed_diagnostics()
    demo_colorless_output()

    print("=" * 60)
    print("All error handling demos completed!")
    print("=" * 60)
