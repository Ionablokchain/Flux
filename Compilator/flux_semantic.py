# flux_semantic.py
from flux_ast import *
from typing import Dict, Set, List

class SemanticAnalyzer:
    def __init__(self):
        self.simboluri: Dict[str, Node] = {}
        self.erori: List[str] = []
        
    def analyze(self, program: Program):
        for decl in program.declaratii:
            if isinstance(decl, IntentieDecl):
                self._verifica_intentie(decl)
            elif isinstance(decl, FluxDecl):
                self._verifica_flux(decl)
            elif isinstance(decl, FunctieDecl):
                self._verifica_functie(decl)
        return self.erori
    
    def _verifica_intentie(self, node: IntentieDecl):
        if node.prioritate is not None and (node.prioritate < 0 or node.prioritate > 1):
            self.erori.append(f"Prioritatea {node.prioritate} nu este în [0,1] (linia {node.linie})")
        # Verifică că declansarea este un eveniment valid
        if node.declansare:
            self._verifica_expresie(node.declansare)
        # Verifică condiția
        if node.conditie:
            self._verifica_expresie(node.conditie)
        # Verifică corpul
        for stmt in node.corp:
            self._verifica_statement(stmt)
    
    def _verifica_flux(self, node: FluxDecl):
        # Fluxurile sunt similare funcțiilor
        pass
    
    def _verifica_functie(self, node: FunctieDecl):
        # Salvăm temporar simbolurile parametrilor
        salvate = self.simboluri.copy()
        for nume, tip in node.parametri:
            self.simboluri[nume] = tip
        for stmt in node.corp:
            self._verifica_statement(stmt)
        self.simboluri = salvate
    
    def _verifica_statement(self, stmt: Node):
        if isinstance(stmt, TrimiteSenzatie):
            # tip trebuie să fie unul dintre: "imagine mentală", "vorbire interioară", etc.
            if stmt.tip not in ("imagine mentală", "vorbire interioară", "senzație tactilă"):
                self.erori.append(f"Tip de senzație necunoscut: {stmt.tip}")
            self._verifica_expresie(stmt.continut)
            if stmt.durata:
                self._verifica_expresie(stmt.durata)
        elif isinstance(stmt, AscultaIntentie):
            if stmt.sursa not in ("utilizator", "sistem", "flux"):
                self.erori.append(f"Sursă invalidă pentru ascultare: {stmt.sursa}")
        elif isinstance(stmt, Colapseaza):
            self._verifica_expresie(stmt.expresie)
            if stmt.metoda not in ("pondere_maximă", "medie", "aleator"):
                self.erori.append(f"Metodă de colaps necunoscută: {stmt.metoda}")
        elif isinstance(stmt, IfNode):
            self._verifica_expresie(stmt.conditie)
            for s in stmt.atunci:
                self._verifica_statement(s)
            for s in stmt.altfel:
                self._verifica_statement(s)
        elif isinstance(stmt, ReturnNode):
            if stmt.valoare:
                self._verifica_expresie(stmt.valoare)
        elif isinstance(stmt, BinOp):
            self._verifica_expresie(stmt)
    
    def _verifica_expresie(self, expr: Node):
        # Simplu: doar traversează
        if isinstance(expr, BinOp):
            self._verifica_expresie(expr.stanga)
            self._verifica_expresie(expr.dreapta)
        elif isinstance(expr, Call):
            # Verifică dacă funcția există
            if expr.nume not in self.simboluri and expr.nume not in ("trimite_senzatie", "asculta_intentie", "colapseaza"):
                self.erori.append(f"Funcție necunoscută: {expr.nume}")
            for arg in expr.argumente:
                self._verifica_expresie(arg)
        # Celelalte cazuri sunt atomi (Ident, NumberLiteral, etc.) – nu necesită verificare suplimentară