#!/usr/bin/env python3
"""
Parser Tests for Brainhair Compiler

Tests parsing of various language constructs into AST nodes.
"""

import sys
import os

# Add parent directory to path to import parser
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lexer import Lexer, TokenType
from parser import Parser
from ast_nodes import *

def parse_code(code):
    """Helper function to lex and parse code"""
    lexer = Lexer(code)
    tokens = lexer.tokenize()
    parser = Parser(tokens)
    return parser.parse()

def parse_expression(code):
    """Helper function to parse a single expression"""
    lexer = Lexer(code)
    tokens = lexer.tokenize()
    parser = Parser(tokens)
    return parser.parse_expression()

# ===== Variable Declaration Tests =====

def test_simple_var_declaration():
    """Test parsing a simple variable declaration"""
    ast = parse_code("var x: int32")

    assert_eq(len(ast.declarations), 1, "Should have one declaration")
    decl = ast.declarations[0]

    assert_true(isinstance(decl, VarDecl), "Should be a VarDecl")
    assert_eq(decl.name, "x", "Variable name should be 'x'")
    assert_eq(decl.var_type.name, "int32", "Variable type should be 'int32'")
    assert_eq(decl.value, None, "Should have no initial value")
    assert_eq(decl.is_const, False, "Should not be const")

def test_var_declaration_with_value():
    """Test parsing a variable declaration with initial value"""
    ast = parse_code("var x: int32 = 42")

    decl = ast.declarations[0]

    assert_true(isinstance(decl, VarDecl), "Should be a VarDecl")
    assert_eq(decl.name, "x", "Variable name should be 'x'")
    assert_true(isinstance(decl.value, IntLiteral), "Initial value should be IntLiteral")
    assert_eq(decl.value.value, 42, "Initial value should be 42")

def test_const_declaration():
    """Test parsing a const declaration"""
    ast = parse_code("const PI: int32 = 314")

    decl = ast.declarations[0]

    assert_true(isinstance(decl, VarDecl), "Should be a VarDecl")
    assert_eq(decl.is_const, True, "Should be const")
    assert_eq(decl.name, "PI", "Constant name should be 'PI'")

def test_pointer_type_declaration():
    """Test parsing a pointer type declaration"""
    ast = parse_code("var ptr_var: ptr uint8")

    decl = ast.declarations[0]

    assert_true(isinstance(decl, VarDecl), "Should be a VarDecl")
    assert_true(isinstance(decl.var_type, PointerType), "Should be PointerType")
    assert_eq(decl.var_type.base_type.name, "uint8", "Base type should be uint8")

# ===== Expression Tests =====

def test_integer_literal():
    """Test parsing integer literals"""
    expr = parse_expression("42")

    assert_true(isinstance(expr, IntLiteral), "Should be IntLiteral")
    assert_eq(expr.value, 42, "Value should be 42")

def test_string_literal():
    """Test parsing string literals"""
    expr = parse_expression('"hello world"')

    assert_true(isinstance(expr, StringLiteral), "Should be StringLiteral")
    assert_eq(expr.value, "hello world", "Value should be 'hello world'")

def test_char_literal():
    """Test parsing character literals"""
    expr = parse_expression("'a'")

    assert_true(isinstance(expr, CharLiteral), "Should be CharLiteral")
    assert_eq(expr.value, "a", "Value should be 'a'")

def test_bool_literals():
    """Test parsing boolean literals"""
    expr_true = parse_expression("true")
    expr_false = parse_expression("false")

    assert_true(isinstance(expr_true, BoolLiteral), "Should be BoolLiteral")
    assert_eq(expr_true.value, True, "Value should be True")

    assert_true(isinstance(expr_false, BoolLiteral), "Should be BoolLiteral")
    assert_eq(expr_false.value, False, "Value should be False")

def test_identifier():
    """Test parsing identifiers"""
    expr = parse_expression("myVariable")

    assert_true(isinstance(expr, Identifier), "Should be Identifier")
    assert_eq(expr.name, "myVariable", "Name should be 'myVariable'")

