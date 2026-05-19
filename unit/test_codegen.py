from flux.lexer import Lexer
from flux.parser import Parser
from flux.codegen import BytecodeGenerator

def test_codegen_simple():
    source = 'intention X { execute: { send_sensation("tactile", "buzz", 500ms); } }'
    tokens = Lexer(source).tokenize()
    ast = Parser(tokens).parse()
    gen = BytecodeGenerator()
    bc = gen.generate(ast)
    assert "INTENTIE X" in bc
    assert "TRIMITE_SENZAȚIE tactile" in bc