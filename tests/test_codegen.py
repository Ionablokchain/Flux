# test_codegen.py - Unit tests for AST -> bytecode lowering
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "compiler"))

from flux_lexer import Lexer
from flux_parser import Parser
from flux_codegen import BytecodeGenerator
from flux_bytecode import Op


def compile_module(src):
    prog = Parser(Lexer(src).tokenize()).parse()
    return BytecodeGenerator().generate(prog)


def ops(code_obj):
    return [i.op for i in code_obj.instructions]


class TestCodegen(unittest.TestCase):

    def test_intention_compiles_to_a_code_object(self):
        mod = compile_module(
            'intention Hi { priority: 0.5 execute: { send("k","c",1s); } }'
        )
        self.assertEqual(len(mod.intentions), 1)
        co = mod.intentions[0]
        self.assertEqual(co.name, "Hi")
        self.assertEqual(co.kind, "intention")
        self.assertEqual(co.priority, 0.5)
        # Must terminate with RETURN.
        self.assertEqual(co.instructions[-1].op, Op.RETURN)

    def test_let_emits_declare_var(self):
        mod = compile_module(
            'intention I { execute: { let x = 42; } }'
        )
        op_list = ops(mod.intentions[0])
        self.assertIn(Op.PUSH_NUM, op_list)
        self.assertIn(Op.DECLARE_VAR, op_list)

    def test_assignment_emits_store_var(self):
        mod = compile_module(
            'intention I { execute: { let x = 1; x = 2; } }'
        )
        op_list = ops(mod.intentions[0])
        self.assertIn(Op.DECLARE_VAR, op_list)
        self.assertIn(Op.STORE_VAR, op_list)

    def test_if_emits_jump_if_false_and_jump(self):
        mod = compile_module(
            'intention I { execute: {'
            '  if true { send("k","a",1s); } else { send("k","b",1s); }'
            '} }'
        )
        op_list = ops(mod.intentions[0])
        self.assertIn(Op.JUMP_IF_FALSE, op_list)
        self.assertIn(Op.JUMP, op_list)

    def test_while_loop_back_edge(self):
        mod = compile_module(
            'intention I { execute: {'
            '  let i = 0;'
            '  while i < 3 { i = i + 1; }'
            '} }'
        )
        ins = mod.intentions[0].instructions
        # There must be at least one backward JUMP (target < current index).
        backward_jumps = [
            (idx, ins[idx]) for idx in range(len(ins))
            if ins[idx].op is Op.JUMP and ins[idx].arg is not None
            and ins[idx].arg < idx
        ]
        self.assertTrue(backward_jumps, "expected a backward JUMP for the loop")

    def test_for_desugars_to_iter_protocol(self):
        mod = compile_module(
            'intention I { execute: { for x in [1, 5] { send("k","c",1s); } } }'
        )
        calls = [
            i.arg[0] for i in mod.intentions[0].instructions
            if i.op is Op.CALL
        ]
        self.assertIn("__iter", calls)
        self.assertIn("__has_next", calls)
        self.assertIn("__next", calls)

    def test_collapse_statement_pops_result(self):
        mod = compile_module(
            'intention I { execute: { collapse(0.5, max_weight); } }'
        )
        ins = mod.intentions[0].instructions
        # COLLAPSE should be immediately followed by POP (statement form).
        for i, instr in enumerate(ins):
            if instr.op is Op.COLLAPSE:
                self.assertEqual(ins[i + 1].op, Op.POP,
                                 "statement-form collapse must POP its result")
                break
        else:
            self.fail("no COLLAPSE instruction emitted")

    def test_collapse_expression_does_not_pop(self):
        mod = compile_module(
            'intention I { execute: { let v = collapse(0.5, max_weight); } }'
        )
        ins = mod.intentions[0].instructions
        # COLLAPSE should be followed by DECLARE_VAR (consuming the result).
        for i, instr in enumerate(ins):
            if instr.op is Op.COLLAPSE:
                self.assertNotEqual(ins[i + 1].op, Op.POP)
                # The next consuming op should be DECLARE_VAR for v.
                next_ops = [x.op for x in ins[i + 1:i + 3]]
                self.assertIn(Op.DECLARE_VAR, next_ops)
                break
        else:
            self.fail("no COLLAPSE instruction emitted")

    def test_user_function_in_module(self):
        mod = compile_module("function add(a: int, b: int) -> int { return a + b; }")
        self.assertEqual(len(mod.functions), 1)
        fn = mod.functions[0]
        self.assertEqual(fn.params, ["a", "b"])
        # Must end with a RETURN (explicit, in this case).
        self.assertEqual(fn.instructions[-1].op, Op.RETURN)


if __name__ == "__main__":
    unittest.main()