def test_binary_addition():
    """Test parsing binary addition"""
    expr = parse_expression("1 + 2")

    assert_true(isinstance(expr, BinaryExpr), "Should be BinaryExpr")
    assert_eq(expr.op, BinOp.ADD, "Operator should be ADD")
    assert_true(isinstance(expr.left, IntLiteral), "Left should be IntLiteral")
    assert_eq(expr.left.value, 1, "Left value should be 1")
    assert_true(isinstance(expr.right, IntLiteral), "Right should be IntLiteral")
    assert_eq(expr.right.value, 2, "Right value should be 2")

def test_binary_subtraction():
    """Test parsing binary subtraction"""
    expr = parse_expression("10 - 3")

    assert_true(isinstance(expr, BinaryExpr), "Should be BinaryExpr")
    assert_eq(expr.op, BinOp.SUB, "Operator should be SUB")

def test_binary_multiplication():
    """Test parsing binary multiplication"""
    expr = parse_expression("5 * 6")

    assert_true(isinstance(expr, BinaryExpr), "Should be BinaryExpr")
    assert_eq(expr.op, BinOp.MUL, "Operator should be MUL")

def test_binary_division():
    """Test parsing binary division"""
    expr = parse_expression("20 / 4")

    assert_true(isinstance(expr, BinaryExpr), "Should be BinaryExpr")
    assert_eq(expr.op, BinOp.DIV, "Operator should be DIV")

def test_operator_precedence():
    """Test that operator precedence is correct (multiplication before addition)"""
    expr = parse_expression("2 + 3 * 4")

    # Should parse as: 2 + (3 * 4)
    assert_true(isinstance(expr, BinaryExpr), "Should be BinaryExpr")
    assert_eq(expr.op, BinOp.ADD, "Top operator should be ADD")
    assert_true(isinstance(expr.left, IntLiteral), "Left should be IntLiteral")
    assert_eq(expr.left.value, 2, "Left value should be 2")
    assert_true(isinstance(expr.right, BinaryExpr), "Right should be BinaryExpr")
    assert_eq(expr.right.op, BinOp.MUL, "Right operator should be MUL")

def test_parenthesized_expression():
    """Test that parentheses override precedence"""
    expr = parse_expression("(2 + 3) * 4")

    # Should parse as: (2 + 3) * 4
    assert_true(isinstance(expr, BinaryExpr), "Should be BinaryExpr")
    assert_eq(expr.op, BinOp.MUL, "Top operator should be MUL")
    assert_true(isinstance(expr.left, BinaryExpr), "Left should be BinaryExpr")
    assert_eq(expr.left.op, BinOp.ADD, "Left operator should be ADD")

def test_comparison_operators():
    """Test parsing comparison operators"""
    tests = [
        ("1 == 2", BinOp.EQ),
        ("1 != 2", BinOp.NEQ),
        ("1 < 2", BinOp.LT),
        ("1 <= 2", BinOp.LTE),
        ("1 > 2", BinOp.GT),
        ("1 >= 2", BinOp.GTE),
    ]

    for code, expected_op in tests:
        expr = parse_expression(code)
        assert_true(isinstance(expr, BinaryExpr), f"Should be BinaryExpr for {code}")
        assert_eq(expr.op, expected_op, f"Operator should be {expected_op} for {code}")

def test_logical_operators():
    """Test parsing logical operators"""
    expr_and = parse_expression("true and false")
    expr_or = parse_expression("true or false")

    assert_true(isinstance(expr_and, BinaryExpr), "Should be BinaryExpr")
    assert_eq(expr_and.op, BinOp.AND, "Operator should be AND")

    assert_true(isinstance(expr_or, BinaryExpr), "Should be BinaryExpr")
    assert_eq(expr_or.op, BinOp.OR, "Operator should be OR")

def test_unary_negation():
    """Test parsing unary negation"""
    expr = parse_expression("-42")

    assert_true(isinstance(expr, UnaryExpr), "Should be UnaryExpr")
    assert_eq(expr.op, UnaryOp.NEG, "Operator should be NEG")
    assert_true(isinstance(expr.expr, IntLiteral), "Operand should be IntLiteral")
    assert_eq(expr.expr.value, 42, "Operand value should be 42")

def test_unary_not():
    """Test parsing unary not"""
    expr = parse_expression("not true")

    assert_true(isinstance(expr, UnaryExpr), "Should be UnaryExpr")
    assert_eq(expr.op, UnaryOp.NOT, "Operator should be NOT")

