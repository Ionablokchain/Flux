# test_lexer.py - Unit tests for the Flux lexer
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "compiler"))

from flux_lexer import Lexer, LexerError, TokenType


class TestLexer(unittest.TestCase):

    def _types(self, src):
        return [t.type for t in Lexer(src).tokenize()]

    def _values(self, src):
        return [t.value for t in Lexer(src).tokenize()]

    def test_empty_input_just_eof(self):
        toks = Lexer("").tokenize()
        self.assertEqual(len(toks), 1)
        self.assertEqual(toks[0].type, TokenType.EOF)

    def test_keywords_recognized(self):
        types = self._types("intention flow function struct let if else")
        self.assertEqual(types[:7], [
            TokenType.INTENTION, TokenType.FLOW, TokenType.FUNCTION,
            TokenType.STRUCT, TokenType.LET, TokenType.IF, TokenType.ELSE,
        ])

    def test_identifiers_not_keywords(self):
        toks = Lexer("intention_like _x123 a_b").tokenize()
        self.assertEqual(toks[0].type, TokenType.IDENT)
        self.assertEqual(toks[0].value, "intention_like")
        self.assertEqual(toks[1].value, "_x123")
        self.assertEqual(toks[2].value, "a_b")

    def test_integer_vs_float(self):
        toks = Lexer("42 3.14").tokenize()
        self.assertEqual(toks[0].type, TokenType.INTEGER)
        self.assertEqual(toks[0].value, 42)
        self.assertEqual(toks[1].type, TokenType.FLOAT)
        self.assertAlmostEqual(toks[1].value, 3.14)

    def test_duration_units_normalize_to_nanoseconds(self):
        # All four units, plus 'cycles' (kept as raw count).
        cases = [
            ("5s",     5_000_000_000),
            ("10ms",   10_000_000),
            ("500us",  500_000),
            ("250ns",  250),
            ("3cycles", 3),
        ]
        for src, expected_ns in cases:
            toks = Lexer(src).tokenize()
            self.assertEqual(toks[0].type, TokenType.DURATION, msg=src)
            nanos, original = toks[0].value
            self.assertEqual(nanos, expected_ns, msg=src)
            self.assertEqual(original, src)

    def test_duration_with_decimal(self):
        toks = Lexer("2.5s").tokenize()
        self.assertEqual(toks[0].type, TokenType.DURATION)
        nanos, _ = toks[0].value
        self.assertEqual(nanos, 2_500_000_000)

    def test_duration_suffix_not_glued_to_identifier(self):
        # "2species" is integer 2 then identifier "species", not a duration.
        toks = Lexer("2species").tokenize()
        self.assertEqual(toks[0].type, TokenType.INTEGER)
        self.assertEqual(toks[1].type, TokenType.IDENT)
        self.assertEqual(toks[1].value, "species")

    def test_two_char_operators(self):
        toks = Lexer("== != <= >= && || ++ ->").tokenize()
        types = [t.type for t in toks[:-1]]  # drop EOF
        self.assertEqual(types, [
            TokenType.EQ, TokenType.NEQ, TokenType.LE, TokenType.GE,
            TokenType.AND, TokenType.OR, TokenType.CONCAT, TokenType.ARROW,
        ])

    def test_string_escape_sequences(self):
        toks = Lexer(r'"a\nb\tc\""').tokenize()
        self.assertEqual(toks[0].type, TokenType.STRING)
        self.assertEqual(toks[0].value, "a\nb\tc\"")

    def test_unterminated_string_raises(self):
        with self.assertRaises(LexerError):
            Lexer('"never closed').tokenize()

    def test_comments_skipped(self):
        toks = Lexer("# comment\nintention\n// also comment\nflow").tokenize()
        types = [t.type for t in toks[:-1]]
        self.assertEqual(types, [TokenType.INTENTION, TokenType.FLOW])

    def test_line_and_column_tracked(self):
        toks = Lexer("intention\n  Hello").tokenize()
        self.assertEqual(toks[0].line, 1)
        self.assertEqual(toks[1].line, 2)
        self.assertEqual(toks[1].value, "Hello")

    def test_unknown_character_raises(self):
        with self.assertRaises(LexerError):
            Lexer("let x = @").tokenize()


if __name__ == "__main__":
    unittest.main()
