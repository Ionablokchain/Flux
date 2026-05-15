# flux_lexer.py - Tokenizer for Flux
from dataclasses import dataclass
from enum import Enum, auto
from typing import List, Any


class TokenType(Enum):
    # keywords - declarations
    INTENTION = auto()
    FLOW = auto()
    FUNCTION = auto()
    STRUCT = auto()
    CAUSAL_MOSAIC = auto()
    # keywords - statements
    LET = auto()
    IF = auto()
    ELSE = auto()
    FOR = auto()
    WHILE = auto()
    IN = auto()
    RETURN = auto()
    LAUNCH = auto()
    SEND = auto()
    LISTEN = auto()
    COLLAPSE = auto()
    DIST = auto()
    # keywords - intention fields
    TRIGGER = auto()
    PRIORITY = auto()
    CONDITION = auto()
    EXECUTE = auto()
    # keywords - literals
    TRUE = auto()
    FALSE = auto()

    # punctuation / operators
    ASSIGN = auto()        # =
    EQ = auto()            # ==
    NEQ = auto()           # !=
    LT = auto()            # <
    GT = auto()            # >
    LE = auto()            # <=
    GE = auto()            # >=
    AND = auto()           # &&
    OR = auto()            # ||
    NOT = auto()           # !
    PLUS = auto()          # +
    MINUS = auto()         # -
    STAR = auto()          # *
    SLASH = auto()         # /
    PERCENT = auto()       # %
    CONCAT = auto()        # ++
    DOT = auto()           # .
    COMMA = auto()         # ,
    COLON = auto()         # :
    SEMICOLON = auto()     # ;
    ARROW = auto()         # ->
    LPAREN = auto()
    RPAREN = auto()
    LBRACE = auto()
    RBRACE = auto()
    LBRACKET = auto()
    RBRACKET = auto()

    # literals / identifiers
    IDENT = auto()
    INTEGER = auto()
    FLOAT = auto()
    STRING = auto()
    DURATION = auto()      # (nanoseconds: int, original: str)

    EOF = auto()


KEYWORDS = {
    "intention": TokenType.INTENTION,
    "flow": TokenType.FLOW,
    "function": TokenType.FUNCTION,
    "struct": TokenType.STRUCT,
    "causal_mosaic": TokenType.CAUSAL_MOSAIC,
    "let": TokenType.LET,
    "if": TokenType.IF,
    "else": TokenType.ELSE,
    "for": TokenType.FOR,
    "while": TokenType.WHILE,
    "in": TokenType.IN,
    "return": TokenType.RETURN,
    "launch": TokenType.LAUNCH,
    "send": TokenType.SEND,
    "listen": TokenType.LISTEN,
    "collapse": TokenType.COLLAPSE,
    "dist": TokenType.DIST,
    "trigger": TokenType.TRIGGER,
    "priority": TokenType.PRIORITY,
    "condition": TokenType.CONDITION,
    "execute": TokenType.EXECUTE,
    "true": TokenType.TRUE,
    "false": TokenType.FALSE,
}


@dataclass
class Token:
    type: TokenType
    value: Any
    line: int
    column: int
    end_line: int = 0    # if 0, treated as `line`
    end_col: int = 0     # if 0, treated as `column + 1`

    def __repr__(self) -> str:
        return f"Token({self.type.name}, {self.value!r}, L{self.line}:C{self.column})"

    def span(self):
        from flux_diagnostics import Span
        return Span(self.line, self.column,
                    self.end_line or self.line,
                    self.end_col or (self.column + 1))


# Duration unit -> nanoseconds multiplier
_DURATION_UNITS = {
    "ns": 1,
    "us": 1_000,
    "ms": 1_000_000,
    "s":  1_000_000_000,
    "cycles": 1,    # logical cycles, unit-less; kept as-is for hardware DSL feel
}


from flux_diagnostics import Span, FluxDiagnosticError


class LexerError(FluxDiagnosticError):
    """Backwards-compatible alias - lexer errors are diagnostic errors."""
    pass


