"""
Error handling system for the Brainhair compiler.

This module provides a comprehensive error reporting infrastructure with:
- Structured error types for different compilation phases
- Source location tracking with span information
- Colorized output for better readability
- Error codes for documentation lookup
- Support for both errors and warnings
"""

from dataclasses import dataclass, field
from typing import Optional, List, Tuple
from enum import Enum


# ANSI color codes for terminal output
class Color:
    """ANSI color codes for terminal formatting."""
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    RESET = '\033[0m'


@dataclass
class SourceSpan:
    """
    Represents a location in source code.

    Attributes:
        file: Path to the source file
        line: Starting line number (1-indexed)
        column: Starting column number (1-indexed)
        end_line: Ending line number (1-indexed)
        end_column: Ending column number (1-indexed)
        source_line: Optional actual source code line for display
    """
    file: str
    line: int
    column: int
    end_line: Optional[int] = None
    end_column: Optional[int] = None
    source_line: Optional[str] = None

    def __str__(self) -> str:
        """Format span as file:line:column."""
        return f"{self.file}:{self.line}:{self.column}"

    def format_location(self) -> str:
        """Format the full location range."""
        if self.end_line and self.end_column:
            if self.line == self.end_line:
                return f"{self.file}:{self.line}:{self.column}-{self.end_column}"
            return f"{self.file}:{self.line}:{self.column}-{self.end_line}:{self.end_column}"
        return str(self)


class Severity(Enum):
    """Error severity levels."""
    ERROR = "error"
    WARNING = "warning"
    NOTE = "note"


@dataclass
class CompilerError(Exception):
    """
    Base class for all compiler errors.

    Attributes:
        message: Human-readable error message
        span: Optional source location where error occurred
        error_code: Optional error code (e.g., "E001")
        notes: Additional context or hints for the user
        severity: Error severity level (error or warning)
    """
    message: str
    span: Optional[SourceSpan] = None
    error_code: Optional[str] = None
    notes: List[str] = field(default_factory=list)
    severity: Severity = Severity.ERROR

    def __str__(self) -> str:
        """String representation of the error."""
        parts = []
        if self.error_code:
            parts.append(f"{self.severity.value}[{self.error_code}]")
        else:
            parts.append(self.severity.value)
        parts.append(f": {self.message}")
        if self.span:
            parts.append(f" at {self.span}")
        return "".join(parts)

    def format(self, use_color: bool = True) -> str:
        """
        Format error with colors and source code context.

        Args:
            use_color: Whether to use ANSI color codes

        Returns:
            Formatted error message with source context
        """
        lines = []

        # Error header
        if use_color:
            severity_color = Color.RED if self.severity == Severity.ERROR else Color.YELLOW
            header = f"{severity_color}{Color.BOLD}{self.severity.value}"
            if self.error_code:
                header += f"[{self.error_code}]"
            header += f"{Color.RESET}: {Color.BOLD}{self.message}{Color.RESET}"
        else:
            header = f"{self.severity.value}"
            if self.error_code:
                header += f"[{self.error_code}]"
            header += f": {self.message}"

        lines.append(header)

        # Location information
        if self.span:
            if use_color:
                location = f"  {Color.BLUE}-->{Color.RESET} {self.span.format_location()}"
            else:
                location = f"  --> {self.span.format_location()}"
            lines.append(location)

            # Source code context
            if self.span.source_line:
                lines.append("")

                # Line number
                line_num = str(self.span.line)
                line_num_width = len(line_num)

                if use_color:
                    lines.append(f"  {Color.BLUE}{line_num}{Color.RESET} | {self.span.source_line}")
                else:
                    lines.append(f"  {line_num} | {self.span.source_line}")

                # Caret indicator
                caret_padding = " " * (line_num_width + 3 + self.span.column - 1)
                caret_length = 1
                if self.span.end_column:
                    caret_length = max(1, self.span.end_column - self.span.column)

                caret = "^" * caret_length
                if use_color:
                    severity_color = Color.RED if self.severity == Severity.ERROR else Color.YELLOW
                    lines.append(f"{caret_padding}{severity_color}{caret}{Color.RESET}")
                else:
                    lines.append(f"{caret_padding}{caret}")

        # Additional notes
        if self.notes:
            lines.append("")
            for note in self.notes:
                if use_color:
                    lines.append(f"  {Color.CYAN}note:{Color.RESET} {note}")
                else:
                    lines.append(f"  note: {note}")

        return "\n".join(lines)


