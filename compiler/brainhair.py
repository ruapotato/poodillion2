#!/usr/bin/env python3
"""
Brainhair Compiler - Complete compiler driver

Usage:
    ./brainhair.py source.bh -o output

Compiles Brainhair to native x86 executable
"""

# Polyglot imports: try Brainhair native, fall back to Python stdlib
try:
    from lib.sys import exit, argv, argc
    from lib.os import path_exists, path_join, path_dirname, path_abspath, path_getsize, path_stem
    from lib.subprocess import run

    def get_compiler_path() -> str:
        return path_abspath(argv(0))
except:
    import sys as _sys
    import os as _os
    from pathlib import Path as _Path
    import subprocess as _subprocess

    def exit(code: int):
        _sys.exit(code)

    def argv(i: int):
        if i < len(_sys.argv):
            return _sys.argv[i]
        return ""

    def argc() -> int:
        return len(_sys.argv)

    def path_exists(p: str) -> bool:
        return _os.path.exists(p)

    def path_join(a: str, b: str) -> str:
        return _os.path.join(a, b)

    def path_dirname(p: str) -> str:
        return _os.path.dirname(p)

    def path_abspath(p: str) -> str:
        return _os.path.abspath(p)

    def path_getsize(p: str) -> int:
        return _os.path.getsize(p)

    def path_stem(p: str) -> str:
        return _Path(p).stem

    def run(cmd: str) -> int:
        result = _subprocess.run(cmd, shell=True)
        return result.returncode

    def get_compiler_path() -> str:
        return _os.path.abspath(__file__)

# Python-syntax lexer and parser
from lexer import Lexer
from parser import Parser
from codegen_x86 import X86CodeGen
from codegen_x86_64 import X86_64CodeGen
from codegen_llvm import LLVMCodeGen
from type_checker import TypeChecker
from ownership import OwnershipChecker
from lifetimes import LifetimeChecker
from ast_nodes import Program, ImportDecl

# Generics is optional - provide fallback that gets overridden in Python
def monomorphize(ast):
    return ast

try:
    from generics import monomorphize
except:
    pass

