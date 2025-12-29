#!/usr/bin/env python3
"""
Brainhair x86 Code Generator

Takes AST and generates x86 assembly (NASM syntax)
Phase 1: Generate assembly
Phase 2: Assemble to machine code
"""

from ast_nodes import *
from typing import Dict, List


def is_char_type(t) -> int:
    """Check if type is 'char'. Returns 1 if true, 0 otherwise."""
    if t is None:
        return 0
    if isinstance(t, Type):
        if t.name == 'char':
            return 1
    return 0


def is_str_type(t) -> int:
    """Check if type is 'str' or string pointer. Returns 1 if true, 0 otherwise."""
    if t is None:
        return 0
    if isinstance(t, Type):
        if t.name == 'str' or t.name == 'string':
            return 1
    if isinstance(t, PointerType):
        if isinstance(t.base_type, Type):
            if t.base_type.name == 'uint8' or t.base_type.name == 'char':
                return 1
    return 0


def get_type_name(t) -> str:
    """Get the type name from a Type or PointerType. Returns empty string if not available."""
    if t is None:
        return ""
    if isinstance(t, Type):
        return t.name
    if isinstance(t, PointerType):
        if isinstance(t.base_type, Type):
            return t.base_type.name
    return ""


def filter_non_self_params(params: List) -> List:
    """Filter out 'self' parameter from params list."""
    result: List = []
    for p in params:
        if p.name != 'self':
            result.append(p)
    return result


def get_field_names(fields: List) -> List[str]:
    """Get list of field names from field declarations."""
    result: List[str] = []
    for f in fields:
        result.append(f.name)
    return result


def get_param_defaults(params: List) -> List:
    """Get list of (name, default_value) tuples for params with defaults."""
    result: List = []
    for p in params:
        if p.default_value is not None:
            result.append((p.name, p.default_value))
    return result


