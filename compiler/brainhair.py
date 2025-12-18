#!/usr/bin/env python3
"""
Brainhair Compiler - Complete compiler driver

Usage:
    ./brainhair.py source.bh -o output

Compiles Brainhair to native x86 executable
"""

import sys
import subprocess
import os
from pathlib import Path

from lexer import Lexer
from parser import Parser
from codegen_x86 import X86CodeGen
from codegen_llvm import LLVMCodeGen
from type_checker import TypeChecker
from ownership import OwnershipChecker
from lifetimes import LifetimeChecker
from generics import monomorphize

class Compiler:
    def __init__(self, source_file: str, output_file: str = None, kernel_mode: bool = False,
                 check_types: bool = True, check_ownership: bool = True, check_lifetimes: bool = True,
                 use_llvm: bool = False):
        self.source_file = source_file
        self.output_file = output_file or Path(source_file).stem
        self.kernel_mode = kernel_mode
        self.check_types = check_types
        self.check_ownership = check_ownership
        self.check_lifetimes = check_lifetimes
        self.use_llvm = use_llvm

        # Intermediate files
        self.asm_file = f"{self.output_file}.asm"
        self.ll_file = f"{self.output_file}.ll"
        self.obj_file = f"{self.output_file}.o"

    def compile(self):
        """Full compilation pipeline"""
        print(f"[Brainhair] Compiling {self.source_file}...")

        # 1. Read source
        with open(self.source_file, 'r') as f:
            source_code = f.read()

        # 2. Lex
        print("  [1/4] Lexing...")
        lexer = Lexer(source_code)
        tokens = lexer.tokenize()
        print(f"        Generated {len(tokens)} tokens")

        # 3. Parse
        print("  [2/8] Parsing...")
        parser = Parser(tokens)
        ast = parser.parse()
        print(f"        Generated AST with {len(ast.declarations)} declarations")

        # 4. Monomorphization (instantiate generic functions/types)
        print("  [3/8] Monomorphizing generics...")
        ast = monomorphize(ast)
        generic_count = sum(1 for d in ast.declarations
                          if hasattr(d, 'name') and '$' in getattr(d, 'name', ''))
        if generic_count > 0:
            print(f"        Generated {generic_count} generic instantiation(s)")
        else:
            print("        No generic instantiations needed")

        # 5. Type checking (optional)
        if self.check_types:
            print("  [4/8] Type checking...")
            checker = TypeChecker()
            errors = checker.check(ast)
            if errors:
                print(f"        Found {len(errors)} type error(s):")
                for error in errors:
                    print(f"          - {error}")
                # Type errors are warnings for now during transition
                print("        (continuing with code generation)")
            else:
                print("        No type errors found")
        else:
            print("  [4/8] Type checking... (skipped)")

        # 6. Ownership checking (optional)
        if self.check_ownership:
            print("  [5/8] Ownership checking...")
            ownership_checker = OwnershipChecker()
            ownership_errors = ownership_checker.check(ast)
            if ownership_errors:
                print(f"        Found {len(ownership_errors)} ownership error(s):")
                for error in ownership_errors:
                    print(f"          - {error}")
                # Ownership errors are warnings for now during transition
                print("        (continuing with code generation)")
            else:
                print("        No ownership errors found")
        else:
            print("  [5/8] Ownership checking... (skipped)")

        # 7. Lifetime checking (optional)
        if self.check_lifetimes:
            print("  [6/8] Lifetime checking...")
            lifetime_checker = LifetimeChecker()
            lifetime_errors = lifetime_checker.check(ast)
            if lifetime_errors:
                print(f"        Found {len(lifetime_errors)} lifetime error(s):")
                for error in lifetime_errors:
                    print(f"          - {error}")
                # Lifetime errors are warnings for now during transition
                print("        (continuing with code generation)")
            else:
                print("        No lifetime errors found")
        else:
            print("  [6/8] Lifetime checking... (skipped)")

        # 8. Code generation
        if self.use_llvm:
            print("  [7/8] Generating LLVM IR...")
            codegen = LLVMCodeGen()
            llvm_code = codegen.generate(ast)

            # Write LLVM IR file
            with open(self.ll_file, 'w') as f:
                f.write(llvm_code)
            print(f"        Wrote {self.ll_file}")

            # 9. Compile LLVM IR to object file
            print("  [8/8] Compiling LLVM IR...")
            try:
                subprocess.run([
                    'clang',
                    '-m32',
                    '-c',
                    self.ll_file,
                    '-o', self.obj_file
                ], check=True, capture_output=True)
                print(f"        Created {self.obj_file}")
            except subprocess.CalledProcessError as e:
                print(f"ERROR: LLVM compilation failed!")
                print(e.stderr.decode())
                return False
            except FileNotFoundError:
                print("ERROR: clang not found! Install with: sudo apt install clang")
                return False
        else:
            print("  [7/8] Generating x86 assembly...")
            codegen = X86CodeGen(kernel_mode=self.kernel_mode)
            asm_code = codegen.generate(ast)

            # Write assembly file
            with open(self.asm_file, 'w') as f:
                f.write(asm_code)
            print(f"        Wrote {self.asm_file}")

            # 9. Assemble with NASM
            print("  [8/8] Assembling...")
            try:
                subprocess.run([
                    'nasm',
                    '-f', 'elf32',
                    self.asm_file,
                    '-o', self.obj_file
                ], check=True, capture_output=True)
                print(f"        Created {self.obj_file}")
            except subprocess.CalledProcessError as e:
                print(f"ERROR: Assembly failed!")
                print(e.stderr.decode())
                return False
            except FileNotFoundError:
                print("ERROR: nasm not found! Install with: sudo apt install nasm")
                return False

        # 10. Link (for standalone binary - skip in kernel mode)
        if not self.kernel_mode:
            print("  [9/9] Linking...")
            try:
                subprocess.run([
                    'ld',
                    '-m', 'elf_i386',
                    '-o', self.output_file,
                    self.obj_file
                ], check=True, capture_output=True)
                print(f"        Created {self.output_file}")
            except subprocess.CalledProcessError as e:
                print(f"ERROR: Linking failed!")
                print(e.stderr.decode())
                return False

            print(f"\n✓ Compilation successful!")
            print(f"  Output: {self.output_file}")
            print(f"  Size: {os.path.getsize(self.output_file)} bytes")
        else:
            print(f"\n✓ Compilation successful!")
            print(f"  Output: {self.obj_file} (kernel object file)")
            print(f"  Size: {os.path.getsize(self.obj_file)} bytes")

        return True

    def run(self):
        """Compile and run the program"""
        if self.compile():
            print(f"\n[Brainhair] Running {self.output_file}...\n")
            print("=" * 50)
            result = subprocess.run([f"./{self.output_file}"])
            print("=" * 50)
            return result.returncode
        return 1

