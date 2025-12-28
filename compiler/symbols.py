"""
Symbol table framework for the Brainhair compiler.

This module provides the infrastructure for tracking symbols (variables, functions,
types, etc.) across different scopes during semantic analysis and type checking.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any
from enum import Enum, auto


class SymbolKind(Enum):
    """Classification of symbol types."""
    VARIABLE = auto()
    FUNCTION = auto()
    TYPE = auto()
    PARAMETER = auto()


@dataclass
class TypeInfo:
    """
    Type information for symbols.

    This will be populated during type checking and can represent:
    - Primitive types (i32, u8, bool, etc.)
    - Pointer types (*T)
    - Array types ([T; N])
    - Slice types ([]T) - fat pointer with ptr + len
    - Struct types
    - Function types
    """
    name: str
    is_pointer: bool = False
    is_array: bool = False
    is_slice: bool = False
    array_size: Optional[int] = None
    element_type: Optional['TypeInfo'] = None
    struct_fields: Optional[Dict[str, 'TypeInfo']] = None

    def __str__(self) -> str:
        if self.is_pointer and self.element_type:
            return f"*{self.element_type}"
        if self.is_array and self.element_type:
            size_str = str(self.array_size) if self.array_size else ""
            return f"[{self.element_type}; {size_str}]"
        if self.is_slice and self.element_type:
            return f"[]{self.element_type}"
        return self.name

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, TypeInfo):
            return False
        if self.name != other.name:
            return False
        if self.is_pointer != other.is_pointer:
            return False
        if self.is_array != other.is_array:
            return False
        if self.is_slice != other.is_slice:
            return False
        if self.array_size != other.array_size:
            return False
        if self.element_type != other.element_type:
            return False
        return True


@dataclass
class Span:
    """Source location information for error reporting."""
    line: int
    column: int
    length: int
    source_file: Optional[str] = None

    def __str__(self) -> str:
        if self.source_file:
            return f"{self.source_file}:{self.line}:{self.column}"
        return f"{self.line}:{self.column}"


@dataclass
class Symbol:
    """
    Base class for all symbols in the symbol table.

    A symbol represents any named entity in the program: variables,
    functions, types, parameters, etc.
    """
    name: str
    span: Span
    type_info: Optional[TypeInfo] = None
    kind: SymbolKind = SymbolKind.VARIABLE

    def __str__(self) -> str:
        type_str = f": {self.type_info}" if self.type_info else ""
        return f"{self.name}{type_str}"


@dataclass
class VariableSymbol(Symbol):
    """
    Symbol for variable declarations.

    Tracks mutability and ownership information for variables.
    This is essential for Brainhair's borrow checker.
    """
    is_mutable: bool = False
    is_moved: bool = False  # Track if value has been moved (for ownership)
    owner_scope: Optional['Scope'] = None
    is_captured: bool = False  # For closure analysis

    def __post_init__(self):
        self.kind = SymbolKind.VARIABLE

    def __str__(self) -> str:
        mut_str = "mut " if self.is_mutable else ""
        type_str = f": {self.type_info}" if self.type_info else ""
        moved_str = " (moved)" if self.is_moved else ""
        return f"{mut_str}{self.name}{type_str}{moved_str}"


@dataclass
class ParamSymbol(Symbol):
    """
    Symbol for function parameters.

    Parameters are similar to variables but have additional context
    about their position in the parameter list.
    """
    is_mutable: bool = False
    position: int = 0  # Position in parameter list
    default_value: Optional[Any] = None  # For future default arguments

    def __post_init__(self):
        self.kind = SymbolKind.PARAMETER

    def __str__(self) -> str:
        mut_str = "mut " if self.is_mutable else ""
        type_str = f": {self.type_info}" if self.type_info else ""
        return f"{mut_str}{self.name}{type_str}"


@dataclass
class FunctionSymbol(Symbol):
    """
    Symbol for function declarations.

    Stores parameter and return type information for type checking
    and call validation.
    """
    params: List[ParamSymbol] = field(default_factory=list)
    return_type: Optional[TypeInfo] = None
    is_extern: bool = False  # External/foreign function
    is_variadic: bool = False  # For future variadic functions
    body_scope: Optional['Scope'] = None  # The function's body scope

    def __post_init__(self):
        self.kind = SymbolKind.FUNCTION

    def get_signature(self) -> str:
        """Get function signature string for error messages."""
        param_str = ", ".join(str(p) for p in self.params)
        ret_str = f" -> {self.return_type}" if self.return_type else ""
        extern_str = "extern " if self.is_extern else ""
        return f"{extern_str}fn {self.name}({param_str}){ret_str}"

    def __str__(self) -> str:
        return self.get_signature()


@dataclass
class TypeSymbol(Symbol):
    """
    Symbol for type definitions (structs, enums, type aliases).

    Stores structure information including fields for struct types.
    """
    fields: Dict[str, TypeInfo] = field(default_factory=dict)
    is_struct: bool = True
    is_enum: bool = False
    is_alias: bool = False
    aliased_type: Optional[TypeInfo] = None

    def __post_init__(self):
        self.kind = SymbolKind.TYPE

    def get_field(self, field_name: str) -> Optional[TypeInfo]:
        """Get type info for a specific field."""
        return self.fields.get(field_name)

    def has_field(self, field_name: str) -> bool:
        """Check if type has a specific field."""
        return field_name in self.fields

    def __str__(self) -> str:
        if self.is_alias and self.aliased_type:
            return f"type {self.name} = {self.aliased_type}"
        kind_str = "enum" if self.is_enum else "struct"
        if self.fields:
            fields_str = ", ".join(f"{k}: {v}" for k, v in self.fields.items())
            return f"{kind_str} {self.name} {{ {fields_str} }}"
        return f"{kind_str} {self.name}"


class SymbolError(Exception):
    """Base exception for symbol table errors."""
    pass


class DuplicateSymbolError(SymbolError):
    """Raised when attempting to define a symbol that already exists in the current scope."""

    def __init__(self, symbol: Symbol, existing: Symbol):
        self.symbol = symbol
        self.existing = existing
        self.message = f"Duplicate symbol '{symbol.name}' at {symbol.span}. Previously defined at {existing.span}"


class UndefinedSymbolError(SymbolError):
    """Raised when looking up a symbol that doesn't exist."""

    def __init__(self, name: str, span: Optional[Span] = None):
        self.name = name
        self.span = span
        location = f" at {span}" if span else ""
        self.message = f"Undefined symbol '{name}'{location}"


