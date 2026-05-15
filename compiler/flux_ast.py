# flux_ast.py - AST node definitions for Flux
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple


class Node:
    """Base class for all AST nodes."""
    pass


@dataclass
class Program(Node):
    declarations: List[Node]


# ---------- top-level declarations ----------

@dataclass
class IntentionDecl(Node):
    name: str
    trigger: Optional[Node]
    priority: Optional[float]
    condition: Optional[Node]
    body: List[Node]
    line: int = 0


@dataclass
class FlowDecl(Node):
    name: str
    params: List[str]
    body: List[Node]


@dataclass
class FunctionDecl(Node):
    name: str
    params: List[Tuple[str, str]]
    return_type: Optional[str]
    body: List[Node]


@dataclass
class StructDecl(Node):
    name: str
    fields: Dict[str, "Node"]


@dataclass
class CausalMosaicDecl(Node):
    name: str
    components: Node


# ---------- statements ----------

@dataclass
class Let(Node):
    name: str
    value: Node


@dataclass
class Assign(Node):
    name: str
    value: Node


@dataclass
class SendSensation(Node):
    kind: Node
    content: Node
    duration: Optional[Node]


@dataclass
class Collapse(Node):
    expression: Node
    method: str


@dataclass
class IfNode(Node):
    condition: Node
    then_branch: List[Node]
    else_branch: List[Node] = field(default_factory=list)


@dataclass
class ForNode(Node):
    variable: str
    source: Node
    body: List[Node]


@dataclass
class WhileNode(Node):
    condition: Node
    body: List[Node]


@dataclass
class ReturnNode(Node):
    value: Optional[Node]


@dataclass
class Launch(Node):
    """Spawn an intention/flow by name."""
    name: str
    args: List[Node]


@dataclass
class ExpressionStmt(Node):
    expression: Node


# ---------- expressions ----------

@dataclass
class Identifier(Node):
    name: str


@dataclass
class StringLiteral(Node):
    value: str


@dataclass
class NumberLiteral(Node):
    value: float


@dataclass
class BoolLiteral(Node):
    value: bool


@dataclass
class DurationLiteral(Node):
    """A duration value like 5s, 10ms, 500ns. Normalized to nanoseconds."""
    nanoseconds: int
    original: str


@dataclass
class Probability(Node):
    value: float


@dataclass
class ListenIntention(Node):
    source: str
    timeout: Optional[Node]
    fallback: Optional[Node]


@dataclass
class BinOp(Node):
    left: Node
    op: str
    right: Node


@dataclass
class UnaryOp(Node):
    op: str
    operand: Node


@dataclass
class Call(Node):
    name: str
    args: List[Node]


@dataclass
class FieldAccess(Node):
    obj: Node
    field: str


@dataclass
class MethodCall(Node):
    obj: Node
    method: str
    args: List[Node]


@dataclass
class ListLiteral(Node):
    items: List[Node]


@dataclass
class DistLiteral(Node):
    """A discrete distribution literal: dist { v1: w1, v2: w2, ... }.
    Entries are pairs of (value-expression, weight-expression). Weights are
    evaluated at runtime; a non-positive weight drops the entry."""
    entries: List[Tuple[Node, Node]]