def main():
    if len(sys.argv) < 2:
        print("Brainhair Compiler")
        print("Usage: brainhair.py <source.bh> [-o output] [--run] [--kernel]")
        print("")
        print("Options:")
        print("  -o <name>       Output filename (default: same as source)")
        print("  --run           Compile and run immediately")
        print("  --asm-only      Only generate assembly, don't assemble")
        print("  --kernel        Kernel mode: don't generate _start, export main")
        print("  --no-typecheck  Skip type checking phase")
        print("  --no-ownership  Skip ownership checking phase")
        print("  --no-lifetimes  Skip lifetime checking phase")
        print("  --llvm          Use LLVM backend instead of x86")
        print("  --emit-llvm     Output LLVM IR (for --llvm)")
        sys.exit(1)

    source_file = sys.argv[1]
    output_file = None
    run_after = False
    asm_only = False
    kernel_mode = False
    check_types = True
    check_ownership = True
    check_lifetimes = True
    use_llvm = False
    emit_llvm = False

    # Parse arguments
    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == '-o' and i + 1 < len(sys.argv):
            output_file = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == '--run':
            run_after = True
            i += 1
        elif sys.argv[i] == '--asm-only':
            asm_only = True
            i += 1
        elif sys.argv[i] == '--kernel':
            kernel_mode = True
            i += 1
        elif sys.argv[i] == '--no-typecheck':
            check_types = False
            i += 1
        elif sys.argv[i] == '--no-ownership':
            check_ownership = False
            i += 1
        elif sys.argv[i] == '--no-lifetimes':
            check_lifetimes = False
            i += 1
        elif sys.argv[i] == '--llvm':
            use_llvm = True
            i += 1
        elif sys.argv[i] == '--emit-llvm':
            emit_llvm = True
            use_llvm = True
            i += 1
        else:
            print(f"Unknown option: {sys.argv[i]}")
            sys.exit(1)

    compiler = Compiler(source_file, output_file, kernel_mode=kernel_mode,
                       check_types=check_types, check_ownership=check_ownership,
                       check_lifetimes=check_lifetimes, use_llvm=use_llvm)

    if asm_only or emit_llvm:
        # Just generate assembly/LLVM IR
        with open(source_file, 'r') as f:
            source_code = f.read()

        lexer = Lexer(source_code)
        tokens = lexer.tokenize()

        parser = Parser(tokens)
        ast = parser.parse()

        # Monomorphize generics
        ast = monomorphize(ast)

        if emit_llvm or use_llvm:
            codegen = LLVMCodeGen()
            llvm_code = codegen.generate(ast)
            print(llvm_code)
        else:
            codegen = X86CodeGen(kernel_mode=kernel_mode)
            asm_code = codegen.generate(ast)
            print(asm_code)
    elif run_after:
        sys.exit(compiler.run())
    else:
        sys.exit(0 if compiler.compile() else 1)

if __name__ == '__main__':
    main()
