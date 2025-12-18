#!/usr/bin/env python3
"""
Mid-Level Intermediate Representation (MIR) for Brainhair Compiler

This module defines the MIR data structures, which sit between the AST and
machine code generation. MIR is in SSA (Static Single Assignment) form and
provides explicit control flow and memory operations.

Key features:
- SSA form with explicit phi nodes
- Basic blocks with explicit control flow
- Typed values and operations
- Explicit memory operations (load, store)
- Target-independent representation
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Set, Union
from enum import Enum, auto


# ============================================================================
# Types
# ============================================================================

class MIRType(Enum):
    """Primitive MIR types."""
    VOID = auto()
    BOOL = auto()
    I8 = auto()
    I16 = auto()
    I32 = auto()
    I64 = auto()
    U8 = auto()
    U16 = auto()
    U32 = auto()
    U64 = auto()
    F32 = auto()
    F64 = auto()
    PTR = auto()  # Generic pointer

    def size_bytes(self) -> int:
        """Return size of type in bytes."""
        sizes = {
            MIRType.VOID: 0,
            MIRType.BOOL: 1,
            MIRType.I8: 1, MIRType.U8: 1,
            MIRType.I16: 2, MIRType.U16: 2,
            MIRType.I32: 4, MIRType.U32: 4,
            MIRType.I64: 8, MIRType.U64: 8,
            MIRType.F32: 4, MIRType.F64: 8,
            MIRType.PTR: 4,  # 32-bit target
        }
        return sizes.get(self, 4)

    def is_integer(self) -> bool:
        """Check if type is an integer type."""
        return self in {
            MIRType.I8, MIRType.I16, MIRType.I32, MIRType.I64,
            MIRType.U8, MIRType.U16, MIRType.U32, MIRType.U64,
        }

    def is_signed(self) -> bool:
        """Check if type is a signed integer."""
        return self in {MIRType.I8, MIRType.I16, MIRType.I32, MIRType.I64}

    def is_float(self) -> bool:
        """Check if type is a floating point type."""
        return self in {MIRType.F32, MIRType.F64}


@dataclass
class PointerMIRType:
    """Pointer type with known pointee type."""
    pointee: Union[MIRType, 'PointerMIRType', 'ArrayMIRType', 'StructMIRType']

    def size_bytes(self) -> int:
        return 4  # 32-bit target

    def __str__(self):
        return f"*{self.pointee}"


@dataclass
class ArrayMIRType:
    """Fixed-size array type."""
    element: Union[MIRType, 'PointerMIRType', 'ArrayMIRType', 'StructMIRType']
    size: int

    def size_bytes(self) -> int:
        elem_size = self.element.size_bytes() if hasattr(self.element, 'size_bytes') else 4
        return elem_size * self.size

    def __str__(self):
        return f"[{self.element}; {self.size}]"


@dataclass
class StructMIRType:
    """Struct type with named fields."""
    name: str
    fields: Dict[str, Union[MIRType, 'PointerMIRType', 'ArrayMIRType', 'StructMIRType']]
    field_order: List[str] = field(default_factory=list)

    def size_bytes(self) -> int:
        # Simple calculation without padding for now
        total = 0
        for field_type in self.fields.values():
            if hasattr(field_type, 'size_bytes'):
                total += field_type.size_bytes()
            else:
                total += 4
        return total

    def __str__(self):
        return self.name


# Type alias for all MIR types
MIRAnyType = Union[MIRType, PointerMIRType, ArrayMIRType, StructMIRType]


# ============================================================================
# Values (SSA)
# ============================================================================

@dataclass
class MIRValue:
    """
    Base class for all MIR values (SSA values).

    In SSA form, each value is assigned exactly once. Values can be:
    - Constants (immediate values)
    - Virtual registers (instruction results)
    - Function parameters
    - Global references
    """
    name: str  # SSA name like %1, %temp, etc.
    ty: MIRAnyType

    def __str__(self):
        return f"{self.name}: {self.ty}"


@dataclass
class MIRConstant(MIRValue):
    """Constant immediate value."""
    value: Union[int, float, bool, str]

    def __str__(self):
        return f"{self.value}"


@dataclass
class MIRVirtualReg(MIRValue):
    """Virtual register (result of an instruction)."""
    pass


@dataclass
class MIRParam(MIRValue):
    """Function parameter."""
    index: int  # Parameter position


@dataclass
class MIRGlobal(MIRValue):
    """Reference to a global variable or function."""
    is_function: bool = False


# ============================================================================
# Instructions
# ============================================================================

class MIROp(Enum):
    """MIR operation opcodes."""
    # Arithmetic
    ADD = auto()
    SUB = auto()
    MUL = auto()
    DIV = auto()
    MOD = auto()
    NEG = auto()

    # Bitwise
    AND = auto()
    OR = auto()
    XOR = auto()
    NOT = auto()
    SHL = auto()
    SHR = auto()

    # Comparison
    EQ = auto()
    NE = auto()
    LT = auto()
    LE = auto()
    GT = auto()
    GE = auto()

    # Memory
    LOAD = auto()
    STORE = auto()
    ALLOCA = auto()  # Stack allocation
    GEP = auto()     # Get element pointer (array/struct access)

    # Control flow
    BR = auto()      # Unconditional branch
    CONDBR = auto()  # Conditional branch
    CALL = auto()
    RET = auto()

    # Type conversion
    CAST = auto()
    ZEXT = auto()    # Zero extend
    SEXT = auto()    # Sign extend
    TRUNC = auto()   # Truncate

    # SSA
    PHI = auto()     # Phi node for merging values

    # Misc
    NOP = auto()


@dataclass
class MIRInstruction:
    """
    A single MIR instruction.

    Each instruction may produce a result value (dest) and operate on
    operand values (operands). The operation is determined by the op field.
    """
    op: MIROp
    dest: Optional[MIRValue] = None  # Result register (None for void ops)
    operands: List[MIRValue] = field(default_factory=list)
    ty: Optional[MIRAnyType] = None  # Type for type-specific ops

    # For branch instructions
    true_block: Optional['MIRBasicBlock'] = None
    false_block: Optional['MIRBasicBlock'] = None

    # For phi nodes: list of (value, predecessor_block) pairs
    phi_incoming: List[tuple] = field(default_factory=list)

    # For call instructions
    callee: Optional[str] = None
    args: List[MIRValue] = field(default_factory=list)

    def __str__(self):
        if self.op == MIROp.BR:
            return f"br {self.true_block.name if self.true_block else '?'}"
        elif self.op == MIROp.CONDBR:
            cond = self.operands[0].name if self.operands else "?"
            t = self.true_block.name if self.true_block else "?"
            f = self.false_block.name if self.false_block else "?"
            return f"condbr {cond}, {t}, {f}"
        elif self.op == MIROp.RET:
            if self.operands:
                return f"ret {self.operands[0].name}"
            return "ret void"
        elif self.op == MIROp.CALL:
            args_str = ", ".join(o.name for o in self.args)
            if self.dest:
                return f"{self.dest.name} = call {self.callee}({args_str})"
            return f"call {self.callee}({args_str})"
        elif self.op == MIROp.PHI:
            incoming = ", ".join(f"[{v.name}, {b.name}]" for v, b in self.phi_incoming)
            return f"{self.dest.name} = phi {incoming}"
        elif self.op == MIROp.ALLOCA:
            return f"{self.dest.name} = alloca {self.ty}"
        elif self.op == MIROp.LOAD:
            return f"{self.dest.name} = load {self.operands[0].name}"
        elif self.op == MIROp.STORE:
            return f"store {self.operands[0].name}, {self.operands[1].name}"
        elif self.op == MIROp.GEP:
            indices = ", ".join(o.name for o in self.operands[1:])
            return f"{self.dest.name} = gep {self.operands[0].name}, {indices}"
        elif self.dest:
            ops_str = ", ".join(o.name if hasattr(o, 'name') else str(o) for o in self.operands)
            return f"{self.dest.name} = {self.op.name.lower()} {ops_str}"
        else:
            ops_str = ", ".join(o.name if hasattr(o, 'name') else str(o) for o in self.operands)
            return f"{self.op.name.lower()} {ops_str}"


# ============================================================================
# Basic Blocks
# ============================================================================

@dataclass
class MIRBasicBlock:
    """
    A basic block in the control flow graph.

    A basic block is a sequence of instructions with:
    - A single entry point (the first instruction)
    - A single exit point (the last instruction, which is a terminator)
    - No branches into the middle
    """
    name: str
    instructions: List[MIRInstruction] = field(default_factory=list)
    predecessors: List['MIRBasicBlock'] = field(default_factory=list)
    successors: List['MIRBasicBlock'] = field(default_factory=list)

    def add_instruction(self, inst: MIRInstruction) -> None:
        """Add an instruction to this block."""
        self.instructions.append(inst)

    def add_predecessor(self, block: 'MIRBasicBlock') -> None:
        """Add a predecessor block."""
        if block not in self.predecessors:
            self.predecessors.append(block)

    def add_successor(self, block: 'MIRBasicBlock') -> None:
        """Add a successor block."""
        if block not in self.successors:
            self.successors.append(block)

    def is_terminated(self) -> bool:
        """Check if block has a terminator instruction."""
        if not self.instructions:
            return False
        last_op = self.instructions[-1].op
        return last_op in {MIROp.BR, MIROp.CONDBR, MIROp.RET}

    def terminator(self) -> Optional[MIRInstruction]:
        """Get the terminator instruction if present."""
        if self.instructions and self.is_terminated():
            return self.instructions[-1]
        return None

    def __str__(self):
        lines = [f"{self.name}:"]
        for inst in self.instructions:
            lines.append(f"  {inst}")
        return "\n".join(lines)


# ============================================================================
# Functions
# ============================================================================

@dataclass
class MIRFunction:
    """
    A function in MIR form.

    Contains:
    - Function signature (name, parameters, return type)
    - Entry block
    - All basic blocks
    - Local allocations
    """
    name: str
    params: List[MIRParam] = field(default_factory=list)
    return_type: MIRAnyType = MIRType.VOID
    blocks: List[MIRBasicBlock] = field(default_factory=list)
    is_extern: bool = False

    # Value numbering counter
    _value_counter: int = field(default=0, repr=False)

    def entry_block(self) -> Optional[MIRBasicBlock]:
        """Get the entry basic block."""
        return self.blocks[0] if self.blocks else None

    def create_block(self, name: Optional[str] = None) -> MIRBasicBlock:
        """Create a new basic block."""
        if name is None:
            name = f"bb{len(self.blocks)}"
        block = MIRBasicBlock(name)
        self.blocks.append(block)
        return block

    def new_value(self, ty: MIRAnyType, prefix: str = "v") -> MIRVirtualReg:
        """Create a new SSA value."""
        name = f"%{prefix}{self._value_counter}"
        self._value_counter += 1
        return MIRVirtualReg(name, ty)

    def __str__(self):
        params_str = ", ".join(str(p) for p in self.params)
        if self.is_extern:
            return f"extern fn {self.name}({params_str}) -> {self.return_type}"

        lines = [f"fn {self.name}({params_str}) -> {self.return_type} {{"]
        for block in self.blocks:
            for line in str(block).split("\n"):
                lines.append(f"  {line}")
        lines.append("}")
        return "\n".join(lines)


# ============================================================================
# Module
# ============================================================================

@dataclass
class MIRModule:
    """
    A complete MIR module (compilation unit).

    Contains:
    - Global variables
    - Type definitions
    - Functions
    """
    name: str = "module"
    globals: Dict[str, MIRGlobal] = field(default_factory=dict)
    types: Dict[str, StructMIRType] = field(default_factory=dict)
    functions: Dict[str, MIRFunction] = field(default_factory=dict)

    def add_function(self, func: MIRFunction) -> None:
        """Add a function to the module."""
        self.functions[func.name] = func

    def add_global(self, name: str, ty: MIRAnyType, value: Optional[MIRConstant] = None) -> MIRGlobal:
        """Add a global variable."""
        glob = MIRGlobal(f"@{name}", ty)
        self.globals[name] = glob
        return glob

    def add_type(self, struct_type: StructMIRType) -> None:
        """Add a struct type definition."""
        self.types[struct_type.name] = struct_type

    def get_function(self, name: str) -> Optional[MIRFunction]:
        """Get a function by name."""
        return self.functions.get(name)

    def __str__(self):
        lines = [f"; MIR Module: {self.name}", ""]

        # Types
        if self.types:
            lines.append("; Types")
            for name, ty in self.types.items():
                fields_str = ", ".join(f"{n}: {t}" for n, t in ty.fields.items())
                lines.append(f"type {name} = {{ {fields_str} }}")
            lines.append("")

        # Globals
        if self.globals:
            lines.append("; Globals")
            for name, glob in self.globals.items():
                lines.append(f"@{name}: {glob.ty}")
            lines.append("")

        # Functions
        if self.functions:
            lines.append("; Functions")
            for func in self.functions.values():
                lines.append(str(func))
                lines.append("")

        return "\n".join(lines)


# ============================================================================
# Builder Helper
# ============================================================================

class MIRBuilder:
    """
    Helper class for building MIR code.

    Provides convenient methods for creating instructions and managing
    the current insertion point.
    """

    def __init__(self, function: MIRFunction):
        self.function = function
        self.current_block: Optional[MIRBasicBlock] = None

    def set_insert_point(self, block: MIRBasicBlock) -> None:
        """Set the current block for inserting instructions."""
        self.current_block = block

    def create_block(self, name: Optional[str] = None) -> MIRBasicBlock:
        """Create a new block and set it as insertion point."""
        block = self.function.create_block(name)
        self.current_block = block
        return block

    def _emit(self, inst: MIRInstruction) -> Optional[MIRValue]:
        """Emit an instruction at the current insertion point."""
        if self.current_block is None:
            raise RuntimeError("No insertion point set")
        self.current_block.add_instruction(inst)
        return inst.dest

    # Arithmetic operations
    def add(self, lhs: MIRValue, rhs: MIRValue) -> MIRValue:
        dest = self.function.new_value(lhs.ty)
        return self._emit(MIRInstruction(MIROp.ADD, dest, [lhs, rhs]))

    def sub(self, lhs: MIRValue, rhs: MIRValue) -> MIRValue:
        dest = self.function.new_value(lhs.ty)
        return self._emit(MIRInstruction(MIROp.SUB, dest, [lhs, rhs]))

    def mul(self, lhs: MIRValue, rhs: MIRValue) -> MIRValue:
        dest = self.function.new_value(lhs.ty)
        return self._emit(MIRInstruction(MIROp.MUL, dest, [lhs, rhs]))

    def div(self, lhs: MIRValue, rhs: MIRValue) -> MIRValue:
        dest = self.function.new_value(lhs.ty)
        return self._emit(MIRInstruction(MIROp.DIV, dest, [lhs, rhs]))

    def mod(self, lhs: MIRValue, rhs: MIRValue) -> MIRValue:
        dest = self.function.new_value(lhs.ty)
        return self._emit(MIRInstruction(MIROp.MOD, dest, [lhs, rhs]))

    def neg(self, val: MIRValue) -> MIRValue:
        dest = self.function.new_value(val.ty)
        return self._emit(MIRInstruction(MIROp.NEG, dest, [val]))

    # Bitwise operations
    def and_(self, lhs: MIRValue, rhs: MIRValue) -> MIRValue:
        dest = self.function.new_value(lhs.ty)
        return self._emit(MIRInstruction(MIROp.AND, dest, [lhs, rhs]))

    def or_(self, lhs: MIRValue, rhs: MIRValue) -> MIRValue:
        dest = self.function.new_value(lhs.ty)
        return self._emit(MIRInstruction(MIROp.OR, dest, [lhs, rhs]))

    def xor(self, lhs: MIRValue, rhs: MIRValue) -> MIRValue:
        dest = self.function.new_value(lhs.ty)
        return self._emit(MIRInstruction(MIROp.XOR, dest, [lhs, rhs]))

    def not_(self, val: MIRValue) -> MIRValue:
        dest = self.function.new_value(val.ty)
        return self._emit(MIRInstruction(MIROp.NOT, dest, [val]))

    def shl(self, val: MIRValue, amount: MIRValue) -> MIRValue:
        dest = self.function.new_value(val.ty)
        return self._emit(MIRInstruction(MIROp.SHL, dest, [val, amount]))

    def shr(self, val: MIRValue, amount: MIRValue) -> MIRValue:
        dest = self.function.new_value(val.ty)
        return self._emit(MIRInstruction(MIROp.SHR, dest, [val, amount]))

    # Comparisons
    def cmp_eq(self, lhs: MIRValue, rhs: MIRValue) -> MIRValue:
        dest = self.function.new_value(MIRType.BOOL)
        return self._emit(MIRInstruction(MIROp.EQ, dest, [lhs, rhs]))

    def cmp_ne(self, lhs: MIRValue, rhs: MIRValue) -> MIRValue:
        dest = self.function.new_value(MIRType.BOOL)
        return self._emit(MIRInstruction(MIROp.NE, dest, [lhs, rhs]))

    def cmp_lt(self, lhs: MIRValue, rhs: MIRValue) -> MIRValue:
        dest = self.function.new_value(MIRType.BOOL)
        return self._emit(MIRInstruction(MIROp.LT, dest, [lhs, rhs]))

    def cmp_le(self, lhs: MIRValue, rhs: MIRValue) -> MIRValue:
        dest = self.function.new_value(MIRType.BOOL)
        return self._emit(MIRInstruction(MIROp.LE, dest, [lhs, rhs]))

    def cmp_gt(self, lhs: MIRValue, rhs: MIRValue) -> MIRValue:
        dest = self.function.new_value(MIRType.BOOL)
        return self._emit(MIRInstruction(MIROp.GT, dest, [lhs, rhs]))

    def cmp_ge(self, lhs: MIRValue, rhs: MIRValue) -> MIRValue:
        dest = self.function.new_value(MIRType.BOOL)
        return self._emit(MIRInstruction(MIROp.GE, dest, [lhs, rhs]))

    # Memory operations
    def alloca(self, ty: MIRAnyType, name: Optional[str] = None) -> MIRValue:
        prefix = name if name else "alloc"
        dest = self.function.new_value(PointerMIRType(ty), prefix)
        return self._emit(MIRInstruction(MIROp.ALLOCA, dest, [], ty))

    def load(self, ptr: MIRValue) -> MIRValue:
        # Get pointee type
        if isinstance(ptr.ty, PointerMIRType):
            result_ty = ptr.ty.pointee
        else:
            result_ty = MIRType.I32  # Default
        dest = self.function.new_value(result_ty)
        return self._emit(MIRInstruction(MIROp.LOAD, dest, [ptr]))

    def store(self, value: MIRValue, ptr: MIRValue) -> None:
        self._emit(MIRInstruction(MIROp.STORE, None, [value, ptr]))

    def gep(self, ptr: MIRValue, indices: List[MIRValue]) -> MIRValue:
        """Get element pointer (for array/struct access)."""
        # For simplicity, assume same pointer type as input
        dest = self.function.new_value(ptr.ty)
        return self._emit(MIRInstruction(MIROp.GEP, dest, [ptr] + indices))

    # Control flow
    def br(self, target: MIRBasicBlock) -> None:
        inst = MIRInstruction(MIROp.BR)
        inst.true_block = target
        self._emit(inst)
        # Update CFG
        self.current_block.add_successor(target)
        target.add_predecessor(self.current_block)

    def cond_br(self, cond: MIRValue, true_block: MIRBasicBlock, false_block: MIRBasicBlock) -> None:
        inst = MIRInstruction(MIROp.CONDBR, None, [cond])
        inst.true_block = true_block
        inst.false_block = false_block
        self._emit(inst)
        # Update CFG
        self.current_block.add_successor(true_block)
        self.current_block.add_successor(false_block)
        true_block.add_predecessor(self.current_block)
        false_block.add_predecessor(self.current_block)

    def ret(self, value: Optional[MIRValue] = None) -> None:
        if value:
            self._emit(MIRInstruction(MIROp.RET, None, [value]))
        else:
            self._emit(MIRInstruction(MIROp.RET))

    def call(self, callee: str, args: List[MIRValue], return_ty: MIRAnyType = MIRType.VOID) -> Optional[MIRValue]:
        if return_ty != MIRType.VOID:
            dest = self.function.new_value(return_ty)
        else:
            dest = None
        inst = MIRInstruction(MIROp.CALL, dest)
        inst.callee = callee
        inst.args = args
        self._emit(inst)
        return dest

    # SSA operations
    def phi(self, ty: MIRAnyType, incoming: List[tuple]) -> MIRValue:
        """Create a phi node. incoming is list of (value, block) pairs."""
        dest = self.function.new_value(ty)
        inst = MIRInstruction(MIROp.PHI, dest)
        inst.phi_incoming = incoming
        return self._emit(inst)

    # Type conversions
    def cast(self, value: MIRValue, target_ty: MIRAnyType) -> MIRValue:
        dest = self.function.new_value(target_ty)
        return self._emit(MIRInstruction(MIROp.CAST, dest, [value], target_ty))

    def zext(self, value: MIRValue, target_ty: MIRAnyType) -> MIRValue:
        dest = self.function.new_value(target_ty)
        return self._emit(MIRInstruction(MIROp.ZEXT, dest, [value], target_ty))

    def sext(self, value: MIRValue, target_ty: MIRAnyType) -> MIRValue:
        dest = self.function.new_value(target_ty)
        return self._emit(MIRInstruction(MIROp.SEXT, dest, [value], target_ty))

    def trunc(self, value: MIRValue, target_ty: MIRAnyType) -> MIRValue:
        dest = self.function.new_value(target_ty)
        return self._emit(MIRInstruction(MIROp.TRUNC, dest, [value], target_ty))

    # Constants
    def const_int(self, value: int, ty: MIRType = MIRType.I32) -> MIRConstant:
        return MIRConstant(f"#{value}", ty, value)

    def const_bool(self, value: bool) -> MIRConstant:
        return MIRConstant(f"#{value}", MIRType.BOOL, value)


# ============================================================================
# Example/Test
# ============================================================================

if __name__ == "__main__":
    # Example: Build a simple function
    #
    # fn add(a: i32, b: i32) -> i32 {
    #   entry:
    #     %0 = add %a, %b
    #     ret %0
    # }

    # Create module and function
    module = MIRModule("test")

    func = MIRFunction("add")
    func.params = [
        MIRParam("%a", MIRType.I32, 0),
        MIRParam("%b", MIRType.I32, 1),
    ]
    func.return_type = MIRType.I32
    module.add_function(func)

    # Build function body
    builder = MIRBuilder(func)
    entry = builder.create_block("entry")

    result = builder.add(func.params[0], func.params[1])
    builder.ret(result)

    # Print MIR
    print(module)
