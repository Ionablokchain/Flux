#!/usr/bin/env python3
# fluxc.py - Compilatorul complet pentru Flux

import sys
from flux_lexer import Lexer
from flux_parser import Parser
from flux_semantic import SemanticAnalyzer
from flux_gen import BytecodeGenerator
from tvm import TemporalVM

def main():
    if len(sys.argv) < 2:
        print("Folosire: fluxc <fisier.flux> [--run]")
        sys.exit(1)
    
    fisier = sys.argv[1]
    with open(fisier, 'r', encoding='utf-8') as f:
        sursa = f.read()
    
    # 1. Lexer
    lexer = Lexer(sursa)
    try:
        tokens = lexer.tokenize()
    except SyntaxError as e:
        print(f"Eroare lexicală: {e}")
        sys.exit(1)
    
    # 2. Parser
    parser = Parser(tokens)
    try:
        ast = parser.parse()
    except SyntaxError as e:
        print(f"Eroare de sintaxă: {e}")
        sys.exit(1)
    
    # 3. Analiză semantică
    semantic = SemanticAnalyzer()
    erori = semantic.analyze(ast)
    if erori:
        print("Erori semantice:")
        for err in erori:
            print(f"  {err}")
        sys.exit(1)
    
    # 4. Generare bytecode
    gen = BytecodeGenerator()
    bytecode = gen.generate(ast)
    
    # Opțional, afișează bytecode-ul
    if "--dump" in sys.argv:
        print("\n=== Bytecode generat ===")
        for instr in bytecode:
            print(instr)
    
    # 5. Executare dacă se specifică --run
    if "--run" in sys.argv:
        print("\n=== Execuție pe TVM ===")
        vm = TemporalVM()
        vm.run(bytecode)
    
if __name__ == "__main__":
    main()