def test_function_call():
    """Test parsing function calls"""
    expr = parse_expression("add(1, 2)")

    assert_true(isinstance(expr, CallExpr), "Should be CallExpr")
    assert_eq(expr.func, "add", "Function name should be 'add'")
    assert_eq(len(expr.args), 2, "Should have 2 arguments")
    assert_true(isinstance(expr.args[0], IntLiteral), "First arg should be IntLiteral")
    assert_eq(expr.args[0].value, 1, "First arg value should be 1")

def test_function_call_no_args():
    """Test parsing function call with no arguments"""
    expr = parse_expression("foo()")

    assert_true(isinstance(expr, CallExpr), "Should be CallExpr")
    assert_eq(expr.func, "foo", "Function name should be 'foo'")
    assert_eq(len(expr.args), 0, "Should have 0 arguments")

def test_cast_expression():
    """Test parsing cast expressions"""
    expr = parse_expression("cast[ptr uint8](0xB8000)")

    assert_true(isinstance(expr, CastExpr), "Should be CastExpr")
    assert_true(isinstance(expr.target_type, PointerType), "Target type should be PointerType")
    assert_eq(expr.target_type.base_type.name, "uint8", "Base type should be uint8")
    assert_true(isinstance(expr.expr, IntLiteral), "Expression should be IntLiteral")

def test_array_indexing():
    """Test parsing array indexing"""
    expr = parse_expression("arr[5]")

    assert_true(isinstance(expr, IndexExpr), "Should be IndexExpr")
    assert_true(isinstance(expr.base, Identifier), "Array should be Identifier")
    assert_eq(expr.base.name, "arr", "Array name should be 'arr'")
    assert_true(isinstance(expr.index, IntLiteral), "Index should be IntLiteral")
    assert_eq(expr.index.value, 5, "Index value should be 5")

def test_addr_of_expression():
    """Test parsing address-of expressions"""
    expr = parse_expression("addr(myVar)")

    assert_true(isinstance(expr, AddrOfExpr), "Should be AddrOfExpr")
    assert_true(isinstance(expr.expr, Identifier), "Expression should be Identifier")
    assert_eq(expr.expr.name, "myVar", "Variable name should be 'myVar'")

def test_bitwise_operators():
    """Test parsing bitwise operators"""
    tests = [
        ("1 | 2", BinOp.BIT_OR),
        ("1 & 2", BinOp.BIT_AND),
        ("1 ^ 2", BinOp.BIT_XOR),
        ("1 << 2", BinOp.SHL),
        ("1 >> 2", BinOp.SHR),
    ]

    for code, expected_op in tests:
        expr = parse_expression(code)
        assert_true(isinstance(expr, BinaryExpr), f"Should be BinaryExpr for {code}")
        assert_eq(expr.op, expected_op, f"Operator should be {expected_op} for {code}")

# ===== Statement Tests =====

def test_assignment_statement():
    """Test parsing assignment statements"""
    ast = parse_code("x = 42")

    stmt = ast.declarations[0]

    assert_true(isinstance(stmt, Assignment), "Should be Assignment")
    assert_true(isinstance(stmt.target, Identifier), "Target should be Identifier")
    assert_eq(stmt.target.name, "x", "Target name should be 'x'")
    assert_true(isinstance(stmt.value, IntLiteral), "Value should be IntLiteral")
    assert_eq(stmt.value.value, 42, "Value should be 42")

def test_return_statement():
    """Test parsing return statements"""
    ast = parse_code("proc test(): int32 =\n  return 42")

    proc = ast.declarations[0]
    ret_stmt = proc.body[0]

    assert_true(isinstance(ret_stmt, ReturnStmt), "Should be ReturnStmt")
    assert_true(isinstance(ret_stmt.value, IntLiteral), "Return value should be IntLiteral")
    assert_eq(ret_stmt.value.value, 42, "Return value should be 42")

def test_return_statement_void():
    """Test parsing void return statements"""
    code = """
proc test() =
  return
"""
    ast = parse_code(code)

    proc = ast.declarations[0]
    ret_stmt = proc.body[0]

    assert_true(isinstance(ret_stmt, ReturnStmt), "Should be ReturnStmt")
    assert_eq(ret_stmt.value, None, "Return value should be None for void return")

