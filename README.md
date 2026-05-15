# Flux

A small, honest programming language with a temporal-causal vocabulary.

Flux programs are organized around **intentions** — event-driven blocks with a
trigger, a priority, an optional condition, and a body. The body sends
**sensations**, listens for input, and can **collapse** weighted distributions
of values. State can be stored in a **causal mosaic** — a sparse key/value
store with weighted branches.

The vocabulary is evocative; the semantics are mundane. There are no quantum
computers in here. `causal_void.exists()` returns `true`. `generate_paradox()`
returns a deterministic counter-derived string. The fun is in writing programs
that read like rituals; the runtime is a plain stack VM.

## Quick start

```
$ cd compiler
$ python3 fluxc.py ../examples/hello.flux --run
[mental_image] Hello from Flux [2s]
```

Flags:

- `--dump` — print the compiled bytecode.
- `--run` — execute the program on the Temporal VM.
- `--seed N` — seed the VM's random number generator for reproducible runs.
- `--quiet` — hide semantic warnings.

## A program

```flux
intention Greet {
    trigger:   on_boot()
    priority:  0.9
    condition: causal_void.exists()
    execute: {
        let name = listen(user, 5s, "world");
        send("mental_image", "hello, " ++ name, 2s);
    }
}
```

## A program that decides

```flux
intention Decide {
    trigger: on_boot()
    execute: {
        let actions = dist {
            "wait":    0.5,
            "explore": 0.3,
            "act":     0.2
        };
        let chosen = collapse(actions, weighted_random);
        send("mental_image", "chose: " ++ chosen, 1s);
    }
}
```

`collapse` is the central operation: it reduces a weighted distribution
to a single value using a method like `max_weight`, `weighted_random`,
`mean`, or `first`. Distributions can be written inline with `dist { ... }`
or produced by mosaic reads.

When the module runs, intentions are scheduled in descending priority order.
Each intention's `trigger` and `condition` are evaluated; if both are truthy,
the body runs.

## Language at a glance

- **Declarations:** `intention`, `function`, `flow`, `struct`, `causal_mosaic`.
- **Statements:** `let`, `<assignment>`, `if`/`else`, `while`, `for ... in ...`,
  `return`, `launch`, `send`, `collapse`.
- **Expressions:** numeric/string/boolean/duration literals, list literals
  `[a, b, c]`, identifiers, `f(args)`, `obj.field`, `obj.method(args)`,
  `listen(source, timeout, fallback)`, `collapse(expr, method)`, binary
  operators (`+ - * / %`, `== != < > <= >=`, `&& ||`, `++` for string
  concatenation), unary `-` and `!`.
- **Durations:** first-class. `2s`, `500ms`, `250us`, `100ns`, `3cycles`.
  Internally normalized to nanoseconds. `2s + 500ms` evaluates to a duration.
- **Collapse methods:** `max_weight`, `mean`, `weighted_random`, `random`,
  `first`. Operates on either a scalar (point distribution) or a list of
  `(value, weight)` tuples (used internally by mosaics).

## Project layout

```
flux/
├── compiler/         # Lexer, parser, semantic analyzer, codegen, VM, CLI
│   ├── flux_lexer.py
│   ├── flux_parser.py
│   ├── flux_ast.py
│   ├── flux_semantic.py
│   ├── flux_bytecode.py
│   ├── flux_codegen.py
│   ├── tvm.py
│   └── fluxc.py
├── examples/         # Standalone example programs
├── benchmarks/       # Loop-heavy programs that exercise the VM
├── integration/      # Small programs used as end-to-end smoke tests
├── tests/            # Unit + end-to-end test suite
├── docs/
│   └── language.md
└── CHANGELOG.md
```

## Tests

```
$ python3 -m unittest discover -s tests -p "test_*.py"
...
Ran 129 tests in 0.18s
OK
```

The tests cover the lexer (duration parsing, escapes, multi-char operators,
token spans), the parser (precedence, associativity, scopes, method-chain
parsing, dist literals), the semantic analyzer (range checks, scope leakage,
unknown-call warnings), codegen (correct opcode sequences,
statement-vs-expression form of `collapse`, dist literals), the VM
(arithmetic, control flow, collapse semantics across all four methods,
mosaic round-trips, deterministic seeded RNG, scripted `listen` input,
priority-ordered intention scheduling, recursive functions), a
distribution-focused suite that verifies sample proportions match weights
over 100 trials, and the diagnostic renderer (caret alignment, clamping,
colorless rendering, and pipeline tests for the kinds of mistakes a user
actually makes).

## Error messages

Compiler errors point at the source. A missing semicolon looks like this:

```
error: expected ';'
  --> greet.flux:3:22
   |
 3 |         let x = 1 + 2
   |                      ^ add ';' at the end of this line
```

The compiler emits ANSI colors when stderr is a terminal. Disable with
`--no-color` or by setting `NO_COLOR=1` in the environment.

## What this is not

Flux is a small interpreted language with a thematic surface. It does not
implement actual probabilistic programming, quantum effects, hardware
acceleration, or causal reasoning. Names like `causal_void`, `paradox`, and
`hardening` are vocabulary — they map to ordinary, deterministic runtime
operations. The point is to be a coherent toy with a consistent voice, not
to over-promise. If you want a real probabilistic system, see Pyro or Stan.

## License

Apache-2.0 license