class LexerError(CompilerError):
    """
    Errors that occur during lexical analysis.

    Examples:
        - Invalid characters
        - Unterminated strings
        - Malformed numbers
        - Invalid escape sequences
    """

    @staticmethod
    def invalid_character(char: str, span: SourceSpan) -> 'LexerError':
        """Create error for invalid character."""
        return LexerError(
            message=f"invalid character: '{char}'",
            span=span,
            error_code="L001"
        )

    @staticmethod
    def unterminated_string(span: SourceSpan) -> 'LexerError':
        """Create error for unterminated string literal."""
        return LexerError(
            message="unterminated string literal",
            span=span,
            error_code="L002",
            notes=["string literals must be closed with a matching quote"]
        )

    @staticmethod
    def invalid_escape_sequence(seq: str, span: SourceSpan) -> 'LexerError':
        """Create error for invalid escape sequence."""
        return LexerError(
            message=f"invalid escape sequence: '\\{seq}'",
            span=span,
            error_code="L003",
            notes=["valid escape sequences are: \\n, \\t, \\r, \\\\, \\', \\\""]
        )

    @staticmethod
    def invalid_number(text: str, span: SourceSpan) -> 'LexerError':
        """Create error for malformed number."""
        return LexerError(
            message=f"invalid number literal: '{text}'",
            span=span,
            error_code="L004"
        )


class ParseError(CompilerError):
    """
    Errors that occur during parsing.

    Examples:
        - Unexpected tokens
        - Missing delimiters
        - Invalid syntax
    """

    @staticmethod
    def unexpected_token(expected: str, found: str, span: SourceSpan) -> 'ParseError':
        """Create error for unexpected token."""
        return ParseError(
            message=f"expected {expected}, found '{found}'",
            span=span,
            error_code="P001"
        )

    @staticmethod
    def missing_delimiter(delimiter: str, span: SourceSpan) -> 'ParseError':
        """Create error for missing delimiter."""
        return ParseError(
            message=f"missing '{delimiter}'",
            span=span,
            error_code="P002"
        )

    @staticmethod
    def invalid_syntax(description: str, span: SourceSpan) -> 'ParseError':
        """Create error for general syntax errors."""
        return ParseError(
            message=f"invalid syntax: {description}",
            span=span,
            error_code="P003"
        )

    @staticmethod
    def unexpected_eof(expected: str, span: SourceSpan) -> 'ParseError':
        """Create error for unexpected end of file."""
        return ParseError(
            message=f"unexpected end of file while parsing {expected}",
            span=span,
            error_code="P004"
        )


class TypeError(CompilerError):
    """
    Errors related to type checking.

    Examples:
        - Type mismatches
        - Unknown types
        - Invalid type operations
    """

    @staticmethod
    def type_mismatch(expected: str, found: str, span: SourceSpan) -> 'TypeError':
        """Create error for type mismatch."""
        return TypeError(
            message=f"type mismatch: expected '{expected}', found '{found}'",
            span=span,
            error_code="T001"
        )

    @staticmethod
    def unknown_type(type_name: str, span: SourceSpan) -> 'TypeError':
        """Create error for unknown type."""
        return TypeError(
            message=f"unknown type: '{type_name}'",
            span=span,
            error_code="T002"
        )

    @staticmethod
    def invalid_operation(op: str, type1: str, type2: Optional[str], span: SourceSpan) -> 'TypeError':
        """Create error for invalid type operation."""
        if type2:
            msg = f"invalid operation '{op}' for types '{type1}' and '{type2}'"
        else:
            msg = f"invalid operation '{op}' for type '{type1}'"
        return TypeError(
            message=msg,
            span=span,
            error_code="T003"
        )

    @staticmethod
    def incompatible_types(type1: str, type2: str, context: str, span: SourceSpan) -> 'TypeError':
        """Create error for incompatible types."""
        return TypeError(
            message=f"incompatible types '{type1}' and '{type2}' in {context}",
            span=span,
            error_code="T004"
        )


