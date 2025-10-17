#!/usr/bin/env python3
"""
Mini-Nim Compiler - Complete compiler driver

Usage:
    ./mininim.py source.nim -o output

Compiles Mini-Nim to native x86 executable
"""

import sys
import subprocess
import os
from pathlib import Path

from lexer import Lexer
from parser import Parser
from codegen_x86 import X86CodeGen

class Compiler:
    def __init__(self, source_file: str, output_file: str = None, kernel_mode: bool = False):
        self.source_file = source_file
        self.output_file = output_file or Path(source_file).stem
        self.kernel_mode = kernel_mode

        # Intermediate files
        self.asm_file = f"{self.output_file}.asm"
        self.obj_file = f"{self.output_file}.o"

    def compile(self):
        """Full compilation pipeline"""
        print(f"[Mini-Nim] Compiling {self.source_file}...")

        # 1. Read source
        with open(self.source_file, 'r') as f:
            source_code = f.read()

        # 2. Lex
        print("  [1/4] Lexing...")
        lexer = Lexer(source_code)
        tokens = lexer.tokenize()
        print(f"        Generated {len(tokens)} tokens")

        # 3. Parse
        print("  [2/4] Parsing...")
        parser = Parser(tokens)
        ast = parser.parse()
        print(f"        Generated AST with {len(ast.declarations)} declarations")

        # 4. Code generation
        print("  [3/4] Generating x86 assembly...")
        codegen = X86CodeGen(kernel_mode=self.kernel_mode)
        asm_code = codegen.generate(ast)

        # Write assembly file
        with open(self.asm_file, 'w') as f:
            f.write(asm_code)
        print(f"        Wrote {self.asm_file}")

        # 5. Assemble with NASM
        print("  [4/4] Assembling...")
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

        # 6. Link (for standalone binary - skip in kernel mode)
        if not self.kernel_mode:
            print("  [5/5] Linking...")
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
            print(f"\n[Mini-Nim] Running {self.output_file}...\n")
            print("=" * 50)
            result = subprocess.run([f"./{self.output_file}"])
            print("=" * 50)
            return result.returncode
        return 1

def main():
    if len(sys.argv) < 2:
        print("Mini-Nim Compiler")
        print("Usage: mininim.py <source.nim> [-o output] [--run] [--kernel]")
        print("")
        print("Options:")
        print("  -o <name>    Output filename (default: same as source)")
        print("  --run        Compile and run immediately")
        print("  --asm-only   Only generate assembly, don't assemble")
        print("  --kernel     Kernel mode: don't generate _start, export main")
        sys.exit(1)

    source_file = sys.argv[1]
    output_file = None
    run_after = False
    asm_only = False
    kernel_mode = False

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
        else:
            print(f"Unknown option: {sys.argv[i]}")
            sys.exit(1)

    compiler = Compiler(source_file, output_file, kernel_mode=kernel_mode)

    if asm_only:
        # Just generate assembly
        with open(source_file, 'r') as f:
            source_code = f.read()

        lexer = Lexer(source_code)
        tokens = lexer.tokenize()

        parser = Parser(tokens)
        ast = parser.parse()

        codegen = X86CodeGen(kernel_mode=kernel_mode)
        asm_code = codegen.generate(ast)

        print(asm_code)
    elif run_after:
        sys.exit(compiler.run())
    else:
        sys.exit(0 if compiler.compile() else 1)

if __name__ == '__main__':
    main()
