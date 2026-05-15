# test_semantic.py - Unit tests for the Flux semantic analyzer
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "compiler"))

from flux_lexer import Lexer
from flux_parser import Parser
from flux_semantic import SemanticAnalyzer


def analyze(src):
    prog = Parser(Lexer(src).tokenize()).parse()
    sa = SemanticAnalyzer()
    diagnostics = sa.analyze(prog)
    return sa, diagnostics


class TestSemantic(unittest.TestCase):

    def test_clean_program_no_errors(self):
        sa, _ = analyze(
            'intention I { execute: { send("k","c",1s); } }'
        )
        self.assertEqual(sa.errors, [])

    def test_priority_out_of_range_is_error(self):
        sa, _ = analyze(
            'intention I { priority: 2.0 execute: { send("k","c",1s); } }'
        )
        self.assertEqual(len(sa.errors), 1)
        self.assertIn("priority", sa.errors[0].message)

    def test_priority_negative_is_error(self):
        sa, _ = analyze(
            'intention I { priority: -0.1 execute: { send("k","c",1s); } }'
        )
        self.assertTrue(any("priority" in e.message for e in sa.errors))

    def test_unknown_collapse_method_is_warning(self):
        sa, _ = analyze(
            'intention I { execute: { collapse(0.5, weird_method); } }'
        )
        self.assertEqual(sa.errors, [])
        self.assertTrue(any("collapse method" in w.message for w in sa.warnings))

    def test_known_collapse_methods_no_warning(self):
        for m in ("max_weight", "mean", "weighted_random", "random", "first"):
            sa, _ = analyze(
                f'intention I {{ execute: {{ collapse(0.5, {m}); }} }}'
            )
            self.assertFalse(
                any("collapse method" in w.message for w in sa.warnings),
                msg=f"unexpected warning for method {m}",
            )

    def test_undeclared_assignment_is_error(self):
        sa, _ = analyze(
            'intention I { execute: { x = 1; } }'
        )
        self.assertTrue(
            any("undeclared" in e.message for e in sa.errors)
        )

    def test_let_followed_by_assignment_is_ok(self):
        sa, _ = analyze(
            'intention I { execute: { let x = 1; x = x + 1; } }'
        )
        self.assertEqual(sa.errors, [])

    def test_launch_unknown_unit_is_warning(self):
        sa, _ = analyze(
            'intention I { execute: { launch(Nope); } }'
        )
        self.assertTrue(any("Nope" in w.message for w in sa.warnings))

    def test_launch_known_intention_no_warning(self):
        sa, _ = analyze(
            'intention A { execute: { send("k","c",1s); } }'
            'intention B { execute: { launch(A); } }'
        )
        self.assertFalse(any("unknown" in w.message for w in sa.warnings))

    def test_scopes_isolate_variables(self):
        # `x` declared inside the `if` should not leak to the outer scope.
        sa, _ = analyze(
            'intention I { execute: {'
            '  if true { let x = 1; }'
            '  x = 2;'
            '} }'
        )
        self.assertTrue(
            any("undeclared" in e.message for e in sa.errors),
            msg="expected an error: x declared in inner scope leaked outward",
        )

    def test_unknown_listen_source_warns(self):
        sa, _ = analyze(
            'intention I { execute: { let r = listen(martian, 1s, "x"); } }'
        )
        self.assertTrue(any("martian" in w.message for w in sa.warnings))


if __name__ == "__main__":
    unittest.main()
