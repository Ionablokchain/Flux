# tvm.py - Temporal Virtual Machine for executing Flux bytecode
#
# Design notes
# ------------
# This is a straightforward stack-based VM. There is no JIT, no GC, no
# concurrency: intentions run sequentially on a single thread, ordered
# by priority. The point of the VM is to be *honest* about its semantics,
# not to be fast.
#
# A few Flux-specific decisions:
#
#   - Durations are first-class. Internally they are integer nanoseconds
#     plus a printable original form. `2s + 500ms` evaluates to a duration.
#
#   - `collapse(expr, method)` operates on either a scalar (treated as a
#     trivial point distribution) or a list of (value, weight) pairs.
#     Supported methods: max_weight, mean, weighted_random, random, first.
#
#   - `listen(source, timeout, fallback)` does NOT block on real input.
#     The VM has a configurable input provider; the default returns the
#     fallback. A deterministic input provider makes tests reproducible.
#
#   - `causal_void`, `current_timeline`, `now`, etc. are concrete builtins
#     with simple semantics (a counter, a string, a clock). The vocabulary
#     stays; the semantics are mundane and explicit.

import random
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from flux_bytecode import Op, Instr, CodeObject, Module


# ---------- runtime values ----------

class Duration:
    __slots__ = ("nanos", "original")

    def __init__(self, nanos: int, original: str = ""):
        self.nanos = int(nanos)
        self.original = original or self._format(self.nanos)

    @staticmethod
    def _format(nanos: int) -> str:
        if nanos % 1_000_000_000 == 0:
            return f"{nanos // 1_000_000_000}s"
        if nanos % 1_000_000 == 0:
            return f"{nanos // 1_000_000}ms"
        if nanos % 1_000 == 0:
            return f"{nanos // 1_000}us"
        return f"{nanos}ns"

    def __repr__(self) -> str:
        return self.original

    def __add__(self, other):
        if isinstance(other, Duration):
            return Duration(self.nanos + other.nanos)
        raise TypeError("can only add Duration to Duration")

    def __sub__(self, other):
        if isinstance(other, Duration):
            return Duration(self.nanos - other.nanos)
        raise TypeError("can only subtract Duration from Duration")

    def __eq__(self, other):
        return isinstance(other, Duration) and self.nanos == other.nanos

    def __lt__(self, other):
        if isinstance(other, Duration):
            return self.nanos < other.nanos
        return NotImplemented

    def __le__(self, other):
        if isinstance(other, Duration):
            return self.nanos <= other.nanos
        return NotImplemented

    def __hash__(self):
        return hash(("Duration", self.nanos))


class Nil:
    """Single sentinel value, used as Flux's nil/unit."""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __repr__(self):
        return "nil"

    def __bool__(self):
        return False


NIL = Nil()


class Distribution:
    """A discrete weighted distribution used as the input to `collapse`."""
    __slots__ = ("entries",)

    def __init__(self, entries: List[Tuple[Any, float]]):
        # Defensive copy + filter out zero/negative weights
        self.entries = [(v, float(w)) for v, w in entries if w > 0]
        if not self.entries:
            self.entries = [(NIL, 1.0)]

    def __repr__(self):
        body = ", ".join(f"{v!r}:{w}" for v, w in self.entries)
        return f"Dist[{body}]"


# ---------- runtime errors ----------

class FluxRuntimeError(RuntimeError):
    pass


# ---------- frame ----------

@dataclass
class Frame:
    code: CodeObject
    ip: int = 0
    scopes: List[Dict[str, Any]] = field(default_factory=lambda: [{}])

    def declare(self, name: str, value: Any) -> None:
        self.scopes[-1][name] = value

    def store(self, name: str, value: Any) -> None:
        for s in reversed(self.scopes):
            if name in s:
                s[name] = value
                return
        # If no scope has it yet, declare in innermost (Flux is lenient here)
        self.scopes[-1][name] = value

    def load(self, name: str) -> Any:
        for s in reversed(self.scopes):
            if name in s:
                return s[name]
        raise FluxRuntimeError(f"undefined variable {name!r}")


# ---------- input provider ----------

class InputProvider:
    """Pluggable source of listen() answers. The default returns the fallback,
    which keeps things deterministic. Tests can install a scripted provider."""

    def __init__(self, scripted: Optional[Dict[str, List[str]]] = None):
        self.scripted = {k: list(v) for k, v in (scripted or {}).items()}

    def listen(self, source: str, timeout: Optional[Duration],
               fallback: Any) -> Any:
        queue = self.scripted.get(source)
        if queue:
            return queue.pop(0)
        return fallback if fallback is not None else NIL


