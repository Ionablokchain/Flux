# test_tvm.py - Unit tests for the Temporal VM
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "compiler"))

from flux_lexer import Lexer
from flux_parser import Parser
from flux_codegen import BytecodeGenerator
from tvm import TemporalVM, InputProvider, OutputSink, Duration, NIL, FluxRuntimeError


def make_vm(src, *, scripted=None, seed=42, capture=True):
    prog = Parser(Lexer(src).tokenize()).parse()
    mod = BytecodeGenerator().generate(prog)
    sink = OutputSink(capture=capture)
    inputs = InputProvider(scripted=scripted)
    vm = TemporalVM(mod, input_provider=inputs, sink=sink, rng_seed=seed)
    vm.install(mod)
    return vm, sink


def run(src, **kwargs):
    vm, sink = make_vm(src, **kwargs)
    vm.run_module()
    return sink


class TestDurationArithmetic(unittest.TestCase):

    def test_duration_addition_normalizes(self):
        d = Duration(2_000_000_000) + Duration(500_000_000)
        self.assertEqual(d.nanos, 2_500_000_000)

    def test_duration_comparison(self):
        self.assertTrue(Duration(1_000_000) < Duration(2_000_000))
        self.assertTrue(Duration(1_000_000) == Duration(1_000_000))
        self.assertFalse(Duration(1_000_000) > Duration(2_000_000))

    def test_duration_scaled_by_number(self):
        # Tested through the VM since the operator dispatch lives there.
        sink = run(
            'intention I { execute: {'
            '  let d = 1s * 3;'
            '  send("k", to_string(d), 0s);'
            '} }'
        )
        # 1s * 3 = 3_000_000_000 ns, which prints as "3s".
        self.assertEqual(sink.events[0][1], "3s")


class TestArithmeticAndComparison(unittest.TestCase):

    def test_integer_arithmetic(self):
        sink = run(
            'intention I { execute: { send("k", to_string(2 + 3 * 4), 0s); } }'
        )
        self.assertEqual(sink.events[0][1], "14")

    def test_subtraction_left_associative(self):
        sink = run(
            'intention I { execute: { send("k", to_string(10 - 3 - 2), 0s); } }'
        )
        # (10 - 3) - 2 = 5
        self.assertEqual(sink.events[0][1], "5")

    def test_division_by_zero_raises(self):
        with self.assertRaises(FluxRuntimeError):
            run('intention I { execute: { let x = 1 / 0; } }')

    def test_modulo(self):
        sink = run(
            'intention I { execute: { send("k", to_string(10 % 3), 0s); } }'
        )
        self.assertEqual(sink.events[0][1], "1")

    def test_string_concat_with_double_plus(self):
        sink = run(
            'intention I { execute: { send("k", "a" ++ "b" ++ "c", 0s); } }'
        )
        self.assertEqual(sink.events[0][1], "abc")

    def test_equality_across_types(self):
        sink = run(
            'intention I { execute: {'
            '  if "x" == "x" { send("k", "yes", 0s); }'
            '  else { send("k", "no", 0s); }'
            '} }'
        )
        self.assertEqual(sink.events[0][1], "yes")


class TestControlFlow(unittest.TestCase):

    def test_if_then(self):
        sink = run(
            'intention I { execute: {'
            '  if true { send("k", "branch_a", 0s); }'
            '  else { send("k", "branch_b", 0s); }'
            '} }'
        )
        self.assertEqual(sink.events[0][1], "branch_a")

    def test_if_else(self):
        sink = run(
            'intention I { execute: {'
            '  if false { send("k", "branch_a", 0s); }'
            '  else { send("k", "branch_b", 0s); }'
            '} }'
        )
        self.assertEqual(sink.events[0][1], "branch_b")

    def test_while_loop_terminates(self):
        sink = run(
            'intention I { execute: {'
            '  let i = 0;'
            '  while i < 3 { i = i + 1; }'
            '  send("k", to_string(i), 0s);'
            '} }'
        )
        self.assertEqual(sink.events[0][1], "3")

    def test_for_range_iterates(self):
        sink = run(
            'intention I { execute: {'
            '  let total = 0;'
            '  for i in [1, 5] { total = total + i; }'
            '  send("k", to_string(total), 0s);'
            '} }'
        )
        # 1+2+3+4+5 = 15
        self.assertEqual(sink.events[0][1], "15")


