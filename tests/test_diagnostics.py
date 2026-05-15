# test_diagnostics.py - Source-aware error message tests
#
# Two parts:
#   1. Renderer tests - verify the visual output for a constructed Diagnostic.
#   2. Pipeline tests - verify that compiler errors carry useful spans and
#      hints, and that the rendered output makes sense for real user mistakes.

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "compiler"))

from flux_diagnostics import (
    Diagnostic, Span, SourceFile, FluxDiagnosticError,
)
from flux_lexer import Lexer, LexerError
from flux_parser import Parser, ParseError


# ---------- renderer ----------

class TestRenderer(unittest.TestCase):

    def test_renders_caret_under_span(self):
        src = SourceFile("x.flux", "let x = 1 + 2\n")
        d = Diagnostic("error", "test message",
                       span=Span(1, 1, 1, 4), hint="point here")
        out = d.render(src)
        # The caret line must align with column 1 (offset 0).
        lines = out.split("\n")
        line_idx = next(i for i, ln in enumerate(lines) if ln.startswith(" 1 |"))
        caret_idx = line_idx + 1
        caret_line = lines[caret_idx]
        # Three carets, starting just after the gutter "  | ".
        self.assertIn("^^^", caret_line)
        self.assertIn("point here", caret_line)

    def test_caret_clamps_to_line_length(self):
        # A span that extends past end-of-line shouldn't crash and shouldn't
        # underline more than the line.
        src = SourceFile("x.flux", "abc\n")
        d = Diagnostic("error", "huh", span=Span(1, 1, 1, 100))
        out = d.render(src)
        # Caret length must be at most the line length (3).
        caret_line = [ln for ln in out.split("\n") if "^" in ln][0]
        # Count consecutive carets in the caret line.
        carets = caret_line.count("^")
        self.assertLessEqual(carets, 3)
        self.assertGreaterEqual(carets, 1)

    def test_renders_filename_and_position(self):
        src = SourceFile("hello.flux", "intention X { }\n")
        d = Diagnostic("error", "bad", span=Span(1, 11, 1, 12))
        out = d.render(src)
        self.assertIn("hello.flux:1:11", out)

    def test_no_span_renders_only_title(self):
        src = SourceFile("x.flux", "")
        d = Diagnostic("error", "no span here", span=None, hint="generic hint")
        out = d.render(src)
        self.assertIn("no span here", out)
        # Caret rendering relies on a span; without one, just the message
        # plus the hint as a note-like trailing line.
        self.assertNotIn("^", out)
        self.assertIn("generic hint", out)

    def test_warning_renders_with_warning_severity(self):
        src = SourceFile("x.flux", "let x = 1\n")
        d = Diagnostic("warning", "ye", span=Span(1, 1, 1, 4))
        out = d.render(src)
        self.assertTrue(out.startswith("warning:"))

    def test_color_codes_only_when_enabled(self):
        src = SourceFile("x.flux", "let x = 1\n")
        d = Diagnostic("error", "ye", span=Span(1, 1, 1, 4))
        plain = d.render(src, color=False)
        colored = d.render(src, color=True)
        self.assertNotIn("\x1b[", plain)
        self.assertIn("\x1b[", colored)


# ---------- lexer diagnostics ----------

class TestLexerDiagnostics(unittest.TestCase):

    def test_unterminated_string_carries_span(self):
        try:
            Lexer('let s = "abc').tokenize()
            self.fail("expected LexerError")
        except LexerError as e:
            self.assertIsNotNone(e.diagnostic.span)
            self.assertIn("unterminated", e.diagnostic.title)
            # Span should start at the opening quote, column 9 (1-based).
            self.assertEqual(e.diagnostic.span.start_col, 9)

    def test_unknown_character_carries_span(self):
        try:
            Lexer("let x = @").tokenize()
            self.fail("expected LexerError")
        except LexerError as e:
            self.assertIsNotNone(e.diagnostic.span)
            self.assertEqual(e.diagnostic.span.start_col, 9)


