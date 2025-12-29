# `ref` Keyword - GC-Managed References

## Overview

The `ref` keyword in Brainhair provides GC-managed heap allocation support. It declares a reference type that points to heap-allocated objects managed by the garbage collector.

## Syntax

```brainhair
var obj: ref MyStruct  # Declare a GC-managed reference
```

## Type System

A `ref T` type is a GC-managed pointer to type `T`. It behaves similarly to `ptr T` but semantically indicates that:

1. The memory is heap-allocated (not stack)
2. The memory is managed by the garbage collector
3. The object will be automatically freed when no longer reachable

## Implementation

### Language Components

1. **Lexer** (`compiler/lexer.py`):
   - Added `REF` token type
   - Added `'ref'` keyword mapping

2. **AST** (`compiler/ast_nodes.py`):
   - Added `RefType` class for representing `ref T` types
   - Similar structure to `PointerType` but semantically distinct

3. **Parser** (`compiler/parser.py`):
   - Added parsing support for `ref T` syntax in `parse_type()`
   - Parses similarly to `ptr T`

4. **Type Checker** (`compiler/type_checker.py`):
   - Added `RefType` handling in `_resolve_type()`
   - Treats `ref T` as a pointer for type compatibility

5. **Code Generator** (`compiler/codegen_x86.py`):
   - Added `RefType` support in all pointer-handling code paths:
     - `type_size()` - returns 4 bytes (32-bit pointer)
     - `_get_expr_type()` - handles field access through refs
     - `gen_expression()` - handles field access, indexing, method calls
     - `gen_statement()` - handles assignments through refs

### Runtime Support

The `ref` keyword works in conjunction with the GC runtime (`lib/gc.bh`):

```brainhair
import "lib/gc.bh"

proc example() =
    # Initialize GC
    discard gc_init()

    # Allocate GC-managed memory
    var obj: ref MyStruct = cast[ref MyStruct](gc_alloc(sizeof(MyStruct)))

    # Use like a normal pointer
    obj.field = 42

    # Garbage collection
    discard gc_collect()
```

## Usage Examples

### Basic Allocation

```brainhair
type Point = object
    x: int32
    y: int32

proc test() =
    var point: ref Point
    point = cast[ref Point](gc_alloc(8))

    # Access fields (automatic dereference)
    point.x = 10
    point.y = 20
```

### Linked Data Structures

```brainhair
type Node = object
    value: int32
    next: ref Node

proc create_list() =
    var head: ref Node = cast[ref Node](gc_alloc(8))
    var tail: ref Node = cast[ref Node](gc_alloc(8))

    head.value = 1
    head.next = tail

    tail.value = 2
    tail.next = cast[ref Node](0)  # null
```

### Global References

```brainhair
var global_ref: ref MyStruct

proc setup() =
    # Register global variable as GC root
    discard gc_register_root(cast[ptr int32](addr(global_ref)))

    # Allocate and assign
    global_ref = cast[ref MyStruct](gc_alloc(sizeof(MyStruct)))
    global_ref.field = 100

    # global_ref will survive garbage collection
    discard gc_collect()
```

## Technical Details

### Memory Layout

A `ref T` variable is stored as a 4-byte pointer (on 32-bit systems):

```
[ref Point variable]
    |
    v
[GC Header: 16 bytes][Point data: 8 bytes]
 - mark_and_type: u32
 - size: u32
 - next: ptr
 - prev: ptr
```

### Field Access

Field access through refs is automatically handled:

```brainhair
obj.field = value
```

Compiles to:
```asm
mov eax, [ebp-4]     ; Load ref (pointer)
add eax, <offset>    ; Add field offset
mov [eax], value     ; Store value
```

### Type Safety

The type checker ensures:
- `ref T` can only point to heap-allocated `T`
- Cannot create `ref` to stack variables (use `ptr` instead)
- Field access respects struct definitions
- Type compatibility in assignments and function calls

## Comparison with `ptr`

| Feature | `ptr T` | `ref T` |
|---------|---------|---------|
| Memory location | Stack or heap | Heap only |
| Lifetime | Manual | GC-managed |
| Allocation | Any | `gc_alloc()` |
| Deallocation | Manual (if needed) | Automatic |
| Use case | General pointers | GC-managed objects |

## Future Enhancements

Potential future improvements:

1. **`new` operator**: Syntactic sugar for allocation
   ```brainhair
   var obj: ref MyStruct = new MyStruct()  # Auto gc_alloc
   ```

2. **Automatic root registration**: Global refs auto-registered
   ```brainhair
   var global: ref T  # Automatically added to GC roots
   ```

3. **Type-aware GC**: Use type IDs for smarter collection
   ```brainhair
   var obj: ref MyStruct  # GC knows to scan MyStruct fields
   ```

4. **Reference counting**: Optional for deterministic cleanup
   ```brainhair
   var obj: rc[MyStruct]  # Reference counted instead of GC
   ```

## Testing

Test files:
- `test_ref.bh` - Full GC integration test
- `test_ref_simple.bh` - Simple ref type verification

Compile and run:
```bash
python3 compiler/brainhair.py test_ref_simple.bh -o test_ref_simple
./test_ref_simple
```

## Implementation Status

✅ Lexer support
✅ AST node definition
✅ Parser support
✅ Type checking
✅ Code generation
✅ All pointer operations (field access, indexing, method calls)
✅ Assignment handling
✅ Integration with existing GC runtime

The `ref` keyword is fully implemented and ready for use with the Brainhair GC library.