class TestCollapseSemantics(unittest.TestCase):

    def test_max_weight_picks_highest(self):
        # The VM accepts (value, weight) pairs as a Python list of tuples.
        # From Flux we can't directly construct tuples, so we test via a
        # scalar (which becomes a point distribution).
        vm, sink = make_vm(
            'intention I { execute: { let r = collapse(42, max_weight); '
            'send("k", to_string(r), 0s); } }'
        )
        vm.run_module()
        self.assertEqual(sink.events[0][1], "42")

    def test_weighted_random_is_seeded(self):
        # Same seed -> same result. We collapse a number twice in two VMs
        # and check determinism on a single scalar (trivial) plus that the
        # output is reproducible.
        out1 = run(
            'intention I { execute: { let r = collapse(0.5, weighted_random); '
            'send("k", to_string(r), 0s); } }', seed=7
        )
        out2 = run(
            'intention I { execute: { let r = collapse(0.5, weighted_random); '
            'send("k", to_string(r), 0s); } }', seed=7
        )
        self.assertEqual(out1.events[0][1], out2.events[0][1])

    def test_collapse_dist_via_mosaic_round_trip(self):
        # Write the same key twice with different weights; reading defaults
        # to highest-weight value (most_probable).
        sink = run(
            'causal_mosaic m = sparse_temporal_matrix();'
            'intention I { execute: {'
            '  m.accept("k").write("low", 0.1);'
            '  m.accept("k").write("high", 0.9);'
            '  send("k", m.accept("k").read(), 0s);'
            '} }'
        )
        self.assertEqual(sink.events[0][1], "high")


class TestListenAndInputProvider(unittest.TestCase):

    def test_listen_returns_fallback_by_default(self):
        sink = run(
            'intention I { execute: {'
            '  let r = listen(user, 1s, "default_value");'
            '  send("k", r, 0s);'
            '} }'
        )
        self.assertEqual(sink.events[0][1], "default_value")

    def test_scripted_input_overrides_fallback(self):
        sink = run(
            'intention I { execute: {'
            '  let r = listen(user, 1s, "default_value");'
            '  send("k", r, 0s);'
            '} }',
            scripted={"user": ["scripted_answer"]},
        )
        self.assertEqual(sink.events[0][1], "scripted_answer")

    def test_scripted_input_consumed_in_order(self):
        sink = run(
            'intention I { execute: {'
            '  let a = listen(user, 1s, "fallback");'
            '  let b = listen(user, 1s, "fallback");'
            '  send("k", a ++ "|" ++ b, 0s);'
            '} }',
            scripted={"user": ["first", "second"]},
        )
        self.assertEqual(sink.events[0][1], "first|second")


class TestIntentionPriorityOrdering(unittest.TestCase):

    def test_higher_priority_runs_first(self):
        sink = run(
            'intention Low { priority: 0.1 execute: { send("k", "low", 0s); } }'
            'intention High { priority: 0.9 execute: { send("k", "high", 0s); } }'
        )
        kinds = [e[1] for e in sink.events]
        self.assertEqual(kinds, ["high", "low"])

    def test_condition_false_skips_intention(self):
        sink = run(
            'intention Skip { condition: false execute: { send("k","s",0s); } }'
            'intention Run  { condition: true  execute: { send("k","r",0s); } }'
        )
        self.assertEqual(len(sink.events), 1)
        self.assertEqual(sink.events[0][1], "r")


class TestUserFunctions(unittest.TestCase):

    def test_function_call_with_args_and_return(self):
        sink = run(
            'function add(a: int, b: int) -> int { return a + b; }'
            'intention I { execute: { send("k", to_string(add(2, 3)), 0s); } }'
        )
        self.assertEqual(sink.events[0][1], "5")

    def test_recursive_function(self):
        sink = run(
            'function fact(n: int) -> int {'
            '  if n <= 1 { return 1; }'
            '  return n * fact(n - 1);'
            '}'
            'intention I { execute: { send("k", to_string(fact(5)), 0s); } }'
        )
        # 5! = 120
        self.assertEqual(sink.events[0][1], "120")


class TestTimelineBuiltins(unittest.TestCase):

    def test_current_timeline_starts_at_primary(self):
        sink = run(
            'intention I { execute: { send("k", current_timeline(), 0s); } }'
        )
        self.assertEqual(sink.events[0][1], "primary")

    def test_create_and_switch_timeline(self):
        sink = run(
            'intention I { execute: {'
            '  let t = create_timeline();'
            '  set_current_timeline(t);'
            '  send("k", current_timeline(), 0s);'
            '} }'
        )
        # First created timeline should be timeline_1.
        self.assertEqual(sink.events[0][1], "timeline_1")


class TestSendSensation(unittest.TestCase):

    def test_send_emits_kind_content_duration(self):
        sink = run(
            'intention I { execute: { send("mental_image", "hi", 500ms); } }'
        )
        self.assertEqual(len(sink.events), 1)
        kind, content, duration = sink.events[0]
        self.assertEqual(kind, "mental_image")
        self.assertEqual(content, "hi")
        self.assertIsInstance(duration, Duration)
        self.assertEqual(duration.nanos, 500_000_000)


if __name__ == "__main__":
    unittest.main()