class Scope:
    """
    Represents a lexical scope in the program.

    Scopes form a tree structure with parent-child relationships.
    Each scope maintains its own symbol table and can look up symbols
    in parent scopes.
    """

    def __init__(self, name: str = "global", parent: Optional['Scope'] = None):
        """
        Initialize a new scope.

        Args:
            name: Human-readable name for debugging
            parent: Parent scope (None for global scope)
        """
        self.name = name
        self.parent = parent
        self.symbols: Dict[str, Symbol] = {}
        self.children: List['Scope'] = []

        if parent:
            parent.children.append(self)

    def define(self, symbol: Symbol) -> None:
        """
        Define a symbol in this scope.

        Args:
            symbol: The symbol to define

        Raises:
            DuplicateSymbolError: If symbol already exists in this scope
        """
        if symbol.name in self.symbols:
            raise DuplicateSymbolError(symbol, self.symbols[symbol.name])

        self.symbols[symbol.name] = symbol

        # Set owner scope for variables
        if isinstance(symbol, VariableSymbol):
            symbol.owner_scope = self

    def lookup_local(self, name: str) -> Optional[Symbol]:
        """
        Look up a symbol only in this scope (not parent scopes).

        Args:
            name: Symbol name to look up

        Returns:
            The symbol if found, None otherwise
        """
        return self.symbols.get(name)

    def lookup(self, name: str) -> Optional[Symbol]:
        """
        Look up a symbol in this scope or any parent scope.

        Searches from innermost to outermost scope, supporting shadowing.

        Args:
            name: Symbol name to look up

        Returns:
            The symbol if found, None otherwise
        """
        # Check current scope first
        symbol = self.lookup_local(name)
        if symbol:
            return symbol

        # Recursively check parent scopes
        if self.parent:
            return self.parent.lookup(name)

        return None

    def get_all_symbols(self) -> Dict[str, Symbol]:
        """Get all symbols defined in this scope."""
        return self.symbols.copy()

    def get_depth(self) -> int:
        """Get the nesting depth of this scope (0 for global)."""
        depth = 0
        current = self.parent
        while current:
            depth += 1
            current = current.parent
        return depth

    def __str__(self) -> str:
        return f"Scope({self.name}, {len(self.symbols)} symbols)"

    def __repr__(self) -> str:
        return f"<Scope {self.name} at depth {self.get_depth()}>"


