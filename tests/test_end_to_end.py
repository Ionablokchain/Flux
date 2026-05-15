# test_end_to_end.py - Compile and run every example/integration program.
#
# Each test verifies that the program runs to completion AND emits the
# expected sensations. This is the test that catches regressions in the
# whole pipeline at once.

import os
import sys
import unittest

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, "..", "compiler"))

from flux_lexer import Lexer
from flux_parser import Parser
from flux_codegen import BytecodeGenerator
from tvm import TemporalVM, InputProvider, OutputSink


EXAMPLES_DIR     = os.path.abspath(os.path.join(HERE, "..", "examples"))
INTEGRATION_DIR  = os.path.abspath(os.path.join(HERE, "..", "integration"))
BENCHMARKS_DIR   = os.path.abspath(os.path.join(HERE, "..", "benchmarks"))


def run_file(path, *, seed=42, scripted=None):
    with open(path, "r", encoding="utf-8") as f:
        src = f.read()
    prog = Parser(Lexer(src).tokenize()).parse()
    mod = BytecodeGenerator().generate(prog)
    sink = OutputSink(capture=True)
    inputs = InputProvider(scripted=scripted)
    vm = TemporalVM(mod, input_provider=inputs, sink=sink, rng_seed=seed)
    vm.install(mod)
    vm.run_module()
    return sink


class TestExamples(unittest.TestCase):

    def test_hello(self):
        sink = run_file(os.path.join(EXAMPLES_DIR, "hello.flux"))
        self.assertEqual(len(sink.events), 1)
        kind, content, _ = sink.events[0]
        self.assertEqual(kind, "mental_image")
        self.assertEqual(content, "Hello from Flux")

    def test_probability_demo(self):
        sink = run_file(os.path.join(EXAMPLES_DIR, "probability_demo.flux"), seed=42)
        self.assertEqual(len(sink.events), 1)
        # The result must be either the "heads" or the "tails" branch.
        content = sink.events[0][1]
        self.assertTrue(
            content.startswith("heads") or content == "tails",
            msg=f"unexpected content: {content!r}",
        )

    def test_causal_mosaic_round_trip(self):
        sink = run_file(os.path.join(EXAMPLES_DIR, "causal_mosaic.flux"))
        kinds = [e[0] for e in sink.events]
        # Higher-priority Save runs before lower-priority Load.
        self.assertEqual(kinds, ["tactile", "inner_voice"])
        # The Load result must reflect what Save wrote.
        self.assertEqual(sink.events[1][1], "loaded: default_value")

    def test_paradox_auth_succeeds_deterministically(self):
        sink = run_file(os.path.join(EXAMPLES_DIR, "paradox_auth.flux"))
        self.assertEqual(sink.events[0][1], "access granted")

    def test_timeline_fork(self):
        sink = run_file(os.path.join(EXAMPLES_DIR, "timeline_fork.flux"))
        self.assertEqual(len(sink.events), 2)
        self.assertIn("timeline_1", sink.events[0][1])
        self.assertIn("primary", sink.events[1][1])

    def test_hardening_succeeds(self):
        sink = run_file(os.path.join(EXAMPLES_DIR, "hardening.flux"))
        # estimate_hardening_cost = 0.001 < 0.01, so the success branch runs.
        self.assertIn("hardened", sink.events[0][1])

    def test_neural_chat_default_path(self):
        sink = run_file(os.path.join(EXAMPLES_DIR, "neural_chat.flux"))
        # Default fallback is "hello", which triggers the equality branch.
        self.assertEqual(sink.events[0][1], "hello back")

    def test_neural_chat_scripted_path(self):
        sink = run_file(
            os.path.join(EXAMPLES_DIR, "neural_chat.flux"),
            scripted={"user": ["anything else"]},
        )
        self.assertEqual(sink.events[0][1], "echo: anything else")

    def test_weighted_decision_picks_mode_deterministically(self):
        sink = run_file(os.path.join(EXAMPLES_DIR, "weighted_decision.flux"))
        # The "mode" line always reports "wait" (highest weight at 0.5).
        mode_event = next(e for e in sink.events if "mode is:" in e[1])
        self.assertEqual(mode_event[1], "mode is: wait")

    def test_belief_update_best_guess(self):
        sink = run_file(os.path.join(EXAMPLES_DIR, "belief_update.flux"))
        # Observe runs first (priority 0.9), Believe second (priority 0.5).
        # The "best guess" from the mosaic is the max-weight value: cloudy.
        best = next(e for e in sink.events if "best guess:" in e[1])
        self.assertEqual(best[1], "best guess: cloudy")


class TestIntegration(unittest.TestCase):

    def test_basic_intention(self):
        sink = run_file(os.path.join(INTEGRATION_DIR, "test_basic_intention.flux"))
        self.assertEqual(sink.events[0][1], "integration test passed")

    def test_mosaic(self):
        sink = run_file(os.path.join(INTEGRATION_DIR, "test_mosaic.flux"))
        self.assertEqual(sink.events[0][1], "read: 42")


class TestBenchmarks(unittest.TestCase):
    """The benchmark files use real loops; we just verify they terminate
    and emit one sensation. Performance is not asserted."""

    def test_collapse_speed_terminates(self):
        sink = run_file(os.path.join(BENCHMARKS_DIR, "collapse_speed.flux"))
        self.assertEqual(len(sink.events), 1)
        self.assertIn("10000 collapses", sink.events[0][1])

    def test_timeline_switch_terminates(self):
        sink = run_file(os.path.join(BENCHMARKS_DIR, "timeline_switch.flux"))
        self.assertEqual(len(sink.events), 1)
        self.assertIn("1000 switches", sink.events[0][1])


if __name__ == "__main__":
    unittest.main()