# ===== Control Flow Tests =====

def test_if_statement():
    """Test parsing if statements"""
    code = """
if x > 0:
  y = 1
"""
    ast = parse_code(code)

    if_stmt = ast.declarations[0]

    assert_true(isinstance(if_stmt, IfStmt), "Should be IfStmt")
    assert_true(isinstance(if_stmt.condition, BinaryExpr), "Condition should be BinaryExpr")
    assert_eq(if_stmt.condition.op, BinOp.GT, "Condition operator should be GT")
    assert_eq(len(if_stmt.then_block), 1, "Then block should have 1 statement")
    assert_true(isinstance(if_stmt.then_block[0], Assignment), "Then block should contain Assignment")

def test_if_else_statement():
    """Test parsing if-else statements"""
    code = """
if x > 0:
  y = 1
else:
  y = 2
"""
    ast = parse_code(code)

    if_stmt = ast.declarations[0]

    assert_true(isinstance(if_stmt, IfStmt), "Should be IfStmt")
    assert_true(if_stmt.else_block is not None, "Should have else block")
    assert_eq(len(if_stmt.else_block), 1, "Else block should have 1 statement")

def test_if_elif_else_statement():
    """Test parsing if-elif-else statements"""
    code = """
if x > 0:
  y = 1
elif x < 0:
  y = 2
else:
  y = 3
"""
    ast = parse_code(code)

    if_stmt = ast.declarations[0]

    assert_true(isinstance(if_stmt, IfStmt), "Should be IfStmt")
    assert_true(if_stmt.elif_blocks is not None, "Should have elif blocks")
    assert_eq(len(if_stmt.elif_blocks), 1, "Should have 1 elif block")
    assert_true(if_stmt.else_block is not None, "Should have else block")

def test_while_statement():
    """Test parsing while statements"""
    code = """
while x > 0:
  x = x - 1
"""
    ast = parse_code(code)

    while_stmt = ast.declarations[0]

    assert_true(isinstance(while_stmt, WhileStmt), "Should be WhileStmt")
    assert_true(isinstance(while_stmt.condition, BinaryExpr), "Condition should be BinaryExpr")
    assert_eq(len(while_stmt.body), 1, "Body should have 1 statement")

def test_for_statement():
    """Test parsing for statements"""
    code = """
for i in 0..10:
  x = x + i
"""
    ast = parse_code(code)

    for_stmt = ast.declarations[0]

    assert_true(isinstance(for_stmt, ForStmt), "Should be ForStmt")
    assert_eq(for_stmt.var, "i", "Loop variable should be 'i'")
    assert_true(isinstance(for_stmt.start, IntLiteral), "Start should be IntLiteral")
    assert_eq(for_stmt.start.value, 0, "Start value should be 0")
    assert_true(isinstance(for_stmt.end, IntLiteral), "End should be IntLiteral")
    assert_eq(for_stmt.end.value, 10, "End value should be 10")
    assert_eq(len(for_stmt.body), 1, "Body should have 1 statement")

def test_break_statement():
    """Test parsing break statements"""
    code = """
while true:
  break
"""
    ast = parse_code(code)

    while_stmt = ast.declarations[0]
    break_stmt = while_stmt.body[0]

    assert_true(isinstance(break_stmt, BreakStmt), "Should be BreakStmt")

def test_continue_statement():
    """Test parsing continue statements"""
    code = """
while true:
  continue
"""
    ast = parse_code(code)

    while_stmt = ast.declarations[0]
    continue_stmt = while_stmt.body[0]

    assert_true(isinstance(continue_stmt, ContinueStmt), "Should be ContinueStmt")

# ===== Function Declaration Tests =====

def test_simple_proc_declaration():
    """Test parsing a simple procedure declaration"""
    code = """
proc foo() =
  return
"""
    ast = parse_code(code)

    proc = ast.declarations[0]

    assert_true(isinstance(proc, ProcDecl), "Should be ProcDecl")
    assert_eq(proc.name, "foo", "Procedure name should be 'foo'")
    assert_eq(len(proc.params), 0, "Should have 0 parameters")
    assert_eq(proc.return_type, None, "Should have no return type")
    assert_eq(len(proc.body), 1, "Body should have 1 statement")