class SymbolTable:
    """
    Manages the complete symbol table for a Brainhair program.

    Provides a stack-based scope management system for tracking symbols
    throughout the compilation process. Handles entering/exiting scopes
    and looking up symbols across scope boundaries.
    """

    def __init__(self):
        """Initialize the symbol table with a global scope."""
        self.global_scope = Scope("global")
        self.scope_stack: List[Scope] = [self.global_scope]
        self._scope_counter = 0
        self._initialize_builtins()

    def _initialize_builtins(self) -> None:
        """Initialize built-in types and functions."""
        # Built-in types
        builtin_types = [
            "i8", "i16", "i32", "i64",
            "u8", "u16", "u32", "u64",
            "f32", "f64",
            "bool", "char", "str",
            "void"
        ]

        for type_name in builtin_types:
            type_symbol = TypeSymbol(
                name=type_name,
                span=Span(0, 0, 0, source_file="<builtin>"),
                type_info=TypeInfo(type_name),
                is_struct=False
            )
            self.global_scope.define(type_symbol)

    @property
    def current_scope(self) -> Scope:
        """Get the current (innermost) scope."""
        return self.scope_stack[-1]

    def push_scope(self, name: Optional[str] = None) -> Scope:
        """
        Enter a new scope.

        Args:
            name: Optional name for the scope (auto-generated if None)

        Returns:
            The newly created scope
        """
        if name is None:
            self._scope_counter += 1
            name = f"scope_{self._scope_counter}"

        new_scope = Scope(name, parent=self.current_scope)
        self.scope_stack.append(new_scope)
        return new_scope

    def pop_scope(self) -> Scope:
        """
        Exit the current scope and return to the parent scope.

        Returns:
            The scope that was popped

        Raises:
            SymbolError: If attempting to pop the global scope
        """
        if len(self.scope_stack) <= 1:
            raise SymbolError("Cannot pop global scope")

        return self.scope_stack.pop()

    def define(self, symbol: Symbol) -> None:
        """
        Define a symbol in the current scope.

        Args:
            symbol: The symbol to define

        Raises:
            DuplicateSymbolError: If symbol already exists in current scope
        """
        self.current_scope.define(symbol)

    def lookup(self, name: str, span: Optional[Span] = None) -> Symbol:
        """
        Look up a symbol in the current scope or any parent scope.

        Args:
            name: Symbol name to look up
            span: Source location for error reporting

        Returns:
            The symbol if found

        Raises:
            UndefinedSymbolError: If symbol is not found
        """
        symbol = self.current_scope.lookup(name)
        if symbol is None:
            raise UndefinedSymbolError(name, span)
        return symbol

    def lookup_optional(self, name: str) -> Optional[Symbol]:
        """
        Look up a symbol without raising an error if not found.

        Args:
            name: Symbol name to look up

        Returns:
            The symbol if found, None otherwise
        """
        return self.current_scope.lookup(name)

    def lookup_local(self, name: str) -> Optional[Symbol]:
        """
        Look up a symbol only in the current scope.

        Args:
            name: Symbol name to look up

        Returns:
            The symbol if found, None otherwise
        """
        return self.current_scope.lookup_local(name)

    def is_global_scope(self) -> bool:
        """Check if we're currently in the global scope."""
        return len(self.scope_stack) == 1

    def get_scope_depth(self) -> int:
        """Get the current scope nesting depth."""
        return len(self.scope_stack) - 1

    def dump(self) -> str:
        """
        Generate a string representation of the entire symbol table.

        Useful for debugging and visualization.
        """
        lines = ["Symbol Table Dump:"]
        self._dump_scope(self.global_scope, lines, indent=0)
        return "\n".join(lines)

    def _dump_scope(self, scope: Scope, lines: List[str], indent: int) -> None:
        """Recursively dump scope contents."""
        prefix = "  " * indent
        lines.append(f"{prefix}{scope}")

        for name, symbol in sorted(scope.symbols.items()):
            lines.append(f"{prefix}  {symbol.kind.name}: {symbol}")

        for child in scope.children:
            self._dump_scope(child, lines, indent + 1)

    def __str__(self) -> str:
        return f"SymbolTable(depth={self.get_scope_depth()}, current={self.current_scope.name})"

    def __repr__(self) -> str:
        return f"<SymbolTable with {len(self.scope_stack)} scopes>"


