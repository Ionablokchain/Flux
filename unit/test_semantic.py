import pytest
from flux.lexer import Lexer
from flux.parser import Parser
from flux.semantic import SemanticAnalyzer

def test_valid_intention():
    source = """
    intention Good {
        trigger: on_boot()
        priority: 0.5
        condition: true
        execute: {
            send_sensation("inner_voice", "ok", 1s);
        }
    }
    """
    tokens = Lexer(source).tokenize()
    ast = Parser(tokens).parse()
    sem = SemanticAnalyzer()
    errors = sem.analyze(ast)
    assert errors == []

def test_invalid_priority():
    source = """
    intention Bad {
        priority: 1.5
        execute: { }
    }
    """
    tokens = Lexer(source).tokenize()
    ast = Parser(tokens).parse()
    sem = SemanticAnalyzer()
    errors = sem.analyze(ast)
    assert any("Prioritatea" in err for err in errors)