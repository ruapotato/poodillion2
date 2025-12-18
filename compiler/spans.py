"""
Source location tracking for the Brainhair compiler.

This module provides types and utilities for tracking source code locations
throughout the compilation process, enabling precise error reporting and
debugging information.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, List
from pathlib import Path


@dataclass(frozen=True)
class Span:
    """
    Represents a location in source code.

    A Span tracks the exact position of a piece of code, including the file,
    starting line/column, and ending line/column. Spans are immutable and
    hashable, making them suitable for use as dictionary keys.

    All line and column numbers are 1-indexed to match standard editor behavior.

    Attributes:
        file: The source filename (absolute or relative path)
        line: The starting line number (1-indexed)
        column: The starting column number (1-indexed)
        end_line: The ending line number (1-indexed)
        end_column: The ending column number (1-indexed, exclusive)
        source_text: Optional cached source text for this span

    Example:
        >>> span = Span("test.bh", 1, 5, 1, 10)
        >>> print(span_to_string(span))
        test.bh:1:5
    """
    file: str
    line: int
    column: int
    end_line: int
    end_column: int
    source_text: Optional[str] = field(default=None, compare=False, hash=False)

    def __post_init__(self):
        """Validate span invariants."""
        if self.line < 1:
            raise ValueError(f"line must be >= 1, got {self.line}")
        if self.column < 1:
            raise ValueError(f"column must be >= 1, got {self.column}")
        if self.end_line < 1:
            raise ValueError(f"end_line must be >= 1, got {self.end_line}")
        if self.end_column < 1:
            raise ValueError(f"end_column must be >= 1, got {self.end_column}")

        if self.end_line < self.line:
            raise ValueError(
                f"end_line ({self.end_line}) cannot be before line ({self.line})"
            )
        if self.end_line == self.line and self.end_column < self.column:
            raise ValueError(
                f"end_column ({self.end_column}) cannot be before column "
                f"({self.column}) on the same line"
            )

    def __lt__(self, other: 'Span') -> bool:
        """
        Compare spans by position.

        Spans are ordered first by file, then by starting position, then by
        ending position.
        """
        if not isinstance(other, Span):
            return NotImplemented
        return (self.file, self.line, self.column, self.end_line, self.end_column) < \
               (other.file, other.line, other.column, other.end_line, other.end_column)

    def contains_position(self, line: int, column: int) -> bool:
        """
        Check if a position falls within this span.

        Args:
            line: Line number (1-indexed)
            column: Column number (1-indexed)

        Returns:
            True if the position is within this span
        """
        if line < self.line or line > self.end_line:
            return False
        if line == self.line and column < self.column:
            return False
        if line == self.end_line and column >= self.end_column:
            return False
        return True

    def overlaps(self, other: 'Span') -> bool:
        """
        Check if this span overlaps with another span.

        Args:
            other: Another span to check

        Returns:
            True if the spans overlap
        """
        if self.file != other.file:
            return False

        # Check if either span's start is within the other
        return (self.contains_position(other.line, other.column) or
                other.contains_position(self.line, self.column))


def span_from_token(token) -> Span:
    """
    Create a Span from a lexer token.

    This function works with tokens from various lexer implementations.
    It attempts to extract position information using common token attributes.

    Args:
        token: A token object with position information. Expected attributes:
               - file or filename: str
               - line or lineno: int
               - column or col: int
               - end_line (optional): int
               - end_column or end_col (optional): int
               - value or text (optional): str

    Returns:
        A Span representing the token's location

    Raises:
        AttributeError: If the token lacks required position information

    Example:
        >>> from dataclasses import dataclass
        >>> @dataclass
        ... class Token:
        ...     file: str
        ...     line: int
        ...     column: int
        ...     value: str
        >>> token = Token("test.bh", 1, 5, "func")
        >>> span = span_from_token(token)
        >>> span.line, span.column
        (1, 5)
    """
    # Extract file
    file = getattr(token, 'file', None) or getattr(token, 'filename', '<unknown>')

    # Extract starting position
    line = getattr(token, 'line', None) or getattr(token, 'lineno', 1)
    column = getattr(token, 'column', None) or getattr(token, 'col', 1)

    # Extract or calculate ending position
    end_line = getattr(token, 'end_line', None)
    end_column = getattr(token, 'end_column', None) or getattr(token, 'end_col', None)

    # Get token text for length calculation if needed
    text = getattr(token, 'value', None) or getattr(token, 'text', '')

    if end_line is None:
        # If token text contains newlines, calculate end position
        if '\n' in text:
            lines = text.split('\n')
            end_line = line + len(lines) - 1
            end_column = len(lines[-1]) + 1
        else:
            end_line = line
            end_column = column + len(text)
    elif end_column is None:
        end_column = column + len(text)

    # Extract source text if available
    source_text = text if text else None

    return Span(
        file=str(file),
        line=int(line),
        column=int(column),
        end_line=int(end_line),
        end_column=int(end_column),
        source_text=source_text
    )


def span_union(span1: Span, span2: Span) -> Span:
    """
    Merge two spans to create a span covering both.

    This is useful for creating spans for AST nodes that encompass multiple
    tokens or sub-expressions.

    Args:
        span1: First span
        span2: Second span

    Returns:
        A new Span covering both input spans

    Raises:
        ValueError: If the spans are from different files

    Example:
        >>> s1 = Span("test.bh", 1, 5, 1, 10)
        >>> s2 = Span("test.bh", 1, 15, 2, 5)
        >>> union = span_union(s1, s2)
        >>> union.line, union.column, union.end_line, union.end_column
        (1, 5, 2, 5)
    """
    if span1.file != span2.file:
        raise ValueError(
            f"Cannot merge spans from different files: {span1.file} and {span2.file}"
        )

    # Find the earliest start
    if (span1.line, span1.column) <= (span2.line, span2.column):
        start_line, start_column = span1.line, span1.column
    else:
        start_line, start_column = span2.line, span2.column

    # Find the latest end
    if (span1.end_line, span1.end_column) >= (span2.end_line, span2.end_column):
        end_line, end_column = span1.end_line, span1.end_column
    else:
        end_line, end_column = span2.end_line, span2.end_column

    return Span(
        file=span1.file,
        line=start_line,
        column=start_column,
        end_line=end_line,
        end_column=end_column,
        source_text=None  # Combined span doesn't have cached text
    )


def span_to_string(span: Span, include_end: bool = False) -> str:
    """
    Convert a span to a human-readable string.

    Args:
        span: The span to format
        include_end: If True, include ending position (default: False)

    Returns:
        A string in the format "file:line:column" or "file:line:column-end_line:end_column"

    Example:
        >>> span = Span("test.bh", 10, 5, 10, 15)
        >>> span_to_string(span)
        'test.bh:10:5'
        >>> span_to_string(span, include_end=True)
        'test.bh:10:5-10:15'
    """
    base = f"{span.file}:{span.line}:{span.column}"

    if include_end:
        if span.line == span.end_line:
            base += f"-{span.end_column}"
        else:
            base += f"-{span.end_line}:{span.end_column}"

    return base


class SourceMap:
    """
    Maps filenames to their source code for error reporting.

    The SourceMap stores the original source code for each file encountered
    during compilation, allowing the compiler to display relevant source
    snippets in error messages.

    Example:
        >>> source_map = SourceMap()
        >>> source_map.add_source("test.bh", "func main() {\\n  print(42)\\n}")
        >>> source_map.get_line("test.bh", 2)
        '  print(42)'
        >>> span = Span("test.bh", 2, 3, 2, 8)
        >>> source_map.get_snippet(span)
        'print'
    """

    def __init__(self):
        """Initialize an empty SourceMap."""
        self._sources: Dict[str, str] = {}
        self._lines_cache: Dict[str, List[str]] = {}

    def add_source(self, filename: str, source: str) -> None:
        """
        Add source code for a file.

        Args:
            filename: The name of the file
            source: The complete source code
        """
        self._sources[filename] = source
        # Cache the lines for efficient access
        self._lines_cache[filename] = source.splitlines()

    def add_source_file(self, filepath: str) -> None:
        """
        Load and add source code from a file.

        Args:
            filepath: Path to the source file

        Raises:
            FileNotFoundError: If the file doesn't exist
            IOError: If the file cannot be read
        """
        path = Path(filepath)
        source = path.read_text(encoding='utf-8')
        self.add_source(str(filepath), source)

    def has_source(self, filename: str) -> bool:
        """
        Check if source code is available for a file.

        Args:
            filename: The name of the file

        Returns:
            True if source code is available
        """
        return filename in self._sources

    def get_source(self, filename: str) -> Optional[str]:
        """
        Get the complete source code for a file.

        Args:
            filename: The name of the file

        Returns:
            The source code, or None if not available
        """
        return self._sources.get(filename)

    def get_line(self, filename: str, line_num: int) -> Optional[str]:
        """
        Retrieve a specific line from a file.

        Args:
            filename: The name of the file
            line_num: The line number (1-indexed)

        Returns:
            The line content, or None if not available

        Example:
            >>> source_map = SourceMap()
            >>> source_map.add_source("test.bh", "line1\\nline2\\nline3")
            >>> source_map.get_line("test.bh", 2)
            'line2'
        """
        lines = self._lines_cache.get(filename)
        if lines is None or line_num < 1 or line_num > len(lines):
            return None
        return lines[line_num - 1]

    def get_lines(self, filename: str, start_line: int, end_line: int) -> Optional[List[str]]:
        """
        Retrieve a range of lines from a file.

        Args:
            filename: The name of the file
            start_line: The starting line number (1-indexed, inclusive)
            end_line: The ending line number (1-indexed, inclusive)

        Returns:
            A list of lines, or None if not available

        Example:
            >>> source_map = SourceMap()
            >>> source_map.add_source("test.bh", "line1\\nline2\\nline3")
            >>> source_map.get_lines("test.bh", 1, 2)
            ['line1', 'line2']
        """
        lines = self._lines_cache.get(filename)
        if lines is None:
            return None

        # Clamp to valid range
        start_line = max(1, start_line)
        end_line = min(len(lines), end_line)

        if start_line > end_line:
            return []

        return lines[start_line - 1:end_line]

    def get_snippet(self, span: Span) -> Optional[str]:
        """
        Extract the source text for a given span.

        This method extracts the exact text covered by a span, handling
        multi-line spans correctly.

        Args:
            span: The span to extract

        Returns:
            The source text, or None if not available

        Example:
            >>> source_map = SourceMap()
            >>> source_map.add_source("test.bh", "func main() {\\n  print(42)\\n}")
            >>> span = Span("test.bh", 1, 1, 1, 5)
            >>> source_map.get_snippet(span)
            'func'
        """
        # Return cached text if available
        if span.source_text is not None:
            return span.source_text

        lines = self._lines_cache.get(span.file)
        if lines is None:
            return None

        # Single line span
        if span.line == span.end_line:
            if span.line < 1 or span.line > len(lines):
                return None
            line = lines[span.line - 1]
            # Column is 1-indexed, end_column is exclusive
            start = max(0, span.column - 1)
            end = span.end_column - 1
            return line[start:end]

        # Multi-line span
        if span.line < 1 or span.end_line > len(lines):
            return None

        result_lines = []

        # First line (from column to end)
        first_line = lines[span.line - 1]
        result_lines.append(first_line[span.column - 1:])

        # Middle lines (complete lines)
        for i in range(span.line, span.end_line - 1):
            result_lines.append(lines[i])

        # Last line (from start to end_column)
        last_line = lines[span.end_line - 1]
        result_lines.append(last_line[:span.end_column - 1])

        return '\n'.join(result_lines)

    def format_error_context(self, span: Span, context_lines: int = 2) -> Optional[str]:
        """
        Format source code context for error reporting.

        This method generates a multi-line string showing the relevant source
        code with line numbers, with a pointer (^) indicating the error location.

        Args:
            span: The span to highlight
            context_lines: Number of context lines to show before and after

        Returns:
            Formatted error context, or None if source not available

        Example:
            >>> source_map = SourceMap()
            >>> source_map.add_source("test.bh", "line1\\nerror here\\nline3")
            >>> span = Span("test.bh", 2, 1, 2, 6)
            >>> print(source_map.format_error_context(span, context_lines=1))
             1 | line1
             2 | error here
               | ^^^^^
             3 | line3
        """
        lines = self._lines_cache.get(span.file)
        if lines is None:
            return None

        # Determine line range to display
        start = max(1, span.line - context_lines)
        end = min(len(lines), span.end_line + context_lines)

        # Calculate width needed for line numbers
        line_num_width = len(str(end))

        result_lines = []

        for line_num in range(start, end + 1):
            line = lines[line_num - 1]
            prefix = f"{line_num:>{line_num_width}} | "
            result_lines.append(prefix + line)

            # Add pointer line for error location
            if span.line <= line_num <= span.end_line:
                pointer_prefix = " " * line_num_width + " | "

                if line_num == span.line == span.end_line:
                    # Single line error
                    pointer = " " * (span.column - 1) + "^" * (span.end_column - span.column)
                elif line_num == span.line:
                    # First line of multi-line error
                    pointer = " " * (span.column - 1) + "^" * (len(line) - span.column + 1)
                elif line_num == span.end_line:
                    # Last line of multi-line error
                    pointer = "^" * (span.end_column - 1)
                else:
                    # Middle line of multi-line error
                    pointer = "^" * len(line)

                result_lines.append(pointer_prefix + pointer)

        return '\n'.join(result_lines)

    def clear(self) -> None:
        """Clear all stored source code."""
        self._sources.clear()
        self._lines_cache.clear()

    def __len__(self) -> int:
        """Return the number of files in the source map."""
        return len(self._sources)

    def __contains__(self, filename: str) -> bool:
        """Check if a file is in the source map."""
        return filename in self._sources
