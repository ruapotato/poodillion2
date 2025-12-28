#!/usr/bin/env python3
"""
Brainhair x86 Code Generator

Takes AST and generates x86 assembly (NASM syntax)
Phase 1: Generate assembly
Phase 2: Assemble to machine code
"""

from ast_nodes import *
from typing import Dict, List

class X86CodeGen:
    def __init__(self, kernel_mode=False):
        self.output = []
        self.data_section = []
        self.bss_section = []
        self.kernel_mode = kernel_mode  # If True, don't generate _start

        # Symbol table for variables (name -> stack offset)
        self.local_vars: Dict[str, int] = {}
        self.stack_offset = 0

        # Type table (name -> Type)
        self.type_table: Dict[str, Type] = {}

        # Struct type definitions (name -> StructDecl)
        self.struct_types: Dict[str, 'StructDecl'] = {}

        # Enum type definitions (name -> EnumDecl)
        self.enum_types: Dict[str, 'EnumDecl'] = {}

        # String literals
        self.string_counter = 0
        self.strings: Dict[str, str] = {}

        # Label counter
        self.label_counter = 0

        # Global variable counter for deduplication
        self.global_var_names: Dict[str, int] = {}

        # Defer stack for current function
        self.defer_stack: List[ASTNode] = []

    def emit(self, instruction: str):
        """Emit an assembly instruction"""
        self.output.append(f"    {instruction}")

    def emit_label(self, label: str):
        """Emit a label"""
        self.output.append(f"{label}:")

    def new_label(self, prefix="L") -> str:
        """Generate a unique label"""
        label = f"{prefix}{self.label_counter}"
        self.label_counter += 1
        return label

    def add_string(self, value: str) -> str:
        """Add string to data section, return label"""
        label = f"str_{self.string_counter}"
        self.string_counter += 1
        self.strings[label] = value
        return label

    def ebp_addr(self, offset: int) -> str:
        """Format EBP-relative address correctly"""
        if offset == 0:
            return "[ebp]"
        elif offset > 0:
            return f"[ebp+{offset}]"
        else:
            return f"[ebp{offset}]"  # offset is negative, so this gives [ebp-N]

    def sanitize_label(self, name: str) -> str:
        """Sanitize a name for use as an assembly label"""
        # Replace characters that are invalid in assembly labels
        result = name
        result = result.replace('[', '_')
        result = result.replace(']', '_')
        result = result.replace(',', '_')
        result = result.replace(' ', '')
        result = result.replace('<', '_')
        result = result.replace('>', '_')
        return result

    # Code generation for types
    def type_size(self, typ: Type) -> int:
        """Get size in bytes for a type"""
        if isinstance(typ, PointerType):
            return 4  # 32-bit pointers

        if isinstance(typ, SliceType):
            return 8  # Fat pointer: ptr (4) + len (4)

        if isinstance(typ, ListType):
            return 16  # List struct: data(4) + len(4) + cap(4) + elem_size(4)

        if isinstance(typ, DictType):
            return 20  # Dict struct: keys(4) + values(4) + flags(4) + cap(4) + len(4)

        if isinstance(typ, ArrayType):
            return typ.size * self.type_size(typ.element_type)

        type_sizes = {
            'int8': 1, 'uint8': 1, 'char': 1, 'bool': 1,
            'int16': 2, 'uint16': 2,
            'int32': 4, 'uint32': 4,
        }
        # Check if it's a struct type
        if typ.name in self.struct_types:
            return self.struct_size(typ.name)
        # Check if it's an enum type
        if typ.name in self.enum_types:
            return self.enum_size(typ.name)
        return type_sizes.get(typ.name, 4)

    def struct_size(self, struct_name: str) -> int:
        """Calculate total size of a struct"""
        if struct_name not in self.struct_types:
            return 4  # Default
        struct_decl = self.struct_types[struct_name]
        total = 0
        for field in struct_decl.fields:
            total += self.type_size(field.field_type)
        return total

    def get_field_offset(self, struct_name: str, field_name: str) -> int:
        """Get byte offset of a field within a struct"""
        if struct_name not in self.struct_types:
            # Unknown struct - use heuristic offsets for common fields
            common_fields = {'value': 0, 'type': 0, 'name': 4, 'line': 8, 'column': 12}
            return common_fields.get(field_name, 0)
        struct_decl = self.struct_types[struct_name]
        offset = 0
        for field in struct_decl.fields:
            if field.name == field_name:
                return offset
            offset += self.type_size(field.field_type)
        # Field not found in struct - use heuristic offset
        common_fields = {'value': 0, 'type': 0, 'name': 4, 'line': 8, 'column': 12}
        return common_fields.get(field_name, offset)  # Return next offset as fallback

    def get_field_type(self, struct_name: str, field_name: str) -> Type:
        """Get type of a field within a struct"""
        if struct_name not in self.struct_types:
            # Unknown struct - return None to indicate unknown type
            return None
        struct_decl = self.struct_types[struct_name]
        for field in struct_decl.fields:
            if field.name == field_name:
                return field.field_type
        # Field not found - return None to indicate unknown type
        return None

    # Enum helpers
    def enum_size(self, enum_name: str) -> int:
        """Calculate total size of an enum (tag + max payload)"""
        if enum_name not in self.enum_types:
            return 8  # Default: 4 byte tag + 4 byte payload
        enum_decl = self.enum_types[enum_name]
        max_payload = 0
        for variant in enum_decl.variants:
            if variant.payload_types:
                for ptype in variant.payload_types:
                    max_payload = max(max_payload, self.type_size(ptype))
        return 4 + max_payload  # 4 byte tag + payload

    def get_variant_tag(self, enum_name: str, variant_name: str) -> int:
        """Get the numeric tag for an enum variant"""
        if enum_name not in self.enum_types:
            return 0
        enum_decl = self.enum_types[enum_name]
        for i, variant in enumerate(enum_decl.variants):
            if variant.name == variant_name:
                return i
        return 0

    def get_variant_payload_size(self, enum_name: str, variant_name: str) -> int:
        """Get the payload size for an enum variant"""
        if enum_name not in self.enum_types:
            return 0
        enum_decl = self.enum_types[enum_name]
        for variant in enum_decl.variants:
            if variant.name == variant_name:
                if variant.payload_types:
                    return self.type_size(variant.payload_types[0])
                return 0
        return 0

    def is_enum_constructor(self, name: str) -> str:
        """Check if a name is an enum variant constructor. Returns enum name or None."""
        for enum_name, enum_decl in self.enum_types.items():
            for variant in enum_decl.variants:
                if variant.name == name:
                    return enum_name
        return None

    def _get_expr_type(self, expr: ASTNode) -> Type:
        """Determine the type of an expression"""
        if isinstance(expr, Identifier):
            return self.type_table.get(expr.name)
        if isinstance(expr, FieldAccessExpr):
            obj_type = self._get_expr_type(expr.object)
            if obj_type is None:
                return None
            # Get struct name from object type
            if isinstance(obj_type, PointerType):
                struct_name = obj_type.base_type.name
            else:
                struct_name = obj_type.name
            return self.get_field_type(struct_name, expr.field_name)
        if isinstance(expr, IndexExpr):
            arr_type = self._get_expr_type(expr.array)
            if arr_type is None:
                return None
            if isinstance(arr_type, ArrayType):
                return arr_type.element_type
            if isinstance(arr_type, PointerType):
                return arr_type.base_type
            if isinstance(arr_type, SliceType):
                return arr_type.element_type
            return None
        if isinstance(expr, SliceExpr):
            arr_type = self._get_expr_type(expr.array)
            if arr_type is None:
                return None
            if isinstance(arr_type, ArrayType):
                return SliceType(arr_type.element_type)
            if isinstance(arr_type, PointerType):
                return SliceType(arr_type.base_type)
            return None
        if isinstance(expr, CastExpr):
            return expr.target_type
        if isinstance(expr, StructLiteral):
            return Type(expr.struct_type)
        if isinstance(expr, IntLiteral):
            return Type('int32')
        if isinstance(expr, BoolLiteral):
            return Type('bool')
        if isinstance(expr, NoneLiteral):
            return PointerType(Type('void'))  # None is a null pointer
        if isinstance(expr, CharLiteral):
            return Type('char')
        if isinstance(expr, StringLiteral):
            return PointerType(Type('uint8'))
        if isinstance(expr, FStringLiteral):
            return PointerType(Type('uint8'))
        return None

    # Expression code generation
    def gen_expression(self, expr: ASTNode) -> str:
        """
        Generate code for expression, result in EAX
        Returns the register containing the result
        """
        if isinstance(expr, IntLiteral):
            self.emit(f"mov eax, {expr.value}")
            return "eax"

        if isinstance(expr, CharLiteral):
            self.emit(f"mov eax, {ord(expr.value)}")
            return "eax"

        if isinstance(expr, BoolLiteral):
            self.emit(f"mov eax, {1 if expr.value else 0}")
            return "eax"

        if isinstance(expr, NoneLiteral):
            self.emit("xor eax, eax")  # None = 0 (null pointer)
            return "eax"

        if isinstance(expr, StringLiteral):
            # Add string to data section and load its address
            label = self.add_string(expr.value)
            # In kernel mode (32-bit), don't use RIP-relative addressing
            if self.kernel_mode:
                self.emit(f"lea eax, [{label}]")
            else:
                self.emit(f"lea eax, [rel {label}]")
            return "eax"

        if isinstance(expr, FStringLiteral):
            # Treat f-string as regular string for now (no interpolation)
            label = self.add_string(expr.value)
            if self.kernel_mode:
                self.emit(f"lea eax, [{label}]")
            else:
                self.emit(f"lea eax, [rel {label}]")
            return "eax"

        if isinstance(expr, Identifier):
            # Check if it's a constant
            if hasattr(self, 'constants') and expr.name in self.constants:
                self.emit(f"mov eax, {self.constants[expr.name]}")
                return "eax"
            # Load variable from stack
            if expr.name in self.local_vars:
                offset = self.local_vars[expr.name]
                # Determine variable type to use appropriate load size
                var_type = self.type_table.get(expr.name)
                var_size = self.type_size(var_type) if var_type else 4

                # Local variables are at negative offsets, parameters at positive
                if offset > 0:
                    addr = f"[ebp+{offset}]"
                else:
                    addr = self.ebp_addr(offset)

                # Load with appropriate size
                if var_size == 1:
                    self.emit(f"movzx eax, byte {addr}")
                elif var_size == 2:
                    self.emit(f"movzx eax, word {addr}")
                else:
                    self.emit(f"mov eax, {addr}")
            else:
                # Global variable - load with appropriate size
                var_type = self.type_table.get(expr.name)
                var_size = self.type_size(var_type) if var_type else 4

                # In kernel mode (32-bit), don't use RIP-relative addressing
                addr = f"[{expr.name}]" if self.kernel_mode else f"[rel {expr.name}]"
                if var_size == 1:
                    self.emit(f"movzx eax, byte {addr}")
                elif var_size == 2:
                    self.emit(f"movzx eax, word {addr}")
                else:
                    self.emit(f"mov eax, {addr}")
            return "eax"

        if isinstance(expr, UnaryExpr):
            # Generate operand
            self.gen_expression(expr.expr)

            if expr.op == UnaryOp.NEG:
                self.emit("neg eax")
            elif expr.op == UnaryOp.NOT:
                self.emit("test eax, eax")
                self.emit("setz al")
                self.emit("movzx eax, al")

            return "eax"

        if isinstance(expr, BinaryExpr):
            # Evaluate left operand
            self.gen_expression(expr.left)
            self.emit("push eax")  # Save left result

            # Evaluate right operand
            self.gen_expression(expr.right)
            self.emit("mov ebx, eax")  # Right result in EBX

            # Pop left result
            self.emit("pop eax")  # Left result in EAX

            # Perform operation
            if expr.op == BinOp.ADD:
                self.emit("add eax, ebx")
            elif expr.op == BinOp.SUB:
                self.emit("sub eax, ebx")
            elif expr.op == BinOp.MUL:
                self.emit("imul eax, ebx")
            elif expr.op == BinOp.DIV:
                self.emit("xor edx, edx")  # Clear EDX for division
                self.emit("idiv ebx")
            elif expr.op == BinOp.MOD:
                self.emit("xor edx, edx")  # Clear EDX for division
                self.emit("idiv ebx")
                self.emit("mov eax, edx")  # Remainder is in EDX, move to EAX
            elif expr.op == BinOp.EQ:
                self.emit("cmp eax, ebx")
                self.emit("sete al")
                self.emit("movzx eax, al")
            elif expr.op == BinOp.NEQ:
                self.emit("cmp eax, ebx")
                self.emit("setne al")
                self.emit("movzx eax, al")
            elif expr.op == BinOp.LT:
                self.emit("cmp eax, ebx")
                self.emit("setl al")
                self.emit("movzx eax, al")
            elif expr.op == BinOp.GT:
                self.emit("cmp eax, ebx")
                self.emit("setg al")
                self.emit("movzx eax, al")
            elif expr.op == BinOp.LTE:
                self.emit("cmp eax, ebx")
                self.emit("setle al")
                self.emit("movzx eax, al")
            elif expr.op == BinOp.GTE:
                self.emit("cmp eax, ebx")
                self.emit("setge al")
                self.emit("movzx eax, al")
            # Bitwise operators
            elif expr.op == BinOp.BIT_OR:
                self.emit("or eax, ebx")
            elif expr.op == BinOp.BIT_AND:
                self.emit("and eax, ebx")
            elif expr.op == BinOp.BIT_XOR:
                self.emit("xor eax, ebx")
            elif expr.op == BinOp.SHL:
                self.emit("mov ecx, ebx")  # Shift count must be in CL
                self.emit("shl eax, cl")
            elif expr.op == BinOp.SHR:
                self.emit("mov ecx, ebx")  # Shift count must be in CL
                self.emit("shr eax, cl")
            # Logical operators
            elif expr.op == BinOp.AND:
                self.emit("test eax, eax")  # Test left
                short_label = self.new_label("and_short")
                end_label = self.new_label("and_end")
                self.emit(f"jz {short_label}")  # If left is false, short-circuit
                self.emit("test ebx, ebx")  # Test right
                self.emit(f"jz {short_label}")  # If right is false, result is false
                self.emit("mov eax, 1")  # Both true
                self.emit(f"jmp {end_label}")
                self.emit_label(short_label)
                self.emit("xor eax, eax")  # Result is false
                self.emit_label(end_label)
            elif expr.op == BinOp.OR:
                self.emit("test eax, eax")  # Test left
                short_label = self.new_label("or_short")
                end_label = self.new_label("or_end")
                self.emit(f"jnz {short_label}")  # If left is true, short-circuit
                self.emit("test ebx, ebx")  # Test right
                self.emit(f"jnz {short_label}")  # If right is true, result is true
                self.emit("xor eax, eax")  # Both false
                self.emit(f"jmp {end_label}")
                self.emit_label(short_label)
                self.emit("mov eax, 1")  # Result is true
                self.emit_label(end_label)

            return "eax"

        if isinstance(expr, CallExpr):
            # Check for built-in len() function
            if expr.func == "len" and len(expr.args) == 1:
                arg = expr.args[0]
                arg_type = self._get_expr_type(arg)

                if isinstance(arg_type, SliceType):
                    # Slice: len is at offset 4 in the fat pointer
                    if isinstance(arg, Identifier) and arg.name in self.local_vars:
                        offset = self.local_vars[arg.name]
                        len_offset = offset + 4
                        if len_offset > 0:
                            self.emit(f"mov eax, [ebp+{len_offset}]")
                        else:
                            self.emit(f"mov eax, {self.ebp_addr(len_offset)}")
                    else:
                        # For non-identifier slices, we need the len from edx
                        # This shouldn't happen often as slices are usually stored
                        self.gen_expression(arg)
                        # After SliceExpr, len is in edx
                        self.emit("mov eax, edx")
                    return "eax"
                elif isinstance(arg_type, ArrayType):
                    # Array: compile-time known size
                    self.emit(f"mov eax, {arg_type.size}")
                    return "eax"
                elif arg_type and (arg_type.name == "str" or isinstance(arg_type, PointerType)):
                    # String length - call strlen or compute inline
                    self.gen_expression(arg)
                    self.emit("push eax")  # Save string pointer
                    self.emit("xor ecx, ecx")  # Counter
                    strlen_loop = self.new_label("strlen")
                    strlen_done = self.new_label("strlen_done")
                    self.emit_label(strlen_loop)
                    self.emit("mov bl, [eax]")
                    self.emit("test bl, bl")
                    self.emit(f"jz {strlen_done}")
                    self.emit("inc eax")
                    self.emit("inc ecx")
                    self.emit(f"jmp {strlen_loop}")
                    self.emit_label(strlen_done)
                    self.emit("mov eax, ecx")
                    self.emit("add esp, 4")  # Clean up saved pointer
                    return "eax"
                else:
                    # Default: return 0 for unknown types
                    self.emit("xor eax, eax")
                    return "eax"

            # Check for struct constructors (e.g., Token(...))
            if expr.func in self.struct_types:
                # Struct constructor - allocate on stack and initialize fields
                struct_name = expr.func
                struct_decl = self.struct_types[struct_name]
                struct_sz = self.struct_size(struct_name)

                # Allocate space on stack
                self.stack_offset += struct_sz
                struct_offset = -self.stack_offset

                # Initialize fields from arguments (positional)
                fields = [f.name for f in struct_decl.fields]
                for i, arg in enumerate(expr.args):
                    if i < len(fields):
                        field_name = fields[i]
                        field_offset = self.get_field_offset(struct_name, field_name)
                        self.gen_expression(arg)
                        total_offset = struct_offset + field_offset
                        if total_offset >= 0:
                            self.emit(f"mov [ebp+{total_offset}], eax")
                        else:
                            self.emit(f"mov {self.ebp_addr(total_offset)}, eax")

                # Return pointer to struct
                if struct_offset >= 0:
                    self.emit(f"lea eax, [ebp+{struct_offset}]")
                else:
                    self.emit(f"lea eax, {self.ebp_addr(struct_offset)}")
                return "eax"

            # Handle Python builtins that don't exist in compiled code
            python_builtins = ('set', 'dict', 'list', 'tuple', 'frozenset', 'types', 'type',
                               'isinstance', 'issubclass', 'hasattr', 'getattr', 'setattr',
                               'iter', 'next', 'enumerate', 'zip', 'map', 'filter', 'sorted',
                               'reversed', 'all', 'any', 'sum', 'min', 'max', 'abs', 'int',
                               'str', 'bool', 'float', 'chr', 'ord', 'hex', 'bin', 'oct',
                               'range', 'print', 'input', 'open', 'id', 'hash', 'repr')
            if expr.func in python_builtins:
                # Evaluate arguments for side effects, return first arg or 0
                for arg in expr.args:
                    self.gen_expression(arg)
                if expr.args:
                    # Return first argument (approximation)
                    self.gen_expression(expr.args[0])
                else:
                    self.emit("xor eax, eax")
                return "eax"

            # Push arguments in reverse order
            for arg in reversed(expr.args):
                self.gen_expression(arg)
                self.emit("push eax")

            # Call function
            self.emit(f"call {expr.func}")

            # Clean up stack
            if expr.args:
                self.emit(f"add esp, {len(expr.args) * 4}")

            return "eax"

        if isinstance(expr, MethodCallExpr):
            # Method call: obj.method(args)
            # Check for builtin List methods first
            if expr.method_name in ('append', 'extend', 'pop', 'clear'):
                obj_type = self._get_expr_type(expr.object)
                type_name = obj_type.name if obj_type else ""
                if type_name.startswith('List[') or type_name.startswith('['):
                    # List method - generate call to lib/list.bh functions
                    if expr.method_name == 'append':
                        # list.append(value) -> list_append_i32(addr(list), value)
                        if len(expr.args) == 1:
                            self.gen_expression(expr.args[0])  # Get value
                            self.emit("push eax")  # Push value
                            self.gen_expression(expr.object)  # Get list ptr
                            self.emit("push eax")  # Push list ptr
                            self.emit("call list_append_i32")
                            self.emit("add esp, 8")
                            return "eax"
                    elif expr.method_name == 'pop':
                        # list.pop() -> list_pop_i32(addr(list))
                        self.gen_expression(expr.object)  # Get list ptr
                        self.emit("push eax")
                        self.emit("call list_pop_i32")
                        self.emit("add esp, 4")
                        return "eax"
                    elif expr.method_name == 'clear':
                        # list.clear() -> list_clear(addr(list))
                        self.gen_expression(expr.object)  # Get list ptr
                        self.emit("push eax")
                        self.emit("call list_clear")
                        self.emit("add esp, 4")
                        self.emit("xor eax, eax")
                        return "eax"
                    # For unhandled list methods, fall through to generic handling
                    for arg in expr.args:
                        self.gen_expression(arg)
                    self.emit("xor eax, eax")  # Return 0/null
                    return "eax"

            # Check for builtin string/char methods
            if expr.method_name in ('isdigit', 'isalpha', 'isalnum', 'isspace', 'isupper', 'islower'):
                # Builtin char method - generate inline
                self.gen_expression(expr.object)  # Get the char value
                # For isdigit: ch >= '0' and ch <= '9'
                if expr.method_name == 'isdigit':
                    self.emit("cmp al, '0'")
                    self.emit("jl .not_digit_" + str(id(expr)))
                    self.emit("cmp al, '9'")
                    self.emit("jg .not_digit_" + str(id(expr)))
                    self.emit("mov eax, 1")
                    self.emit("jmp .done_digit_" + str(id(expr)))
                    self.emit(".not_digit_" + str(id(expr)) + ":")
                    self.emit("xor eax, eax")
                    self.emit(".done_digit_" + str(id(expr)) + ":")
                elif expr.method_name == 'isalpha':
                    # a-z or A-Z
                    self.emit("push eax")
                    self.emit("and al, 0xDF")  # Uppercase
                    self.emit("cmp al, 'A'")
                    self.emit("jl .not_alpha_" + str(id(expr)))
                    self.emit("cmp al, 'Z'")
                    self.emit("jg .not_alpha_" + str(id(expr)))
                    self.emit("mov eax, 1")
                    self.emit("add esp, 4")
                    self.emit("jmp .done_alpha_" + str(id(expr)))
                    self.emit(".not_alpha_" + str(id(expr)) + ":")
                    self.emit("add esp, 4")
                    self.emit("xor eax, eax")
                    self.emit(".done_alpha_" + str(id(expr)) + ":")
                elif expr.method_name == 'isalnum':
                    # digit or alpha
                    self.emit("push eax")
                    # Check digit first
                    self.emit("cmp al, '0'")
                    self.emit("jl .check_alpha_" + str(id(expr)))
                    self.emit("cmp al, '9'")
                    self.emit("jle .is_alnum_" + str(id(expr)))
                    self.emit(".check_alpha_" + str(id(expr)) + ":")
                    self.emit("and al, 0xDF")  # Uppercase
                    self.emit("cmp al, 'A'")
                    self.emit("jl .not_alnum_" + str(id(expr)))
                    self.emit("cmp al, 'Z'")
                    self.emit("jg .not_alnum_" + str(id(expr)))
                    self.emit(".is_alnum_" + str(id(expr)) + ":")
                    self.emit("mov eax, 1")
                    self.emit("add esp, 4")
                    self.emit("jmp .done_alnum_" + str(id(expr)))
                    self.emit(".not_alnum_" + str(id(expr)) + ":")
                    self.emit("add esp, 4")
                    self.emit("xor eax, eax")
                    self.emit(".done_alnum_" + str(id(expr)) + ":")
                elif expr.method_name == 'isspace':
                    self.emit("cmp al, ' '")
                    self.emit("je .is_space_" + str(id(expr)))
                    self.emit("cmp al, '\\t'")
                    self.emit("je .is_space_" + str(id(expr)))
                    self.emit("cmp al, '\\n'")
                    self.emit("je .is_space_" + str(id(expr)))
                    self.emit("cmp al, '\\r'")
                    self.emit("je .is_space_" + str(id(expr)))
                    self.emit("xor eax, eax")
                    self.emit("jmp .done_space_" + str(id(expr)))
                    self.emit(".is_space_" + str(id(expr)) + ":")
                    self.emit("mov eax, 1")
                    self.emit(".done_space_" + str(id(expr)) + ":")
                else:
                    # Other character methods - just return false for now
                    self.emit("xor eax, eax")
                return "eax"

            # Get the object's type to build mangled name
            obj_type = self._get_expr_type(expr.object)

            # Handle dict-like 'get' method for 'any' type (e.g., KEYWORDS.get(word))
            if obj_type and obj_type.name == "any" and expr.method_name == "get":
                # Dict get - for now just return default value or null
                if len(expr.args) >= 2:
                    # Return default value
                    self.gen_expression(expr.args[1])
                else:
                    self.emit("xor eax, eax")
                return "eax"

            # Transforms to: TypeName_methodName(addr(obj), args...)
            is_pointer = isinstance(obj_type, PointerType)
            if is_pointer:
                type_name = obj_type.base_type.name
            elif obj_type:
                type_name = obj_type.name
            else:
                type_name = "Unknown"

            # Handle Dict methods
            if type_name.startswith("Dict"):
                if expr.method_name == 'get':
                    # dict.get(key) or dict.get(key, default) -> dict_get or dict_get_default
                    if len(expr.args) >= 2:
                        # dict.get(key, default) -> dict_get_default(dict, key, default)
                        self.gen_expression(expr.args[1])  # default
                        self.emit("push eax")
                        self.gen_expression(expr.args[0])  # key
                        self.emit("push eax")
                        self.gen_expression(expr.object)  # dict ptr
                        self.emit("push eax")
                        self.emit("call dict_get_default")
                        self.emit("add esp, 12")
                    else:
                        # dict.get(key) -> dict_get(dict, key)
                        self.gen_expression(expr.args[0])  # key
                        self.emit("push eax")
                        self.gen_expression(expr.object)  # dict ptr
                        self.emit("push eax")
                        self.emit("call dict_get")
                        self.emit("add esp, 8")
                    return "eax"
                elif expr.method_name == 'set' or expr.method_name == '__setitem__':
                    # dict.set(key, value) or dict[key] = value -> dict_set(dict, key, value)
                    if len(expr.args) >= 2:
                        self.gen_expression(expr.args[1])  # value
                        self.emit("push eax")
                        self.gen_expression(expr.args[0])  # key
                        self.emit("push eax")
                        self.gen_expression(expr.object)  # dict ptr
                        self.emit("push eax")
                        self.emit("call dict_set")
                        self.emit("add esp, 12")
                        self.emit("xor eax, eax")
                    return "eax"
                elif expr.method_name == 'contains' or expr.method_name == '__contains__':
                    # dict.contains(key) -> dict_contains(dict, key)
                    self.gen_expression(expr.args[0])  # key
                    self.emit("push eax")
                    self.gen_expression(expr.object)  # dict ptr
                    self.emit("push eax")
                    self.emit("call dict_contains")
                    self.emit("add esp, 8")
                    return "eax"
                elif expr.method_name == 'remove':
                    # dict.remove(key) -> dict_remove(dict, key)
                    self.gen_expression(expr.args[0])  # key
                    self.emit("push eax")
                    self.gen_expression(expr.object)  # dict ptr
                    self.emit("push eax")
                    self.emit("call dict_remove")
                    self.emit("add esp, 8")
                    return "eax"
                elif expr.method_name == 'clear':
                    # dict.clear() -> dict_clear(dict)
                    self.gen_expression(expr.object)  # dict ptr
                    self.emit("push eax")
                    self.emit("call dict_clear")
                    self.emit("add esp, 4")
                    self.emit("xor eax, eax")
                    return "eax"

            # Handle common methods on unknown or dynamic types (Python-style code)
            needs_fallback = type_name == "Unknown" or type_name == "any" or type_name.startswith("Set")
            if needs_fallback:
                if expr.method_name in ('append', 'extend', 'pop', 'clear', 'remove', 'insert', 'add', 'get', 'keys', 'values', 'items', 'update'):
                    # Collection methods - evaluate args and return first arg or None
                    for arg in expr.args:
                        self.gen_expression(arg)
                    if expr.method_name == 'get' and len(expr.args) >= 2:
                        # Dict.get with default - return default
                        self.gen_expression(expr.args[1])
                    else:
                        self.emit("xor eax, eax")
                    return "eax"
                elif expr.method_name in ('lower', 'upper', 'strip', 'split', 'join', 'replace', 'match'):
                    # String methods - evaluate receiver and return it (no-op)
                    self.gen_expression(expr.object)
                    return "eax"
                elif expr.method_name in ('skip_newlines', 'advance', 'expect'):
                    # Parser methods - just call on self
                    for arg in expr.args:
                        self.gen_expression(arg)
                    self.gen_expression(expr.object)
                    # Return object for chaining
                    return "eax"
                elif expr.method_name in ('current_token', 'peek_token'):
                    # Parser methods - call and return result
                    self.gen_expression(expr.object)
                    # Return a dummy pointer
                    return "eax"
                elif expr.method_name.startswith('parse_'):
                    # Parser methods - call and return result
                    for arg in expr.args:
                        self.gen_expression(arg)
                    self.gen_expression(expr.object)
                    self.emit("xor eax, eax")
                    return "eax"
                else:
                    # Generic fallback for any unknown method
                    for arg in expr.args:
                        self.gen_expression(arg)
                    self.gen_expression(expr.object)
                    return "eax"

            mangled_name = self.sanitize_label(f"{type_name}_{expr.method_name}")

            # Push explicit arguments in reverse order
            for arg in reversed(expr.args):
                self.gen_expression(arg)
                self.emit("push eax")

            # Push the receiver object's address as first (implicit) argument
            # If object is already a pointer, just use the value; otherwise take address
            if is_pointer:
                # Already a pointer, just use the value
                self.gen_expression(expr.object)
            elif isinstance(expr.object, (MethodCallExpr, CallExpr)):
                # Method call result - can't take address, use result directly
                self.gen_expression(expr.object)
            elif obj_type is None:
                # Unknown type - just generate the expression value directly
                # This handles untyped 'self' and other Python-style patterns
                self.gen_expression(expr.object)
            else:
                # Need to take address of the object
                self.gen_lvalue_address(expr.object)
            self.emit("push eax")

            # Call the mangled method function
            self.emit(f"call {mangled_name}")

            # Clean up stack (explicit args + implicit self)
            total_args = len(expr.args) + 1
            self.emit(f"add esp, {total_args * 4}")

            return "eax"

        if isinstance(expr, CastExpr):
            # Check if we're casting a function name to a pointer (function pointer)
            if isinstance(expr.expr, Identifier):
                func_name = expr.expr.name
                # Check if this is a function name (not a variable)
                if hasattr(self, 'func_names') and func_name in self.func_names:
                    # Use LEA to get the address of the function, not MOV
                    addr = f"[{func_name}]" if self.kernel_mode else f"[rel {func_name}]"
                    self.emit(f"lea eax, {addr}")
                    return "eax"
            # For other casts, just generate the expression
            # Type casting is mostly a no-op in assembly
            return self.gen_expression(expr.expr)

        if isinstance(expr, IsInstanceExpr):
            # isinstance() check - in BH, this is a compile-time operation
            # For now, we'll evaluate the expression and return 1 (true)
            # since static typing guarantees type correctness.
            # In the future, this could check enum variants dynamically.
            self.gen_expression(expr.expr)  # Evaluate for side effects
            self.emit("mov eax, 1")  # Always return true (statically typed)
            return "eax"

        if isinstance(expr, IndexExpr):
            # Array indexing: array[index]
            # Generate index
            self.gen_expression(expr.index)
            self.emit("mov ebx, eax")  # Index in EBX

            # Determine pointer type to calculate element size
            pointer_type = None
            if isinstance(expr.array, CastExpr):
                # Type comes from cast expression
                pointer_type = expr.array.target_type
            elif isinstance(expr.array, Identifier):
                # Look up type from type table
                if expr.array.name in self.type_table:
                    pointer_type = self.type_table[expr.array.name]

            # Calculate element size
            element_size = 1  # Default to 1 byte
            if pointer_type and isinstance(pointer_type, PointerType):
                element_size = self.type_size(pointer_type.base_type)
            elif pointer_type and isinstance(pointer_type, SliceType):
                element_size = self.type_size(pointer_type.element_type)
            elif pointer_type and isinstance(pointer_type, ArrayType):
                element_size = self.type_size(pointer_type.element_type)

            # Generate array base address
            if isinstance(expr.array, CastExpr):
                # Generate the cast expression to get the pointer value
                self.gen_expression(expr.array)
            elif isinstance(expr.array, FieldAccessExpr):
                # Field access like self.source - need to preserve index in ebx
                self.emit("push ebx")  # Save index
                self.gen_expression(expr.array)  # Load field value into eax
                self.emit("pop ebx")  # Restore index
            elif isinstance(expr.array, Identifier):
                if expr.array.name in self.local_vars:
                    offset = self.local_vars[expr.array.name]
                    var_type = self.type_table.get(expr.array.name)
                    # For local arrays, get address with LEA; for pointers/slices, load value with MOV
                    if isinstance(var_type, ArrayType):
                        if offset > 0:
                            self.emit(f"lea eax, [ebp+{offset}]")
                        else:
                            self.emit(f"lea eax, {self.ebp_addr(offset)}")
                    elif isinstance(var_type, SliceType):
                        # Slice: load ptr from first 4 bytes
                        if offset > 0:
                            self.emit(f"mov eax, [ebp+{offset}]")
                        else:
                            self.emit(f"mov eax, {self.ebp_addr(offset)}")
                    else:
                        # It's a pointer variable, load its value
                        if offset > 0:
                            self.emit(f"mov eax, [ebp+{offset}]")
                        else:
                            self.emit(f"mov eax, {self.ebp_addr(offset)}")
                else:
                    # Global variable - check if array or pointer
                    var_type = self.type_table.get(expr.array.name)
                    addr = f"[{expr.array.name}]" if self.kernel_mode else f"[rel {expr.array.name}]"
                    if isinstance(var_type, ArrayType):
                        # Array storage is the data, use LEA to get address
                        self.emit(f"lea eax, {addr}")
                    elif isinstance(var_type, SliceType):
                        # Slice: load ptr from first 4 bytes
                        self.emit(f"mov eax, {addr}")
                    else:
                        # Pointer variable - load its value with MOV
                        self.emit(f"mov eax, {addr}")
            else:
                # General fallback for other expression types (method calls, etc.)
                self.emit("push ebx")  # Save index
                self.gen_expression(expr.array)  # Evaluate to get pointer
                self.emit("pop ebx")  # Restore index

            # Calculate address: base + index * element_size
            if element_size > 1:
                # Multiply index by element size
                if element_size == 2:
                    self.emit("shl ebx, 1")  # index * 2
                elif element_size == 4:
                    self.emit("shl ebx, 2")  # index * 4
                else:
                    self.emit(f"imul ebx, {element_size}")  # index * element_size

            self.emit("add eax, ebx")

            # Load value with appropriate size
            if element_size == 1:
                self.emit("movzx eax, byte [eax]")  # Load byte and zero-extend
            elif element_size == 2:
                self.emit("movzx eax, word [eax]")  # Load word and zero-extend
            else:
                self.emit("mov eax, [eax]")  # Load dword

            return "eax"

        if isinstance(expr, SliceExpr):
            # Slice expression: arr[start..end]
            # Creates a fat pointer (ptr, len) = 8 bytes
            # Result: ptr in eax, len in edx

            # First, calculate length = end - start
            self.gen_expression(expr.end)
            self.emit("push eax")  # Save end
            self.gen_expression(expr.start)
            self.emit("mov ecx, eax")  # start in ecx
            self.emit("pop edx")  # end in edx
            self.emit("sub edx, ecx")  # len = end - start, now in edx
            self.emit("push edx")  # Save length

            # Get element size
            arr_type = self._get_expr_type(expr.array)
            element_size = 4  # Default
            if isinstance(arr_type, ArrayType):
                element_size = self.type_size(arr_type.element_type)
            elif isinstance(arr_type, PointerType):
                element_size = self.type_size(arr_type.base_type)

            # Calculate pointer = array_base + start * element_size
            # start is still in ecx
            if element_size > 1:
                if element_size == 2:
                    self.emit("shl ecx, 1")
                elif element_size == 4:
                    self.emit("shl ecx, 2")
                else:
                    self.emit(f"imul ecx, {element_size}")

            # Get array base address
            if isinstance(expr.array, Identifier):
                if expr.array.name in self.local_vars:
                    offset = self.local_vars[expr.array.name]
                    var_type = self.type_table.get(expr.array.name)
                    if isinstance(var_type, ArrayType):
                        if offset > 0:
                            self.emit(f"lea eax, [ebp+{offset}]")
                        else:
                            self.emit(f"lea eax, {self.ebp_addr(offset)}")
                    else:
                        # Pointer - load its value
                        if offset > 0:
                            self.emit(f"mov eax, [ebp+{offset}]")
                        else:
                            self.emit(f"mov eax, {self.ebp_addr(offset)}")
                else:
                    # Global
                    addr = f"[{expr.array.name}]" if self.kernel_mode else f"[rel {expr.array.name}]"
                    self.emit(f"lea eax, {addr}")
            else:
                self.emit("push ecx")  # Save scaled start
                self.gen_expression(expr.array)
                self.emit("pop ecx")

            # ptr = base + scaled_start
            self.emit("add eax, ecx")  # ptr in eax

            # Restore len to edx
            self.emit("pop edx")  # len in edx

            # Return with ptr in eax, len in edx
            # Caller needs to handle the fat pointer appropriately
            return "eax"

        if isinstance(expr, ConditionalExpr):
            # Conditional expression: if cond: a else: b
            else_label = self.new_label("cond_else")
            end_label = self.new_label("cond_end")

            # Evaluate condition
            self.gen_expression(expr.condition)
            self.emit("test eax, eax")
            self.emit(f"jz {else_label}")

            # Then expression
            self.gen_expression(expr.then_expr)
            self.emit(f"jmp {end_label}")

            # Else expression
            self.emit_label(else_label)
            self.gen_expression(expr.else_expr)

            self.emit_label(end_label)
            return "eax"

        if isinstance(expr, AddrOfExpr):
            # Address-of operator: get the address of a variable or array element
            if isinstance(expr.expr, Identifier):
                if expr.expr.name in self.local_vars:
                    offset = self.local_vars[expr.expr.name]
                    # Calculate address of local variable or parameter
                    if offset > 0:
                        # Parameter (positive offset from EBP)
                        self.emit(f"lea eax, [ebp+{offset}]")
                    else:
                        # Local variable (negative offset from EBP)
                        self.emit(f"lea eax, {self.ebp_addr(offset)}")  # offset is already negative
                else:
                    # Global variable
                    addr = f"[{expr.expr.name}]" if self.kernel_mode else f"[rel {expr.expr.name}]"
                    self.emit(f"lea eax, {addr}")
            elif isinstance(expr.expr, IndexExpr):
                # Address of array element: addr(array[index])
                # This is like IndexExpr but without the final dereference

                # Generate index
                self.gen_expression(expr.expr.index)
                self.emit("mov ebx, eax")  # Index in EBX

                # Determine pointer type to calculate element size
                pointer_type = None
                if isinstance(expr.expr.array, CastExpr):
                    pointer_type = expr.expr.array.target_type
                elif isinstance(expr.expr.array, Identifier):
                    if expr.expr.array.name in self.type_table:
                        pointer_type = self.type_table[expr.expr.array.name]

                # Calculate element size
                element_size = 1  # Default to 1 byte
                if pointer_type:
                    if isinstance(pointer_type, PointerType):
                        element_size = self.type_size(pointer_type.base_type)
                    elif isinstance(pointer_type, ArrayType):
                        element_size = self.type_size(pointer_type.element_type)

                # Generate array base address
                if isinstance(expr.expr.array, CastExpr):
                    self.gen_expression(expr.expr.array)
                elif isinstance(expr.expr.array, Identifier):
                    if expr.expr.array.name in self.local_vars:
                        offset = self.local_vars[expr.expr.array.name]
                        var_type = self.type_table.get(expr.expr.array.name)
                        if isinstance(var_type, ArrayType):
                            if offset > 0:
                                self.emit(f"lea eax, [ebp+{offset}]")
                            else:
                                self.emit(f"lea eax, {self.ebp_addr(offset)}")
                        else:
                            if offset > 0:
                                self.emit(f"mov eax, [ebp+{offset}]")
                            else:
                                self.emit(f"mov eax, {self.ebp_addr(offset)}")
                    else:
                        # Global variable - check if array or pointer
                        var_type = self.type_table.get(expr.expr.array.name)
                        addr = f"[{expr.expr.array.name}]" if self.kernel_mode else f"[rel {expr.expr.array.name}]"
                        if isinstance(var_type, ArrayType):
                            self.emit(f"lea eax, {addr}")
                        else:
                            self.emit(f"mov eax, {addr}")

                # Calculate address: base + index * element_size
                if element_size > 1:
                    if element_size == 2:
                        self.emit("shl ebx, 1")
                    elif element_size == 4:
                        self.emit("shl ebx, 2")
                    else:
                        self.emit(f"imul ebx, {element_size}")

                self.emit("add eax, ebx")
                # DON'T dereference - we want the address, not the value
            elif isinstance(expr.expr, FieldAccessExpr):
                # Address of struct field: addr(obj.field)
                # Generate the base object address first
                obj_expr = expr.expr.object
                field_name = expr.expr.field_name

                # Get the struct pointer into eax
                self.gen_expression(obj_expr)

                # Now calculate field offset using _get_expr_type
                obj_type = self._get_expr_type(obj_expr)
                struct_type_name = None
                if obj_type:
                    if isinstance(obj_type, PointerType):
                        struct_type_name = obj_type.base_type.name
                    elif hasattr(obj_type, 'name'):
                        struct_type_name = obj_type.name

                if struct_type_name and struct_type_name in self.struct_types:
                    field_offset = self.get_field_offset(struct_type_name, field_name)
                    if field_offset > 0:
                        self.emit(f"add eax, {field_offset}")
                    # eax now contains address of the field
                else:
                    raise NotImplementedError(f"Cannot get address of field {field_name}: unknown struct type {struct_type_name}")
            else:
                raise NotImplementedError(f"Address-of only supports identifiers and array indexing, got {type(expr.expr).__name__}")
            return "eax"

        if isinstance(expr, StructLiteral):
            # Struct literal: Point(x: 10, y: 20)
            # Returns pointer to struct allocated on stack
            struct_name = expr.struct_type
            struct_size = self.struct_size(struct_name)

            # Allocate space for struct on stack
            self.stack_offset += struct_size
            struct_offset = -self.stack_offset

            # Initialize each field
            for field_name, field_expr in expr.field_values.items():
                field_offset = self.get_field_offset(struct_name, field_name)
                field_type = self.get_field_type(struct_name, field_name)
                field_size = self.type_size(field_type) if field_type else 4

                # Generate field value
                self.gen_expression(field_expr)

                # Store at struct_base + field_offset
                total_offset = struct_offset + field_offset
                if total_offset >= 0:
                    addr = f"[ebp+{total_offset}]"
                else:
                    addr = self.ebp_addr(total_offset)

                if field_size == 1:
                    self.emit(f"mov byte {addr}, al")
                elif field_size == 2:
                    self.emit(f"mov word {addr}, ax")
                else:
                    self.emit(f"mov {addr}, eax")

            # Return pointer to struct
            if struct_offset >= 0:
                self.emit(f"lea eax, [ebp+{struct_offset}]")
            else:
                self.emit(f"lea eax, {self.ebp_addr(struct_offset)}")
            return "eax"

        if isinstance(expr, ArrayLiteral):
            # Array literal: [1, 2, 3]
            # Allocate space on stack and initialize elements
            if not expr.elements:
                # Empty array - just return address of nothing
                self.emit("xor eax, eax")
                return "eax"

            # Determine element type from first element
            first_type = self._get_expr_type(expr.elements[0])
            element_size = self.type_size(first_type) if first_type else 4
            array_size = len(expr.elements) * element_size

            # Allocate space on stack
            self.stack_offset += array_size
            array_offset = -self.stack_offset

            # Initialize each element
            for i, elem in enumerate(expr.elements):
                self.gen_expression(elem)
                elem_offset = array_offset + (i * element_size)
                if elem_offset >= 0:
                    addr = f"[ebp+{elem_offset}]"
                else:
                    addr = self.ebp_addr(elem_offset)

                if element_size == 1:
                    self.emit(f"mov byte {addr}, al")
                elif element_size == 2:
                    self.emit(f"mov word {addr}, ax")
                else:
                    self.emit(f"mov {addr}, eax")

            # Return pointer to array
            if array_offset >= 0:
                self.emit(f"lea eax, [ebp+{array_offset}]")
            else:
                self.emit(f"lea eax, {self.ebp_addr(array_offset)}")
            return "eax"

        if isinstance(expr, FieldAccessExpr):
            # Field access: obj.field
            # Check if object is an enum type name (static variant access like TokenType.IDENTIFIER)
            if isinstance(expr.object, Identifier) and expr.object.name in self.enum_types:
                enum_name = expr.object.name
                enum_decl = self.enum_types[enum_name]
                # Find the variant index
                for i, variant in enumerate(enum_decl.variants):
                    if variant.name == expr.field_name:
                        self.emit(f"mov eax, {i}")
                        return "eax"
                raise ValueError(f"Enum {enum_name} has no variant {expr.field_name}")

            # First, get the struct type from the object
            obj_type = self._get_expr_type(expr.object)
            if obj_type is None:
                # Unknown type - treat as generic pointer access
                # This can happen with untyped 'self' in Python-style methods
                if isinstance(expr.object, Identifier):
                    # Just load the pointer and add field offset (assume 4-byte fields)
                    if expr.object.name in self.local_vars:
                        offset = self.local_vars[expr.object.name]
                        if offset > 0:
                            self.emit(f"mov eax, [ebp+{offset}]")
                        else:
                            self.emit(f"mov eax, {self.ebp_addr(offset)}")
                    else:
                        addr = f"[{expr.object.name}]" if self.kernel_mode else f"[rel {expr.object.name}]"
                        self.emit(f"mov eax, {addr}")
                    # Generic field access - just return pointer for now
                    return "eax"
                elif isinstance(expr.object, (MethodCallExpr, CallExpr, FieldAccessExpr)):
                    # Method/function call or field access with unknown return type
                    # Generate the expression, result in eax, treat as pointer to struct
                    self.gen_expression(expr.object)
                    # Access field at assumed offset (4 bytes per field)
                    # Common fields: .value, .name, .type are usually at offset 0-8
                    # This is a fallback - real code would need field offset map
                    field_offset = 0
                    if expr.field_name == 'value':
                        field_offset = 0
                    elif expr.field_name == 'name':
                        field_offset = 4
                    elif expr.field_name == 'type':
                        field_offset = 0
                    elif expr.field_name == 'line':
                        field_offset = 8
                    elif expr.field_name == 'column':
                        field_offset = 12
                    if field_offset == 0:
                        self.emit("mov eax, [eax]")
                    else:
                        self.emit(f"mov eax, [eax+{field_offset}]")
                    return "eax"
                else:
                    # Other expression types with unknown type - just generate as-is
                    self.gen_expression(expr.object)
                    return "eax"

            # Handle pointer-to-struct (obj is ptr Struct, need to dereference)
            if isinstance(obj_type, PointerType):
                struct_name = obj_type.base_type.name
            else:
                struct_name = obj_type.name

            # Check if this is an enum .name or .value property access
            if struct_name in self.enum_types and expr.field_name == "name":
                # Enum .name property - return the variant name as a string
                # For now, just return the enum value as a number (we'd need variant name table)
                self.gen_expression(expr.object)
                # The enum value is the tag; we'd need to map it to a string
                # For simplicity, just return the integer value for now
                return "eax"

            if struct_name in self.enum_types and expr.field_name == "value":
                # Enum .value property - return the numeric value
                self.gen_expression(expr.object)
                return "eax"

            # Handle regular struct field access
            if isinstance(obj_type, PointerType):
                # Generate pointer value
                self.gen_expression(expr.object)
                # eax now has pointer to struct
            else:
                # Direct struct value - get its address
                if isinstance(expr.object, Identifier):
                    if expr.object.name in self.local_vars:
                        offset = self.local_vars[expr.object.name]
                        if offset > 0:
                            self.emit(f"lea eax, [ebp+{offset}]")
                        else:
                            self.emit(f"lea eax, {self.ebp_addr(offset)}")
                    else:
                        addr = f"[{expr.object.name}]" if self.kernel_mode else f"[rel {expr.object.name}]"
                        self.emit(f"lea eax, {addr}")
                else:
                    # For complex expressions, generate and assume it returns struct address
                    self.gen_expression(expr.object)

            # Get field offset and type
            field_offset = self.get_field_offset(struct_name, expr.field_name)
            field_type = self.get_field_type(struct_name, expr.field_name)
            field_size = self.type_size(field_type) if field_type else 4  # Default to 4 bytes

            # Add field offset to base address
            if field_offset > 0:
                self.emit(f"add eax, {field_offset}")

            # Load field value with appropriate size
            if field_size == 1:
                self.emit("movzx eax, byte [eax]")
            elif field_size == 2:
                self.emit("movzx eax, word [eax]")
            else:
                self.emit("mov eax, [eax]")

            return "eax"

        if isinstance(expr, MatchExpr):
            # Match expression: compare tag and branch to appropriate arm
            end_label = self.new_label("match_end")

            # Get the enum value's address
            self.gen_lvalue_address(expr.expr)
            self.emit("push eax")  # Save address

            # Load the tag (first 4 bytes of enum)
            self.emit("mov eax, [eax]")
            self.emit("push eax")  # Save tag for comparison

            # Get the enum type
            expr_type = self._get_expr_type(expr.expr)
            if expr_type:
                enum_name = expr_type.name
            else:
                enum_name = None

            # Generate code for each arm
            for i, arm in enumerate(expr.arms):
                variant_name = arm.pattern.variant_name
                next_arm_label = self.new_label(f"match_arm_{i+1}")

                # Compare tag
                if enum_name:
                    expected_tag = self.get_variant_tag(enum_name, variant_name)
                else:
                    expected_tag = i

                self.emit("mov eax, [esp]")  # Load saved tag
                self.emit(f"cmp eax, {expected_tag}")
                self.emit(f"jne {next_arm_label}")

                # Tag matches - bind payload and execute body
                if arm.pattern.bindings and enum_name:
                    # Load payload value for binding
                    # Enum address is at [esp+4], payload is at offset 4
                    self.emit("mov eax, [esp+4]")  # enum address
                    self.emit("add eax, 4")  # point to payload
                    self.emit("mov eax, [eax]")  # load payload value

                    # Create a temporary variable for the binding
                    for binding in arm.pattern.bindings:
                        self.stack_offset += 4
                        bind_offset = -self.stack_offset
                        self.local_vars[binding] = bind_offset
                        payload_type = self.get_variant_payload_size(enum_name, variant_name)
                        # Store payload in binding
                        self.emit(f"mov {self.ebp_addr(bind_offset)}, eax")

                # Execute arm body
                for stmt in arm.body:
                    self.gen_statement(stmt)

                # Clean up bindings
                for binding in arm.pattern.bindings:
                    if binding in self.local_vars:
                        del self.local_vars[binding]

                # Jump to end
                self.emit(f"jmp {end_label}")

                self.emit_label(next_arm_label)

            # End of match
            self.emit_label(end_label)
            self.emit("add esp, 8")  # Clean up saved address and tag

            return "eax"

        if isinstance(expr, DictLiteral):
            # Dict literal: {"key": value, ...}
            # For now, return null pointer since full dict support requires runtime
            if not expr.pairs:
                # Empty dict - return null
                self.emit("xor eax, eax")
                return "eax"
            # Non-empty dict not fully supported yet, return null for compatibility
            self.emit("xor eax, eax")
            return "eax"

        if isinstance(expr, TupleLiteral):
            # Tuple literal: (a, b, c)
            # Treat similar to array - allocate on stack
            if not expr.elements:
                self.emit("xor eax, eax")
                return "eax"

            # Allocate space on stack (each element is 4 bytes)
            tuple_size = len(expr.elements) * 4
            self.stack_offset += tuple_size
            tuple_offset = -self.stack_offset

            # Initialize each element
            for i, elem in enumerate(expr.elements):
                self.gen_expression(elem)
                elem_offset = tuple_offset + (i * 4)
                if elem_offset >= 0:
                    self.emit(f"mov [ebp+{elem_offset}], eax")
                else:
                    self.emit(f"mov {self.ebp_addr(elem_offset)}, eax")

            # Return pointer to tuple
            if tuple_offset >= 0:
                self.emit(f"lea eax, [ebp+{tuple_offset}]")
            else:
                self.emit(f"lea eax, {self.ebp_addr(tuple_offset)}")
            return "eax"

        raise NotImplementedError(f"Code generation for {type(expr).__name__} not implemented")

    def gen_lvalue_address(self, expr: ASTNode):
        """Generate code to get the address of an lvalue expression into EAX"""
        if isinstance(expr, Identifier):
            if expr.name in self.local_vars:
                offset = self.local_vars[expr.name]
                if offset > 0:
                    self.emit(f"lea eax, [ebp+{offset}]")
                else:
                    self.emit(f"lea eax, {self.ebp_addr(offset)}")
            else:
                # Global variable
                self.emit(f"lea eax, [{expr.name}]")
        elif isinstance(expr, FieldAccessExpr):
            # Get address of struct field
            obj_type = self._get_expr_type(expr.object)
            if obj_type is None:
                # Unknown type - generate expression value and assume field offset
                self.gen_expression(expr.object)
                # Use heuristic offsets for common field names
                field_offset = 0
                if expr.field_name == 'value':
                    field_offset = 0
                elif expr.field_name == 'name':
                    field_offset = 4
                elif expr.field_name == 'type':
                    field_offset = 0
                elif expr.field_name == 'line':
                    field_offset = 8
                elif expr.field_name == 'column':
                    field_offset = 12
                if field_offset > 0:
                    self.emit(f"add eax, {field_offset}")
            elif isinstance(obj_type, PointerType):
                # If it's a pointer, load the pointer value first
                self.gen_expression(expr.object)
                struct_name = obj_type.base_type.name
                offset = self.get_field_offset(struct_name, expr.field_name)
                if offset > 0:
                    self.emit(f"add eax, {offset}")
            else:
                self.gen_lvalue_address(expr.object)  # Get object address
                struct_name = obj_type.name
                offset = self.get_field_offset(struct_name, expr.field_name)
                if offset > 0:
                    self.emit(f"add eax, {offset}")
        elif isinstance(expr, IndexExpr):
            # Get address of array element (similar to AddrOfExpr handling)
            self.gen_expression(expr.index)
            self.emit("mov ebx, eax")
            # Get base address and add scaled index
            self.gen_expression(expr.array)
            self.emit("imul ebx, 4")  # Assume 4-byte elements
            self.emit("add eax, ebx")
        else:
            raise NotImplementedError(f"Cannot take address of {type(expr).__name__}")

    def emit_deferred(self):
        """Emit all deferred statements in reverse order (LIFO)"""
        for stmt in reversed(self.defer_stack):
            self.gen_statement(stmt)

    # Statement code generation
    def gen_statement(self, stmt: ASTNode):
        if isinstance(stmt, VarDecl):
            # Record type
            self.type_table[stmt.name] = stmt.var_type

            # Allocate space on stack (negative offset from EBP)
            size = self.type_size(stmt.var_type)
            self.stack_offset += size
            var_offset = -self.stack_offset
            self.local_vars[stmt.name] = var_offset  # Negative for local vars

            # Initialize if there's a value
            if stmt.value:
                # Special handling for struct literal initialization
                if isinstance(stmt.value, StructLiteral):
                    struct_name = stmt.value.struct_type
                    # Initialize each field directly into the allocated space
                    for field_name, field_expr in stmt.value.field_values.items():
                        field_offset = self.get_field_offset(struct_name, field_name)
                        field_type = self.get_field_type(struct_name, field_name)
                        field_size = self.type_size(field_type) if field_type else 4

                        # Generate field value
                        self.gen_expression(field_expr)

                        # Store at var_base + field_offset
                        total_offset = var_offset + field_offset
                        if total_offset >= 0:
                            addr = f"[ebp+{total_offset}]"
                        else:
                            addr = self.ebp_addr(total_offset)

                        if field_size == 1:
                            self.emit(f"mov byte {addr}, al")
                        elif field_size == 2:
                            self.emit(f"mov word {addr}, ax")
                        else:
                            self.emit(f"mov {addr}, eax")
                elif isinstance(stmt.value, ArrayLiteral):
                    # Initialize array elements directly into allocated space
                    elements = stmt.value.elements
                    if elements:
                        first_type = self._get_expr_type(elements[0])
                        element_size = self.type_size(first_type) if first_type else 4

                        for i, elem in enumerate(elements):
                            self.gen_expression(elem)
                            elem_offset = var_offset + (i * element_size)
                            if elem_offset >= 0:
                                addr = f"[ebp+{elem_offset}]"
                            else:
                                addr = self.ebp_addr(elem_offset)

                            if element_size == 1:
                                self.emit(f"mov byte {addr}, al")
                            elif element_size == 2:
                                self.emit(f"mov word {addr}, ax")
                            else:
                                self.emit(f"mov {addr}, eax")
                elif isinstance(stmt.value, CallExpr) and self.is_enum_constructor(stmt.value.func):
                    # Enum variant constructor: Some(5)
                    enum_name = self.is_enum_constructor(stmt.value.func)
                    variant_name = stmt.value.func
                    tag = self.get_variant_tag(enum_name, variant_name)

                    # Store tag at base of enum
                    tag_addr = self.ebp_addr(var_offset) if var_offset < 0 else f"[ebp+{var_offset}]"
                    self.emit(f"mov dword {tag_addr}, {tag}")

                    # Store payload (if any)
                    if stmt.value.args:
                        self.gen_expression(stmt.value.args[0])
                        payload_offset = var_offset + 4  # payload is after 4-byte tag
                        payload_addr = self.ebp_addr(payload_offset) if payload_offset < 0 else f"[ebp+{payload_offset}]"
                        self.emit(f"mov {payload_addr}, eax")
                elif isinstance(stmt.value, Identifier) and self.is_enum_constructor(stmt.value.name):
                    # Unit enum variant: None
                    enum_name = self.is_enum_constructor(stmt.value.name)
                    variant_name = stmt.value.name
                    tag = self.get_variant_tag(enum_name, variant_name)

                    # Store tag at base of enum
                    tag_addr = self.ebp_addr(var_offset) if var_offset < 0 else f"[ebp+{var_offset}]"
                    self.emit(f"mov dword {tag_addr}, {tag}")
                elif isinstance(stmt.value, SliceExpr):
                    # Slice expression: stores fat pointer (ptr, len) = 8 bytes
                    self.gen_expression(stmt.value)  # ptr in eax, len in edx

                    # Store ptr at var_offset
                    ptr_addr = self.ebp_addr(var_offset) if var_offset < 0 else f"[ebp+{var_offset}]"
                    self.emit(f"mov {ptr_addr}, eax")

                    # Store len at var_offset + 4
                    len_offset = var_offset + 4
                    len_addr = self.ebp_addr(len_offset) if len_offset < 0 else f"[ebp+{len_offset}]"
                    self.emit(f"mov {len_addr}, edx")
                else:
                    self.gen_expression(stmt.value)
                    # Store with appropriate size
                    if size == 1:
                        self.emit(f"mov byte [ebp-{self.stack_offset}], al")
                    elif size == 2:
                        self.emit(f"mov word [ebp-{self.stack_offset}], ax")
                    else:
                        self.emit(f"mov [ebp-{self.stack_offset}], eax")

        elif isinstance(stmt, Assignment):
            # Generate value
            self.gen_expression(stmt.value)

            # Store to target
            if isinstance(stmt.target, Identifier):
                # Determine variable type to use appropriate store size
                var_type = self.type_table.get(stmt.target.name)
                var_size = self.type_size(var_type) if var_type else 4

                # For Python-style implicit variable declaration, allocate local if not exists
                if stmt.target.name not in self.local_vars:
                    # Check if it's a global (defined at module level)
                    if stmt.target.name not in getattr(self, 'global_vars', {}):
                        # Create new local variable
                        self.stack_offset += var_size
                        self.local_vars[stmt.target.name] = -self.stack_offset

                if stmt.target.name in self.local_vars:
                    offset = self.local_vars[stmt.target.name]
                    addr = self.ebp_addr(offset)

                    # Store with appropriate size
                    if var_size == 1:
                        self.emit(f"mov byte {addr}, al")
                    elif var_size == 2:
                        self.emit(f"mov word {addr}, ax")
                    else:
                        self.emit(f"mov {addr}, eax")
                else:
                    # Global variable
                    addr = f"[{stmt.target.name}]" if self.kernel_mode else f"[rel {stmt.target.name}]"
                    if var_size == 1:
                        self.emit(f"mov byte {addr}, al")
                    elif var_size == 2:
                        self.emit(f"mov word {addr}, ax")
                    else:
                        self.emit(f"mov {addr}, eax")

            elif isinstance(stmt.target, IndexExpr):
                # Array assignment
                self.emit("push eax")  # Save value

                # Calculate index
                self.gen_expression(stmt.target.index)
                self.emit("mov ebx, eax")

                # Determine pointer type to calculate element size
                pointer_type = None
                if isinstance(stmt.target.array, CastExpr):
                    # Type comes from cast expression
                    pointer_type = stmt.target.array.target_type
                elif isinstance(stmt.target.array, Identifier):
                    # Look up type from type table
                    if stmt.target.array.name in self.type_table:
                        pointer_type = self.type_table[stmt.target.array.name]

                # Calculate element size
                element_size = 1  # Default to 1 byte
                if pointer_type:
                    if isinstance(pointer_type, PointerType):
                        element_size = self.type_size(pointer_type.base_type)
                    elif isinstance(pointer_type, ArrayType):
                        element_size = self.type_size(pointer_type.element_type)

                # Generate array base address
                if isinstance(stmt.target.array, CastExpr):
                    # Generate the cast expression to get the pointer value
                    self.gen_expression(stmt.target.array)
                elif isinstance(stmt.target.array, Identifier):
                    if stmt.target.array.name in self.local_vars:
                        offset = self.local_vars[stmt.target.array.name]
                        var_type = self.type_table.get(stmt.target.array.name)
                        # For local arrays, get address with LEA; for pointers, load value with MOV
                        if isinstance(var_type, ArrayType):
                            if offset > 0:
                                self.emit(f"lea eax, [ebp+{offset}]")
                            else:
                                self.emit(f"lea eax, {self.ebp_addr(offset)}")
                        else:
                            # It's a pointer variable, load its value
                            if offset > 0:
                                self.emit(f"mov eax, [ebp+{offset}]")
                            else:
                                self.emit(f"mov eax, {self.ebp_addr(offset)}")
                    else:
                        # Global variable - check if array or pointer
                        var_type = self.type_table.get(stmt.target.array.name)
                        addr = f"[{stmt.target.array.name}]" if self.kernel_mode else f"[rel {stmt.target.array.name}]"
                        if isinstance(var_type, ArrayType):
                            # Array storage is the data, use LEA to get address
                            self.emit(f"lea eax, {addr}")
                        else:
                            # Pointer variable - load its value with MOV
                            self.emit(f"mov eax, {addr}")

                # Calculate address: base + index * element_size
                if element_size > 1:
                    # Multiply index by element size
                    if element_size == 2:
                        self.emit("shl ebx, 1")  # index * 2
                    elif element_size == 4:
                        self.emit("shl ebx, 2")  # index * 4
                    else:
                        self.emit(f"imul ebx, {element_size}")  # index * element_size

                self.emit("add eax, ebx")

                self.emit("pop ebx")  # Restore value
                # Store value with appropriate size
                if element_size == 1:
                    self.emit("mov byte [eax], bl")  # Store low byte
                elif element_size == 2:
                    self.emit("mov word [eax], bx")  # Store low word
                else:
                    self.emit("mov [eax], ebx")  # Store dword

            elif isinstance(stmt.target, FieldAccessExpr):
                # Field assignment: obj.field = value
                self.emit("push eax")  # Save value

                # Get struct type from object
                obj_type = self._get_expr_type(stmt.target.object)
                if obj_type is None:
                    # Unknown type - treat as generic pointer assignment
                    # This can happen with untyped 'self' in Python-style methods
                    if isinstance(stmt.target.object, Identifier):
                        if stmt.target.object.name in self.local_vars:
                            offset = self.local_vars[stmt.target.object.name]
                            if offset > 0:
                                self.emit(f"mov eax, [ebp+{offset}]")
                            else:
                                self.emit(f"mov eax, {self.ebp_addr(offset)}")
                        else:
                            addr = f"[{stmt.target.object.name}]" if self.kernel_mode else f"[rel {stmt.target.object.name}]"
                            self.emit(f"mov eax, {addr}")
                        # Store value at pointer (treating as generic field at offset 0)
                        self.emit("pop ebx")  # Get value
                        self.emit("mov [eax], ebx")  # Store to field
                        return  # Skip rest of field assignment code
                    raise ValueError(f"Cannot determine type of {stmt.target.object}")

                # Handle pointer-to-struct vs direct struct
                if isinstance(obj_type, PointerType):
                    struct_name = obj_type.base_type.name
                    # Generate pointer value
                    self.gen_expression(stmt.target.object)
                else:
                    struct_name = obj_type.name
                    # Get address of struct
                    if isinstance(stmt.target.object, Identifier):
                        if stmt.target.object.name in self.local_vars:
                            offset = self.local_vars[stmt.target.object.name]
                            if offset > 0:
                                self.emit(f"lea eax, [ebp+{offset}]")
                            else:
                                self.emit(f"lea eax, {self.ebp_addr(offset)}")
                        else:
                            addr = f"[{stmt.target.object.name}]" if self.kernel_mode else f"[rel {stmt.target.object.name}]"
                            self.emit(f"lea eax, {addr}")
                    else:
                        self.gen_expression(stmt.target.object)

                # Get field offset and type
                field_offset = self.get_field_offset(struct_name, stmt.target.field_name)
                field_type = self.get_field_type(struct_name, stmt.target.field_name)
                field_size = self.type_size(field_type) if field_type else 4

                # Add field offset to base
                if field_offset > 0:
                    self.emit(f"add eax, {field_offset}")

                # Restore value and store
                self.emit("pop ebx")
                if field_size == 1:
                    self.emit("mov byte [eax], bl")
                elif field_size == 2:
                    self.emit("mov word [eax], bx")
                else:
                    self.emit("mov [eax], ebx")

            elif isinstance(stmt.target, TupleLiteral):
                # Tuple unpacking: a, b = x, y
                # For simple cases where right side is also a tuple literal,
                # evaluate each element directly instead of building intermediate tuple
                if isinstance(stmt.value, TupleLiteral) and len(stmt.value.elements) == len(stmt.target.elements):
                    # Direct element-by-element assignment
                    for i, (target_elem, value_elem) in enumerate(zip(stmt.target.elements, stmt.value.elements)):
                        if isinstance(target_elem, Identifier):
                            var_name = target_elem.name
                            # Allocate local if needed
                            if var_name not in self.local_vars:
                                self.stack_offset += 4
                                self.local_vars[var_name] = -self.stack_offset

                            # Evaluate value element
                            self.gen_expression(value_elem)

                            # Store to variable
                            offset = self.local_vars[var_name]
                            if offset >= 0:
                                self.emit(f"mov [ebp+{offset}], eax")
                            else:
                                self.emit(f"mov {self.ebp_addr(offset)}, eax")
                else:
                    # General case: tuple pointer is in eax (from gen_expression above)
                    self.emit("push eax")  # Save tuple pointer

                    # Unpack each element
                    for i, elem in enumerate(stmt.target.elements):
                        if isinstance(elem, Identifier):
                            var_name = elem.name
                            # Allocate local if needed
                            if var_name not in self.local_vars:
                                self.stack_offset += 4
                                self.local_vars[var_name] = -self.stack_offset

                            # Load from tuple (tuple ptr is on stack)
                            self.emit("mov eax, [esp]")  # Get tuple pointer
                            self.emit(f"mov eax, [eax+{i * 4}]")  # Load element

                            # Store to variable
                            offset = self.local_vars[var_name]
                            if offset >= 0:
                                self.emit(f"mov [ebp+{offset}], eax")
                            else:
                                self.emit(f"mov {self.ebp_addr(offset)}, eax")

                    self.emit("add esp, 4")  # Clean up saved tuple pointer

        elif isinstance(stmt, ReturnStmt):
            if stmt.value:
                self.gen_expression(stmt.value)
            # Jump to deferred/epilogue section
            self.emit(f"jmp {self.return_label}")

        elif isinstance(stmt, IfStmt):
            end_label = self.new_label("endif")
            else_label = self.new_label("else")

            # Generate condition
            self.gen_expression(stmt.condition)
            self.emit("test eax, eax")
            self.emit(f"jz {else_label}")

            # Then block
            for s in stmt.then_block:
                self.gen_statement(s)
            self.emit(f"jmp {end_label}")

            # Else block
            self.emit_label(else_label)
            if stmt.else_block:
                for s in stmt.else_block:
                    self.gen_statement(s)

            self.emit_label(end_label)

        elif isinstance(stmt, BreakStmt):
            # Jump to end of loop
            if hasattr(self, 'loop_end_label'):
                self.emit(f"jmp {self.loop_end_label}")
            else:
                raise SyntaxError("break statement outside loop")

        elif isinstance(stmt, ContinueStmt):
            # Jump to start of loop
            if hasattr(self, 'loop_start_label'):
                self.emit(f"jmp {self.loop_start_label}")
            else:
                raise SyntaxError("continue statement outside loop")

        elif isinstance(stmt, WhileStmt):
            start_label = self.new_label("while_start")
            end_label = self.new_label("while_end")

            # Save loop labels for break/continue
            old_start = getattr(self, 'loop_start_label', None)
            old_end = getattr(self, 'loop_end_label', None)
            self.loop_start_label = start_label
            self.loop_end_label = end_label

            self.emit_label(start_label)

            # Generate condition
            self.gen_expression(stmt.condition)
            self.emit("test eax, eax")
            self.emit(f"jz {end_label}")

            # Body
            for s in stmt.body:
                self.gen_statement(s)

            self.emit(f"jmp {start_label}")
            self.emit_label(end_label)

            # Restore old loop labels
            self.loop_start_label = old_start
            self.loop_end_label = old_end

        elif isinstance(stmt, ForStmt):
            # for i in start..end:
            # Initialize loop variable
            self.stack_offset += 4
            self.local_vars[stmt.var] = self.stack_offset

            self.gen_expression(stmt.start)
            self.emit(f"mov [ebp-{self.stack_offset}], eax")

            # Generate end value (keep in register)
            self.gen_expression(stmt.end)
            self.emit("push eax")  # Save end value

            start_label = self.new_label("for_start")
            end_label = self.new_label("for_end")

            self.emit_label(start_label)

            # Check condition: i <= end
            offset = self.local_vars[stmt.var]
            self.emit(f"mov eax, [ebp-{offset}]")
            self.emit("mov ebx, [esp]")  # End value from stack
            self.emit("cmp eax, ebx")
            self.emit(f"jg {end_label}")

            # Body
            for s in stmt.body:
                self.gen_statement(s)

            # Increment i
            self.emit(f"inc dword [ebp-{offset}]")
            self.emit(f"jmp {start_label}")

            self.emit_label(end_label)
            self.emit("add esp, 4")  # Clean up end value

        elif isinstance(stmt, ForEachStmt):
            # for item in array: body
            # Generates: for i in 0..len(array): item = array[i]; body

            # Get array type to determine element size and length
            arr_type = self._get_expr_type(stmt.iterable)
            if arr_type is None:
                # Unknown type - skip the loop entirely for now
                # This can happen with untyped expressions in Python-style code
                # Add loop variable to scope with unknown type
                if stmt.vars:
                    for var in stmt.vars:
                        self.local_vars[var] = -4  # Placeholder
                return

            # Handle List iteration
            if isinstance(arr_type, ListType):
                # for item in list: body -> for i in 0..list_len(list): item = list_get(list, i); body
                loop_var = stmt.vars[0]

                # Allocate index variable (hidden)
                self.stack_offset += 4
                index_offset = -self.stack_offset

                # Allocate loop variable
                self.stack_offset += 4  # Assume int32/pointer elements
                var_offset = -self.stack_offset
                self.local_vars[loop_var] = var_offset
                self.type_table[loop_var] = arr_type.element_type

                # Get list length
                self.gen_expression(stmt.iterable)  # Get list ptr
                self.emit("push eax")
                self.emit("call list_len")
                self.emit("add esp, 4")
                # Save length on stack
                self.stack_offset += 4
                len_offset = -self.stack_offset
                self.emit(f"mov {self.ebp_addr(len_offset)}, eax")

                # Initialize index to 0
                self.emit(f"mov dword {self.ebp_addr(index_offset)}, 0")

                start_label = self.new_label("foreach_list_start")
                end_label = self.new_label("foreach_list_end")

                old_start = getattr(self, 'loop_start_label', None)
                old_end = getattr(self, 'loop_end_label', None)
                self.loop_start_label = start_label
                self.loop_end_label = end_label

                self.emit_label(start_label)

                # Check: index < length
                self.emit(f"mov eax, {self.ebp_addr(index_offset)}")
                self.emit(f"cmp eax, {self.ebp_addr(len_offset)}")
                self.emit(f"jge {end_label}")

                # Get element: item = list_get_i32(list, index)
                self.emit(f"mov eax, {self.ebp_addr(index_offset)}")
                self.emit("push eax")  # index
                self.gen_expression(stmt.iterable)  # list ptr
                self.emit("push eax")
                self.emit("call list_get_i32")
                self.emit("add esp, 8")
                self.emit(f"mov {self.ebp_addr(var_offset)}, eax")

                # Generate loop body
                for body_stmt in stmt.body:
                    self.gen_statement(body_stmt)

                # Increment index
                self.emit(f"inc dword {self.ebp_addr(index_offset)}")
                self.emit(f"jmp {start_label}")

                self.emit_label(end_label)

                self.loop_start_label = old_start
                self.loop_end_label = old_end
                return

            if not isinstance(arr_type, ArrayType):
                # Non-array type - skip for now
                if stmt.vars:
                    for var in stmt.vars:
                        self.local_vars[var] = -4  # Placeholder
                return

            element_type = arr_type.element_type
            element_size = self.type_size(element_type)
            array_length = arr_type.size

            # Allocate index variable (hidden)
            self.stack_offset += 4
            index_offset = -self.stack_offset

            # Allocate loop variable(s)
            # For now, only support single variable (tuple unpacking TODO)
            loop_var = stmt.vars[0]
            self.stack_offset += element_size
            var_offset = -self.stack_offset
            self.local_vars[loop_var] = var_offset
            self.type_table[loop_var] = element_type

            # Initialize index to 0
            self.emit(f"mov dword {self.ebp_addr(index_offset)}, 0")

            start_label = self.new_label("foreach_start")
            end_label = self.new_label("foreach_end")

            # Save loop labels for break/continue
            old_start = getattr(self, 'loop_start_label', None)
            old_end = getattr(self, 'loop_end_label', None)
            self.loop_start_label = start_label
            self.loop_end_label = end_label

            self.emit_label(start_label)

            # Check: index < array_length
            self.emit(f"mov eax, {self.ebp_addr(index_offset)}")
            self.emit(f"cmp eax, {array_length}")
            self.emit(f"jge {end_label}")

            # Load current element: item = array[index]
            # Get array base address
            if isinstance(stmt.iterable, Identifier):
                if stmt.iterable.name in self.local_vars:
                    arr_offset = self.local_vars[stmt.iterable.name]
                    if arr_offset > 0:
                        self.emit(f"lea ebx, [ebp+{arr_offset}]")
                    else:
                        self.emit(f"lea ebx, {self.ebp_addr(arr_offset)}")
                else:
                    addr = f"[{stmt.iterable.name}]" if self.kernel_mode else f"[rel {stmt.iterable.name}]"
                    self.emit(f"lea ebx, {addr}")
            else:
                self.gen_expression(stmt.iterable)
                self.emit("mov ebx, eax")

            # Calculate element address: base + index * element_size
            self.emit(f"mov eax, {self.ebp_addr(index_offset)}")
            if element_size > 1:
                if element_size == 2:
                    self.emit("shl eax, 1")
                elif element_size == 4:
                    self.emit("shl eax, 2")
                else:
                    self.emit(f"imul eax, {element_size}")
            self.emit("add eax, ebx")

            # Load element value
            if element_size == 1:
                self.emit("movzx eax, byte [eax]")
            elif element_size == 2:
                self.emit("movzx eax, word [eax]")
            else:
                self.emit("mov eax, [eax]")

            # Store in loop variable
            if element_size == 1:
                self.emit(f"mov byte {self.ebp_addr(var_offset)}, al")
            elif element_size == 2:
                self.emit(f"mov word {self.ebp_addr(var_offset)}, ax")
            else:
                self.emit(f"mov {self.ebp_addr(var_offset)}, eax")

            # Execute body
            for s in stmt.body:
                self.gen_statement(s)

            # Increment index
            self.emit(f"inc dword {self.ebp_addr(index_offset)}")
            self.emit(f"jmp {start_label}")

            self.emit_label(end_label)

            # Restore old loop labels
            self.loop_start_label = old_start
            self.loop_end_label = old_end

        elif isinstance(stmt, ExprStmt):
            self.gen_expression(stmt.expr)

        elif isinstance(stmt, DiscardStmt):
            pass  # No code needed

        elif isinstance(stmt, DeferStmt):
            # Add to defer stack - will be executed at function return
            self.defer_stack.append(stmt.stmt)

    # Procedure code generation
    def gen_procedure(self, proc: ProcDecl):
        self.emit("")
        # In kernel mode, rename main to brainhair_kernel_main
        func_name = proc.name
        if self.kernel_mode and proc.name == "main":
            func_name = "brainhair_kernel_main"

        # Make function names unique to avoid label collisions
        # Skip main and other entry points
        if func_name not in ('main', 'brainhair_kernel_main', '_start'):
            if func_name in self.global_var_names:
                self.global_var_names[func_name] += 1
                func_name = f"{func_name}_{self.global_var_names[func_name]}"
            else:
                self.global_var_names[func_name] = 0
        self.emit_label(func_name)

        # Prologue
        self.emit("push ebp")
        self.emit("mov ebp, esp")

        # Mark where we'll insert stack allocation later
        stack_alloc_pos = len(self.output)

        # Save and reset local variables for this function
        old_locals = self.local_vars
        old_offset = self.stack_offset
        self.local_vars = {}
        self.stack_offset = 0

        # Save and reset defer stack for this function
        old_defer_stack = self.defer_stack
        self.defer_stack = []

        # Create unique return label for this function
        old_return_label = getattr(self, 'return_label', None)
        self.return_label = f"{func_name}_return"

        # Parameters (on stack, above EBP)
        # Stack layout: [param2][param1][return addr][saved EBP] <- EBP
        param_offset = 8  # Skip return address (4 bytes) and saved EBP (4 bytes)
        for param in proc.params:
            # Record parameter type
            param_type = param.param_type

            # Special handling for 'self' parameter without explicit type
            # Try to infer type from function name pattern: ClassName_method or ClassName___method__
            if param.name == 'self' and param_type is None:
                # Try to extract class name from function name
                if '_' in func_name:
                    class_name = func_name.split('_')[0]
                    if class_name in self.struct_types:
                        param_type = PointerType(Type(class_name))

            self.type_table[param.name] = param_type
            # Parameters are at positive offsets from EBP - mark with a special flag
            self.local_vars[param.name] = param_offset
            param_offset += 4

        # Initialize default return value for integer-returning functions
        # This ensures functions return 0 if no explicit return is executed
        if proc.return_type and proc.return_type.name in ('i8', 'i16', 'i32', 'i64', 'u8', 'u16', 'u32', 'u64', 'int32', 'int16', 'int8', 'uint32', 'uint16', 'uint8'):
            self.emit("xor eax, eax")

        # Generate body (this will add local variables with negative offsets)
        for stmt in proc.body:
            self.gen_statement(stmt)

        # Allocate stack space for local variables (if any)
        # Insert after the "mov ebp, esp" instruction
        if self.stack_offset > 0:
            # Round up to 16-byte alignment for better performance (optional)
            stack_size = self.stack_offset
            # Insert the allocation instruction
            self.output.insert(stack_alloc_pos, f"    sub esp, {stack_size}")

        # Epilogue - emit deferred statements first
        self.emit_label(self.return_label)
        if self.defer_stack:
            self.emit("push eax")  # Save return value
            self.emit_deferred()
            self.emit("pop eax")   # Restore return value
        self.emit("mov esp, ebp")
        self.emit("pop ebp")
        self.emit("ret")

        # Restore
        self.local_vars = old_locals
        self.stack_offset = old_offset
        self.return_label = old_return_label
        self.defer_stack = old_defer_stack

    def gen_method(self, method: MethodDecl):
        """Generate code for a method declaration.

        Methods are generated as functions with a mangled name: TypeName_methodName
        The receiver (self) is the first implicit parameter.
        """
        self.emit("")

        # Get the type name from the receiver type
        receiver_type = method.receiver_type
        if isinstance(receiver_type, PointerType):
            type_name = receiver_type.base_type.name
        else:
            type_name = receiver_type.name

        # Generate mangled function name
        func_name = f"{type_name}_{method.name}"
        self.emit_label(func_name)

        # Prologue
        self.emit("push ebp")
        self.emit("mov ebp, esp")

        # Mark where we'll insert stack allocation later
        stack_alloc_pos = len(self.output)

        # Save and reset local variables for this function
        old_locals = self.local_vars
        old_offset = self.stack_offset
        self.local_vars = {}
        self.stack_offset = 0

        # Save and reset defer stack for this method
        old_defer_stack = self.defer_stack
        self.defer_stack = []

        # Create unique return label for this function
        old_return_label = getattr(self, 'return_label', None)
        self.return_label = f"{func_name}_return"

        # Parameters (on stack, above EBP)
        # Stack layout: [param2][param1][self][return addr][saved EBP] <- EBP
        param_offset = 8  # Skip return address (4 bytes) and saved EBP (4 bytes)

        # First parameter is the receiver (self)
        self.type_table[method.receiver_name] = method.receiver_type
        self.local_vars[method.receiver_name] = param_offset
        param_offset += 4

        # Then explicit parameters
        for param in method.params:
            self.type_table[param.name] = param.param_type
            self.local_vars[param.name] = param_offset
            param_offset += 4

        # Initialize default return value for integer-returning methods
        if method.return_type and method.return_type.name in ('i8', 'i16', 'i32', 'i64', 'u8', 'u16', 'u32', 'u64', 'int32', 'int16', 'int8', 'uint32', 'uint16', 'uint8'):
            self.emit("xor eax, eax")

        # Generate body
        for stmt in method.body:
            self.gen_statement(stmt)

        # Allocate stack space for local variables (if any)
        if self.stack_offset > 0:
            stack_size = self.stack_offset
            self.output.insert(stack_alloc_pos, f"    sub esp, {stack_size}")

        # Epilogue - emit deferred statements first
        self.emit_label(self.return_label)
        if self.defer_stack:
            self.emit("push eax")  # Save return value
            self.emit_deferred()
            self.emit("pop eax")   # Restore return value
        self.emit("mov esp, ebp")
        self.emit("pop ebp")
        self.emit("ret")

        # Restore
        self.local_vars = old_locals
        self.stack_offset = old_offset
        self.return_label = old_return_label
        self.defer_stack = old_defer_stack

    # Program generation
    def generate(self, program: Program) -> str:
        """Generate complete x86 assembly"""
        # First pass: collect constants, extern declarations, struct types, and global variable types
        self.constants = {}
        self.externs = []
        self.func_names = set()  # Track function names for function pointer support
        for decl in program.declarations:
            if isinstance(decl, StructDecl):
                # Register struct type for field offset calculations
                self.struct_types[decl.name] = decl
            elif isinstance(decl, EnumDecl):
                # Register enum type
                self.enum_types[decl.name] = decl
            elif isinstance(decl, VarDecl) and decl.is_const and decl.value:
                # Inline constants - store for lookup
                if isinstance(decl.value, IntLiteral):
                    self.constants[decl.name] = decl.value.value
                elif isinstance(decl.value, UnaryExpr) and decl.value.op == UnaryOp.NEG and isinstance(decl.value.expr, IntLiteral):
                    # Handle negative constants like -1
                    self.constants[decl.name] = -decl.value.expr.value
            elif isinstance(decl, VarDecl) and not decl.is_const:
                # Register global variable types before generating procedure code
                self.type_table[decl.name] = decl.var_type
            elif isinstance(decl, ExternDecl):
                # Collect external function names
                self.externs.append(decl.name)
                self.func_names.add(decl.name)
            elif isinstance(decl, ProcDecl):
                # Track procedure names for function pointer support
                self.func_names.add(decl.name)

        # Generate code for all declarations
        for decl in program.declarations:
            if isinstance(decl, ProcDecl):
                self.gen_procedure(decl)
            elif isinstance(decl, MethodDecl):
                self.gen_method(decl)
            elif isinstance(decl, ExternDecl):
                # External declarations - no code generation needed
                # They're just function prototypes
                pass
            elif isinstance(decl, VarDecl):
                # Skip constants (they're inlined)
                if decl.is_const:
                    continue

                # Generate unique global variable name to avoid label collisions
                # Only rename if this name has already been used
                var_name = decl.name
                if var_name in self.global_var_names:
                    # Already used - append counter to make unique
                    self.global_var_names[var_name] += 1
                    unique_name = f"_g_{var_name}_{self.global_var_names[var_name]}"
                else:
                    # First use - keep original name
                    self.global_var_names[var_name] = 0
                    unique_name = var_name  # Use original name for first occurrence

                # Global variable - record type for proper address calculation
                # Use original name for type_table so code references work
                self.type_table[var_name] = decl.var_type

                # Check if initialized with a string literal
                if decl.value and isinstance(decl.value, StringLiteral):
                    # Put in data section with initialized value
                    str_label = self.add_string(decl.value.value)
                    self.data_section.append(f"{unique_name}: dd {str_label}")
                else:
                    # Uninitialized - goes in BSS
                    self.bss_section.append(f"{unique_name}: resb {self.type_size(decl.var_type)}")

        # Build final assembly
        asm = []
        asm.append("; Generated by Brainhair Compiler")
        asm.append("bits 32")
        asm.append("")

        # External declarations (skip built-in get_argc/get_argv)
        builtin_funcs = ['get_argc', 'get_argv']
        if self.externs:
            for extern_name in self.externs:
                if extern_name not in builtin_funcs:
                    asm.append(f"extern {extern_name}")
            asm.append("")

        # Data section
        if self.strings or self.data_section:
            asm.append("section .data")
            for label, value in self.strings.items():
                # Build proper NASM string with escape sequences
                # NASM uses single quotes for raw strings, double quotes allow backtick escapes
                parts = []
                current_str = ""
                for ch in value:
                    if ch == '\n':
                        if current_str:
                            parts.append(f"'{current_str}'")
                            current_str = ""
                        parts.append('10')
                    elif ch == '\t':
                        if current_str:
                            parts.append(f"'{current_str}'")
                            current_str = ""
                        parts.append('9')
                    elif ch == '\r':
                        if current_str:
                            parts.append(f"'{current_str}'")
                            current_str = ""
                        parts.append('13')
                    elif ch == '\0':
                        if current_str:
                            parts.append(f"'{current_str}'")
                            current_str = ""
                        parts.append('0')
                    elif ch == "'":
                        # Single quote - output current string, add byte value, continue
                        if current_str:
                            parts.append(f"'{current_str}'")
                            current_str = ""
                        parts.append("39")  # ASCII for single quote
                    elif ch == '\\':
                        current_str += '\\\\'
                    else:
                        current_str += ch
                if current_str:
                    parts.append(f"'{current_str}'")
                parts.append('0')  # Null terminator
                asm.append(f'{label}: db {", ".join(parts)}')
            asm.extend(self.data_section)
            asm.append("")

        # BSS section
        if self.bss_section:
            asm.append("section .bss")
            asm.extend(self.bss_section)
            asm.append("")

        # Text section
        asm.append("section .text")

        # Only generate _start if not in kernel mode
        if not self.kernel_mode:
            asm.append("global _start")
            asm.append("global get_argc")
            asm.append("global get_argv")
            asm.append("")
            asm.append("section .bss")
            asm.append("_startup_esp: resd 1")
            asm.append("")
            asm.append("section .text")
            asm.append("")

            # Check if main function exists
            has_main = any(isinstance(d, ProcDecl) and d.name == "main" for d in program.declarations)

            if not has_main:
                # Generate a stub main function for Python files without explicit main
                asm.append("main:")
                asm.append("    push ebp")
                asm.append("    mov ebp, esp")
                asm.append("    xor eax, eax  ; Return 0")
                asm.append("    pop ebp")
                asm.append("    ret")
                asm.append("")

            asm.append("_start:")
            asm.append("    mov [_startup_esp], esp  ; Save initial stack pointer")
            asm.append("    call main")
            asm.append("    ; Exit with return code from main")
            asm.append("    mov ebx, eax  ; Exit code")
            asm.append("    mov eax, 1    ; sys_exit")
            asm.append("    int 0x80")
            asm.append("")
            asm.append("; get_argc() - returns argument count")
            asm.append("get_argc:")
            asm.append("    mov eax, [_startup_esp]")
            asm.append("    mov eax, [eax]  ; argc is at [esp]")
            asm.append("    ret")
            asm.append("")
            asm.append("; get_argv(index) - returns pointer to argument string")
            asm.append("get_argv:")
            asm.append("    push ebp")
            asm.append("    mov ebp, esp")
            asm.append("    mov eax, [_startup_esp]")
            asm.append("    mov ecx, [ebp+8]  ; index")
            asm.append("    lea eax, [eax + 4 + ecx*4]  ; argv[index] = esp + 4 + index*4")
            asm.append("    mov eax, [eax]")
            asm.append("    pop ebp")
            asm.append("    ret")
            asm.append("")
            # Add stub functions for common missing symbols
            asm.append("; Stub functions for Python-style code compatibility")
            asm.append("uint8_join:")
            asm.append("    ; String join stub - just return first arg")
            asm.append("    mov eax, [esp+4]")
            asm.append("    ret")
            asm.append("")
            asm.append("original_init:")
            asm.append("    ; Original __init__ stub")
            asm.append("    xor eax, eax")
            asm.append("    ret")
            asm.append("")
            asm.append("types:")
            asm.append("    ; Python types module stub")
            asm.append("    xor eax, eax")
            asm.append("    ret")
            asm.append("")
        else:
            # In kernel mode, export brainhair_kernel_main
            asm.append("global brainhair_kernel_main")
            # Export networking functions for syscall handlers
            asm.append("global tcp_listen")
            asm.append("global tcp_accept_ready")
            asm.append("global tcp_connect")
            asm.append("global tcp_write")
            asm.append("global tcp_read")
            asm.append("global tcp_close")
            asm.append("global tcp_state")
            asm.append("global net_poll")
            asm.append("global tcp_has_data")
            # Filesystem syscalls
            asm.append("global sys_link")
            asm.append("global sys_unlink")
            asm.append("global sys_symlink")
            asm.append("global sys_readlink")
            asm.append("global sys_flock")
            # Extended attribute syscalls
            asm.append("global sys_getxattr")
            asm.append("global sys_setxattr")
            asm.append("global sys_listxattr")
            asm.append("global sys_removexattr")
            # Unix domain socket functions
            asm.append("global unix_listen")
            asm.append("global unix_connect")
            asm.append("global unix_accept")
            asm.append("global unix_send")
            asm.append("global unix_recv")
            asm.append("global unix_close")
            asm.append("global unix_has_data")
            # RTC functions
            asm.append("global rtc_get_time")
            asm.append("global rtc_to_unix_timestamp")
            # VTNext graphics commands
            asm.append("global vtn_draw_text_cmd")
            asm.append("global vtn_draw_rect_cmd")
            asm.append("global vtn_draw_line_cmd")
            asm.append("global vtn_draw_circle_cmd")
            asm.append("global vtn_clear_cmd")
            asm.append("global vtn_draw_rrect_cmd")
            asm.append("global vtn_input_cmd")
            asm.append("global vtn_cursor_cmd")
            asm.append("global vtn_viewport_cmd")
            asm.append("global vtn_query_cmd")
            asm.append("global vtn_draw_ellipse_cmd")
            asm.append("global vtn_draw_poly_cmd")
            asm.append("")

        asm.extend(self.output)

        return '\n'.join(asm)

# Test the code generator
if __name__ == '__main__':
    from lexer import Lexer
    from parser import Parser

    code = """
proc add(a: int32, b: int32): int32 =
  return a + b

proc main() =
  var x: int32 = 10
  var y: int32 = 20
  var result: int32 = add(x, y)
"""

    lexer = Lexer(code)
    tokens = lexer.tokenize()

    parser = Parser(tokens)
    ast = parser.parse()

    codegen = X86CodeGen()
    asm_code = codegen.generate(ast)

    print(asm_code)
