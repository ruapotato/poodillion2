#!/usr/bin/env python3
"""
LLVM Type Mapping for Brainhair Compiler

Maps Brainhair types to LLVM IR type representations.
Handles structs, arrays, pointers, and primitives.

Target: i686-unknown-linux-gnu (32-bit x86 Linux)
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from enum import Enum, auto

from ast_nodes import *

# Polyglot: Python string type detection
# In Brainhair, this always returns False; in Python, checks isinstance(ty, str)
def is_python_str(ty) -> bool:
    return False

try:
    def is_python_str(ty) -> bool:
        return isinstance(ty, type(""))
except:
    pass


@dataclass
class LLVMType:
    """Base class for LLVM types."""
    pass


@dataclass
class LLVMIntType(LLVMType):
    """Integer type (i1, i8, i16, i32, i64)."""
    bits: int

    def __str__(self):
        return f"i{self.bits}"


@dataclass
class LLVMFloatType(LLVMType):
    """Float type (float, double)."""
    is_double: bool = False

    def __str__(self):
        return "double" if self.is_double else "float"


@dataclass
class LLVMVoidType(LLVMType):
    """Void type."""

    def __str__(self):
        return "void"


@dataclass
class LLVMPointerType(LLVMType):
    """Pointer type."""
    pointee: LLVMType

    def __str__(self):
        return f"{self.pointee}*"


@dataclass
class LLVMArrayType(LLVMType):
    """Array type [N x T]."""
    size: int
    element_type: LLVMType

    def __str__(self):
        return f"[{self.size} x {self.element_type}]"


@dataclass
class LLVMStructType(LLVMType):
    """Struct type %name = type { ... }."""
    name: str
    fields: List[Tuple[str, LLVMType]]

    def __str__(self):
        return f"%{self.name}"

    def definition(self) -> str:
        """Get LLVM type definition."""
        field_types = ", ".join(str(ft[1]) for ft in self.fields)
        return f"%{self.name} = type {{ {field_types} }}"


@dataclass
class LLVMFunctionType(LLVMType):
    """Function type."""
    return_type: LLVMType
    param_types: List[LLVMType]
    is_vararg: bool = False

    def __str__(self):
        params = ", ".join(str(p) for p in self.param_types)
        if self.is_vararg:
            params = params + ", ..." if params else "..."
        return f"{self.return_type} ({params})"


class LLVMTypeMapper:
    """
    Maps Brainhair types to LLVM types.

    Handles:
    - Primitive types (int8..int64, uint8..uint64, bool, char)
    - Pointer types
    - Array types with sizes
    - Struct types with field layout
    """

    def __init__(self):
        # Type cache for struct definitions
        self.struct_types: Dict[str, LLVMStructType] = {}
        self.struct_definitions: List[str] = []

        # Primitive type mapping
        self.primitive_map = {
            'int8': LLVMIntType(8),
            'int16': LLVMIntType(16),
            'int32': LLVMIntType(32),
            'int64': LLVMIntType(64),
            'uint8': LLVMIntType(8),
            'uint16': LLVMIntType(16),
            'uint32': LLVMIntType(32),
            'uint64': LLVMIntType(64),
            'i8': LLVMIntType(8),
            'i16': LLVMIntType(16),
            'i32': LLVMIntType(32),
            'i64': LLVMIntType(64),
            'u8': LLVMIntType(8),
            'u16': LLVMIntType(16),
            'u32': LLVMIntType(32),
            'u64': LLVMIntType(64),
            'bool': LLVMIntType(1),
            'char': LLVMIntType(8),
            'float32': LLVMFloatType(False),
            'float64': LLVMFloatType(True),
            'float': LLVMFloatType(False),
            'double': LLVMFloatType(True),
            'void': LLVMVoidType(),
        }

    def map_type(self, ty) -> LLVMType:
        """Map a Brainhair type to LLVM type."""
        if ty is None:
            return LLVMVoidType()

        if isinstance(ty, Type):
            name = ty.name.lower()
            if name in self.primitive_map:
                return self.primitive_map[name]
            # Could be a struct name
            if name in self.struct_types:
                return self.struct_types[name]
            # Default to i32 for unknown types
            return LLVMIntType(32)

        if isinstance(ty, PointerType):
            pointee = self.map_type(ty.base_type)
            return LLVMPointerType(pointee)

        if isinstance(ty, ArrayType):
            elem = self.map_type(ty.element_type)
            return LLVMArrayType(ty.size, elem)

        if is_python_str(ty):
            lower = ty.lower()
            if lower in self.primitive_map:
                return self.primitive_map[lower]
            if lower in self.struct_types:
                return self.struct_types[lower]
            return LLVMIntType(32)

        return LLVMVoidType()

    def define_struct(self, name: str, fields: List[Tuple[str, 'Type']]) -> LLVMStructType:
        """Define a struct type."""
        llvm_fields = []
        for field_name, field_type in fields:
            llvm_type = self.map_type(field_type)
            llvm_fields.append((field_name, llvm_type))

        struct_type = LLVMStructType(name.lower(), llvm_fields)
        self.struct_types[name.lower()] = struct_type
        self.struct_definitions.append(struct_type.definition())
        return struct_type

    def get_struct_field_index(self, struct_name: str, field_name: str) -> int:
        """Get the index of a field in a struct."""
        lower_name = struct_name.lower()
        if lower_name not in self.struct_types:
            return -1
        struct_type = self.struct_types[lower_name]
        for i, (name, _) in enumerate(struct_type.fields):
            if name == field_name:
                return i
        return -1

    def get_type_size(self, ty: LLVMType) -> int:
        """Get the size of a type in bytes (for 32-bit target)."""
        if isinstance(ty, LLVMIntType):
            return (ty.bits + 7) // 8
        elif isinstance(ty, LLVMFloatType):
            return 8 if ty.is_double else 4
        elif isinstance(ty, LLVMPointerType):
            return 4  # 32-bit pointers
        elif isinstance(ty, LLVMArrayType):
            return ty.size * self.get_type_size(ty.element_type)
        elif isinstance(ty, LLVMStructType):
            total = 0
            for _, field_type in ty.fields:
                total += self.get_type_size(field_type)
            return total
        elif isinstance(ty, LLVMVoidType):
            return 0
        return 4

    def get_alignment(self, ty: LLVMType) -> int:
        """Get the alignment of a type in bytes."""
        if isinstance(ty, LLVMIntType):
            return min(4, (ty.bits + 7) // 8)
        elif isinstance(ty, LLVMFloatType):
            return 8 if ty.is_double else 4
        elif isinstance(ty, LLVMPointerType):
            return 4
        elif isinstance(ty, LLVMArrayType):
            return self.get_alignment(ty.element_type)
        elif isinstance(ty, LLVMStructType):
            max_align = 1
            for _, field_type in ty.fields:
                max_align = max(max_align, self.get_alignment(field_type))
            return max_align
        return 4

    def get_all_definitions(self) -> str:
        """Get all struct type definitions."""
        return "\n".join(self.struct_definitions)


# ============================================================================
# Test
# ============================================================================

if __name__ == "__main__":
    mapper = LLVMTypeMapper()

    # Test primitive types
    print("=== Primitive Types ===")
    print(f"int32 -> {mapper.map_type(Type('int32'))}")
    print(f"bool -> {mapper.map_type(Type('bool'))}")
    print(f"char -> {mapper.map_type(Type('char'))}")

    # Test pointer types
    print("\n=== Pointer Types ===")
    print(f"ptr int32 -> {mapper.map_type(PointerType(Type('int32')))}")
    print(f"ptr ptr int8 -> {mapper.map_type(PointerType(PointerType(Type('int8'))))}")

    # Test array types
    print("\n=== Array Types ===")
    print(f"array[10, int32] -> {mapper.map_type(ArrayType(size=10, element_type=Type('int32')))}")

    # Test struct types
    print("\n=== Struct Types ===")
    mapper.define_struct("Point", [("x", Type("int32")), ("y", Type("int32"))])
    mapper.define_struct("Rectangle", [
        ("origin", Type("Point")),
        ("width", Type("int32")),
        ("height", Type("int32"))
    ])

    print(mapper.get_all_definitions())
    print(f"Point -> {mapper.map_type(Type('Point'))}")

    # Test sizes
    print("\n=== Type Sizes ===")
    print(f"i32 size: {mapper.get_type_size(LLVMIntType(32))} bytes")
    print(f"i8* size: {mapper.get_type_size(LLVMPointerType(LLVMIntType(8)))} bytes")
    print(f"[10 x i32] size: {mapper.get_type_size(LLVMArrayType(10, LLVMIntType(32)))} bytes")
