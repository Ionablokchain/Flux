# test_distributions.py - Distribution literals and collapse semantics
import os
import sys
import unittest
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "compiler"))

from flux_lexer import Lexer
from flux_parser import Parser, ParseError
from flux_codegen import BytecodeGenerator
from tvm import TemporalVM, InputProvider, OutputSink, Distribution


def make_vm(src, *, seed=42):
    prog = Parser(Lexer(src).tokenize()).parse()
    mod = BytecodeGenerator().generate(prog)
    sink = OutputSink(capture=True)
    vm = TemporalVM(mod, input_provider=InputProvider(),
                    sink=sink, rng_seed=seed)
    vm.install(mod)
    return vm, sink


def run(src, *, seed=42):
    vm, sink = make_vm(src, seed=seed)
    vm.run_module()
    return sink


class TestDistLiteralParsing(unittest.TestCase):

    def test_dist_literal_parses(self):
        prog = Parser(Lexer(
            'intention I { execute: { let d = dist { "a": 1, "b": 2 }; } }'
        ).tokenize()).parse()
        let_stmt = prog.declarations[0].body[0]
        from flux_ast import DistLiteral
        self.assertIsInstance(let_stmt.value, DistLiteral)
        self.assertEqual(len(let_stmt.value.entries), 2)

    def test_empty_dist_is_rejected(self):
        with self.assertRaises(ParseError):
            Parser(Lexer(
                'intention I { execute: { let d = dist { }; } }'
            ).tokenize()).parse()

    def test_trailing_comma_allowed(self):
        # Should not raise.
        Parser(Lexer(
            'intention I { execute: { let d = dist { "a": 1, }; } }'
        ).tokenize()).parse()

    def test_numeric_keys(self):
        Parser(Lexer(
            'intention I { execute: { let d = dist { 1: 0.5, 2: 0.5 }; } }'
        ).tokenize()).parse()


class TestDistLiteralRuntime(unittest.TestCase):

    def test_dist_is_a_distribution_value(self):
        # Use to_string to introspect the value.
        sink = run(
            'intention I { execute: {'
            '  let d = dist { "a": 1, "b": 2 };'
            '  send("k", to_string(d), 0s);'
            '} }'
        )
        self.assertIn("dist{", sink.events[0][1])
        self.assertIn("a:1", sink.events[0][1])
        self.assertIn("b:2", sink.events[0][1])

    def test_collapse_max_weight_on_dist(self):
        sink = run(
            'intention I { execute: {'
            '  let d = dist { "low": 0.1, "high": 0.9 };'
            '  send("k", collapse(d, max_weight), 0s);'
            '} }'
        )
        self.assertEqual(sink.events[0][1], "high")

    def test_collapse_first_returns_first_entry(self):
        sink = run(
            'intention I { execute: {'
            '  let d = dist { "alpha": 0.1, "beta": 0.9 };'
            '  send("k", collapse(d, first), 0s);'
            '} }'
        )
        self.assertEqual(sink.events[0][1], "alpha")

    def test_collapse_mean_on_numeric_dist(self):
        # Mean of {1: 1, 3: 1} = 2.
        sink = run(
            'intention I { execute: {'
            '  let d = dist { 1: 1, 3: 1 };'
            '  send("k", to_string(collapse(d, mean)), 0s);'
            '} }'
        )
        self.assertEqual(sink.events[0][1], "2")

    def test_collapse_mean_weighted(self):
        # Mean of {1: 0.25, 10: 0.75} = 7.75.
        sink = run(
            'intention I { execute: {'
            '  let d = dist { 1: 0.25, 10: 0.75 };'
            '  send("k", to_string(collapse(d, mean)), 0s);'
            '} }'
        )
        self.assertEqual(sink.events[0][1], "7.75")

    def test_weighted_random_seeded_is_reproducible(self):
        src = (
            'intention I { execute: {'
            '  let d = dist { "x": 0.5, "y": 0.5 };'
            '  send("k", collapse(d, weighted_random), 0s);'
            '} }'
        )
        sink_a = run(src, seed=11)
        sink_b = run(src, seed=11)
        self.assertEqual(sink_a.events[0][1], sink_b.events[0][1])

    def test_zero_weight_entry_dropped(self):
        # An entry with weight 0 must not be sampled.
        # Sample many times; "zero" should never appear.
        seen = Counter()
        for s in range(50):
            sink = run(
                'intention I { execute: {'
                '  let d = dist { "zero": 0, "real": 1 };'
                '  send("k", collapse(d, weighted_random), 0s);'
                '} }',
                seed=s,
            )
            seen[sink.events[0][1]] += 1
        self.assertEqual(seen["zero"], 0)
        self.assertEqual(seen["real"], 50)

    def test_proportions_match_weights_loosely(self):
        # 100 samples from {"a": 0.8, "b": 0.2}: expect mostly "a".
        # We assert a loose lower bound to avoid flakiness while still
        # catching obviously broken weighting.
        seen = Counter()
        for s in range(100):
            sink = run(
                'intention I { execute: {'
                '  let d = dist { "a": 0.8, "b": 0.2 };'
                '  send("k", collapse(d, weighted_random), 0s);'
                '} }',
                seed=s,
            )
            seen[sink.events[0][1]] += 1
        # With p=0.8 and N=100, P(count_a < 60) is ~1e-6. Loose threshold:
        self.assertGreaterEqual(seen["a"], 60,
                                f"weighted sampling looks broken: {dict(seen)}")
        self.assertGreater(seen["b"], 0,
                           "low-weight entry never sampled - RNG dead?")


class TestDistBuiltins(unittest.TestCase):

    def test_support_returns_values_in_order(self):
        sink = run(
            'intention I { execute: {'
            '  let d = dist { "first": 1, "second": 2, "third": 3 };'
            '  let s = support(d);'
            '  send("k", to_string(s), 0s);'
            '} }'
        )
        # support is a Python list printed via str(); just check it
        # contains all three values in order.
        text = sink.events[0][1]
        self.assertLess(text.index("first"), text.index("second"))
        self.assertLess(text.index("second"), text.index("third"))

    def test_weight_of_returns_weight(self):
        sink = run(
            'intention I { execute: {'
            '  let d = dist { "heads": 0.6, "tails": 0.4 };'
            '  send("k", to_string(weight_of(d, "heads")), 0s);'
            '} }'
        )
        self.assertEqual(sink.events[0][1], "0.6")

    def test_weight_of_missing_value_is_zero(self):
        sink = run(
            'intention I { execute: {'
            '  let d = dist { "x": 1 };'
            '  send("k", to_string(weight_of(d, "y")), 0s);'
            '} }'
        )
        self.assertEqual(sink.events[0][1], "0")

    def test_normalize_sums_to_one(self):
        sink = run(
            'intention I { execute: {'
            '  let d = normalize(dist { "a": 3, "b": 1 });'
            '  let total = weight_of(d, "a") + weight_of(d, "b");'
            '  send("k", to_string(total), 0s);'
            '} }'
        )
        # 3/4 + 1/4 = 1
        self.assertEqual(sink.events[0][1], "1")

    def test_normalize_preserves_proportions(self):
        sink = run(
            'intention I { execute: {'
            '  let d = normalize(dist { "a": 3, "b": 1 });'
            '  send("k", to_string(weight_of(d, "a")), 0s);'
            '} }'
        )
        self.assertEqual(sink.events[0][1], "0.75")


if __name__ == "__main__":
    unittest.main()