class Lexer:
    def __init__(self, source: str):
        self.source = source
        self.pos = 0
        self.line = 1
        self.column = 1
        self.tokens: List[Token] = []

    def tokenize(self) -> List[Token]:
        while self.pos < len(self.source):
            ch = self.source[self.pos]

            if ch.isspace():
                self._advance()
                continue
            if ch == "#":
                self._skip_comment()
                continue
            if ch == "/" and self._peek(1) == "/":
                self._skip_comment()
                continue
            if ch.isalpha() or ch == "_":
                self._read_identifier_or_keyword()
                continue
            if ch.isdigit():
                self._read_number_or_duration()
                continue
            if ch == '"':
                self._read_string()
                continue

            # operators and punctuation
            if self._match2("=="):
                self._add_with_width(TokenType.EQ, "==", 2); continue
            if self._match2("!="):
                self._add_with_width(TokenType.NEQ, "!=", 2); continue
            if self._match2("<="):
                self._add_with_width(TokenType.LE, "<=", 2); continue
            if self._match2(">="):
                self._add_with_width(TokenType.GE, ">=", 2); continue
            if self._match2("&&"):
                self._add_with_width(TokenType.AND, "&&", 2); continue
            if self._match2("||"):
                self._add_with_width(TokenType.OR, "||", 2); continue
            if self._match2("++"):
                self._add_with_width(TokenType.CONCAT, "++", 2); continue
            if self._match2("->"):
                self._add_with_width(TokenType.ARROW, "->", 2); continue

            single = {
                "=": TokenType.ASSIGN, "<": TokenType.LT, ">": TokenType.GT,
                "!": TokenType.NOT, "+": TokenType.PLUS, "-": TokenType.MINUS,
                "*": TokenType.STAR, "/": TokenType.SLASH, "%": TokenType.PERCENT,
                ".": TokenType.DOT, ",": TokenType.COMMA, ":": TokenType.COLON,
                ";": TokenType.SEMICOLON,
                "(": TokenType.LPAREN, ")": TokenType.RPAREN,
                "{": TokenType.LBRACE, "}": TokenType.RBRACE,
                "[": TokenType.LBRACKET, "]": TokenType.RBRACKET,
            }
            if ch in single:
                self._add(single[ch], ch)
                self._advance()
                continue

            raise LexerError(
                f"unknown character {ch!r}",
                span=Span(self.line, self.column,
                          self.line, self.column + 1),
                hint="this character is not part of the Flux syntax",
            )

        self._add(TokenType.EOF, None)
        return self.tokens

    # ---------- helpers ----------

    def _advance(self) -> None:
        if self.source[self.pos] == "\n":
            self.line += 1
            self.column = 1
        else:
            self.column += 1
        self.pos += 1

    def _peek(self, offset: int = 1) -> str:
        p = self.pos + offset
        return self.source[p] if p < len(self.source) else "\0"

    def _match2(self, s: str) -> bool:
        if self.pos + 1 < len(self.source) and self.source[self.pos:self.pos + 2] == s:
            self._advance(); self._advance()
            return True
        return False

    def _add(self, t: TokenType, value: Any) -> None:
        # Single-char punctuator: `self.column` here is still the column of
        # the character about to be consumed (advance happens after _add).
        col = self.column
        self.tokens.append(Token(t, value, self.line, col,
                                 self.line, col + 1))

    def _add_with_width(self, t: TokenType, value: Any, width: int) -> None:
        # Multi-char operator already consumed by _match2; column has moved.
        end_col = self.column
        start_col = end_col - width
        self.tokens.append(Token(t, value, self.line, start_col,
                                 self.line, end_col))

    def _skip_comment(self) -> None:
        while self.pos < len(self.source) and self.source[self.pos] != "\n":
            self._advance()

    def _read_identifier_or_keyword(self) -> None:
        start = self.pos
        start_col = self.column
        while self.pos < len(self.source) and (
            self.source[self.pos].isalnum() or self.source[self.pos] == "_"
        ):
            self._advance()
        text = self.source[start:self.pos]
        tt = KEYWORDS.get(text, TokenType.IDENT)
        end_col = self.column
        tok = Token(tt, text, self.line, start_col, self.line, end_col)
        self.tokens.append(tok)

    def _read_number_or_duration(self) -> None:
        start = self.pos
        start_col = self.column
        is_float = False
        while self.pos < len(self.source) and self.source[self.pos].isdigit():
            self._advance()
        if self.pos < len(self.source) and self.source[self.pos] == "." and self._peek(1).isdigit():
            is_float = True
            self._advance()
            while self.pos < len(self.source) and self.source[self.pos].isdigit():
                self._advance()
        number_text = self.source[start:self.pos]

        # Try to read a duration suffix (longest match: cycles, ms, us, ns, s)
        suffix = ""
        for candidate in ("cycles", "ms", "us", "ns", "s"):
            end = self.pos + len(candidate)
            if end <= len(self.source) and self.source[self.pos:end] == candidate:
                # must not be followed by alphanumeric (would be an identifier glued on)
                next_ch = self.source[end] if end < len(self.source) else ""
                if not (next_ch.isalnum() or next_ch == "_"):
                    suffix = candidate
                    for _ in range(len(candidate)):
                        self._advance()
                    break

        if suffix:
            mult = _DURATION_UNITS[suffix]
            if is_float:
                nanos = int(float(number_text) * mult)
            else:
                nanos = int(number_text) * mult
            end_col = self.column
            tok = Token(TokenType.DURATION, (nanos, number_text + suffix),
                        self.line, start_col, self.line, end_col)
            self.tokens.append(tok)
            return

        end_col = self.column
        if is_float:
            tok = Token(TokenType.FLOAT, float(number_text),
                        self.line, start_col, self.line, end_col)
        else:
            tok = Token(TokenType.INTEGER, int(number_text),
                        self.line, start_col, self.line, end_col)
        self.tokens.append(tok)

    def _read_string(self) -> None:
        start_line = self.line
        start_col = self.column
        self._advance()  # opening quote
        buf = []
        while self.pos < len(self.source) and self.source[self.pos] != '"':
            ch = self.source[self.pos]
            if ch == "\\":
                self._advance()
                if self.pos >= len(self.source):
                    raise LexerError(
                        "unterminated string literal",
                        span=Span(start_line, start_col,
                                  start_line, start_col + 1),
                        hint="string opened here is never closed",
                    )
                esc = self.source[self.pos]
                buf.append({"n": "\n", "t": "\t", "r": "\r", '"': '"', "\\": "\\"}.get(esc, esc))
                self._advance()
            else:
                buf.append(ch)
                self._advance()
        if self.pos >= len(self.source):
            raise LexerError(
                "unterminated string literal",
                span=Span(start_line, start_col,
                          start_line, start_col + 1),
                hint="string opened here is never closed",
            )
        self._advance()  # closing quote
        end_col = self.column
        tok = Token(TokenType.STRING, "".join(buf),
                    start_line, start_col, self.line, end_col)
        self.tokens.append(tok)
