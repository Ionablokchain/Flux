import pytest
from flux.lexer import Lexer, TokenType

def test_empty_input():
    tokens = Lexer("").tokenize()
    assert len(tokens) == 1
    assert tokens[0].tip == TokenType.EOF

def test_keywords():
    source = "intention flux mosaic trigger priority condition execute if else"
    lexer = Lexer(source)
    tokens = lexer.tokenize()
    types = [t.tip for t in tokens if t.tip != TokenType.EOF]
    assert types == [
        TokenType.INTENTIE, TokenType.FLUX, TokenType.MOZAIC, TokenType.TRIGGER,
        TokenType.PRIORITY, TokenType.CONDITION, TokenType.EXECUTE, TokenType.IF,
        TokenType.ELSE
    ]

def test_numbers():
    source = "42 3.14 0.85"
    lexer = Lexer(source)
    tokens = lexer.tokenize()
    values = [t.valoare for t in tokens if t.tip != TokenType.EOF]
    assert values == [42, 3.14, 0.85]

def test_strings():
    source = '"hello" "world"'
    lexer = Lexer(source)
    tokens = lexer.tokenize()
    strings = [t.valoare for t in tokens if t.tip != TokenType.EOF]
    assert strings == ["hello", "world"]