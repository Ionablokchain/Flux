# flux_codegen.py - AST -> bytecode lowering
from typing import List
from flux_ast import *
from flux_bytecode import Op, Instr, CodeObject, Module


class CodegenError(Exception):
    pass


class _Emitter:
    def __init__(self):
        self.instructions: List[Instr] = []

    def emit(self, op: Op, arg=None) -> int:
        idx = len(self.instructions)
        self.instructions.append(Instr(op, arg))
        return idx

    def patch_jump(self, idx: int, target: int) -> None:
        self.instructions[idx] = Instr(self.instructions[idx].op, target)

    def here(self) -> int:
        return len(self.instructions)


class BytecodeGenerator:
    def __init__(self):
        pass

    def generate(self, program: Program) -> Module:
        intentions, functions, flows = [], [], []
        mosaics = []
        for decl in program.declarations:
            if isinstance(decl, IntentionDecl):
                intentions.append(self._gen_intention(decl))
            elif isinstance(decl, FunctionDecl):
                functions.append(self._gen_function(decl))
            elif isinstance(decl, FlowDecl):
                flows.append(self._gen_flow(decl))
            elif isinstance(decl, CausalMosaicDecl):
                mosaics.append((decl.name, decl.components))
            # struct declarations are not codegen'd; runtime is dynamic
        return Module(intentions, functions, flows, mosaics)

    # ---------- top-level units ----------

    def _gen_intention(self, decl: IntentionDecl) -> CodeObject:
        e = _Emitter()
        e.emit(Op.BEGIN_INTENTION, decl.name)
        self._gen_block(decl.body, e)
        e.emit(Op.PUSH_NIL)
        e.emit(Op.RETURN)
        return CodeObject(
            name=decl.name, kind="intention",
            instructions=e.instructions, params=[],
            trigger=decl.trigger,
            priority=decl.priority if decl.priority is not None else 1.0,
            condition=decl.condition,
        )

    def _gen_function(self, decl: FunctionDecl) -> CodeObject:
        e = _Emitter()
        self._gen_block(decl.body, e)
        # implicit return nil if not present
        if not e.instructions or e.instructions[-1].op != Op.RETURN:
            e.emit(Op.PUSH_NIL)
            e.emit(Op.RETURN)
        return CodeObject(
            name=decl.name, kind="function",
            instructions=e.instructions,
            params=[p[0] for p in decl.params],
        )

    def _gen_flow(self, decl: FlowDecl) -> CodeObject:
        e = _Emitter()
        self._gen_block(decl.body, e)
        if not e.instructions or e.instructions[-1].op != Op.RETURN:
            e.emit(Op.PUSH_NIL)
            e.emit(Op.RETURN)
        return CodeObject(
            name=decl.name, kind="flow",
            instructions=e.instructions,
            params=list(decl.params),
        )

    # ---------- statements ----------

    def _gen_block(self, stmts: List[Node], e: _Emitter) -> None:
        for s in stmts:
            self._gen_stmt(s, e)

    def _gen_stmt(self, stmt: Node, e: _Emitter) -> None:
        if isinstance(stmt, Let):
            self._gen_expr(stmt.value, e)
            e.emit(Op.DECLARE_VAR, stmt.name)
        elif isinstance(stmt, Assign):
            self._gen_expr(stmt.value, e)
            e.emit(Op.STORE_VAR, stmt.name)
        elif isinstance(stmt, SendSensation):
            self._gen_expr(stmt.kind, e)
            self._gen_expr(stmt.content, e)
            if stmt.duration is not None:
                self._gen_expr(stmt.duration, e)
            else:
                e.emit(Op.PUSH_NIL)
            e.emit(Op.SEND_SENSATION)
        elif isinstance(stmt, Collapse):
            self._gen_expr(stmt.expression, e)
            e.emit(Op.COLLAPSE, stmt.method)
            # collapse pushes a result; this is a statement so discard it
            e.emit(Op.POP)
        elif isinstance(stmt, IfNode):
            self._gen_if(stmt, e)
        elif isinstance(stmt, ForNode):
            self._gen_for(stmt, e)
        elif isinstance(stmt, WhileNode):
            self._gen_while(stmt, e)
        elif isinstance(stmt, ReturnNode):
            if stmt.value is not None:
                self._gen_expr(stmt.value, e)
            else:
                e.emit(Op.PUSH_NIL)
            e.emit(Op.RETURN)
        elif isinstance(stmt, Launch):
            for a in stmt.args:
                self._gen_expr(a, e)
            e.emit(Op.LAUNCH, (stmt.name, len(stmt.args)))
        elif isinstance(stmt, ExpressionStmt):
            self._gen_expr(stmt.expression, e)
            # statement-level expression: discard result
            e.emit(Op.POP)
        else:
            raise CodegenError(f"unhandled statement: {type(stmt).__name__}")

    def _gen_if(self, stmt: IfNode, e: _Emitter) -> None:
        self._gen_expr(stmt.condition, e)
        jfalse = e.emit(Op.JUMP_IF_FALSE, None)
        self._gen_block(stmt.then_branch, e)
        jend = e.emit(Op.JUMP, None)
        e.patch_jump(jfalse, e.here())
        if stmt.else_branch:
            self._gen_block(stmt.else_branch, e)
        e.patch_jump(jend, e.here())

    def _gen_while(self, stmt: WhileNode, e: _Emitter) -> None:
        loop_start = e.here()
        self._gen_expr(stmt.condition, e)
        jexit = e.emit(Op.JUMP_IF_FALSE, None)
        self._gen_block(stmt.body, e)
        e.emit(Op.JUMP, loop_start)
        e.patch_jump(jexit, e.here())

    def _gen_for(self, stmt: ForNode, e: _Emitter) -> None:
        # Desugar `for i in expr { body }` into:
        #   let __iter = builtin_iter(expr)
        #   while builtin_has_next(__iter) {
        #     let i = builtin_next(__iter)
        #     body
        #   }
        # We use special call names that the VM handles.
        iter_var = f"__iter_{id(stmt)}"
        self._gen_expr(stmt.source, e)
        e.emit(Op.CALL, ("__iter", 1))
        e.emit(Op.DECLARE_VAR, iter_var)

        loop_start = e.here()
        e.emit(Op.LOAD_VAR, iter_var)
        e.emit(Op.CALL, ("__has_next", 1))
        jexit = e.emit(Op.JUMP_IF_FALSE, None)

        e.emit(Op.LOAD_VAR, iter_var)
        e.emit(Op.CALL, ("__next", 1))
        e.emit(Op.DECLARE_VAR, stmt.variable)
        self._gen_block(stmt.body, e)
        e.emit(Op.JUMP, loop_start)
        e.patch_jump(jexit, e.here())

    # ---------- expressions ----------

    def _gen_expr(self, expr: Node, e: _Emitter) -> None:
        if isinstance(expr, NumberLiteral):
            e.emit(Op.PUSH_NUM, float(expr.value))
        elif isinstance(expr, StringLiteral):
            e.emit(Op.PUSH_STR, expr.value)
        elif isinstance(expr, BoolLiteral):
            e.emit(Op.PUSH_BOOL, bool(expr.value))
        elif isinstance(expr, DurationLiteral):
            e.emit(Op.PUSH_DURATION, (expr.nanoseconds, expr.original))
        elif isinstance(expr, Probability):
            e.emit(Op.PUSH_NUM, float(expr.value))
        elif isinstance(expr, Identifier):
            e.emit(Op.LOAD_VAR, expr.name)
        elif isinstance(expr, BinOp):
            self._gen_expr(expr.left, e)
            self._gen_expr(expr.right, e)
            e.emit(Op.BIN_OP, expr.op)
        elif isinstance(expr, UnaryOp):
            self._gen_expr(expr.operand, e)
            e.emit(Op.UNARY_OP, expr.op)
        elif isinstance(expr, Call):
            for a in expr.args:
                self._gen_expr(a, e)
            e.emit(Op.CALL, (expr.name, len(expr.args)))
        elif isinstance(expr, MethodCall):
            self._gen_expr(expr.obj, e)
            for a in expr.args:
                self._gen_expr(a, e)
            e.emit(Op.METHOD_CALL, (expr.method, len(expr.args)))
        elif isinstance(expr, FieldAccess):
            self._gen_expr(expr.obj, e)
            e.emit(Op.FIELD_ACCESS, expr.field)
        elif isinstance(expr, ListenIntention):
            # Source is a static identifier; timeout/fallback (if any) are
            # pushed in order before LISTEN. The instruction knows which to pop.
            has_timeout = expr.timeout is not None
            has_fallback = expr.fallback is not None
            if has_timeout:
                self._gen_expr(expr.timeout, e)
            if has_fallback:
                self._gen_expr(expr.fallback, e)
            e.emit(Op.LISTEN, (expr.source, has_timeout, has_fallback))
        elif isinstance(expr, Collapse):
            self._gen_expr(expr.expression, e)
            e.emit(Op.COLLAPSE, expr.method)
        elif isinstance(expr, ListLiteral):
            for item in expr.items:
                self._gen_expr(item, e)
            e.emit(Op.MAKE_LIST, len(expr.items))
        elif isinstance(expr, DistLiteral):
            for value_expr, weight_expr in expr.entries:
                self._gen_expr(value_expr, e)
                self._gen_expr(weight_expr, e)
            e.emit(Op.MAKE_DIST, len(expr.entries))
        else:
            raise CodegenError(f"unhandled expression: {type(expr).__name__}")


def disassemble(module: Module) -> str:
    """Pretty-print a module's bytecode for --dump."""
    lines = []
    for unit in (module.intentions, module.functions, module.flows):
        for co in unit:
            header = f"=== {co.kind.upper()} {co.name}"
            if co.params:
                header += f"({', '.join(co.params)})"
            if co.kind == "intention":
                header += f"  [priority={co.priority}]"
            lines.append(header)
            width = len(str(len(co.instructions)))
            for i, ins in enumerate(co.instructions):
                lines.append(f"  {i:>{width}}  {ins}")
            lines.append("")
    for name, _ in module.mosaics:
        lines.append(f"=== CAUSAL_MOSAIC {name}")
        lines.append("")
    return "\n".join(lines)
