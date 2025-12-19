#!/bin/bash
# Demonstration: Using BrainhairOS shell utilities for practical scripting
# This shows how test, expr, which, xargs, and env can be used together

echo "========================================"
echo "  BrainhairOS Shell Scripting Demo"
echo "========================================"
echo ""

# Demo 1: Conditional file operations
echo "Demo 1: Checking for utilities before use"
echo "-------------------------------------------"
for util in ls cat echo; do
    if ./bin/test -x ./bin/$util; then
        location=$(./bin/which $util)
        echo "✓ $util found at: $location"
    else
        echo "✗ $util not found"
    fi
done
echo ""

# Demo 2: Arithmetic calculations
echo "Demo 2: Calculate factorial using expr"
echo "-------------------------------------------"
n=5
result=1
i=1
echo "Calculating $n factorial..."
while ./bin/test $i -le $n; do
    result=$(./bin/expr $result \* $i)
    echo "  $i! = $result"
    i=$(./bin/expr $i + 1)
done
echo "Result: $n! = $result"
echo ""

# Demo 3: Batch processing with xargs
echo "Demo 3: Process multiple items with xargs"
echo "-------------------------------------------"
echo "Creating a list of utilities..."
echo -e "test\nexpr\nwhich\nxargs\nenv" > /tmp/util_list.txt
echo "Checking each utility with xargs:"
cat /tmp/util_list.txt | ./bin/xargs ./bin/which
rm -f /tmp/util_list.txt
echo ""

# Demo 4: Environment manipulation
echo "Demo 4: Running commands with custom environment"
echo "-------------------------------------------"
echo "Setting DEBUG=1 and LOGLEVEL=verbose:"
./bin/env DEBUG=1 LOGLEVEL=verbose ./bin/echo "Command executed with custom environment"
echo ""

# Demo 5: Complex condition checking
echo "Demo 5: Filesystem health check"
echo "-------------------------------------------"
critical_files="./bin/test ./bin/expr ./bin/echo"
all_present=1

for file in $critical_files; do
    if ./bin/test -f $file; then
        size=$(./bin/expr $(wc -c < $file) / 1024)
        echo "✓ $file exists (${size}KB)"
    else
        echo "✗ $file MISSING!"
        all_present=0
    fi
done

if [ $all_present -eq 1 ]; then
    echo "✓ All critical files present"
else
    echo "✗ Some files are missing!"
fi
echo ""

# Demo 6: Range operations
echo "Demo 6: Generate and process number ranges"
echo "-------------------------------------------"
echo "Sum of numbers 1-10 using expr:"
sum=0
i=1
while ./bin/test $i -le 10; do
    sum=$(./bin/expr $sum + $i)
    i=$(./bin/expr $i + 1)
done
echo "Sum(1..10) = $sum"
echo ""

# Demo 7: String validation
echo "Demo 7: String validation and comparison"
echo "-------------------------------------------"
test_str="BrainhairOS"
empty_str=""

if ./bin/test -n "$test_str"; then
    echo "✓ String '$test_str' is non-empty"
fi

if ./bin/test -z "$empty_str"; then
    echo "✓ Empty string check works"
fi

if ./bin/test "$test_str" = "BrainhairOS"; then
    echo "✓ String equality check passed"
fi
echo ""

echo "========================================"
echo "  Demo complete!"
echo "  These utilities enable powerful"
echo "  shell scripting capabilities!"
echo "========================================"