class OwnershipError(CompilerError):
    """
    Errors related to ownership and borrowing.

    Examples:
        - Use after move
        - Double free
        - Invalid borrows
        - Lifetime violations
    """

    @staticmethod
    def use_after_move(var_name: str, span: SourceSpan, moved_at: Optional[SourceSpan] = None) -> 'OwnershipError':
        """Create error for use after move."""
        notes = []
        if moved_at:
            notes.append(f"value was moved here: {moved_at}")
        notes.append("consider using a reference or cloning the value")

        return OwnershipError(
            message=f"use of moved value: '{var_name}'",
            span=span,
            error_code="O001",
            notes=notes
        )

    @staticmethod
    def double_free(var_name: str, span: SourceSpan, first_free: Optional[SourceSpan] = None) -> 'OwnershipError':
        """Create error for double free."""
        notes = []
        if first_free:
            notes.append(f"value was already freed here: {first_free}")

        return OwnershipError(
            message=f"double free of value: '{var_name}'",
            span=span,
            error_code="O002",
            notes=notes
        )

    @staticmethod
    def invalid_borrow(var_name: str, reason: str, span: SourceSpan) -> 'OwnershipError':
        """Create error for invalid borrow."""
        return OwnershipError(
            message=f"invalid borrow of '{var_name}': {reason}",
            span=span,
            error_code="O003"
        )

    @staticmethod
    def mutable_borrow_conflict(var_name: str, span: SourceSpan, existing_borrow: Optional[SourceSpan] = None) -> 'OwnershipError':
        """Create error for conflicting mutable borrows."""
        notes = []
        if existing_borrow:
            notes.append(f"existing borrow is here: {existing_borrow}")
        notes.append("cannot borrow as mutable more than once at a time")

        return OwnershipError(
            message=f"cannot borrow '{var_name}' as mutable",
            span=span,
            error_code="O004",
            notes=notes
        )


class NameError(CompilerError):
    """
    Errors related to name resolution.

    Examples:
        - Undefined variables
        - Duplicate definitions
        - Invalid scopes
    """

    @staticmethod
    def undefined_variable(var_name: str, span: SourceSpan) -> 'NameError':
        """Create error for undefined variable."""
        return NameError(
            message=f"undefined variable: '{var_name}'",
            span=span,
            error_code="N001",
            notes=["make sure the variable is declared before use"]
        )

    @staticmethod
    def duplicate_definition(name: str, span: SourceSpan, first_def: Optional[SourceSpan] = None) -> 'NameError':
        """Create error for duplicate definition."""
        notes = []
        if first_def:
            notes.append(f"first defined here: {first_def}")

        return NameError(
            message=f"duplicate definition of '{name}'",
            span=span,
            error_code="N002",
            notes=notes
        )

    @staticmethod
    def undefined_function(func_name: str, span: SourceSpan) -> 'NameError':
        """Create error for undefined function."""
        return NameError(
            message=f"undefined function: '{func_name}'",
            span=span,
            error_code="N003"
        )

    @staticmethod
    def undefined_type(type_name: str, span: SourceSpan) -> 'NameError':
        """Create error for undefined type."""
        return NameError(
            message=f"undefined type: '{type_name}'",
            span=span,
            error_code="N004"
        )


@dataclass
class CompilerWarning(CompilerError):
    """
    Base class for compiler warnings.

    Warnings are non-fatal issues that should be addressed but don't
    prevent compilation.
    """
    severity: Severity = field(default=Severity.WARNING, init=False)

    @staticmethod
    def unused_variable(var_name: str, span: SourceSpan) -> 'CompilerWarning':
        """Create warning for unused variable."""
        return CompilerWarning(
            message=f"unused variable: '{var_name}'",
            span=span,
            error_code="W001",
            notes=["prefix with '_' to suppress this warning"]
        )

    @staticmethod
    def unreachable_code(span: SourceSpan) -> 'CompilerWarning':
        """Create warning for unreachable code."""
        return CompilerWarning(
            message="unreachable code detected",
            span=span,
            error_code="W002"
        )

    @staticmethod
    def deprecated_feature(feature: str, replacement: str, span: SourceSpan) -> 'CompilerWarning':
        """Create warning for deprecated feature."""
        return CompilerWarning(
            message=f"use of deprecated feature: '{feature}'",
            span=span,
            error_code="W003",
            notes=[f"use '{replacement}' instead"]
        )


