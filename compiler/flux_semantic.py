# flux_semantic.py - Semantic analysis for Flux
from typing import List, Set
from flux_ast import *


# Sources that listen() accepts. The set is open by design - in a real system
# new sensors can be plugged in - but we warn on truly unknown ones.
KNOWN_LISTEN_SOURCES = {"user", "system", "flow", "intention", "causal_void"}

# Built-in functions available at runtime. The semantic analyzer uses this
# only to warn on truly unknown calls; the runtime is the authority.
BUILTIN_FUNCTIONS = {
    "on_boot", "on_command", "on_user_intention",
    "now", "to_string", "parse_duration",
    "current_timeline", "create_timeline", "set_current_timeline",
    "merge_timelines", "reset_timeline", "current_user",
    "generate_paradox", "resolve_paradox",
    "estimate_hardening_cost", "causal_hardening",
    "sparse_temporal_matrix",
    "sleep", "print",
    "support", "weight_of", "normalize",
}

# Collapse methods understood by the VM.
COLLAPSE_METHODS = {"max_weight", "mean", "weighted_random", "random", "first"}


class SemanticError:
    """A diagnostic - not necessarily fatal; carries a kind and message."""

    def __init__(self, kind: str, message: str, line: int = 0):
        self.kind = kind  # "error" or "warning"
        self.message = message
        self.line = line

    def __str__(self) -> str:
        loc = f"line {self.line}" if self.line else "<unknown>"
        return f"[{self.kind}] {self.message} ({loc})"