class TestTokenSpans(unittest.TestCase):

    def test_token_end_column_is_one_past_last_char(self):
        toks = Lexer("foo bar").tokenize()
        foo = toks[0]
        self.assertEqual(foo.column, 1)
        self.assertEqual(foo.end_col, 4)   # 'foo' is at cols 1,2,3; end=4
        bar = toks[1]
        self.assertEqual(bar.column, 5)
        self.assertEqual(bar.end_col, 8)

    def test_two_char_operator_span(self):
        toks = Lexer("a == b").tokenize()
        eq = toks[1]
        self.assertEqual(eq.value, "==")
        self.assertEqual(eq.column, 3)
        self.assertEqual(eq.end_col, 5)

    def test_duration_span(self):
        toks = Lexer("wait 500ms").tokenize()
        dur = toks[1]
        self.assertEqual(dur.column, 6)
        self.assertEqual(dur.end_col, 11)  # '500ms' is 5 chars


# ---------- parser diagnostics ----------

class TestParserDiagnostics(unittest.TestCase):

    def _err(self, src):
        try:
            Parser(Lexer(src).tokenize()).parse()
            self.fail("expected ParseError")
        except ParseError as e:
            return e

    def test_missing_semicolon_points_at_end_of_previous_line(self):
        src = (
            "intention I {\n"
            "    execute: {\n"
            "        let x = 1\n"
            "        send(\"k\",\"c\",1s);\n"
            "    }\n"
            "}\n"
        )
        e = self._err(src)
        d = e.diagnostic
        self.assertIn("';'", d.title)
        # The caret should be on line 3 (the line missing the semicolon),
        # not line 4 (the next token).
        self.assertEqual(d.span.start_line, 3)

    def test_top_level_let_is_rejected_with_helpful_hint(self):
        e = self._err("let x = 1;\n")
        d = e.diagnostic
        self.assertIn("top-level", d.title)
        self.assertIsNotNone(d.hint)
        self.assertIn("intention", d.hint)

    def test_unexpected_token_in_intention_body_has_hint(self):
        src = (
            "intention I {\n"
            "    huh: \"x\"\n"
            "}\n"
        )
        e = self._err(src)
        d = e.diagnostic
        self.assertIsNotNone(d.hint)
        self.assertIn("trigger", d.hint)

    def test_priority_non_numeric_points_at_priority_keyword(self):
        src = (
            "intention I {\n"
            "    priority: \"high\"\n"
            "    execute: { send(\"k\",\"c\",1s); }\n"
            "}\n"
        )
        e = self._err(src)
        d = e.diagnostic
        # The caret should be on line 2, at the 'priority' keyword.
        self.assertEqual(d.span.start_line, 2)
        # Column 5 (1-based) is where 'priority' starts after the indent.
        self.assertEqual(d.span.start_col, 5)

    def test_empty_dist_literal_is_rejected_with_hint(self):
        src = (
            "intention I {\n"
            "    execute: { let d = dist { }; }\n"
            "}\n"
        )
        e = self._err(src)
        d = e.diagnostic
        self.assertIn("empty dist", d.title)
        self.assertIn("value:weight", d.hint)

    def test_missing_collapse_method_has_method_list_hint(self):
        src = (
            "intention I {\n"
            "    execute: { let r = collapse(0.5, ); }\n"
            "}\n"
        )
        e = self._err(src)
        d = e.diagnostic
        self.assertIn("collapse method", d.title)
        self.assertIn("max_weight", d.hint)

    def test_unexpected_expression_token(self):
        src = (
            "intention I { execute: { let x = ; } }\n"
        )
        e = self._err(src)
        d = e.diagnostic
        # The caret should point at the ';', not somewhere random.
        self.assertEqual(d.span.start_line, 1)


# ---------- end-to-end: renderer output for a realistic mistake ----------

class TestEndToEndRendering(unittest.TestCase):

    def test_full_rendering_of_missing_semicolon(self):
        src_text = (
            "intention Greet {\n"
            "    execute: {\n"
            "        let x = 1 + 2\n"
            "        send(\"k\", to_string(x), 0s);\n"
            "    }\n"
            "}\n"
        )
        src = SourceFile("greet.flux", src_text)
        try:
            Parser(Lexer(src_text).tokenize()).parse()
            self.fail("expected ParseError")
        except ParseError as e:
            out = e.diagnostic.render(src)

        # Required elements of the rendered message:
        self.assertIn("error:", out)
        self.assertIn("';'", out)
        self.assertIn("greet.flux:3:", out)
        self.assertIn("let x = 1 + 2", out)
        self.assertIn("^", out)


if __name__ == "__main__":
    unittest.main()