class ErrorReporter:
    """
    Collects and reports errors and warnings during compilation.

    The error reporter accumulates errors and warnings as they're discovered
    during compilation, then provides formatted output with all diagnostics.

    Attributes:
        errors: List of accumulated errors
        warnings: List of accumulated warnings
        use_color: Whether to use ANSI color codes in output
    """

    def __init__(self, use_color: bool = True):
        """
        Initialize the error reporter.

        Args:
            use_color: Whether to use colored output (default: True)
        """
        self.errors: List[CompilerError] = []
        self.warnings: List[CompilerWarning] = []
        self.use_color = use_color

    def add_error(self, error: CompilerError) -> None:
        """
        Add an error to the reporter.

        Args:
            error: The error to add
        """
        if error.severity == Severity.WARNING:
            self.warnings.append(error)
        else:
            self.errors.append(error)

    def add_warning(self, warning: CompilerWarning) -> None:
        """
        Add a warning to the reporter.

        Args:
            warning: The warning to add
        """
        self.warnings.append(warning)

    def has_errors(self) -> bool:
        """
        Check if any errors have been reported.

        Returns:
            True if there are errors, False otherwise
        """
        return len(self.errors) > 0

    def has_warnings(self) -> bool:
        """
        Check if any warnings have been reported.

        Returns:
            True if there are warnings, False otherwise
        """
        return len(self.warnings) > 0

    def error_count(self) -> int:
        """Get the number of errors."""
        return len(self.errors)

    def warning_count(self) -> int:
        """Get the number of warnings."""
        return len(self.warnings)

    def clear(self) -> None:
        """Clear all errors and warnings."""
        self.errors.clear()
        self.warnings.clear()

    def report(self) -> str:
        """
        Format and return all errors and warnings.

        Returns:
            Formatted string with all diagnostics
        """
        lines = []

        # Report all errors
        for error in self.errors:
            lines.append(error.format(use_color=self.use_color))
            lines.append("")  # Empty line between errors

        # Report all warnings
        for warning in self.warnings:
            lines.append(warning.format(use_color=self.use_color))
            lines.append("")  # Empty line between warnings

        # Summary
        if self.has_errors() or self.has_warnings():
            summary_parts = []

            if self.has_errors():
                count = self.error_count()
                plural = "error" if count == 1 else "errors"
                if self.use_color:
                    summary_parts.append(f"{Color.RED}{Color.BOLD}{count} {plural}{Color.RESET}")
                else:
                    summary_parts.append(f"{count} {plural}")

            if self.has_warnings():
                count = self.warning_count()
                plural = "warning" if count == 1 else "warnings"
                if self.use_color:
                    summary_parts.append(f"{Color.YELLOW}{Color.BOLD}{count} {plural}{Color.RESET}")
                else:
                    summary_parts.append(f"{count} {plural}")

            summary = ", ".join(summary_parts) + " generated"
            lines.append(summary)

        return "\n".join(lines)

    def print_report(self) -> None:
        """Print all errors and warnings to stdout."""
        report = self.report()
        if report:
            print(report)

    def get_all_diagnostics(self) -> List[CompilerError]:
        """
        Get all diagnostics (errors and warnings) in order.

        Returns:
            Combined list of errors and warnings
        """
        return self.errors + self.warnings


# Convenience functions for quick error reporting
def format_error(error: CompilerError, use_color: bool = True) -> str:
    """
    Format a single error with colors and context.

    Args:
        error: The error to format
        use_color: Whether to use ANSI color codes

    Returns:
        Formatted error message
    """
    return error.format(use_color=use_color)


def print_error(error: CompilerError, use_color: bool = True) -> None:
    """
    Print a single error to stdout.

    Args:
        error: The error to print
        use_color: Whether to use colored output
    """
    print(format_error(error, use_color=use_color))