def join_str_list(sep: str, parts: List[str]) -> str:
    """Join a list of strings with a separator."""
    if len(parts) == 0:
        return ""
    result: str = parts[0]
    i: int = 1
    while i < len(parts):
        result = result + sep + parts[i]
        i = i + 1
    return result


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

        # Method return types (TypeName_methodName -> return_type)
        self.method_return_types: Dict[str, Type] = {}

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

    def _print_string_expr(self, expr):
        """Helper: Print a string expression to stdout"""
        self.gen_expression(expr)
        self.emit("push eax")  # Save string pointer
        # Calculate string length
        self.emit("xor ecx, ecx")
        strlen_loop = self.new_label("print_strlen")
        strlen_done = self.new_label("print_strlen_done")
        self.emit_label(strlen_loop)
        self.emit("mov bl, [eax]")
        self.emit("test bl, bl")
        self.emit(f"jz {strlen_done}")
        self.emit("inc eax")
        self.emit("inc ecx")
        self.emit(f"jmp {strlen_loop}")
        self.emit_label(strlen_done)
        # sys_write(1, string, length)
        self.emit("pop ebx")  # String pointer
        self.emit("mov edx, ecx")  # Length
        self.emit("mov ecx, ebx")  # Buffer
        self.emit("mov ebx, 1")  # stdout
        self.emit("mov eax, 4")  # sys_write
        self.emit("int 0x80")

    def _print_char_expr(self, expr):
        """Helper: Print a single character to stdout"""
        self.gen_expression(expr)
        # Character value is in AL, store on stack and print 1 byte
        self.emit("sub esp, 4")
        self.emit("mov byte [esp], al")
        self.emit("mov ecx, esp")
        self.emit("mov edx, 1")
        self.emit("mov ebx, 1")  # stdout
        self.emit("mov eax, 4")  # sys_write
        self.emit("int 0x80")
        self.emit("add esp, 4")

    def _emit_print_int_eax(self):
        """Helper: Print integer in eax as decimal string"""
        # Handle negative numbers
        pos_label = self.new_label("print_int_pos")
        done_label = self.new_label("print_int_done")
        div_loop = self.new_label("print_int_div")
        out_loop = self.new_label("print_int_out")

        self.emit("test eax, eax")
        self.emit(f"jns {pos_label}")  # Jump if positive or zero
        # Print minus sign
        self.emit("push eax")
        self.emit("sub esp, 4")
        self.emit("mov byte [esp], 45")  # '-'
        self.emit("mov ecx, esp")
        self.emit("mov edx, 1")
        self.emit("mov ebx, 1")
        self.emit("mov eax, 4")
        self.emit("int 0x80")
        self.emit("add esp, 4")
        self.emit("pop eax")
        self.emit("neg eax")  # Make positive

        self.emit_label(pos_label)
        # Special case for 0
        self.emit("test eax, eax")
        self.emit(f"jnz {div_loop}")
        self.emit("sub esp, 4")
        self.emit("mov byte [esp], 48")  # '0'
        self.emit("mov ecx, esp")
        self.emit("mov edx, 1")
        self.emit("mov ebx, 1")
        self.emit("mov eax, 4")
        self.emit("int 0x80")
        self.emit("add esp, 4")
        self.emit(f"jmp {done_label}")

        # Convert to decimal digits (reversed on stack)
        self.emit_label(div_loop)
        self.emit("xor esi, esi")  # Digit count
        div_inner = self.new_label("print_int_div_inner")
        self.emit_label(div_inner)
        self.emit("test eax, eax")
        self.emit(f"jz {out_loop}")
        self.emit("xor edx, edx")
        self.emit("mov ebx, 10")
        self.emit("div ebx")  # eax = eax/10, edx = eax%10
        self.emit("add edx, 48")  # Convert to ASCII
        self.emit("push edx")
        self.emit("inc esi")
        self.emit(f"jmp {div_inner}")

        # Print digits
        self.emit_label(out_loop)
        self.emit("test esi, esi")
        self.emit(f"jz {done_label}")
        self.emit("mov ecx, esp")
        self.emit("mov edx, 1")
        self.emit("mov ebx, 1")
        self.emit("mov eax, 4")
        self.emit("int 0x80")
        self.emit("add esp, 4")
        self.emit("dec esi")
        self.emit(f"jmp {out_loop}")

        self.emit_label(done_label)

    def _print_fstring(self, fstring_value: str):
        """Helper: Parse and print an f-string with interpolation"""
        # Parse f-string without regex: find {expr} patterns
        i = 0
        n = len(fstring_value)
        while i < n:
            # Find next {
            brace_start = -1
            j = i
            while j < n:
                if fstring_value[j] == '{':
                    brace_start = j
                    break
                j = j + 1

            if brace_start == -1:
                # No more braces, print rest of string
                rest = fstring_value[i:]
                if rest:
                    label = self.add_string(rest)
                    self.emit(f"mov ecx, {label}")
                    self.emit(f"mov edx, {len(rest)}")
                    self.emit("mov ebx, 1")
                    self.emit("mov eax, 4")
                    self.emit("int 0x80")
                break

            # Print static text before brace
            if brace_start > i:
                static_part = fstring_value[i:brace_start]
                label = self.add_string(static_part)
                self.emit(f"mov ecx, {label}")
                self.emit(f"mov edx, {len(static_part)}")
                self.emit("mov ebx, 1")
                self.emit("mov eax, 4")
                self.emit("int 0x80")

            # Find closing brace
            brace_end = -1
            k = brace_start + 1
            while k < n:
                if fstring_value[k] == '}':
                    brace_end = k
                    break
                k = k + 1

            if brace_end == -1:
                # No closing brace, print rest as literal
                rest = fstring_value[brace_start:]
                label = self.add_string(rest)
                self.emit(f"mov ecx, {label}")
                self.emit(f"mov edx, {len(rest)}")
                self.emit("mov ebx, 1")
                self.emit("mov eax, 4")
                self.emit("int 0x80")
                break

            # Extract variable name
            var_name = fstring_value[brace_start+1:brace_end]
            # Strip whitespace manually
            while var_name and var_name[0] == ' ':
                var_name = var_name[1:]
            while var_name and var_name[-1] == ' ':
                var_name = var_name[:-1]

            # Print variable value
            # Check for field access (e.g., self.source_file)
            if '.' in var_name:
                # Parse field access: obj.field
                parts = var_name.split('.')
                obj_name = parts[0]
                if obj_name in self.local_vars:
                    # Get object pointer
                    offset = self.local_vars[obj_name]
                    if offset > 0:
                        self.emit(f"mov eax, [ebp+{offset}]")
                    else:
                        self.emit(f"mov eax, {self.ebp_addr(-offset)}")
                    # Follow field chain
                    for field in parts[1:]:
                        # Assume field is at offset based on field name hash
                        # For now, use struct layout if known
                        obj_type = self.type_table.get(obj_name)
                        if obj_type and hasattr(obj_type, 'name'):
                            type_name = obj_type.name
                            if type_name.startswith('ptr '):
                                type_name = type_name[4:]
                            if type_name in self.struct_types:
                                field_offset = self.get_field_offset(type_name, field)
                                self.emit(f"mov eax, [eax+{field_offset}]")
                            else:
                                # Simple offset based on field index
                                field_idx = 0
                                if field == 'source_file':
                                    field_idx = 0
                                elif field == 'output_file':
                                    field_idx = 4
                                self.emit(f"mov eax, [eax+{field_idx}]")
                        else:
                            # Default to first field
                            self.emit("mov eax, [eax]")
                    # Now eax has the string pointer, print it
                    self.emit("push eax")
                    self.emit("xor ecx, ecx")
                    strlen_loop = self.new_label("fstr_strlen")
                    strlen_done = self.new_label("fstr_strlen_done")
                    self.emit_label(strlen_loop)
                    self.emit("mov bl, [eax]")
                    self.emit("test bl, bl")
                    self.emit(f"jz {strlen_done}")
                    self.emit("inc eax")
                    self.emit("inc ecx")
                    self.emit(f"jmp {strlen_loop}")
                    self.emit_label(strlen_done)
                    self.emit("pop ebx")
                    self.emit("mov edx, ecx")
                    self.emit("mov ecx, ebx")
                    self.emit("mov ebx, 1")
                    self.emit("mov eax, 4")
                    self.emit("int 0x80")
                else:
                    # Unknown object - print placeholder
                    placeholder = "<" + var_name + ">"
                    label = self.add_string(placeholder)
                    self.emit(f"mov ecx, {label}")
                    self.emit(f"mov edx, {len(placeholder)}")
                    self.emit("mov ebx, 1")
                    self.emit("mov eax, 4")
                    self.emit("int 0x80")
            elif var_name in self.local_vars:
                offset = self.local_vars[var_name]
                # Check if variable is an integer type
                var_type = self.type_table.get(var_name)
                is_int = False
                if var_type and hasattr(var_type, 'name'):
                    type_name = var_type.name
                    if type_name in ('int32', 'int16', 'int8', 'uint32', 'uint16', 'uint8', 'i32', 'i16', 'i8', 'u32', 'u16', 'u8'):
                        is_int = True

                # Load variable value
                self.emit(f"mov eax, {self.ebp_addr(offset)}")

                if is_int:
                    # Print integer value
                    self._emit_print_int_eax()
                else:
                    # Print as string
                    self.emit("push eax")
                    self.emit("xor ecx, ecx")
                    strlen_loop = self.new_label("fstr_strlen")
                    strlen_done = self.new_label("fstr_strlen_done")
                    self.emit_label(strlen_loop)
                    self.emit("mov bl, [eax]")
                    self.emit("test bl, bl")
                    self.emit(f"jz {strlen_done}")
                    self.emit("inc eax")
                    self.emit("inc ecx")
                    self.emit(f"jmp {strlen_loop}")
                    self.emit_label(strlen_done)
                    self.emit("pop ebx")
                    self.emit("mov edx, ecx")
                    self.emit("mov ecx, ebx")
                    self.emit("mov ebx, 1")
                    self.emit("mov eax, 4")
                    self.emit("int 0x80")
            else:
                # Unknown variable - print placeholder
                placeholder = "<" + var_name + ">"
                label = self.add_string(placeholder)
                self.emit(f"mov ecx, {label}")
                self.emit(f"mov edx, {len(placeholder)}")
                self.emit("mov ebx, 1")
                self.emit("mov eax, 4")
                self.emit("int 0x80")

            i = brace_end + 1

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

    def _infer_assignment_type(self, expr: ASTNode) -> Type:
        # Infer type from assignment value for Python-style implicit declarations
        # Class instantiation: ClassName(...) -> PointerType(Type(ClassName))
        # In Python-style, instances are references (pointers) to the struct
        if isinstance(expr, CallExpr):
            # expr.func is typically a string (function name)
            func_name = expr.func
            if func_name and func_name[0].isupper():
                # This is a class constructor - returns pointer to struct
                return PointerType(Type(func_name))
        # Delegate to regular type inference
        return self._get_expr_type(expr)

    def _get_expr_type(self, expr: ASTNode) -> Type:
        # Determine the type of an expression
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
            arr_type = self._get_expr_type(expr.base)
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
            arr_type = self._get_expr_type(expr.target)
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
        if isinstance(expr, MethodCallExpr):
            # Get return type of method call
            obj_type = self._get_expr_type(expr.object)
            if obj_type:
                # Get class name from object type
                if isinstance(obj_type, PointerType):
                    class_name = obj_type.base_type.name
                else:
                    class_name = obj_type.name
                method_full_name = f"{class_name}_{expr.method_name}"
                return self.method_return_types.get(method_full_name)
        if isinstance(expr, CallExpr):
            # Class constructor call: ClassName(...) -> PointerType(Type(ClassName))
            func_name = expr.func
            if func_name and func_name[0].isupper() and func_name in self.struct_types:
                return PointerType(Type(func_name))
            # For other function calls, check if we have return type info
            # TODO: track function return types
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

        if isinstance(expr, AsmExpr):
            # Inline assembly - emit the instruction directly
            self.emit(expr.instruction)
            return "eax"

        if isinstance(expr, StringLiteral):
            # Add string to data section and load its address
            label = self.add_string(expr.value)
            # In kernel mode (32-bit), don't use RIP-relative addressing
            if self.kernel_mode:
                self.emit(f"lea eax, [{label}]")
            else:
                self.emit(f"mov eax, {label}")
            return "eax"

        if isinstance(expr, FStringLiteral):
            # Treat f-string as regular string for now (no interpolation)
            label = self.add_string(expr.value)
            if self.kernel_mode:
                self.emit(f"lea eax, [{label}]")
            else:
                self.emit(f"mov eax, {label}")
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
                addr = f"[{expr.name}]" if self.kernel_mode else f"[{expr.name}]"
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
            # Special handling for OR and AND - they need short-circuit evaluation
            # and return actual values, not booleans
            if expr.op == BinOp.OR:
                # Python OR: return left if truthy, else return right
                end_label = self.new_label("or_end")
                self.gen_expression(expr.left)
                self.emit("test eax, eax")
                self.emit(f"jnz {end_label}")  # If left is truthy, return it
                # Left was falsy, evaluate and return right
                self.gen_expression(expr.right)
                self.emit_label(end_label)
                return "eax"

            if expr.op == BinOp.AND:
                # Python AND: return left if falsy, else return right
                end_label = self.new_label("and_end")
                self.gen_expression(expr.left)
                self.emit("test eax, eax")
                self.emit(f"jz {end_label}")  # If left is falsy, return it
                # Left was truthy, evaluate and return right
                self.gen_expression(expr.right)
                self.emit_label(end_label)
                return "eax"

            # Special handling for char comparison with single-char string literal
            # e.g., ch == "'" should compare char values, not string pointers
            char_cmp_with_single_char_string = False
            if expr.op in (BinOp.EQ, BinOp.NEQ):
                left_type = self._get_expr_type(expr.left)
                right_type = self._get_expr_type(expr.right)
                # Check: left is char, right is single-char StringLiteral
                if is_char_type(left_type) == 1 and isinstance(expr.right, StringLiteral) and len(expr.right.value) == 1:
                    char_cmp_with_single_char_string = True
                    # Generate left as char
                    self.gen_expression(expr.left)
                    self.emit("push eax")
                    # Generate right as char value (ASCII code)
                    char_val = ord(expr.right.value[0])
                    self.emit(f"mov eax, {char_val}")
                    self.emit("mov ebx, eax")
                    self.emit("pop eax")
                # Check: right is char, left is single-char StringLiteral
                elif is_char_type(right_type) == 1 and isinstance(expr.left, StringLiteral) and len(expr.left.value) == 1:
                    char_cmp_with_single_char_string = True
                    # Generate left as char value (ASCII code)
                    char_val = ord(expr.left.value[0])
                    self.emit(f"mov eax, {char_val}")
                    self.emit("push eax")
                    # Generate right as char
                    self.gen_expression(expr.right)
                    self.emit("mov ebx, eax")
                    self.emit("pop eax")

            if not char_cmp_with_single_char_string:
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
                # Check if this is string concatenation
                left_type = self._get_expr_type(expr.left)
                right_type = self._get_expr_type(expr.right)
                is_string_concat = False
                right_is_char = False
                left_is_string = False

                # Check if left is a string (either StringLiteral or string type)
                if isinstance(expr.left, StringLiteral):
                    is_string_concat = True
                    left_is_string = True
                elif left_type:
                    # Check for Type('str') or Type('string') or PointerType(Type('uint8'))
                    if is_str_type(left_type) == 1:
                        is_string_concat = True
                        left_is_string = True

                # Check if right is a string literal
                if isinstance(expr.right, StringLiteral):
                    is_string_concat = True
                elif is_str_type(right_type) == 1:
                    is_string_concat = True

                # Check if right operand is a char (from string indexing like s[i])
                # If left is a string and right type is unknown, assume char for safety
                # NOTE: A char is Type('char') or Type('uint8'), NOT PointerType
                # PointerType(uint8) is a string, not a char
                if is_string_concat:
                    is_right_ptr: int = 0
                    if right_type and isinstance(right_type, PointerType):
                        is_right_ptr = 1
                    rt_name: str = get_type_name(right_type)
                    if (rt_name == 'uint8' or rt_name == 'char' or rt_name == 'int8') and is_right_ptr == 0:
                        right_is_char = True
                    elif left_is_string and right_type is None:
                        # If left is definitely a string and right type is unknown,
                        # check if the right operand looks like it could be a char
                        # (not a StringLiteral, and left is a string)
                        if not isinstance(expr.right, StringLiteral):
                            right_is_char = True

                if is_string_concat:
                    if right_is_char:
                        # String + char concatenation: call strcat_char(s, c)
                        # eax = s (string pointer), ebx = c (char value)
                        self.emit("push ebx")  # c (char)
                        self.emit("push eax")  # s (string)
                        self.emit("call strcat_char")
                        self.emit("add esp, 8")
                    else:
                        # String + string concatenation: call strcat_alloc(s1, s2)
                        # eax = s1 (left), ebx = s2 (right)
                        self.emit("push ebx")  # s2
                        self.emit("push eax")  # s1
                        self.emit("call strcat_alloc")
                        self.emit("add esp, 8")
                else:
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
                # Check if comparing strings (either operand is StringLiteral)
                # CharLiteral means char comparison, NOT string comparison
                is_char_cmp = isinstance(expr.left, CharLiteral) or isinstance(expr.right, CharLiteral)
                is_string_cmp = isinstance(expr.left, StringLiteral) or isinstance(expr.right, StringLiteral)
                if is_char_cmp:
                    is_string_cmp = False  # Char comparison, not string
                elif is_string_cmp:
                    # Check if comparing char variable with single-char string literal
                    # e.g., ch == "'" should be char comparison, not string comparison
                    left_type = self._get_expr_type(expr.left)
                    right_type = self._get_expr_type(expr.right)
                    # If left is char type and right is single-char StringLiteral
                    if is_char_type(left_type) == 1 and isinstance(expr.right, StringLiteral) and len(expr.right.value) == 1:
                        is_string_cmp = False
                        is_char_cmp = True
                    # If right is char type and left is single-char StringLiteral
                    elif is_char_type(right_type) == 1 and isinstance(expr.left, StringLiteral) and len(expr.left.value) == 1:
                        is_string_cmp = False
                        is_char_cmp = True
                if not is_string_cmp and not is_char_cmp:
                    # Also check if comparing against a variable that's likely a string (e.g., from argv)
                    # Only PointerType(uint8) is a string, raw 'uint8' or 'char' is a byte value
                    left_type = self._get_expr_type(expr.left)
                    right_type = self._get_expr_type(expr.right)
                    if is_str_type(left_type) == 1:
                        is_string_cmp = True
                    lt_name: str = get_type_name(left_type)
                    if lt_name == 'str' or lt_name == 'any':
                        is_string_cmp = True
                    if is_str_type(right_type) == 1:
                        is_string_cmp = True
                    rt_name2: str = get_type_name(right_type)
                    if rt_name2 == 'str' or rt_name2 == 'any':
                        is_string_cmp = True
                if is_string_cmp:
                    # Use strcmp for string comparison
                    self.emit("push ebx")  # s2
                    self.emit("push eax")  # s1
                    self.emit("call strcmp")
                    self.emit("add esp, 8")
                    self.emit("test eax, eax")
                    self.emit("setz al")  # EQ: strcmp returns 0 if equal
                    self.emit("movzx eax, al")
                else:
                    self.emit("cmp eax, ebx")
                    self.emit("sete al")
                    self.emit("movzx eax, al")
            elif expr.op == BinOp.NEQ:
                # Check if comparing strings
                # CharLiteral means char comparison, NOT string comparison
                is_char_cmp = isinstance(expr.left, CharLiteral) or isinstance(expr.right, CharLiteral)
                is_string_cmp = isinstance(expr.left, StringLiteral) or isinstance(expr.right, StringLiteral)
                if is_char_cmp:
                    is_string_cmp = False  # Char comparison, not string
                elif not is_string_cmp:
                    # Only PointerType(uint8) is a string, raw 'uint8' or 'char' is a byte value
                    left_type = self._get_expr_type(expr.left)
                    right_type = self._get_expr_type(expr.right)
                    if is_str_type(left_type) == 1:
                        is_string_cmp = True
                    lt_name2: str = get_type_name(left_type)
                    if lt_name2 == 'str' or lt_name2 == 'any':
                        is_string_cmp = True
                    if is_str_type(right_type) == 1:
                        is_string_cmp = True
                    rt_name3: str = get_type_name(right_type)
                    if rt_name3 == 'str' or rt_name3 == 'any':
                        is_string_cmp = True
                if is_string_cmp:
                    # Use strcmp for string comparison
                    self.emit("push ebx")  # s2
                    self.emit("push eax")  # s1
                    self.emit("call strcmp")
                    self.emit("add esp, 8")
                    self.emit("test eax, eax")
                    self.emit("setnz al")  # NEQ: strcmp returns nonzero if different
                    self.emit("movzx eax, al")
                else:
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
                elif type(arg_type).__name__ == 'ListType' or (hasattr(arg_type, 'name') and 'List' in str(arg_type.name)):
                    # List: len is at offset 4 in the list struct
                    self.gen_expression(arg)  # Get list pointer
                    self.emit("mov eax, [eax+4]")  # len is at offset 4
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

            # Python dataclass field() function - returns default value or 0
            if expr.func == "field":
                # field(default_factory=list) -> return 0 (null pointer)
                self.emit("xor eax, eax")
                return "eax"

            # Check for struct constructors (e.g., Token(...) or Compiler(...))
            if expr.func in self.struct_types:
                struct_name = expr.func
                struct_decl = self.struct_types[struct_name]
                struct_sz = self.struct_size(struct_name)

                # Check if this class has an __init__ method
                init_func = f"{struct_name}___init__"  # Compiler___init__
                if init_func in self.func_names:
                    # Python-style class: ALWAYS heap-allocate for reference semantics
                    # This ensures the object survives function returns
                    self.emit(f"; Allocate {struct_name} instance on heap ({struct_sz} bytes)")
                    self.emit(f"push {struct_sz}")
                    self.emit("call alloc")
                    self.emit("add esp, 4")
                    # Save heap pointer
                    self.emit("push eax")

                    # Push args in reverse order for __init__
                    for arg in reversed(expr.args):
                        self.gen_expression(arg)
                        self.emit("push eax")
                    # Push self pointer (from saved heap pointer)
                    self.emit(f"mov eax, [esp+{len(expr.args) * 4}]")
                    self.emit("push eax")
                    # Call __init__
                    self.emit(f"call {init_func}")
                    # Clean up stack (self + args)
                    self.emit(f"add esp, {4 + len(expr.args) * 4}")
                    # Restore heap pointer as return value
                    self.emit("pop eax")
                else:
                    # Brainhair-style struct: allocate on stack
                    self.stack_offset += struct_sz
                    struct_offset = -self.stack_offset

                    fields = get_field_names(struct_decl.fields)
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

            # Handle open() - open file and return file descriptor
            if expr.func == "open" and len(expr.args) >= 1:
                # open(path, mode) -> fd using sys_open
                # mode 'r' = O_RDONLY = 0, 'w' = O_WRONLY|O_CREAT|O_TRUNC = 577
                self.gen_expression(expr.args[0])  # path
                self.emit("push eax")  # save path
                # Determine flags based on mode
                flags = 0  # O_RDONLY by default
                if len(expr.args) >= 2 and isinstance(expr.args[1], StringLiteral):
                    mode = expr.args[1].value
                    if 'w' in mode:
                        flags = 577  # O_WRONLY | O_CREAT | O_TRUNC
                    elif 'a' in mode:
                        flags = 1089  # O_WRONLY | O_CREAT | O_APPEND
                self.emit("pop ebx")  # path
                self.emit(f"mov ecx, {flags}")  # flags
                self.emit("mov edx, 420")  # mode 0644
                self.emit("mov eax, 5")  # sys_open
                self.emit("int 0x80")
                # eax now contains fd (or negative error)
                return "eax"

            # Handle print() - output string to stdout with newline
            if expr.func == "print":
                if expr.args:
                    arg = expr.args[0]
                    # Check for f-string with interpolation
                    if isinstance(arg, FStringLiteral):
                        self._print_fstring(arg.value)
                    elif isinstance(arg, CharLiteral):
                        # Print single char literal
                        self._print_char_expr(arg)
                    else:
                        # Check if argument is char type
                        arg_type = self._get_expr_type(arg)
                        if arg_type and hasattr(arg_type, 'name') and arg_type.name == 'char':
                            self._print_char_expr(arg)
                        else:
                            # Regular string - print it
                            self._print_string_expr(arg)
                # Print newline
                newline_label = self.add_string("\n")
                self.emit(f"mov ecx, {newline_label}")
                self.emit("mov edx, 1")
                self.emit("mov ebx, 1")
                self.emit("mov eax, 4")
                self.emit("int 0x80")
                self.emit("xor eax, eax")
                return "eax"

            # Handle hasattr(obj, 'attr_name') - check if object has named attribute
            if expr.func == 'hasattr' and len(expr.args) == 2:
                # Get the object's type
                obj_type = self._get_expr_type(expr.args[0])
                # Get the attribute name (should be a string literal)
                attr_name = None
                if isinstance(expr.args[1], StringLiteral):
                    attr_name = expr.args[1].value

                # Check if the type has this attribute
                has_attr = False
                if obj_type and attr_name:
                    type_name = obj_type.name
                    if type_name and type_name in self.struct_types:
                        struct_decl = self.struct_types[type_name]
                        for field in struct_decl.fields:
                            if field.name == attr_name:
                                has_attr = True
                                break
                    # For unknown types, assume True (duck typing)
                    elif type_name is None or type_name == 'any':
                        has_attr = True
                elif attr_name:
                    # Unknown object type - assume True for duck typing
                    has_attr = True

                # Return 1 (True) or 0 (False)
                self.emit(f"mov eax, {1 if has_attr else 0}")
                return "eax"

            # Handle Python builtins that don't exist in compiled code
            python_builtins = ('set', 'dict', 'list', 'tuple', 'frozenset', 'types', 'type',
                               'isinstance', 'issubclass', 'getattr', 'setattr',
                               'iter', 'next', 'enumerate', 'zip', 'map', 'filter', 'sorted',
                               'reversed', 'all', 'any', 'sum', 'min', 'max', 'abs', 'int',
                               'str', 'bool', 'float', 'chr', 'ord', 'hex', 'bin', 'oct',
                               'range', 'input', 'open', 'id', 'hash', 'repr',
                               # Python class constructors (dataclasses, etc.)
                               'LLVMIntType', 'LLVMFloatType', 'LLVMPointerType', 'LLVMArrayType',
                               'LLVMVoidType', 'LLVMStructType', 'LLVMTypeMapper', 'LLVMType',
                               'TypeInfo', 'Span', 'Symbol', 'VariableSymbol', 'ParamSymbol',
                               'FunctionSymbol', 'TypeSymbol', 'Scope', 'SymbolTable',
                               'SymbolError', 'DuplicateSymbolError', 'UndefinedSymbolError')
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

            # Handle string methods ONLY for string types (check type first)
            # Python strings use methods like .replace(), .lower() etc
            string_methods = ('lower', 'upper', 'strip', 'lstrip', 'rstrip', 'split', 'join',
                            'replace', 'startswith', 'endswith', 'find', 'rfind', 'index',
                            'rindex', 'count', 'format', 'center', 'ljust', 'rjust', 'zfill',
                            'capitalize', 'title', 'swapcase', 'encode', 'decode')
            if expr.method_name in string_methods and type_name in ('str', 'string', 'Unknown', ''):
                # String methods - evaluate receiver and return it (no-op stub)
                self.gen_expression(expr.object)
                return "eax"

            # Handle file I/O methods: read(), write(), close()
            if expr.method_name == 'read':
                # f.read() - read entire file using sys_read
                # fd is in the receiver (treated as integer)
                self.gen_expression(expr.object)  # Get fd
                self.emit("push eax")  # save fd
                # First, get file size using sys_lseek to end
                self.emit("mov ebx, eax")  # fd
                self.emit("xor ecx, ecx")  # offset 0
                self.emit("mov edx, 2")  # SEEK_END
                self.emit("mov eax, 19")  # sys_lseek
                self.emit("int 0x80")
                self.emit("push eax")  # save size
                # Seek back to start
                self.emit("mov ebx, [esp+4]")  # fd
                self.emit("xor ecx, ecx")  # offset 0
                self.emit("xor edx, edx")  # SEEK_SET
                self.emit("mov eax, 19")  # sys_lseek
                self.emit("int 0x80")
                # Allocate buffer on heap using sys_brk
                self.emit("xor ebx, ebx")  # get current brk
                self.emit("mov eax, 45")  # sys_brk
                self.emit("int 0x80")
                self.emit("push eax")  # save buffer start
                self.emit("mov ebx, eax")
                self.emit("add ebx, [esp+4]")  # size
                self.emit("add ebx, 1")  # null terminator
                self.emit("mov eax, 45")  # sys_brk
                self.emit("int 0x80")
                # Now read the file: sys_read(fd, buf, size)
                self.emit("mov edx, [esp+4]")  # size
                self.emit("mov ecx, [esp]")  # buffer
                self.emit("mov ebx, [esp+8]")  # fd
                self.emit("mov eax, 3")  # sys_read
                self.emit("int 0x80")
                # Null terminate
                self.emit("mov ecx, [esp]")  # buffer
                self.emit("add ecx, eax")  # end of data
                self.emit("mov byte [ecx], 0")
                # Return buffer pointer
                self.emit("mov eax, [esp]")
                self.emit("add esp, 12")  # clean up stack
                return "eax"

            if expr.method_name == 'write':
                # f.write(data) - write string to file using sys_write
                self.gen_expression(expr.args[0])  # data string
                self.emit("push eax")  # save string ptr
                self.gen_expression(expr.object)  # Get fd
                self.emit("mov ebx, eax")  # fd
                self.emit("pop ecx")  # buffer
                self.emit("push ecx")  # save for strlen
                # Get string length
                self.emit("xor edx, edx")
                write_strlen = self.new_label("write_strlen")
                self.emit(f"{write_strlen}:")
                self.emit("cmp byte [ecx+edx], 0")
                self.emit(f"je .write_done_len_{id(expr)}")
                self.emit("inc edx")
                self.emit(f"jmp {write_strlen}")
                self.emit(f".write_done_len_{id(expr)}:")
                # sys_write(fd, buf, len)
                self.emit("pop ecx")  # buffer
                self.emit("mov eax, 4")  # sys_write
                self.emit("int 0x80")
                return "eax"

            if expr.method_name == 'close':
                # f.close() - close file using sys_close
                self.gen_expression(expr.object)  # Get fd
                self.emit("mov ebx, eax")  # fd
                self.emit("mov eax, 6")  # sys_close
                self.emit("int 0x80")
                return "eax"

            # Handle list.append() on any type - but NOT if class has its own append method
            if expr.method_name == 'append' and len(expr.args) == 1:
                # Check if this is a user-defined class with an append method
                obj_type = self._get_expr_type(expr.object)
                class_name = None
                if obj_type:
                    if isinstance(obj_type, PointerType):
                        class_name = obj_type.base_type.name
                    else:
                        class_name = obj_type.name
                # If it's a known class with an append method, don't use fallback
                append_method = f"{class_name}_append" if class_name else None
                if not (append_method and append_method in self.func_names):
                    # Use list fallback
                    self.gen_expression(expr.args[0])  # Get value
                    self.emit("push eax")
                    self.gen_expression(expr.object)  # Get list ptr
                    self.emit("push eax")
                    self.emit("call list_append_i32")
                    self.emit("add esp, 8")
                    return "eax"

            # Handle lookup() method on scope-like objects (symbol tables, etc.)
            if expr.method_name == 'lookup':
                # Just evaluate receiver and return null for now
                self.gen_expression(expr.object)
                self.emit("xor eax, eax")  # Return null
                return "eax"

            # Handle Dict methods (both 'Dict' and 'dict' lowercase)
            if type_name.startswith("Dict") or type_name == "dict":
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
                elif expr.method_name in ('keys', 'values', 'items'):
                    # dict.keys/values/items() - stub: just return empty list for now
                    self.gen_expression(expr.object)
                    self.emit("xor eax, eax")  # Return empty/null list
                    return "eax"

            # Handle common methods on unknown or dynamic types (Python-style code)
            needs_fallback = type_name == "Unknown" or type_name == "any" or type_name.startswith("Set")
            if needs_fallback:
                # For 'any' type, generate actual list/dict operations assuming List/Dict
                if expr.method_name == 'append' and len(expr.args) == 1:
                    # Assume it's a List - call list_append_i32(obj, value)
                    self.gen_expression(expr.args[0])  # Get value
                    self.emit("push eax")
                    self.gen_expression(expr.object)  # Get list ptr
                    self.emit("push eax")
                    self.emit("call list_append_i32")
                    self.emit("add esp, 8")
                    return "eax"
                elif expr.method_name == 'pop' and len(expr.args) == 0:
                    # Assume it's a List - call list_pop_i32(obj)
                    self.gen_expression(expr.object)
                    self.emit("push eax")
                    self.emit("call list_pop_i32")
                    self.emit("add esp, 4")
                    return "eax"
                elif expr.method_name == 'clear':
                    # Assume it's a List - call list_clear(obj)
                    self.gen_expression(expr.object)
                    self.emit("push eax")
                    self.emit("call list_clear")
                    self.emit("add esp, 4")
                    self.emit("xor eax, eax")
                    return "eax"
                elif expr.method_name == 'get':
                    # Assume it's a Dict - call dict_get or dict_get_default
                    if len(expr.args) >= 2:
                        self.gen_expression(expr.args[1])  # default
                        self.emit("push eax")
                        self.gen_expression(expr.args[0])  # key
                        self.emit("push eax")
                        self.gen_expression(expr.object)
                        self.emit("push eax")
                        self.emit("call dict_get_default")
                        self.emit("add esp, 12")
                    elif len(expr.args) == 1:
                        self.gen_expression(expr.args[0])  # key
                        self.emit("push eax")
                        self.gen_expression(expr.object)
                        self.emit("push eax")
                        self.emit("call dict_get")
                        self.emit("add esp, 8")
                    else:
                        self.emit("xor eax, eax")
                    return "eax"
                elif expr.method_name in ('extend', 'remove', 'insert', 'add', 'keys', 'values', 'items', 'update'):
                    # Other collection methods - evaluate args and return None (stub)
                    for arg in expr.args:
                        self.gen_expression(arg)
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

            # Handle string methods on 'str' type (no-op: just return the string)
            if type_name == "str" and expr.method_name in ('lower', 'upper', 'strip', 'lstrip', 'rstrip', 'split', 'join', 'replace', 'startswith', 'endswith', 'find', 'rfind', 'index', 'rindex', 'count', 'format'):
                self.gen_expression(expr.object)
                return "eax"

            mangled_name = self.sanitize_label(f"{type_name}_{expr.method_name}")

            # Check for default arguments - fill in missing args with defaults
            actual_args = list(expr.args)
            if mangled_name in self.func_param_defaults:
                params = self.func_param_defaults[mangled_name]
                # params includes 'self', so skip first param when counting
                non_self_params = filter_non_self_params(params)
                num_provided = len(actual_args)
                num_expected = len(non_self_params)

                # If fewer args provided than expected, add defaults
                if num_provided < num_expected:
                    for i in range(num_provided, num_expected):
                        param = non_self_params[i]
                        if param.default_value is not None:
                            actual_args.append(param.default_value)
                        else:
                            # No default - use 0 as fallback
                            actual_args.append(IntLiteral(0))

            # Push explicit arguments in reverse order
            for arg in reversed(actual_args):
                self.gen_expression(arg)
                self.emit("push eax")

            # Push the receiver object's address as first (implicit) argument
            # If object is already a pointer, just use the value; otherwise take address
            is_class_type = type_name in self.struct_types

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
            elif is_class_type:
                # Class type: variable contains a pointer, load it
                # (class instances are heap-allocated with reference semantics)
                self.gen_expression(expr.object)
            else:
                # Need to take address of the object
                self.gen_lvalue_address(expr.object)
            self.emit("push eax")

            # Call the mangled method function
            self.emit(f"call {mangled_name}")

            # Clean up stack (explicit args + implicit self)
            total_args = len(actual_args) + 1
            self.emit(f"add esp, {total_args * 4}")

            return "eax"

        if isinstance(expr, CastExpr):
            # Check if we're casting a function name to a pointer (function pointer)
            if isinstance(expr.expr, Identifier):
                func_name = expr.expr.name
                # Check if this is a function name (not a variable)
                if hasattr(self, 'func_names') and func_name in self.func_names:
                    # Use LEA to get the address of the function, not MOV
                    addr = f"[{func_name}]" if self.kernel_mode else f"[{func_name}]"
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
            if isinstance(expr.base, CastExpr):
                # Type comes from cast expression
                pointer_type = expr.base.target_type
            elif isinstance(expr.base, Identifier):
                # Look up type from type table
                if expr.base.name in self.type_table:
                    pointer_type = self.type_table[expr.base.name]

            # Calculate element size
            element_size = 1  # Default to 1 byte
            if pointer_type and isinstance(pointer_type, PointerType):
                element_size = self.type_size(pointer_type.base_type)
            elif pointer_type and isinstance(pointer_type, SliceType):
                element_size = self.type_size(pointer_type.element_type)
            elif pointer_type and isinstance(pointer_type, ArrayType):
                element_size = self.type_size(pointer_type.element_type)

            # Generate array base address
            if isinstance(expr.base, CastExpr):
                # Generate the cast expression to get the pointer value
                self.gen_expression(expr.base)
            elif isinstance(expr.base, FieldAccessExpr):
                # Field access like self.source - need to preserve index in ebx
                self.emit("push ebx")  # Save index
                self.gen_expression(expr.base)  # Load field value into eax
                self.emit("pop ebx")  # Restore index
            elif isinstance(expr.base, Identifier):
                if expr.base.name in self.local_vars:
                    offset = self.local_vars[expr.base.name]
                    var_type = self.type_table.get(expr.base.name)
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
                    var_type = self.type_table.get(expr.base.name)
                    addr = f"[{expr.base.name}]"
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
                self.gen_expression(expr.base)  # Evaluate to get pointer
                self.emit("pop ebx")  # Restore index

            # For List types, dereference list struct to get data pointer first
            base_type = self._get_expr_type(expr.base)
            is_list: int = 0
            if base_type:
                if type(base_type).__name__ == 'ListType':
                    is_list = 1
                bt_name: str = get_type_name(base_type)
                if 'List' in bt_name:
                    is_list = 1
            if is_list == 1:
                # eax has list struct pointer, need data pointer at offset 0
                self.emit("mov eax, [eax]")  # eax = data pointer
                element_size = 4  # List elements are 4 bytes

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
            arr_type = self._get_expr_type(expr.target)
            element_size = 4  # Default
            if isinstance(arr_type, ArrayType):
                element_size = self.type_size(arr_type.element_type)
            elif isinstance(arr_type, PointerType):
                element_size = self.type_size(arr_type.base_type)
            elif arr_type and arr_type.name == 'str':
                element_size = 1  # String chars are 1 byte each

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
            if isinstance(expr.target, Identifier):
                if expr.target.name in self.local_vars:
                    offset = self.local_vars[expr.target.name]
                    var_type = self.type_table.get(expr.target.name)
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
                    addr = f"[{expr.target.name}]"
                    self.emit(f"lea eax, {addr}")
            else:
                self.emit("push ecx")  # Save scaled start
                self.gen_expression(expr.target)
                self.emit("pop ecx")

            # ptr = base + scaled_start
            self.emit("add eax, ecx")  # ptr in eax

            # Restore len to edx
            self.emit("pop edx")  # len in edx

            # For string slices, allocate a new null-terminated string
            if arr_type and arr_type.name == 'str':
                # eax = source ptr, edx = length
                # Stack layout: [source_ptr] [length]
                self.emit("push eax")  # Save source ptr [esp]
                self.emit("push edx")  # Save length [esp]

                # Allocate len+1 bytes
                self.emit("lea eax, [edx+1]")  # len+1
                self.emit("push eax")
                self.emit("call alloc")
                self.emit("add esp, 4")
                # eax = dest buffer

                self.emit("mov edi, eax")  # edi = dest start (save for return)
                self.emit("pop ecx")       # ecx = length
                self.emit("pop esi")       # esi = source

                # Copy loop: copy ecx bytes from esi to eax
                slice_copy = self.new_label("slice_copy")
                slice_done = self.new_label("slice_done")
                self.emit("test ecx, ecx")
                self.emit(f"jz {slice_done}")
                self.emit_label(slice_copy)
                self.emit("mov bl, [esi]")
                self.emit("mov [eax], bl")
                self.emit("inc esi")
                self.emit("inc eax")
                self.emit("dec ecx")
                self.emit(f"jnz {slice_copy}")
                self.emit_label(slice_done)

                # Null terminate
                self.emit("mov byte [eax], 0")

                # Return dest start
                self.emit("mov eax, edi")
                return "eax"

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
                    addr = f"[{expr.expr.name}]"
                    self.emit(f"lea eax, {addr}")
            elif isinstance(expr.expr, IndexExpr):
                # Address of array element: addr(array[index])
                # This is like IndexExpr but without the final dereference

                # Generate index
                self.gen_expression(expr.expr.index)
                self.emit("mov ebx, eax")  # Index in EBX

                # Determine pointer type to calculate element size
                pointer_type = None
                if isinstance(expr.expr.base, CastExpr):
                    pointer_type = expr.expr.base.target_type
                elif isinstance(expr.expr.base, Identifier):
                    if expr.expr.base.name in self.type_table:
                        pointer_type = self.type_table[expr.expr.base.name]

                # Calculate element size
                element_size = 1  # Default to 1 byte
                if pointer_type:
                    if isinstance(pointer_type, PointerType):
                        element_size = self.type_size(pointer_type.base_type)
                    elif isinstance(pointer_type, ArrayType):
                        element_size = self.type_size(pointer_type.element_type)

                # Generate array base address
                if isinstance(expr.expr.base, CastExpr):
                    self.gen_expression(expr.expr.base)
                elif isinstance(expr.expr.base, Identifier):
                    if expr.expr.base.name in self.local_vars:
                        offset = self.local_vars[expr.expr.base.name]
                        var_type = self.type_table.get(expr.expr.base.name)
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
                        var_type = self.type_table.get(expr.expr.base.name)
                        addr = f"[{expr.expr.base.name}]"
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
            # Array/List literal: [] or [1, 2, 3]
            # For dynamic lists (like Python), use list structure (16 bytes)
            # List structure: [data_ptr, len, cap, elem_size]

            initial_cap = max(len(expr.elements), 4)

            # Allocate 16 bytes on HEAP for list header
            self.emit("push 16")
            self.emit("call alloc")
            self.emit("add esp, 4")
            self.emit("push eax")  # Save list header ptr

            # Allocate data array: cap * 4 bytes
            self.emit(f"push {initial_cap * 4}")
            self.emit("call alloc")
            self.emit("add esp, 4")
            self.emit("mov ebx, eax")  # ebx = data ptr
            self.emit("pop eax")       # eax = list header ptr

            # Save list header in a local variable
            self.stack_offset += 4
            list_var_offset = -self.stack_offset
            list_var_addr = self.ebp_addr(list_var_offset)
            self.emit(f"mov {list_var_addr}, eax")

            # Initialize list header: [data_ptr, len, cap, elem_size]
            self.emit("mov [eax], ebx")      # list[0] = data_ptr
            self.emit("mov dword [eax+4], 0")   # list[1] = len = 0
            self.emit(f"mov dword [eax+8], {initial_cap}")   # list[2] = cap
            self.emit("mov dword [eax+12], 4")  # list[3] = elem_size = 4

            # Append each element using list_append_i32
            for elem in expr.elements:
                self.gen_expression(elem)
                self.emit("push eax")  # value
                self.emit(f"push dword {list_var_addr}")  # list pointer
                self.emit("call list_append_i32")
                self.emit("add esp, 8")

            # Return pointer to list
            self.emit(f"mov eax, {list_var_addr}")
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
                        addr = f"[{expr.object.name}]"
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
                # Check if this is a class type (reference semantics - var holds pointer)
                # In Python/Brainhair, class instances are always heap-allocated
                is_class_type = struct_name in self.struct_types

                if isinstance(expr.object, Identifier):
                    if expr.object.name in self.local_vars:
                        offset = self.local_vars[expr.object.name]
                        if is_class_type:
                            # Class type: variable contains a pointer, load it
                            if offset > 0:
                                self.emit(f"mov eax, [ebp+{offset}]")
                            else:
                                self.emit(f"mov eax, {self.ebp_addr(offset)}")
                        else:
                            # Plain struct: get address of struct on stack
                            if offset > 0:
                                self.emit(f"lea eax, [ebp+{offset}]")
                            else:
                                self.emit(f"lea eax, {self.ebp_addr(offset)}")
                    else:
                        addr = f"[{expr.object.name}]"
                        if is_class_type:
                            self.emit(f"mov eax, {addr}")
                        else:
                            self.emit(f"lea eax, {addr}")
                else:
                    # For complex expressions, generate and assume it returns struct address/pointer
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

                # Clean up bindings (set to None for Brainhair compatibility)
                for binding in arm.pattern.bindings:
                    if binding in self.local_vars:
                        self.local_vars[binding] = None

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
            self.gen_expression(expr.base)
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
                    # Check if this is a List type (dynamic) or Array type (fixed)
                    is_list_type = False
                    if stmt.var_type:
                        # Check for ListType class
                        if type(stmt.var_type).__name__ == 'ListType':
                            is_list_type = True
                        # Also check for 'List' in the name (for types like List[int])
                        elif hasattr(stmt.var_type, 'name') and 'List' in str(stmt.var_type.name):
                            is_list_type = True

                    if is_list_type:
                        # Dynamic list - use heap allocation via gen_expression
                        self.gen_expression(stmt.value)
                        addr = self.ebp_addr(var_offset) if var_offset < 0 else f"[ebp+{var_offset}]"
                        self.emit(f"mov {addr}, eax")
                    else:
                        # Fixed-size array - initialize elements directly into stack space
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
                elif isinstance(stmt.value, CallExpr) and stmt.value.func in self.struct_types:
                    # Struct/class constructor: MyClass(args...)
                    # For Python semantics: allocate on heap, store pointer in variable
                    struct_name = stmt.value.func
                    struct_sz = self.struct_size(struct_name)
                    init_func = f"{struct_name}___init__"

                    # Allocate heap memory for the class instance
                    self.emit(f"; Allocate {struct_name} instance ({struct_sz} bytes)")
                    self.emit(f"push {struct_sz}")
                    self.emit("call alloc")
                    self.emit("add esp, 4")
                    # eax now has pointer to heap-allocated struct

                    # Store heap pointer in variable
                    var_addr = self.ebp_addr(var_offset)
                    self.emit(f"mov {var_addr}, eax")

                    if init_func in self.func_names:
                        # Check for default arguments - fill in missing args with defaults
                        actual_args = list(stmt.value.args)
                        if init_func in self.func_param_defaults:
                            params = self.func_param_defaults[init_func]
                            # params includes 'self', so skip first param when counting
                            non_self_params = filter_non_self_params(params)
                            num_provided = len(actual_args)
                            num_expected = len(non_self_params)

                            # If fewer args provided than expected, add defaults
                            if num_provided < num_expected:
                                for i in range(num_provided, num_expected):
                                    param = non_self_params[i]
                                    if param.default_value is not None:
                                        actual_args.append(param.default_value)
                                    else:
                                        # No default - use 0 as fallback
                                        actual_args.append(IntLiteral(0))

                        # Push args in reverse order
                        for arg in reversed(actual_args):
                            self.gen_expression(arg)
                            self.emit("push eax")
                        # Push pointer to heap-allocated struct (load from variable)
                        self.emit(f"mov eax, {var_addr}")
                        self.emit("push eax")
                        # Call __init__
                        self.emit(f"call {init_func}")
                        self.emit(f"add esp, {4 + len(actual_args) * 4}")
                    else:
                        # No __init__ - initialize fields from positional args
                        struct_decl = self.struct_types[struct_name]
                        fields = get_field_names(struct_decl.fields)
                        for i, arg in enumerate(stmt.value.args):
                            if i < len(fields):
                                field_name = fields[i]
                                field_offset = self.get_field_offset(struct_name, field_name)
                                self.gen_expression(arg)
                                self.emit("push eax")  # Save field value
                                self.emit(f"mov ebx, {var_addr}")  # Load struct pointer
                                self.emit("pop eax")  # Restore field value
                                if field_offset > 0:
                                    self.emit(f"mov [ebx+{field_offset}], eax")
                                else:
                                    self.emit("mov [ebx], eax")
                else:
                    self.gen_expression(stmt.value)
                    # Store with appropriate size
                    # Use var_offset (not stack_offset) since gen_expression may allocate more stack
                    var_addr = self.ebp_addr(var_offset)
                    if size == 1:
                        self.emit(f"mov byte {var_addr}, al")
                    elif size == 2:
                        self.emit(f"mov word {var_addr}, ax")
                    else:
                        self.emit(f"mov {var_addr}, eax")

        elif isinstance(stmt, Assignment):
            # For Python-style code, infer and track type from value expression
            # This must be done BEFORE generating the value, so we know the type
            if isinstance(stmt.target, Identifier) and stmt.target.name not in self.type_table:
                inferred_type = self._infer_assignment_type(stmt.value)
                if inferred_type:
                    self.type_table[stmt.target.name] = inferred_type

            # Special case: assigning single-char string to char variable
            # e.g., ch = "'" should store ASCII 39, not string pointer
            is_single_char_assign: int = 0
            if isinstance(stmt.target, Identifier) and isinstance(stmt.value, StringLiteral):
                if len(stmt.value.value) == 1:
                    is_single_char_assign = 1
            if is_single_char_assign == 1:
                var_type = self.type_table.get(stmt.target.name)
                if is_char_type(var_type) == 1:
                    # Generate char value instead of string pointer
                    char_val = ord(stmt.value.value[0])
                    self.emit(f"mov eax, {char_val}")
                    # Store value - get var info
                    if stmt.target.name in self.local_vars:
                        offset = self.local_vars[stmt.target.name]
                        addr = self.ebp_addr(offset)
                        self.emit(f"mov byte {addr}, al")
                    else:
                        addr = f"[{stmt.target.name}]"
                        self.emit(f"mov byte {addr}, al")
                    return  # Done with this statement

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
                    if stmt.target.name not in self.global_var_names:
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
                    addr = f"[{stmt.target.name}]"
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
                if isinstance(stmt.target.base, CastExpr):
                    # Type comes from cast expression
                    pointer_type = stmt.target.base.target_type
                elif isinstance(stmt.target.base, Identifier):
                    # Look up type from type table
                    if stmt.target.base.name in self.type_table:
                        pointer_type = self.type_table[stmt.target.base.name]

                # Calculate element size
                element_size = 1  # Default to 1 byte
                if pointer_type:
                    if isinstance(pointer_type, PointerType):
                        element_size = self.type_size(pointer_type.base_type)
                    elif isinstance(pointer_type, ArrayType):
                        element_size = self.type_size(pointer_type.element_type)

                # Generate array base address
                if isinstance(stmt.target.base, CastExpr):
                    # Generate the cast expression to get the pointer value
                    self.gen_expression(stmt.target.base)
                elif isinstance(stmt.target.base, Identifier):
                    if stmt.target.base.name in self.local_vars:
                        offset = self.local_vars[stmt.target.base.name]
                        var_type = self.type_table.get(stmt.target.base.name)
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
                        var_type = self.type_table.get(stmt.target.base.name)
                        addr = f"[{stmt.target.base.name}]"
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
                            addr = f"[{stmt.target.object.name}]"
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
                            addr = f"[{stmt.target.object.name}]"
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

            # Handle elif blocks by creating chain of labels
            elif_labels = []
            elif_blocks = getattr(stmt, 'elif_blocks', None) or []
            for i in range(len(elif_blocks)):
                elif_labels.append(self.new_label("elif"))
            else_label = self.new_label("else")

            # Generate main if condition
            self.gen_expression(stmt.condition)
            self.emit("test eax, eax")
            if elif_labels:
                self.emit(f"jz {elif_labels[0]}")
            else:
                self.emit(f"jz {else_label}")

            # Then block
            for s in stmt.then_block:
                self.gen_statement(s)
            self.emit(f"jmp {end_label}")

            # Generate elif blocks
            for i, (elif_cond, elif_body) in enumerate(elif_blocks):
                self.emit_label(elif_labels[i])
                self.gen_expression(elif_cond)
                self.emit("test eax, eax")
                if i + 1 < len(elif_blocks):
                    self.emit(f"jz {elif_labels[i + 1]}")
                else:
                    self.emit(f"jz {else_label}")
                for s in elif_body:
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
                    addr = f"[{stmt.iterable.name}]"
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

        elif isinstance(stmt, AsmExpr):
            # Inline assembly statement - emit directly
            self.emit(stmt.instruction)

        elif isinstance(stmt, DiscardStmt):
            pass  # No code needed

        elif isinstance(stmt, DeferStmt):
            # Add to defer stack - will be executed at function return
            self.defer_stack.append(stmt.stmt)

        elif isinstance(stmt, TryExceptStmt):
            # For Brainhair, execute the try body (primary Brainhair code)
            # The except body is fallback which we skip
            for s in stmt.try_body:
                self.gen_statement(s)
            # Also execute finally body if present
            for s in stmt.finally_body:
                self.gen_statement(s)

        elif isinstance(stmt, WithStmt):
            # With statement: evaluate context, optionally bind to var, execute body
            # Note: This doesn't properly call __enter__/__exit__ context manager methods
            self.gen_expression(stmt.context)
            if stmt.var_name:
                # Allocate stack space and store the context value
                self.stack_offset += 4
                self.local_vars[stmt.var_name] = -self.stack_offset  # negative offset for local vars
                self.emit(f"mov [ebp-{self.stack_offset}], eax")
            # Execute body
            for s in stmt.body:
                self.gen_statement(s)

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

        # Initialize default return value for all functions (Python auto-return None)
        # This ensures functions return 0/null if no explicit return is executed
        if proc.return_type:
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

        # Initialize default return value for all methods (Python auto-return None)
        if method.return_type:
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
        self.func_param_defaults = {}  # Track function parameter defaults: func_name -> [(param_name, default_value), ...]

        # Use a stack to process declarations including those inside TryExceptStmt
        decl_stack = list(program.declarations)
        while decl_stack:
            decl = decl_stack.pop(0)
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
                # Track parameter defaults
                if decl.params:
                    defaults = get_param_defaults(decl.params)
                    if defaults:
                        self.func_param_defaults[decl.name] = decl.params
            elif isinstance(decl, MethodDecl):
                # Track method names (ClassName_methodName) - same format as gen_method
                # receiver_type can be PointerType(base_type=Type(name='ClassName'))
                if isinstance(decl.receiver_type, PointerType):
                    class_name = decl.receiver_type.base_type.name
                else:
                    class_name = decl.receiver_type.name
                method_name = f"{class_name}_{decl.name}"
                self.func_names.add(method_name)
                # Track method return types for type inference
                if decl.return_type:
                    self.method_return_types[method_name] = decl.return_type
                # Track parameter defaults (excluding 'self' which is first param)
                if decl.params:
                    defaults = get_param_defaults(decl.params)
                    if defaults:
                        self.func_param_defaults[method_name] = decl.params
            elif isinstance(decl, TryExceptStmt):
                # Also check inside try/except for polyglot code
                for stmt in decl.try_body:
                    decl_stack.append(stmt)
                for stmt in decl.except_body:
                    decl_stack.append(stmt)

        # First pass: collect all global variable names so assignments work correctly
        for decl in program.declarations:
            if isinstance(decl, VarDecl) and not decl.is_const:
                if decl.name not in self.global_var_names:
                    self.global_var_names[decl.name] = 0
                    self.type_table[decl.name] = decl.var_type

        # Generate code for all declarations
        for decl in program.declarations:
            if isinstance(decl, ProcDecl):
                self.gen_procedure(decl)
            elif isinstance(decl, MethodDecl):
                self.gen_method(decl)
            elif isinstance(decl, TryExceptStmt):
                # Extract ProcDecl from try_body for polyglot code
                for stmt in decl.try_body:
                    if isinstance(stmt, ProcDecl):
                        self.gen_procedure(stmt)
                    elif isinstance(stmt, MethodDecl):
                        self.gen_method(stmt)
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
                if var_name in self.global_var_names and self.global_var_names[var_name] > 0:
                    # Already processed - append counter to make unique
                    self.global_var_names[var_name] += 1
                    unique_name = f"_g_{var_name}_{self.global_var_names[var_name]}"
                else:
                    # First use - keep original name (counter was 0 from first pass or not present)
                    self.global_var_names[var_name] = 1  # Mark as processed (1 = first BSS entry)
                    unique_name = var_name  # Use original name for first occurrence

                # Global variable - record type for proper address calculation
                # Use original name for type_table so code references work
                self.type_table[var_name] = decl.var_type

                # Check if initialized with a literal - put in data section
                if decl.value and isinstance(decl.value, StringLiteral):
                    # Put in data section with initialized value
                    str_label = self.add_string(decl.value.value)
                    self.data_section.append(f"{unique_name}: dd {str_label}")
                elif decl.value and isinstance(decl.value, IntLiteral):
                    # Integer literal - put in data section
                    self.data_section.append(f"{unique_name}: dd {decl.value.value}")
                elif decl.value and isinstance(decl.value, BoolLiteral):
                    # Bool literal - put in data section
                    val = 1 if decl.value.value else 0
                    self.data_section.append(f"{unique_name}: dd {val}")
                else:
                    # Uninitialized - goes in BSS
                    self.bss_section.append(f"{unique_name}: resb {self.type_size(decl.var_type)}")

        # Build final assembly
        asm_lines = []
        asm_lines.append("; Generated by Brainhair Compiler")
        asm_lines.append("bits 32")
        asm_lines.append("")

        # External declarations (skip built-in get_argc/get_argv)
        builtin_funcs = ['get_argc', 'get_argv']
        if self.externs:
            for extern_name in self.externs:
                if extern_name not in builtin_funcs:
                    asm_lines.append(f"extern {extern_name}")
            asm_lines.append("")

        # Data section
        if self.strings or self.data_section:
            asm_lines.append("section .data")
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
                db_str: str = join_str_list(", ", parts)
                asm_lines.append(f'{label}: db {db_str}')
            asm_lines.extend(self.data_section)
            asm_lines.append("")

        # BSS section
        if self.bss_section:
            asm_lines.append("section .bss")
            asm_lines.extend(self.bss_section)
            asm_lines.append("")

        # Text section
        asm_lines.append("section .text")

        # Only generate _start if not in kernel mode
        if not self.kernel_mode:
            asm_lines.append("global _start")
            asm_lines.append("global get_argc")
            asm_lines.append("global get_argv")
            asm_lines.append("")
            asm_lines.append("section .bss")
            asm_lines.append("_startup_esp: resd 1")
            asm_lines.append("")
            asm_lines.append("section .text")
            asm_lines.append("")

            # Check if main function exists
            has_main = any(isinstance(d, ProcDecl) and d.name == "main" for d in program.declarations)

            if not has_main:
                # Generate a stub main function for Python files without explicit main
                asm_lines.append("main:")
                asm_lines.append("    push ebp")
                asm_lines.append("    mov ebp, esp")
                asm_lines.append("    xor eax, eax  ; Return 0")
                asm_lines.append("    pop ebp")
                asm_lines.append("    ret")
                asm_lines.append("")

            asm_lines.append("_start:")
            asm_lines.append("    mov [_startup_esp], esp  ; Save initial stack pointer")
            asm_lines.append("    call main")
            asm_lines.append("    ; Exit with return code from main")
            asm_lines.append("    mov ebx, eax  ; Exit code")
            asm_lines.append("    mov eax, 1    ; sys_exit")
            asm_lines.append("    int 0x80")
            asm_lines.append("")
            asm_lines.append("; get_argc() - returns argument count")
            asm_lines.append("get_argc:")
            asm_lines.append("    mov eax, [_startup_esp]")
            asm_lines.append("    mov eax, [eax]  ; argc is at [esp]")
            asm_lines.append("    ret")
            asm_lines.append("")
            asm_lines.append("; get_argv(index) - returns pointer to argument string")
            asm_lines.append("get_argv:")
            asm_lines.append("    push ebp")
            asm_lines.append("    mov ebp, esp")
            asm_lines.append("    mov eax, [_startup_esp]")
            asm_lines.append("    mov ecx, [ebp+8]  ; index")
            asm_lines.append("    lea eax, [eax + 4 + ecx*4]  ; argv[index] = esp + 4 + index*4")
            asm_lines.append("    mov eax, [eax]")
            asm_lines.append("    pop ebp")
            asm_lines.append("    ret")
            asm_lines.append("")
            # Add stub functions for common missing symbols (only if not already defined)
            asm_lines.append("; Stub functions for Python-style code compatibility")
            asm_lines.append("")
            has_strcmp = any(isinstance(d, ProcDecl) and d.name == "strcmp" for d in program.declarations)
            if not has_strcmp:
                asm_lines.append("; strcmp(s1, s2) - returns 0 if equal, nonzero otherwise")
                asm_lines.append("strcmp:")
                asm_lines.append("    push ebp")
                asm_lines.append("    mov ebp, esp")
                asm_lines.append("    push esi")
                asm_lines.append("    push edi")
                asm_lines.append("    mov esi, [ebp+8]   ; s1")
                asm_lines.append("    mov edi, [ebp+12]  ; s2")
                asm_lines.append(".strcmp_loop:")
                asm_lines.append("    mov al, [esi]")
                asm_lines.append("    mov bl, [edi]")
                asm_lines.append("    cmp al, bl")
                asm_lines.append("    jne .strcmp_diff")
                asm_lines.append("    test al, al")
                asm_lines.append("    jz .strcmp_equal")
                asm_lines.append("    inc esi")
                asm_lines.append("    inc edi")
                asm_lines.append("    jmp .strcmp_loop")
                asm_lines.append(".strcmp_equal:")
                asm_lines.append("    xor eax, eax")
                asm_lines.append("    jmp .strcmp_done")
                asm_lines.append(".strcmp_diff:")
                asm_lines.append("    movzx eax, al")
                asm_lines.append("    movzx ebx, bl")
                asm_lines.append("    sub eax, ebx")
                asm_lines.append(".strcmp_done:")
                asm_lines.append("    pop edi")
                asm_lines.append("    pop esi")
                asm_lines.append("    pop ebp")
                asm_lines.append("    ret")
                asm_lines.append("")
            asm_lines.append("; strcat_alloc(s1, s2) - allocates new string with s1+s2 concatenated")
            asm_lines.append("strcat_alloc:")
            asm_lines.append("    push ebp")
            asm_lines.append("    mov ebp, esp")
            asm_lines.append("    push esi")
            asm_lines.append("    push edi")
            asm_lines.append("    push ebx")
            asm_lines.append("    ; Calculate strlen(s1)")
            asm_lines.append("    mov esi, [ebp+8]   ; s1")
            asm_lines.append("    xor ecx, ecx       ; len1 = 0")
            asm_lines.append(".strlen1_loop:")
            asm_lines.append("    mov al, [esi+ecx]")
            asm_lines.append("    test al, al")
            asm_lines.append("    jz .strlen1_done")
            asm_lines.append("    inc ecx")
            asm_lines.append("    jmp .strlen1_loop")
            asm_lines.append(".strlen1_done:")
            asm_lines.append("    mov ebx, ecx       ; ebx = len1")
            asm_lines.append("    ; Calculate strlen(s2)")
            asm_lines.append("    mov edi, [ebp+12]  ; s2")
            asm_lines.append("    xor ecx, ecx       ; len2 = 0")
            asm_lines.append(".strlen2_loop:")
            asm_lines.append("    mov al, [edi+ecx]")
            asm_lines.append("    test al, al")
            asm_lines.append("    jz .strlen2_done")
            asm_lines.append("    inc ecx")
            asm_lines.append("    jmp .strlen2_loop")
            asm_lines.append(".strlen2_done:")
            asm_lines.append("    ; ecx = len2, ebx = len1")
            asm_lines.append("    add ecx, ebx       ; ecx = len1 + len2")
            asm_lines.append("    inc ecx            ; +1 for null terminator")
            asm_lines.append("    push ecx           ; save total size")
            asm_lines.append("    push ebx           ; save len1")
            asm_lines.append("    ; Allocate buffer: call alloc(size)")
            asm_lines.append("    push ecx")
            asm_lines.append("    call alloc")
            asm_lines.append("    add esp, 4")
            asm_lines.append("    mov edx, eax       ; edx = new buffer pointer")
            asm_lines.append("    pop ebx            ; restore len1")
            asm_lines.append("    pop ecx            ; restore total size (not needed anymore)")
            asm_lines.append("    ; Copy s1 to buffer")
            asm_lines.append("    mov esi, [ebp+8]   ; s1")
            asm_lines.append("    mov edi, edx       ; dest = buffer")
            asm_lines.append(".copy1_loop:")
            asm_lines.append("    mov al, [esi]")
            asm_lines.append("    mov [edi], al")
            asm_lines.append("    test al, al")
            asm_lines.append("    jz .copy1_done")
            asm_lines.append("    inc esi")
            asm_lines.append("    inc edi")
            asm_lines.append("    jmp .copy1_loop")
            asm_lines.append(".copy1_done:")
            asm_lines.append("    ; edi points to null terminator position, copy s2 there")
            asm_lines.append("    mov esi, [ebp+12]  ; s2")
            asm_lines.append(".copy2_loop:")
            asm_lines.append("    mov al, [esi]")
            asm_lines.append("    mov [edi], al")
            asm_lines.append("    test al, al")
            asm_lines.append("    jz .copy2_done")
            asm_lines.append("    inc esi")
            asm_lines.append("    inc edi")
            asm_lines.append("    jmp .copy2_loop")
            asm_lines.append(".copy2_done:")
            asm_lines.append("    mov eax, edx       ; return buffer pointer")
            asm_lines.append("    pop ebx")
            asm_lines.append("    pop edi")
            asm_lines.append("    pop esi")
            asm_lines.append("    pop ebp")
            asm_lines.append("    ret")
            asm_lines.append("")
            asm_lines.append("; strcat_char(s, c) - concatenates string s with single char c")
            asm_lines.append("strcat_char:")
            asm_lines.append("    push ebp")
            asm_lines.append("    mov ebp, esp")
            asm_lines.append("    push esi")
            asm_lines.append("    push edi")
            asm_lines.append("    push ebx")
            asm_lines.append("    ; Calculate strlen(s)")
            asm_lines.append("    mov esi, [ebp+8]   ; s")
            asm_lines.append("    xor ecx, ecx       ; len = 0")
            asm_lines.append(".strcat_char_strlen:")
            asm_lines.append("    mov al, [esi+ecx]")
            asm_lines.append("    test al, al")
            asm_lines.append("    jz .strcat_char_strlen_done")
            asm_lines.append("    inc ecx")
            asm_lines.append("    jmp .strcat_char_strlen")
            asm_lines.append(".strcat_char_strlen_done:")
            asm_lines.append("    ; ecx = len(s), need len+2 for new string (char + null)")
            asm_lines.append("    mov ebx, ecx       ; save len")
            asm_lines.append("    add ecx, 2         ; +1 for char, +1 for null")
            asm_lines.append("    push ebx           ; save len")
            asm_lines.append("    push ecx")
            asm_lines.append("    call alloc")
            asm_lines.append("    add esp, 4")
            asm_lines.append("    mov edx, eax       ; edx = new buffer")
            asm_lines.append("    pop ebx            ; restore len")
            asm_lines.append("    ; Copy s to buffer")
            asm_lines.append("    mov esi, [ebp+8]   ; s")
            asm_lines.append("    mov edi, edx       ; dest")
            asm_lines.append(".strcat_char_copy:")
            asm_lines.append("    mov al, [esi]")
            asm_lines.append("    mov [edi], al")
            asm_lines.append("    test al, al")
            asm_lines.append("    jz .strcat_char_copy_done")
            asm_lines.append("    inc esi")
            asm_lines.append("    inc edi")
            asm_lines.append("    jmp .strcat_char_copy")
            asm_lines.append(".strcat_char_copy_done:")
            asm_lines.append("    ; edi points to null terminator, add char there")
            asm_lines.append("    mov eax, [ebp+12]  ; c (char value)")
            asm_lines.append("    mov [edi], al      ; store char")
            asm_lines.append("    mov byte [edi+1], 0  ; null terminator")
            asm_lines.append("    mov eax, edx       ; return buffer")
            asm_lines.append("    pop ebx")
            asm_lines.append("    pop edi")
            asm_lines.append("    pop esi")
            asm_lines.append("    pop ebp")
            asm_lines.append("    ret")
            asm_lines.append("")
            asm_lines.append("uint8_join:")
            asm_lines.append("    ; String join stub - just return first arg")
            asm_lines.append("    mov eax, [esp+4]")
            asm_lines.append("    ret")
            asm_lines.append("")
            asm_lines.append("original_init:")
            asm_lines.append("    ; Original __init__ stub")
            asm_lines.append("    xor eax, eax")
            asm_lines.append("    ret")
            asm_lines.append("")
            asm_lines.append("types:")
            asm_lines.append("    ; Python types module stub")
            asm_lines.append("    xor eax, eax")
            asm_lines.append("    ret")
            asm_lines.append("")
        else:
            # In kernel mode, export brainhair_kernel_main
            asm_lines.append("global brainhair_kernel_main")
            # Export networking functions for syscall handlers
            asm_lines.append("global tcp_listen")
            asm_lines.append("global tcp_accept_ready")
            asm_lines.append("global tcp_connect")
            asm_lines.append("global tcp_write")
            asm_lines.append("global tcp_read")
            asm_lines.append("global tcp_close")
            asm_lines.append("global tcp_state")
            asm_lines.append("global net_poll")
            asm_lines.append("global tcp_has_data")
            # Filesystem syscalls
            asm_lines.append("global sys_link")
            asm_lines.append("global sys_unlink")
            asm_lines.append("global sys_symlink")
            asm_lines.append("global sys_readlink")
            asm_lines.append("global sys_flock")
            # Extended attribute syscalls
            asm_lines.append("global sys_getxattr")
            asm_lines.append("global sys_setxattr")
            asm_lines.append("global sys_listxattr")
            asm_lines.append("global sys_removexattr")
            # Unix domain socket functions
            asm_lines.append("global unix_listen")
            asm_lines.append("global unix_connect")
            asm_lines.append("global unix_accept")
            asm_lines.append("global unix_send")
            asm_lines.append("global unix_recv")
            asm_lines.append("global unix_close")
            asm_lines.append("global unix_has_data")
            # RTC functions
            asm_lines.append("global rtc_get_time")
            asm_lines.append("global rtc_to_unix_timestamp")
            # VTNext graphics commands
            asm_lines.append("global vtn_draw_text_cmd")
            asm_lines.append("global vtn_draw_rect_cmd")
            asm_lines.append("global vtn_draw_line_cmd")
            asm_lines.append("global vtn_draw_circle_cmd")
            asm_lines.append("global vtn_clear_cmd")
            asm_lines.append("global vtn_draw_rrect_cmd")
            asm_lines.append("global vtn_input_cmd")
            asm_lines.append("global vtn_cursor_cmd")
            asm_lines.append("global vtn_viewport_cmd")
            asm_lines.append("global vtn_query_cmd")
            asm_lines.append("global vtn_draw_ellipse_cmd")
            asm_lines.append("global vtn_draw_poly_cmd")
            asm_lines.append("")

        asm_lines.extend(self.output)

        return join_str_list("\n", asm_lines)

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