# ---------- output sink ----------

class OutputSink:
    """Collects sensations emitted by send(). Default prints to stdout."""

    def __init__(self, capture: bool = False):
        self.capture = capture
        self.events: List[Tuple[str, Any, Optional[Duration]]] = []

    def emit(self, kind: str, content: Any, duration: Optional[Duration]) -> None:
        self.events.append((kind, content, duration))
        if not self.capture:
            dur = f" [{duration}]" if isinstance(duration, Duration) else ""
            print(f"[{kind}] {content}{dur}")


# ---------- the VM ----------

class TemporalVM:
    def __init__(
        self,
        module: Optional[Module] = None,
        *,
        input_provider: Optional[InputProvider] = None,
        sink: Optional[OutputSink] = None,
        rng_seed: Optional[int] = None,
        clock_start_ns: int = 0,
    ):
        self.module = module
        self.input_provider = input_provider or InputProvider()
        self.sink = sink or OutputSink()
        self.rng = random.Random(rng_seed) if rng_seed is not None else random.Random()
        self.clock_ns = clock_start_ns
        # Sequence counter, drives `causal_void.exists()`, `now()`, etc.
        self._step = 0
        # Each VM has a single ambient timeline; create_timeline returns names.
        self.current_timeline = "primary"
        self._timeline_counter = 0
        self._known_timelines = {"primary"}
        # Mosaic storage: dict of mosaic_name -> dict[key -> list of (value, weight)]
        self._mosaics: Dict[str, Dict[Any, List[Tuple[Any, float]]]] = {}

    # ---------- module setup ----------

    def install(self, module: Module) -> None:
        self.module = module
        for name, _components in module.mosaics:
            self._mosaics.setdefault(name, {})

    # ---------- top-level: run intentions in priority order ----------

    def run_module(self) -> None:
        if self.module is None:
            raise FluxRuntimeError("no module installed")
        intentions = sorted(
            self.module.intentions, key=lambda i: -i.priority
        )
        for intent in intentions:
            self.run_intention(intent)

    def run_intention(self, intent: CodeObject) -> Any:
        # Trigger and condition are stored as AST nodes. We compile each into
        # a tiny ephemeral code object and evaluate it on a fresh frame.
        # The intention body runs only if both evaluate truthy.
        if intent.trigger is not None and not self._eval_ast(intent.trigger):
            return NIL
        if intent.condition is not None and not self._eval_ast(intent.condition):
            return NIL
        return self._execute(intent, args=[])

    def _eval_ast(self, node) -> bool:
        """Compile a single AST expression and evaluate it. Returns truthy."""
        from flux_codegen import _Emitter, BytecodeGenerator
        from flux_bytecode import CodeObject as _CO
        gen = BytecodeGenerator()
        emitter = _Emitter()
        gen._gen_expr(node, emitter)
        emitter.emit(Op.RETURN)
        co = _CO(name="<predicate>", kind="function",
                 instructions=emitter.instructions, params=[])
        result = self._execute(co, args=[])
        return self._truthy(result)

    def run_function(self, name: str, args: List[Any]) -> Any:
        fn = self.module.get_function(name) if self.module else None
        if fn is None:
            raise FluxRuntimeError(f"unknown function {name!r}")
        if len(args) != len(fn.params):
            raise FluxRuntimeError(
                f"function {name!r} expects {len(fn.params)} args, got {len(args)}"
            )
        return self._execute(fn, args=args)

    def _lookup_singleton(self, name: str):
        if name == "causal_void":
            return _CausalVoid()
        if name in self._mosaics:
            return _MosaicCursor(name)
        if name == "user":
            return "user"
        return None

    # ---------- core executor ----------

    def _execute(self, code: CodeObject, args: List[Any]) -> Any:
        frame = Frame(code=code)
        for pname, pval in zip(code.params, args):
            frame.declare(pname, pval)
        stack: List[Any] = []
        ins = code.instructions
        n = len(ins)
        while frame.ip < n:
            instr = ins[frame.ip]
            frame.ip += 1
            op = instr.op
            arg = instr.arg
            self._step += 1

            if op is Op.PUSH_NUM:
                stack.append(float(arg))
            elif op is Op.PUSH_STR:
                stack.append(arg)
            elif op is Op.PUSH_BOOL:
                stack.append(bool(arg))
            elif op is Op.PUSH_DURATION:
                nanos, original = arg
                stack.append(Duration(nanos, original))
            elif op is Op.PUSH_NIL:
                stack.append(NIL)
            elif op is Op.POP:
                stack.pop()
            elif op is Op.DUP:
                stack.append(stack[-1])
            elif op is Op.MAKE_LIST:
                count = arg
                if count == 0:
                    stack.append([])
                else:
                    items = stack[-count:]
                    del stack[-count:]
                    stack.append(list(items))
            elif op is Op.MAKE_DIST:
                count = arg
                # Stack layout (bottom-to-top): v1, w1, v2, w2, ..., vN, wN
                entries: List[Tuple[Any, float]] = []
                if count > 0:
                    raw = stack[-2 * count:]
                    del stack[-2 * count:]
                    for i in range(0, len(raw), 2):
                        v = raw[i]
                        w_raw = raw[i + 1]
                        if isinstance(w_raw, bool):
                            w_raw = float(w_raw)
                        if not isinstance(w_raw, (int, float)):
                            raise FluxRuntimeError(
                                f"dist weight must be numeric, got "
                                f"{type(w_raw).__name__}"
                            )
                        entries.append((v, float(w_raw)))
                stack.append(Distribution(entries))

            elif op is Op.LOAD_VAR:
                try:
                    stack.append(frame.load(arg))
                except FluxRuntimeError:
                    # Fall back to known runtime singletons (e.g. `causal_void`).
                    singleton = self._lookup_singleton(arg)
                    if singleton is None:
                        raise
                    stack.append(singleton)
            elif op is Op.STORE_VAR:
                v = stack.pop()
                frame.store(arg, v)
            elif op is Op.DECLARE_VAR:
                v = stack.pop()
                frame.declare(arg, v)

            elif op is Op.BIN_OP:
                b = stack.pop()
                a = stack.pop()
                stack.append(self._apply_binop(a, arg, b))
            elif op is Op.UNARY_OP:
                v = stack.pop()
                stack.append(self._apply_unop(arg, v))

            elif op is Op.JUMP:
                frame.ip = arg
            elif op is Op.JUMP_IF_FALSE:
                v = stack.pop()
                if not self._truthy(v):
                    frame.ip = arg

            elif op is Op.CALL:
                name, argc = arg
                call_args = [stack.pop() for _ in range(argc)][::-1]
                stack.append(self._call(name, call_args))
            elif op is Op.METHOD_CALL:
                method, argc = arg
                call_args = [stack.pop() for _ in range(argc)][::-1]
                receiver = stack.pop()
                stack.append(self._method_call(receiver, method, call_args))
            elif op is Op.FIELD_ACCESS:
                receiver = stack.pop()
                stack.append(self._field_access(receiver, arg))

            elif op is Op.SEND_SENSATION:
                duration = stack.pop()
                content = stack.pop()
                kind = stack.pop()
                if duration is NIL:
                    duration = None
                if not isinstance(kind, str):
                    kind = str(kind)
                self.sink.emit(kind, content, duration if isinstance(duration, Duration) else None)
            elif op is Op.LISTEN:
                source, has_timeout, has_fallback = arg
                fallback = stack.pop() if has_fallback else None
                timeout = stack.pop() if has_timeout else None
                if timeout is not None and not isinstance(timeout, Duration):
                    timeout = None
                stack.append(self.input_provider.listen(source, timeout, fallback))
            elif op is Op.COLLAPSE:
                method = arg
                v = stack.pop()
                stack.append(self._collapse(v, method))
            elif op is Op.LAUNCH:
                name, argc = arg
                call_args = [stack.pop() for _ in range(argc)][::-1]
                self._launch(name, call_args)

            elif op is Op.BEGIN_INTENTION:
                pass
            elif op is Op.END_INTENTION:
                pass
            elif op is Op.RETURN:
                return stack.pop() if stack else NIL
            elif op is Op.HALT:
                return NIL
            else:
                raise FluxRuntimeError(f"unknown opcode {op}")
        return NIL

    # ---------- operator dispatch ----------

    def _apply_binop(self, a: Any, op: str, b: Any) -> Any:
        # Concatenation
        if op == "++":
            return self._to_string(a) + self._to_string(b)
        # Equality across types (Python's == is fine for our value types)
        if op == "==":
            return a == b
        if op == "!=":
            return a != b
        # Comparison: numbers and durations
        if op in ("<", ">", "<=", ">="):
            try:
                if op == "<":  return a < b
                if op == ">":  return a > b
                if op == "<=": return a <= b
                if op == ">=": return a >= b
            except TypeError:
                raise FluxRuntimeError(
                    f"cannot compare {type(a).__name__} {op} {type(b).__name__}"
                )
        # Logical
        if op == "&&":
            return self._truthy(a) and self._truthy(b)
        if op == "||":
            return self._truthy(a) or self._truthy(b)
        # Arithmetic
        if op in ("+", "-", "*", "/", "%"):
            return self._arith(a, op, b)
        raise FluxRuntimeError(f"unknown binary operator {op!r}")

    def _arith(self, a: Any, op: str, b: Any) -> Any:
        # Duration arithmetic
        if isinstance(a, Duration) and isinstance(b, Duration):
            if op == "+": return a + b
            if op == "-": return a - b
            raise FluxRuntimeError(f"duration {op} duration is not defined")
        if isinstance(a, Duration) and isinstance(b, (int, float)):
            if op == "*": return Duration(int(a.nanos * b))
            if op == "/": return Duration(int(a.nanos / b))
        if isinstance(a, (int, float)) and isinstance(b, Duration):
            if op == "*": return Duration(int(a * b.nanos))
        # String + string is also accepted via +, to be friendly
        if op == "+" and isinstance(a, str) and isinstance(b, str):
            return a + b
        # Numeric
        if isinstance(a, bool):
            a = float(a)
        if isinstance(b, bool):
            b = float(b)
        if op == "+": return a + b
        if op == "-": return a - b
        if op == "*": return a * b
        if op == "/":
            if b == 0:
                raise FluxRuntimeError("division by zero")
            return a / b
        if op == "%":
            if b == 0:
                raise FluxRuntimeError("modulo by zero")
            return a % b
        raise FluxRuntimeError(f"bad arithmetic: {a!r} {op} {b!r}")

    def _apply_unop(self, op: str, v: Any) -> Any:
        if op == "-":
            if isinstance(v, Duration):
                return Duration(-v.nanos)
            return -v
        if op == "!":
            return not self._truthy(v)
        raise FluxRuntimeError(f"unknown unary operator {op!r}")

    def _truthy(self, v: Any) -> bool:
        if v is NIL:
            return False
        if isinstance(v, bool):
            return v
        if isinstance(v, (int, float)):
            return v != 0
        if isinstance(v, str):
            return len(v) > 0
        if isinstance(v, Duration):
            return v.nanos != 0
        if isinstance(v, (list, tuple, dict)):
            return len(v) > 0
        return True

    def _to_string(self, v: Any) -> str:
        if v is NIL:
            return "nil"
        if isinstance(v, bool):
            return "true" if v else "false"
        if isinstance(v, float):
            if v == int(v):
                return str(int(v))
            return f"{v:g}"
        if isinstance(v, Duration):
            return v.original
        if isinstance(v, Distribution):
            parts = [f"{self._to_string(val)}:{w:g}" for val, w in v.entries]
            return "dist{" + ", ".join(parts) + "}"
        return str(v)

    # ---------- calls ----------

    def _call(self, name: str, args: List[Any]) -> Any:
        # User function?
        if self.module is not None:
            fn = self.module.get_function(name)
            if fn is not None:
                if len(args) != len(fn.params):
                    raise FluxRuntimeError(
                        f"function {name!r} expects {len(fn.params)} args, "
                        f"got {len(args)}"
                    )
                return self._execute(fn, args)

        # Iteration protocol (used by `for` desugaring)
        if name == "__iter":
            return self._builtin_iter(args[0])
        if name == "__has_next":
            return self._builtin_has_next(args[0])
        if name == "__next":
            return self._builtin_next(args[0])

        # Built-ins
        return self._builtin_call(name, args)

    def _method_call(self, receiver: Any, method: str, args: List[Any]) -> Any:
        # Mosaic methods: mosaic.accept(key:k).write(value:v, weight:w) etc.
        # The grammar doesn't have keyword arguments, so we accept positional.
        if isinstance(receiver, _MosaicCursor):
            return receiver.dispatch(self, method, args)
        if isinstance(receiver, str) and receiver in self._mosaics:
            cursor = _MosaicCursor(receiver)
            return cursor.dispatch(self, method, args)
        # Generic .to_string()
        if method == "to_string":
            return self._to_string(receiver)
        # Generic .exists() on causal_void
        if isinstance(receiver, _CausalVoid):
            return receiver.dispatch(self, method, args)
        raise FluxRuntimeError(
            f"no method {method!r} on {type(receiver).__name__}"
        )

    def _field_access(self, receiver: Any, field: str) -> Any:
        if isinstance(receiver, dict):
            if field in receiver:
                return receiver[field]
        raise FluxRuntimeError(f"no field {field!r} on {type(receiver).__name__}")

    def _launch(self, name: str, args: List[Any]) -> None:
        if self.module is None:
            raise FluxRuntimeError("nothing to launch: no module")
        target = (self.module.get_intention(name)
                  or self.module.get_flow(name)
                  or self.module.get_function(name))
        if target is None:
            raise FluxRuntimeError(f"cannot launch unknown unit {name!r}")
        self._execute(target, args)

    # ---------- collapse ----------

    def _collapse(self, value: Any, method: str) -> Any:
        # Scalar values become point distributions.
        if isinstance(value, Distribution):
            entries = value.entries
        elif isinstance(value, list):
            # Accept [(v, w), ...] or flat [v, ...] (uniform weight).
            if all(isinstance(x, tuple) and len(x) == 2 for x in value):
                entries = [(v, float(w)) for v, w in value]
            else:
                entries = [(v, 1.0) for v in value]
        else:
            entries = [(value, 1.0)]

        if method == "max_weight":
            return max(entries, key=lambda e: e[1])[0]
        if method == "mean":
            total_w = sum(w for _, w in entries)
            if total_w == 0:
                return 0.0
            # Numeric mean if possible, else max_weight fallback.
            try:
                return sum(float(v) * w for v, w in entries) / total_w
            except (TypeError, ValueError):
                return max(entries, key=lambda e: e[1])[0]
        if method == "weighted_random" or method == "random":
            total_w = sum(w for _, w in entries)
            r = self.rng.random() * total_w
            acc = 0.0
            for v, w in entries:
                acc += w
                if r <= acc:
                    return v
            return entries[-1][0]
        if method == "first":
            return entries[0][0]
        # Unknown method: be lenient (warning was already emitted by analyzer)
        return max(entries, key=lambda e: e[1])[0]

    # ---------- built-ins ----------

    def _builtin_call(self, name: str, args: List[Any]) -> Any:
        if name == "on_boot":
            return True
        if name == "on_command":
            # In this VM the embedder is responsible for routing commands;
            # at runtime we just return true once (it gets re-evaluated by
            # the host when intentions are scheduled).
            return True
        if name == "on_user_intention":
            return True
        if name == "now":
            self.clock_ns += 1
            return Duration(self.clock_ns)
        if name == "to_string":
            return self._to_string(args[0]) if args else ""
        if name == "parse_duration":
            if not args or not isinstance(args[0], str):
                return Duration(0)
            return self._parse_duration_str(args[0])
        if name == "current_timeline":
            return self.current_timeline
        if name == "create_timeline":
            self._timeline_counter += 1
            new_name = f"timeline_{self._timeline_counter}"
            self._known_timelines.add(new_name)
            return new_name
        if name == "set_current_timeline":
            if args and isinstance(args[0], str) and args[0] in self._known_timelines:
                self.current_timeline = args[0]
            return NIL
        if name == "merge_timelines":
            # Simplified: just drop the source timeline from known set.
            if args:
                src = args[0]
                if isinstance(src, str):
                    self._known_timelines.discard(src)
            return NIL
        if name == "reset_timeline":
            return NIL
        if name == "current_user":
            return "user"
        if name == "generate_paradox":
            # Deterministic stand-in: derive a code from internal step count.
            return f"P{self._step:06d}"
        if name == "resolve_paradox":
            # The "answer" is the paradox value itself; the caller compares.
            return args[0] if args else NIL
        if name == "estimate_hardening_cost":
            return 0.001
        if name == "causal_hardening":
            return NIL
        if name == "sparse_temporal_matrix":
            return {"_kind": "sparse_temporal_matrix"}
        if name == "sleep":
            # No real sleep - update the clock.
            if args and isinstance(args[0], Duration):
                self.clock_ns += args[0].nanos
            return NIL
        if name == "print":
            print(*[self._to_string(a) for a in args])
            return NIL
        if name == "support":
            # Returns the list of values in a distribution (in insertion order).
            if not args or not isinstance(args[0], Distribution):
                raise FluxRuntimeError("support() expects a distribution")
            return [v for v, _ in args[0].entries]
        if name == "weight_of":
            # weight_of(dist, value) -> sum of weights for entries equal to value.
            if len(args) < 2 or not isinstance(args[0], Distribution):
                raise FluxRuntimeError(
                    "weight_of() expects (distribution, value)"
                )
            target = args[1]
            return float(sum(w for v, w in args[0].entries if v == target))
        if name == "normalize":
            # normalize(dist) -> distribution scaled to total weight 1.
            if not args or not isinstance(args[0], Distribution):
                raise FluxRuntimeError("normalize() expects a distribution")
            d = args[0]
            total = sum(w for _, w in d.entries)
            if total <= 0:
                return Distribution(list(d.entries))
            return Distribution([(v, w / total) for v, w in d.entries])
        # Special objects accessed as bare identifiers (e.g. `causal_void.exists()`)
        if name == "causal_void":
            return _CausalVoid()
        # Unknown function: in a real system this might be an error; here we
        # surface it so it's visible in tests.
        raise FluxRuntimeError(f"unknown function {name!r}")

    def _parse_duration_str(self, s: str) -> Duration:
        s = s.strip()
        # Greedy: find numeric prefix, then suffix
        i = 0
        while i < len(s) and (s[i].isdigit() or s[i] == "."):
            i += 1
        if i == 0:
            return Duration(0)
        try:
            num = float(s[:i])
        except ValueError:
            return Duration(0)
        suffix = s[i:].strip()
        mult = {"ns": 1, "us": 1_000, "ms": 1_000_000, "s": 1_000_000_000,
                "cycles": 1}.get(suffix, 0)
        return Duration(int(num * mult), original=s)

    # ---------- iteration protocol ----------

    def _builtin_iter(self, src: Any) -> Any:
        if isinstance(src, list):
            # Special-case [a, b] from for-range like `for i in [1, 10]`.
            if len(src) == 2 and all(isinstance(x, (int, float)) for x in src):
                return _RangeIter(int(src[0]), int(src[1]))
            return _ListIter(list(src))
        if isinstance(src, str):
            return _ListIter(list(src))
        raise FluxRuntimeError(f"value of type {type(src).__name__} is not iterable")

    def _builtin_has_next(self, it: Any) -> bool:
        if isinstance(it, (_ListIter, _RangeIter)):
            return it.has_next()
        raise FluxRuntimeError("invalid iterator")

    def _builtin_next(self, it: Any) -> Any:
        if isinstance(it, (_ListIter, _RangeIter)):
            return it.next()
        raise FluxRuntimeError("invalid iterator")