class Compiler:
    def __init__(self, source_file: str, output_file: str = None, kernel_mode: bool = False,
                 check_types: bool = True, check_ownership: bool = True, check_lifetimes: bool = True,
                 use_llvm: bool = False, use_x86_64: bool = False):
        self.source_file = source_file
        self.output_file = output_file or path_stem(source_file)
        self.kernel_mode = kernel_mode
        self.check_types = check_types
        self.check_ownership = check_ownership
        self.check_lifetimes = check_lifetimes
        self.use_llvm = use_llvm
        self.use_x86_64 = use_x86_64

        # Intermediate files
        self.asm_file = f"{self.output_file}.asm"
        self.ll_file = f"{self.output_file}.ll"
        self.obj_file = f"{self.output_file}.o"

        # Track imported files to prevent circular imports
        self.imported_files = set()

    def resolve_imports(self, ast: Program, source_dir: str) -> Program:
        """
        Recursively resolve all imports in the AST.
        Imported declarations are prepended to the main AST.
        """
        if not ast.imports:
            return ast

        all_imported_decls = []

        for imp in ast.imports:
            # Resolve import path relative to source file or compiler dir
            import_path = self._resolve_import_path(imp.path, source_dir)

            if import_path is None:
                print(f"WARNING: Cannot find import '{imp.path}'")
                continue

            # Check for circular imports
            abs_path = path_abspath(import_path)
            if abs_path in self.imported_files:
                continue  # Already imported, skip

            self.imported_files.add(abs_path)

            # Parse the imported file
            try:
                with open(import_path, 'r') as f:
                    import_source = f.read()

                lexer = Lexer(import_source)
                tokens = lexer.tokenize()

                parser = Parser(tokens)
                imported_ast = parser.parse()

                # Recursively resolve imports in the imported file
                import_dir = path_dirname(import_path)
                imported_ast = self.resolve_imports(imported_ast, import_dir)

                # Collect declarations (skip duplicates by name)
                for decl in imported_ast.declarations:
                    all_imported_decls.append(decl)

                if imp.alias:
                    print(f"        Imported '{imp.path}' as '{imp.alias}'")
                else:
                    print(f"        Imported '{imp.path}'")

            except Exception as e:
                print(f"WARNING: Error importing '{imp.path}': {e}")
                continue

        # Prepend imported declarations to main declarations
        merged_decls = all_imported_decls + ast.declarations
        return Program(declarations=merged_decls, imports=[])

    def _resolve_import_path(self, import_path: str, source_dir: str) -> str:
        """
        Resolve an import path to an actual file path.
        Tries:
        1. Relative to source file directory
        2. Relative to compiler lib directory
        3. Absolute path
        Supports both .bh and .py extensions.
        """
        # Determine extensions to try
        if import_path.endswith('.bh') or import_path.endswith('.py'):
            extensions = ['']  # Already has extension
        else:
            extensions = ['.bh', '.py']  # Try both

        for ext in extensions:
            import_path_with_ext = import_path + ext

            # Try relative to source directory
            candidate = path_join(source_dir, import_path_with_ext)
            if path_exists(candidate):
                return candidate

            # Try relative to compiler's parent directory (project root)
            compiler_dir = path_dirname(get_compiler_path())
            project_root = path_dirname(compiler_dir)
            candidate = path_join(project_root, import_path_with_ext)
            if path_exists(candidate):
                return candidate

            # Try relative to compiler directory itself (for compiler imports)
            candidate = path_join(compiler_dir, import_path_with_ext)
            if path_exists(candidate):
                return candidate

            # Try as absolute path
            if path_exists(import_path_with_ext):
                return import_path_with_ext

        return None

    def _auto_import_stdlib(self, ast: Program, source_dir: str) -> Program:
        """Auto-import standard library files when needed."""
        # Standard library files to auto-import
        stdlib_files = ['lib/list', 'lib/memory', 'lib/dict']

        all_stdlib_decls = []
        for lib_path in stdlib_files:
            import_path = self._resolve_import_path(lib_path, source_dir)
            if import_path is None:
                continue

            abs_path = path_abspath(import_path)
            if abs_path in self.imported_files:
                continue  # Already imported

            self.imported_files.add(abs_path)

            try:
                with open(import_path, 'r') as f:
                    import_source = f.read()

                lexer = Lexer(import_source)
                tokens = lexer.tokenize()

                parser = Parser(tokens)
                imported_ast = parser.parse()

                # Recursively resolve imports in the library
                import_dir = path_dirname(import_path)
                imported_ast = self.resolve_imports(imported_ast, import_dir)

                for decl in imported_ast.declarations:
                    all_stdlib_decls.append(decl)

            except Exception as e:
                # Silently skip if stdlib not found
                continue

        if all_stdlib_decls:
            merged_decls = all_stdlib_decls + ast.declarations
            return Program(declarations=merged_decls, imports=[])
        return ast

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

        # 3.5 Resolve imports
        source_dir = path_dirname(path_abspath(self.source_file))
        self.imported_files.add(path_abspath(self.source_file))  # Mark main file as imported
        if ast.imports:
            print("  [2.5/8] Resolving imports...")
            ast = self.resolve_imports(ast, source_dir)
            print(f"        Now have {len(ast.declarations)} declarations after imports")

        # 3.6 Auto-import standard library files (lib/list.bh, lib/memory.bh)
        ast = self._auto_import_stdlib(ast, source_dir)

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
            cmd = f"clang -m32 -c {self.ll_file} -o {self.obj_file}"
            ret = run(cmd)
            if ret != 0:
                print("ERROR: LLVM compilation failed!")
                return False
            print(f"        Created {self.obj_file}")
        else:
            if self.use_x86_64:
                print("  [7/8] Generating x86_64 assembly...")
                codegen = X86_64CodeGen(kernel_mode=self.kernel_mode)
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
            elf_format = 'elf64' if self.use_x86_64 else 'elf32'
            cmd = f"nasm -f {elf_format} {self.asm_file} -o {self.obj_file}"
            ret = run(cmd)
            if ret != 0:
                print("ERROR: Assembly failed!")
                return False
            print(f"        Created {self.obj_file}")

        # 10. Link (for standalone binary - skip in kernel mode)
        if not self.kernel_mode:
            print("  [9/9] Linking...")
            # Find lib/syscalls.o relative to compiler location
            compiler_dir = path_dirname(path_dirname(get_compiler_path()))
            lib_dir = path_join(compiler_dir, 'lib')
            if self.use_x86_64:
                syscalls_obj = path_join(lib_dir, 'syscalls64.o')
            else:
                syscalls_obj = path_join(lib_dir, 'syscalls.o')
            link_files = [self.obj_file]
            if path_exists(syscalls_obj):
                link_files = [syscalls_obj, self.obj_file]
            ld_emulation = 'elf_x86_64' if self.use_x86_64 else 'elf_i386'
            link_files_str = ' '.join(link_files)
            cmd = f"ld -m {ld_emulation} -o {self.output_file} {link_files_str}"
            ret = run(cmd)
            if ret != 0:
                print("ERROR: Linking failed!")
                return False
            print(f"        Created {self.output_file}")

            print(f"\n✓ Compilation successful!")
            print(f"  Output: {self.output_file}")
            print(f"  Size: {path_getsize(self.output_file)} bytes")
        else:
            print(f"\n✓ Compilation successful!")
            print(f"  Output: {self.obj_file} (kernel object file)")
            print(f"  Size: {path_getsize(self.obj_file)} bytes")

        return True

    def run(self):
        """Compile and run the program"""
        if self.compile():
            print(f"\n[Brainhair] Running {self.output_file}...\n")
            print("=" * 50)
            ret = run(f"./{self.output_file}")
            print("=" * 50)
            return ret
        return 1

