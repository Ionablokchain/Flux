# flux_bytecode.py - Bytecode instruction set for the Temporal VM
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, List, Tuple


class Op(Enum):
    # ---- stack manipulation ----
    PUSH_NUM        = auto()    # arg: float
    PUSH_STR        = auto()    # arg: str
    PUSH_BOOL       = auto()    # arg: bool
    PUSH_DURATION   = auto()    # arg: (nanoseconds: int, original: str)
    PUSH_NIL        = auto()
    POP             = auto()
    DUP             = auto()
    MAKE_LIST       = auto()    # arg: count; pops `count` items and pushes a list
    MAKE_DIST       = auto()    # arg: count; pops `2*count` items (v1,w1,v2,w2,...) and pushes Distribution

    # ---- variables ----
    LOAD_VAR        = auto()    # arg: name
    STORE_VAR       = auto()    # arg: name (top of stack -> var; pops)
    DECLARE_VAR     = auto()    # arg: name (top of stack -> var; pops)

    # ---- arithmetic / comparison ----
    BIN_OP          = auto()    # arg: operator string
    UNARY_OP        = auto()    # arg: operator string

    # ---- control flow ----
    JUMP            = auto()    # arg: absolute bytecode index
    JUMP_IF_FALSE   = auto()    # arg: absolute bytecode index (pops cond)

    # ---- calls ----
    CALL            = auto()    # arg: (name: str, argc: int)
    METHOD_CALL     = auto()    # arg: (method: str, argc: int) - receiver on stack
    FIELD_ACCESS    = auto()    # arg: field name
    RETURN          = auto()    # value is on stack (or NIL pushed before)

    # ---- Flux-specific primitives ----
    SEND_SENSATION  = auto()    # stack: kind, content, duration_or_nil
    LISTEN          = auto()    # arg: (source, has_timeout, has_fallback)
                                # stack pushed by VM
    COLLAPSE        = auto()    # arg: method name; consumes top, pushes result
    LAUNCH          = auto()    # arg: (name: str, argc: int)

    # ---- intention / function frame markers ----
    BEGIN_INTENTION = auto()    # arg: name (purely informational)
    END_INTENTION   = auto()
    HALT            = auto()


@dataclass
class Instr:
    op: Op
    arg: Any = None
    line: int = 0

    def __repr__(self) -> str:
        if self.arg is None:
            return f"{self.op.name}"
        return f"{self.op.name} {self.arg!r}"


@dataclass
class CodeObject:
    """A compiled callable unit (intention, function, or flow)."""
    name: str
    kind: str   # "intention" | "function" | "flow"
    instructions: List[Instr]
    params: List[str]
    # for intentions:
    trigger: Any = None          # raw AST node, evaluated by host
    priority: float = 1.0
    condition: Any = None        # raw AST node, evaluated by host


@dataclass
class Module:
    intentions: List[CodeObject]
    functions: List[CodeObject]
    flows: List[CodeObject]
    mosaics: List[Tuple[str, Any]]   # (name, components AST)

    def get_function(self, name: str):
        for f in self.functions:
            if f.name == name:
                return f
        return None

    def get_intention(self, name: str):
        for i in self.intentions:
            if i.name == name:
                return i
        return None

    def get_flow(self, name: str):
        for f in self.flows:
            if f.name == name:
                return f
        return None
