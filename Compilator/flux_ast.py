# flux_ast.py
from dataclasses import dataclass, field
from typing import List, Optional, Any, Dict

class Node:
    pass

@dataclass
class Program(Node):
    declaratii: List[Node]

@dataclass
class IntentieDecl(Node):
    nume: str
    declansare: Optional[Node]
    prioritate: Optional[float]
    conditie: Optional[Node]
    corp: List[Node]
    linie: int

@dataclass
class FluxDecl(Node):
    nume: str
    parametri: List[str]
    corp: List[Node]

@dataclass
class StructuraDecl(Node):
    nume: str
    campuri: Dict[str, Node]

@dataclass
class MozaicCauzal(Node):
    nume: str
    componente: Node

@dataclass
class FunctieDecl(Node):
    nume: str
    parametri: List[tuple]  # (nume, tip)
    tip_retur: Optional[str]
    corp: List[Node]

@dataclass
class TrimiteSenzatie(Node):
    tip: str
    continut: Node
    durata: Optional[Node]

@dataclass
class AscultaIntentie(Node):
    sursa: str
    timeout: Optional[Node]
    fallback: Optional[Node]

@dataclass
class Colapseaza(Node):
    expresie: Node
    metoda: str

@dataclass
class Probabilitate(Node):
    valoare: float

@dataclass
class IntervalTemporal(Node):
    start: Node
    end: Node
    unitate: str  # s, ms, ns, cycles

@dataclass
class IfNode(Node):
    conditie: Node
    atunci: List[Node]
    altfel: List[Node] = field(default_factory=list)

@dataclass
class ForNode(Node):
    variabila: str
    in: Node
    corp: List[Node]

@dataclass
class ReturnNode(Node):
    valoare: Optional[Node]

@dataclass
class Ident(Node):
    nume: str

@dataclass
class StringLiteral(Node):
    valoare: str

@dataclass
class NumberLiteral(Node):
    valoare: float

@dataclass
class BinOp(Node):
    stanga: Node
    operator: str
    dreapta: Node

@dataclass
class Call(Node):
    nume: str
    argumente: List[Node]