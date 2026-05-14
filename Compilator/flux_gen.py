# flux_gen.py
from flux_ast import *
from typing import List, Dict

class BytecodeGenerator:
    def __init__(self):
        self.instructions = []
        self.labels = {}
        self.temp_counter = 0
        
    def generate(self, program: Program) -> List[str]:
        for decl in program.declaratii:
            if isinstance(decl, IntentieDecl):
                self._gen_intentie(decl)
            elif isinstance(decl, FluxDecl):
                self._gen_flux(decl)
            elif isinstance(decl, FunctieDecl):
                self._gen_functie(decl)
        return self.instructions
    
    def _gen_intentie(self, node: IntentieDecl):
        # Emite antet intentie
        self.instructions.append(f"INTENTIE {node.nume}")
        if node.prioritate is not None:
            self.instructions.append(f"  PRIORITATE {node.prioritate}")
        if node.declansare:
            self.instructions.append("  DECLANȘARE")
            self._gen_expresie(node.declansare, indent=4)
        if node.conditie:
            self.instructions.append("  CONDIȚIE")
            self._gen_expresie(node.conditie, indent=4)
        self.instructions.append("  EXECUTĂ")
        for stmt in node.corp:
            self._gen_statement(stmt, indent=6)
        self.instructions.append("SFÂRȘIT_INTENTIE")
    
    def _gen_flux(self, node: FluxDecl):
        self.instructions.append(f"FLUX {node.nume}")
        for stmt in node.corp:
            self._gen_statement(stmt, indent=2)
        self.instructions.append("SFÂRȘIT_FLUX")
    
    def _gen_functie(self, node: FunctieDecl):
        self.instructions.append(f"FUNCȚIE {node.nume}")
        for stmt in node.corp:
            self._gen_statement(stmt, indent=2)
        self.instructions.append("SFÂRȘIT_FUNCȚIE")
    
    def _gen_statement(self, stmt: Node, indent: int = 0):
        sp = " " * indent
        if isinstance(stmt, TrimiteSenzatie):
            self.instructions.append(f"{sp}TRIMITE_SENZAȚIE {stmt.tip}")
            self._gen_expresie(stmt.continut, indent+2)
            if stmt.durata:
                self._gen_expresie(stmt.durata, indent+2)
        elif isinstance(stmt, AscultaIntentie):
            self.instructions.append(f"{sp}ASCULTĂ_INTENȚIE {stmt.sursa}")
            if stmt.timeout:
                self._gen_expresie(stmt.timeout, indent+2)
            if stmt.fallback:
                self._gen_expresie(stmt.fallback, indent+2)
        elif isinstance(stmt, Colapseaza):
            self.instructions.append(f"{sp}COLAPSEAZĂ {stmt.metoda}")
            self._gen_expresie(stmt.expresie, indent+2)
        elif isinstance(stmt, IfNode):
            self.instructions.append(f"{sp}DACĂ")
            self._gen_expresie(stmt.conditie, indent+2)
            self.instructions.append(f"{sp}ATUNCI")
            for s in stmt.atunci:
                self._gen_statement(s, indent+4)
            if stmt.altfel:
                self.instructions.append(f"{sp}ALTFEL")
                for s in stmt.altfel:
                    self._gen_statement(s, indent+4)
            self.instructions.append(f"{sp}SFÂRȘIT_DACĂ")
        elif isinstance(stmt, ReturnNode):
            self.instructions.append(f"{sp}RETURNEAZĂ")
            if stmt.valoare:
                self._gen_expresie(stmt.valoare, indent+2)
    
    def _gen_expresie(self, expr: Node, indent: int = 0):
        sp = " " * indent
        if isinstance(expr, BinOp):
            self._gen_expresie(expr.stanga, indent)
            self.instructions.append(f"{sp}OPERATOR {expr.operator}")
            self._gen_expresie(expr.dreapta, indent)
        elif isinstance(expr, NumberLiteral):
            self.instructions.append(f"{sp}NUMĂR {expr.valoare}")
        elif isinstance(expr, Probabilitate):
            self.instructions.append(f"{sp}PROBABILITATE {expr.valoare}")
        elif isinstance(expr, StringLiteral):
            self.instructions.append(f"{sp}STRING \"{expr.valoare}\"")
        elif isinstance(expr, Ident):
            self.instructions.append(f"{sp}IDENT {expr.nume}")
        elif isinstance(expr, Call):
            self.instructions.append(f"{sp}APEL {expr.nume}")
            for arg in expr.argumente:
                self._gen_expresie(arg, indent+2)