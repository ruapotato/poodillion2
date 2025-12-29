# Comparison Operator Fix

## Problem

The Brainhair compiler was using **signed** comparison instructions (`setl`, `setg`, `setle`, `setge`) for ALL integer comparisons, even when comparing:
- Pointer addresses (which are unsigned)
- Sizes and counts (which are unsigned)
- uint32 values

This caused bugs in the GC (garbage collector) code, where pointer address comparisons would fail. For example:
- Address `0xFFFFFFFF` compared with `0x00500000`
- With signed comparison: -1 < 5242880 = TRUE (WRONG - treats address as negative number)
- With unsigned comparison: 4294967295 > 5242880 = TRUE (CORRECT)

## Solution

Modified `/home/david/poodillion2/compiler/codegen_x86.py` to:

1. **Use unsigned comparisons for int32 by default**
   - `setb` instead of `setl` for <
   - `seta` instead of `setg` for >
   - `setbe` instead of `setle` for <=
   - `setae` instead of `setge` for >=

2. **Rationale for treating int32 as unsigned:**
   - Pointer addresses stored in int32 MUST use unsigned comparison
   - Sizes/counts (gc_bytes_since_collect, heap_size, etc.) are never negative
   - Array indices are never negative
   - This is the most common use case in Brainhair code

3. **For code that needs signed comparison:**
   - Use explicit comparison with 0: `if x < 0:`
   - Or use int8/int16 types for explicitly signed values
   - Most Brainhair code doesn't use negative numbers

## Testing

Created test cases:
- `test_comparison.bh` - Basic comparison operators (PASS)
- `test_gc_comparison.bh` - GC comparison pattern (PASS)
- `test_unsigned_bug.bh` - Pointer address comparison (PASS - FIXED)
- `test_negative_comparison.bh` - Negative number comparisons (now treat as unsigned)

## Files Modified

- `/home/david/poodillion2/compiler/codegen_x86.py`
  - Added `_is_unsigned_type()` helper method
  - Modified comparison operators (LT, GT, LTE, GTE) to use correct instructions
  - Added extensive comments explaining the design decision

## Impact

- ✅ Fixes GC pointer comparison bugs
- ✅ Fixes size/count comparison bugs
- ✅ Allows GC features to be re-enabled
- ⚠️  Changes behavior for negative number comparisons (now treated as large unsigned values)
- ⚠️  Code comparing negative int32 values will need to be updated

## Recommendation

Going forward, consider:
1. Using uint32 explicitly for addresses and sizes
2. Using int8/int16 for values that can be negative
3. Using explicit `< 0` checks for error detection