# Utility functions for common operations

def create_builtin_type(name: str) -> TypeInfo:
    """Create a TypeInfo for a built-in type."""
    return TypeInfo(name)


def create_pointer_type(element_type: TypeInfo) -> TypeInfo:
    """Create a pointer type (*T)."""
    return TypeInfo(
        name=f"*{element_type.name}",
        is_pointer=True,
        element_type=element_type
    )


def create_array_type(element_type: TypeInfo, size: Optional[int] = None) -> TypeInfo:
    """Create an array type ([T; N])."""
    size_str = str(size) if size else ""
    return TypeInfo(
        name=f"[{element_type.name}; {size_str}]",
        is_array=True,
        array_size=size,
        element_type=element_type
    )


def create_slice_type(element_type: TypeInfo) -> TypeInfo:
    """Create a slice type ([]T) - fat pointer with ptr + len."""
    return TypeInfo(
        name=f"[]{element_type.name}",
        is_slice=True,
        element_type=element_type
    )


def create_list_type(element_type: TypeInfo) -> TypeInfo:
    """Create a list type (List[T]) - dynamic array."""
    return TypeInfo(
        name=f"List[{element_type.name}]",
        is_array=True,  # Lists are array-like
        element_type=element_type
    )


def create_any_type() -> TypeInfo:
    """Create an 'any' type - placeholder for unknown/dynamic types."""
    return TypeInfo(name="any")


def is_numeric_type(type_info: TypeInfo) -> bool:
    """Check if a type is numeric (integer or float)."""
    return type_info.name in ("i8", "i16", "i32", "i64", "u8", "u16", "u32", "u64", "f32", "f64")


def is_integer_type(type_info: TypeInfo) -> bool:
    """Check if a type is an integer type."""
    return type_info.name in ("i8", "i16", "i32", "i64", "u8", "u16", "u32", "u64")


def is_float_type(type_info: TypeInfo) -> bool:
    """Check if a type is a floating-point type."""
    return type_info.name in ("f32", "f64")


def is_signed_type(type_info: TypeInfo) -> bool:
    """Check if a type is a signed integer type."""
    return type_info.name in ("i8", "i16", "i32", "i64")


def is_unsigned_type(type_info: TypeInfo) -> bool:
    """Check if a type is an unsigned integer type."""
    return type_info.name in ("u8", "u16", "u32", "u64")