# ---------- iterator helpers ----------

class _RangeIter:
    __slots__ = ("cur", "end")
    def __init__(self, start: int, end: int):
        self.cur = start
        self.end = end
    def has_next(self) -> bool:
        return self.cur <= self.end
    def next(self):
        v = self.cur
        self.cur += 1
        return float(v)


class _ListIter:
    __slots__ = ("items", "idx")
    def __init__(self, items):
        self.items = items
        self.idx = 0
    def has_next(self) -> bool:
        return self.idx < len(self.items)
    def next(self):
        v = self.items[self.idx]
        self.idx += 1
        return v


# ---------- special objects ----------

class _CausalVoid:
    """The 'causal_void' singleton; supports .exists()."""
    def dispatch(self, vm: TemporalVM, method: str, args):
        if method == "exists":
            return True
        raise FluxRuntimeError(f"causal_void has no method {method!r}")


class _MosaicCursor:
    """A handle to a mosaic; supports .accept(key).write(value, weight) / .read()."""
    __slots__ = ("name", "key")

    def __init__(self, name: str, key=None):
        self.name = name
        self.key = key

    def dispatch(self, vm: TemporalVM, method: str, args):
        if method == "accept":
            if not args:
                raise FluxRuntimeError("mosaic.accept needs a key")
            return _MosaicCursor(self.name, args[0])
        if method == "write":
            if self.key is None:
                raise FluxRuntimeError("mosaic write needs accept(key) first")
            value = args[0] if len(args) >= 1 else NIL
            weight = float(args[1]) if len(args) >= 2 else 1.0
            store = vm._mosaics.setdefault(self.name, {})
            store.setdefault(self.key, []).append((value, weight))
            return NIL
        if method == "read":
            store = vm._mosaics.get(self.name, {})
            entries = store.get(self.key)
            if not entries:
                return NIL
            # Default read policy: most_probable (max weight)
            return max(entries, key=lambda e: e[1])[0]
        raise FluxRuntimeError(f"no mosaic method {method!r}")