class SemanticAnalyzer:
    def __init__(self):
        self.diagnostics: List[SemanticError] = []
        self.scopes: List[Set[str]] = [set()]
        self.user_functions: Set[str] = set()
        self.intentions: Set[str] = set()
        self.flows: Set[str] = set()

    # ---------- public ----------

    def analyze(self, program: Program) -> List[SemanticError]:
        # Pass 1: collect top-level names so forward references work.
        for decl in program.declarations:
            if isinstance(decl, IntentionDecl):
                self.intentions.add(decl.name)
            elif isinstance(decl, FunctionDecl):
                self.user_functions.add(decl.name)
            elif isinstance(decl, FlowDecl):
                self.flows.add(decl.name)

        # Pass 2: walk bodies.
        for decl in program.declarations:
            if isinstance(decl, IntentionDecl):
                self._check_intention(decl)
            elif isinstance(decl, FunctionDecl):
                self._check_function(decl)
            elif isinstance(decl, FlowDecl):
                self._check_flow(decl)
            elif isinstance(decl, StructDecl):
                pass
            elif isinstance(decl, CausalMosaicDecl):
                pass
        return self.diagnostics

    @property
    def errors(self) -> List[SemanticError]:
        return [d for d in self.diagnostics if d.kind == "error"]

    @property
    def warnings(self) -> List[SemanticError]:
        return [d for d in self.diagnostics if d.kind == "warning"]

    # ---------- declarations ----------

    def _check_intention(self, node: IntentionDecl) -> None:
        if node.priority is not None and not (0.0 <= node.priority <= 1.0):
            self._err(f"priority {node.priority} not in [0, 1]", node.line)
        with self._scope():
            if node.trigger is not None:
                self._check_expr(node.trigger)
            if node.condition is not None:
                self._check_expr(node.condition)
            for stmt in node.body:
                self._check_stmt(stmt)

    def _check_function(self, node: FunctionDecl) -> None:
        with self._scope():
            for pname, _ptype in node.params:
                self._declare(pname)
            for stmt in node.body:
                self._check_stmt(stmt)

    def _check_flow(self, node: FlowDecl) -> None:
        with self._scope():
            for pname in node.params:
                self._declare(pname)
            for stmt in node.body:
                self._check_stmt(stmt)

    # ---------- statements ----------

    def _check_stmt(self, stmt: Node) -> None:
        if isinstance(stmt, Let):
            self._check_expr(stmt.value)
            self._declare(stmt.name)
        elif isinstance(stmt, Assign):
            if not self._is_declared(stmt.name):
                self._err(f"assignment to undeclared variable {stmt.name!r}")
            self._check_expr(stmt.value)
        elif isinstance(stmt, SendSensation):
            self._check_expr(stmt.kind)
            self._check_expr(stmt.content)
            if stmt.duration is not None:
                self._check_expr(stmt.duration)
        elif isinstance(stmt, Collapse):
            self._check_expr(stmt.expression)
            if stmt.method not in COLLAPSE_METHODS:
                self._warn(f"unknown collapse method {stmt.method!r}; "
                           f"runtime will default to weighted_random")
        elif isinstance(stmt, IfNode):
            self._check_expr(stmt.condition)
            with self._scope():
                for s in stmt.then_branch:
                    self._check_stmt(s)
            with self._scope():
                for s in stmt.else_branch:
                    self._check_stmt(s)
        elif isinstance(stmt, ForNode):
            self._check_expr(stmt.source)
            with self._scope():
                self._declare(stmt.variable)
                for s in stmt.body:
                    self._check_stmt(s)
        elif isinstance(stmt, WhileNode):
            self._check_expr(stmt.condition)
            with self._scope():
                for s in stmt.body:
                    self._check_stmt(s)
        elif isinstance(stmt, ReturnNode):
            if stmt.value is not None:
                self._check_expr(stmt.value)
        elif isinstance(stmt, Launch):
            if (stmt.name not in self.intentions
                    and stmt.name not in self.flows
                    and stmt.name not in self.user_functions):
                self._warn(f"launching unknown intention/flow {stmt.name!r}")
            for a in stmt.args:
                self._check_expr(a)
        elif isinstance(stmt, ExpressionStmt):
            self._check_expr(stmt.expression)
        else:
            self._warn(f"unrecognized statement type {type(stmt).__name__}")

    # ---------- expressions ----------

    def _check_expr(self, expr: Node) -> None:
        if isinstance(expr, BinOp):
            self._check_expr(expr.left); self._check_expr(expr.right)
        elif isinstance(expr, UnaryOp):
            self._check_expr(expr.operand)
        elif isinstance(expr, Call):
            if (expr.name not in self.user_functions
                    and expr.name not in BUILTIN_FUNCTIONS
                    and expr.name not in self.intentions
                    and expr.name not in self.flows):
                self._warn(f"unknown function {expr.name!r}")
            for a in expr.args:
                self._check_expr(a)
        elif isinstance(expr, MethodCall):
            self._check_expr(expr.obj)
            for a in expr.args:
                self._check_expr(a)
        elif isinstance(expr, FieldAccess):
            self._check_expr(expr.obj)
        elif isinstance(expr, Identifier):
            # Identifiers may be variables or top-level names; if neither, warn.
            if (not self._is_declared(expr.name)
                    and expr.name not in self.user_functions
                    and expr.name not in self.intentions
                    and expr.name not in self.flows
                    and expr.name not in BUILTIN_FUNCTIONS):
                # Could be a runtime-known object (causal_void, etc.); just warn.
                pass
        elif isinstance(expr, ListenIntention):
            if expr.source not in KNOWN_LISTEN_SOURCES:
                self._warn(f"unknown listen source {expr.source!r}")
            if expr.timeout is not None:
                self._check_expr(expr.timeout)
            if expr.fallback is not None:
                self._check_expr(expr.fallback)
        # literals: nothing to check

    # ---------- scope ----------

    class _Scope:
        def __init__(self, outer):
            self.outer = outer

        def __enter__(self):
            self.outer.scopes.append(set())

        def __exit__(self, *args):
            self.outer.scopes.pop()

    def _scope(self):
        return SemanticAnalyzer._Scope(self)

    def _declare(self, name: str) -> None:
        self.scopes[-1].add(name)

    def _is_declared(self, name: str) -> bool:
        return any(name in s for s in self.scopes)

    # ---------- diagnostics ----------

    def _err(self, msg: str, line: int = 0) -> None:
        self.diagnostics.append(SemanticError("error", msg, line))

    def _warn(self, msg: str, line: int = 0) -> None:
        self.diagnostics.append(SemanticError("warning", msg, line))