def test_proc_with_parameters():
    """Test parsing a procedure with parameters"""
    code = """
proc add(a: int32, b: int32): int32 =
  return a + b
"""
    ast = parse_code(code)

    proc = ast.declarations[0]

    assert_true(isinstance(proc, ProcDecl), "Should be ProcDecl")
    assert_eq(proc.name, "add", "Procedure name should be 'add'")
    assert_eq(len(proc.params), 2, "Should have 2 parameters")
    assert_eq(proc.params[0].name, "a", "First param name should be 'a'")
    assert_eq(proc.params[0].param_type.name, "int32", "First param type should be 'int32'")
    assert_eq(proc.params[1].name, "b", "Second param name should be 'b'")
    assert_eq(proc.return_type.name, "int32", "Return type should be 'int32'")

def test_proc_with_single_parameter():
    """Test parsing a procedure with one parameter"""
    code = """
proc square(x: int32): int32 =
  return x * x
"""
    ast = parse_code(code)

    proc = ast.declarations[0]

    assert_eq(len(proc.params), 1, "Should have 1 parameter")
    assert_eq(proc.params[0].name, "x", "Parameter name should be 'x'")

def test_extern_declaration():
    """Test parsing extern declarations"""
    code = "extern proc write(msg: ptr uint8, len: int32)"

    ast = parse_code(code)

    extern = ast.declarations[0]

    assert_true(isinstance(extern, ExternDecl), "Should be ExternDecl")
    assert_eq(extern.name, "write", "Function name should be 'write'")
    assert_eq(len(extern.params), 2, "Should have 2 parameters")
    assert_eq(extern.return_type, None, "Should have no return type")

def test_multiple_declarations():
    """Test parsing multiple top-level declarations"""
    code = """
var x: int32 = 42
var y: int32 = 10

proc add(): int32 =
  return x + y
"""
    ast = parse_code(code)

    assert_eq(len(ast.declarations), 3, "Should have 3 declarations")
    assert_true(isinstance(ast.declarations[0], VarDecl), "First should be VarDecl")
    assert_true(isinstance(ast.declarations[1], VarDecl), "Second should be VarDecl")
    assert_true(isinstance(ast.declarations[2], ProcDecl), "Third should be ProcDecl")

def test_nested_blocks():
    """Test parsing nested control flow blocks"""
    code = """
proc test() =
  if x > 0:
    while y > 0:
      y = y - 1
"""
    ast = parse_code(code)

    proc = ast.declarations[0]
    if_stmt = proc.body[0]
    while_stmt = if_stmt.then_block[0]

    assert_true(isinstance(if_stmt, IfStmt), "Should have IfStmt")
    assert_true(isinstance(while_stmt, WhileStmt), "Should have nested WhileStmt")
    assert_eq(len(while_stmt.body), 1, "While body should have 1 statement")

def test_expression_statement():
    """Test parsing expression statements (function calls as statements)"""
    code = """
proc test() =
  foo()
"""
    ast = parse_code(code)

    proc = ast.declarations[0]
    expr_stmt = proc.body[0]

    assert_true(isinstance(expr_stmt, ExprStmt), "Should be ExprStmt")
    assert_true(isinstance(expr_stmt.expr, CallExpr), "Expression should be CallExpr")

def test_parser_error_handling():
    """Test that parser raises errors for invalid syntax"""
    def parse_invalid():
        parse_code("var")  # Incomplete variable declaration

    assert_raises(SyntaxError, parse_invalid, "Should raise SyntaxError for invalid syntax")

def test_complex_expression_in_if():
    """Test parsing complex expressions in if conditions"""
    code = """
if (x > 0) and (y < 10):
  z = 1
"""
    ast = parse_code(code)

    if_stmt = ast.declarations[0]

    assert_true(isinstance(if_stmt.condition, BinaryExpr), "Condition should be BinaryExpr")
    assert_eq(if_stmt.condition.op, BinOp.AND, "Top operator should be AND")
    assert_true(isinstance(if_stmt.condition.left, BinaryExpr), "Left should be comparison")
    assert_true(isinstance(if_stmt.condition.right, BinaryExpr), "Right should be comparison")