def main():
    if argc() < 2:
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
        print("  --x86_64        Generate 64-bit x86_64 code")
        exit(1)

    source_file = argv(1)
    output_file = None
    run_after = False
    asm_only = False
    kernel_mode = False
    check_types = True
    check_ownership = True
    check_lifetimes = True
    use_llvm = False
    emit_llvm = False
    use_x86_64 = False

    # Parse arguments
    i = 2
    while i < argc():
        arg = argv(i)
        if arg == '-o' and i + 1 < argc():
            output_file = argv(i + 1)
            i = i + 2
        elif arg == '--run':
            run_after = True
            i = i + 1
        elif arg == '--asm-only':
            asm_only = True
            i = i + 1
        elif arg == '--kernel':
            kernel_mode = True
            i = i + 1
        elif arg == '--no-typecheck':
            check_types = False
            i = i + 1
        elif arg == '--no-ownership':
            check_ownership = False
            i = i + 1
        elif arg == '--no-lifetimes':
            check_lifetimes = False
            i = i + 1
        elif arg == '--llvm':
            use_llvm = True
            i = i + 1
        elif arg == '--emit-llvm':
            emit_llvm = True
            use_llvm = True
            i = i + 1
        elif arg == '--x86_64':
            use_x86_64 = True
            i = i + 1
        else:
            print(f"Unknown option: {arg}")
            exit(1)

    compiler = Compiler(source_file, output_file, kernel_mode=kernel_mode,
                       check_types=check_types, check_ownership=check_ownership,
                       check_lifetimes=check_lifetimes, use_llvm=use_llvm,
                       use_x86_64=use_x86_64)

    if asm_only or emit_llvm:
        # Just generate assembly/LLVM IR
        with open(source_file, 'r') as f:
            source_code = f.read()

        lexer = Lexer(source_code)
        tokens = lexer.tokenize()

        parser = Parser(tokens)
        ast = parser.parse()

        # Resolve imports (create temp compiler for import resolution)
        if ast.imports:
            temp_compiler = Compiler(source_file, kernel_mode=kernel_mode)
            source_dir = path_dirname(path_abspath(source_file))
            temp_compiler.imported_files.add(path_abspath(source_file))
            ast = temp_compiler.resolve_imports(ast, source_dir)

        # Monomorphize generics
        ast = monomorphize(ast)

        if emit_llvm or use_llvm:
            codegen = LLVMCodeGen()
            llvm_code = codegen.generate(ast)
            print(llvm_code)
        elif use_x86_64:
            codegen = X86_64CodeGen(kernel_mode=kernel_mode)
            asm_code = codegen.generate(ast)
            print(asm_code)
        else:
            codegen = X86CodeGen(kernel_mode=kernel_mode)
            asm_code = codegen.generate(ast)
            print(asm_code)
    elif run_after:
        exit(compiler.run())
    else:
        result = 0 if compiler.compile() else 1
        exit(result)

if __name__ == '__main__':
    main()
