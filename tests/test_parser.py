# test_parser.py - Unit tests for the Flux parser
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "compiler"))

from flux_lexer import Lexer
from flux_parser import Parser, ParseError
from flux_ast import (
    Program, IntentionDecl, FunctionDecl, Let, Assign, IfNode, WhileNode,
    ForNode, BinOp, UnaryOp, Call, MethodCall, FieldAccess, Identifier,
    StringLiteral, NumberLiteral, BoolLiteral, DurationLiteral, ListLiteral,
    SendSensation, Collapse, ListenIntention, ReturnNode, ExpressionStmt,
)


def parse(src):
    return Parser(Lexer(src).tokenize()).parse()


class TestParser(unittest.TestCase):

    def test_empty_program(self):
        prog = parse("")
        self.assertEqual(prog.declarations, [])

    def test_minimal_intention(self):
        prog = parse('intention X { execute: { send("k","c",1s); } }')
        self.assertEqual(len(prog.declarations), 1)
        intent = prog.declarations[0]
        self.assertIsInstance(intent, IntentionDecl)
        self.assertEqual(intent.name, "X")
        self.assertEqual(len(intent.body), 1)
        self.assertIsInstance(intent.body[0], SendSensation)

    def test_intention_fields(self):
        prog = parse(
            "intention I {"
            "  trigger: on_boot()"
            "  priority: 0.5"
            "  condition: causal_void.exists()"
            "  execute: { send(\"a\",\"b\",1s); }"
            "}"
        )
        intent = prog.declarations[0]
        self.assertIsNotNone(intent.trigger)
        self.assertEqual(intent.priority, 0.5)
        self.assertIsNotNone(intent.condition)
        self.assertIsInstance(intent.condition, MethodCall)

    def test_priority_out_of_range_is_a_parse_value(self):
        # The parser accepts any number; the semantic analyzer enforces [0, 1].
        prog = parse('intention I { priority: 2.0 execute: { send("a","b",1s); } }')
        self.assertEqual(prog.declarations[0].priority, 2.0)

    def test_let_and_assignment(self):
        prog = parse(
            "function f() {"
            "  let x = 1;"
            "  x = x + 2;"
            "  return x;"
            "}"
        )
        body = prog.declarations[0].body
        self.assertIsInstance(body[0], Let)
        self.assertIsInstance(body[1], Assign)
        self.assertIsInstance(body[2], ReturnNode)

    def test_operator_precedence(self):
        # Verify 1 + 2 * 3 parses as 1 + (2 * 3), not (1 + 2) * 3.
        prog = parse("function f() { let r = 1 + 2 * 3; }")
        let_stmt = prog.declarations[0].body[0]
        binop = let_stmt.value
        self.assertIsInstance(binop, BinOp)
        self.assertEqual(binop.op, "+")
        self.assertIsInstance(binop.left, NumberLiteral)
        self.assertEqual(binop.left.value, 1.0)
        # The right side must itself be a multiplication.
        self.assertIsInstance(binop.right, BinOp)
        self.assertEqual(binop.right.op, "*")

    def test_left_associativity(self):
        # 10 - 3 - 2 = (10 - 3) - 2 = 5, not 10 - (3 - 2) = 9.
        prog = parse("function f() { let r = 10 - 3 - 2; }")
        outer = prog.declarations[0].body[0].value
        self.assertEqual(outer.op, "-")
        self.assertIsInstance(outer.left, BinOp)
        self.assertEqual(outer.left.op, "-")
        # Inner left is 10 - 3.
        self.assertEqual(outer.left.left.value, 10.0)
        self.assertEqual(outer.left.right.value, 3.0)
        self.assertEqual(outer.right.value, 2.0)

    def test_comparison_and_logical(self):
        prog = parse(
            "function f() { if x > 0 && y < 10 { return 1; } else { return 0; } }"
        )
        if_node = prog.declarations[0].body[0]
        self.assertIsInstance(if_node, IfNode)
        cond = if_node.condition
        # && has lower precedence than >, < so structure is (x > 0) && (y < 10)
        self.assertEqual(cond.op, "&&")
        self.assertEqual(cond.left.op, ">")
        self.assertEqual(cond.right.op, "<")

    def test_concat_operator(self):
        prog = parse('function f() { let s = "a" ++ "b"; }')
        binop = prog.declarations[0].body[0].value
        self.assertEqual(binop.op, "++")

    def test_for_loop_with_range_literal(self):
        prog = parse("intention I { execute: { for i in [1, 10] { return; } } }")
        for_node = prog.declarations[0].body[0]
        self.assertIsInstance(for_node, ForNode)
        self.assertEqual(for_node.variable, "i")
        self.assertIsInstance(for_node.source, ListLiteral)
        self.assertEqual(len(for_node.source.items), 2)

    def test_while_loop(self):
        prog = parse("intention I { execute: { while x < 10 { x = x + 1; } } }")
        node = prog.declarations[0].body[0]
        self.assertIsInstance(node, WhileNode)

    def test_method_call_chain(self):
        # store.accept("k").write(42, 1.0)
        prog = parse(
            "intention I { execute: { store.accept(\"k\").write(42, 1.0); } }"
        )
        stmt = prog.declarations[0].body[0]
        self.assertIsInstance(stmt, ExpressionStmt)
        outer = stmt.expression
        self.assertIsInstance(outer, MethodCall)
        self.assertEqual(outer.method, "write")
        # Receiver of .write is the .accept(...) call
        self.assertIsInstance(outer.obj, MethodCall)
        self.assertEqual(outer.obj.method, "accept")

    def test_listen_with_timeout_and_fallback(self):
        prog = parse(
            'intention I { execute: { let r = listen(user, 10s, "silence"); } }'
        )
        let_stmt = prog.declarations[0].body[0]
        listen_expr = let_stmt.value
        self.assertIsInstance(listen_expr, ListenIntention)
        self.assertEqual(listen_expr.source, "user")
        self.assertIsInstance(listen_expr.timeout, DurationLiteral)
        self.assertIsInstance(listen_expr.fallback, StringLiteral)

    def test_collapse_as_statement_and_expression(self):
        # Statement form
        prog = parse('intention I { execute: { collapse(0.5, max_weight); } }')
        self.assertIsInstance(prog.declarations[0].body[0], Collapse)
        # Expression form
        prog = parse(
            'intention I { execute: { let v = collapse(0.5, max_weight); } }'
        )
        let_stmt = prog.declarations[0].body[0]
        self.assertIsInstance(let_stmt.value, Collapse)

    def test_if_else_if_chains(self):
        prog = parse(
            "intention I { execute: {"
            "  if x == 1 { return; }"
            "  else if x == 2 { return; }"
            "  else { return; }"
            "} }"
        )
        if_node = prog.declarations[0].body[0]
        self.assertEqual(len(if_node.else_branch), 1)
        self.assertIsInstance(if_node.else_branch[0], IfNode)

    def test_function_with_typed_params_and_return(self):
        prog = parse(
            "function add(a: int, b: int) -> int { return a + b; }"
        )
        fn = prog.declarations[0]
        self.assertIsInstance(fn, FunctionDecl)
        self.assertEqual(fn.params, [("a", "int"), ("b", "int")])
        self.assertEqual(fn.return_type, "int")

    def test_bool_literals(self):
        prog = parse("function f() { let t = true; let f = false; }")
        body = prog.declarations[0].body
        self.assertEqual(body[0].value.value, True)
        self.assertEqual(body[1].value.value, False)

    def test_unary_minus_and_not(self):
        prog = parse("function f() { let r = -1; let b = !true; }")
        body = prog.declarations[0].body
        self.assertIsInstance(body[0].value, UnaryOp)
        self.assertEqual(body[0].value.op, "-")
        self.assertIsInstance(body[1].value, UnaryOp)
        self.assertEqual(body[1].value.op, "!")

    def test_missing_semicolon_raises(self):
        with self.assertRaises(ParseError):
            parse("function f() { let x = 1 }")

    def test_unexpected_top_level_token_raises(self):
        with self.assertRaises(ParseError):
            parse("let x = 1;")  # let is not a top-level declaration


if __name__ == "__main__":
    unittest.main()
