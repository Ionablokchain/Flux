import pytest
from flux.lexer import Lexer
from flux.parser import Parser
from flux.ast import *

def test_parse_intention():
    source = """
    intention Test {
        trigger: on_boot()
        priority: 0.9
        execute: {
            send_sensation("inner", "hi", 1s);
        }
    }
    """
    tokens = Lexer(source).tokenize()
    ast = Parser(tokens).parse()
    assert len(ast.declaratii) == 1
    decl = ast.declaratii[0]
    assert isinstance(decl, IntentieDecl)
    assert decl.nume == "Test"
    assert decl.prioritate == 0.9

def test_parse_function():
    source = "function add(a: int, b: int) -> int { return a + b; }"
    tokens = Lexer(source).tokenize()
    ast = Parser(tokens).parse()
    assert isinstance(ast.declaratii[0], FunctieDecl)