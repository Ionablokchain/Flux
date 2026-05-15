# Changelog

## [1.2.0] — Caret error messages

Errors used to look like:

    parse error: expected SEMICOLON, got IDENT ('send') at line 4, column 9

They now look like:

    error: expected ';'
      --> greet.flux:3:22
       |
     3 |         let x = 1 + 2
       |                      ^ add ';' at the end of this line

### Added

- `flux_diagnostics.py`: a `Span`, `SourceFile`, `Diagnostic`, and renderer.
  The renderer handles caret alignment, line-length clamping, optional ANSI
  color, and structured hints / notes.
- `Token` now carries `end_line` and `end_col`, so errors can underline an
  entire identifier or operator instead of pointing at a single column.
- `FluxDiagnosticError` is the new shared base for lexer and parser errors.
  Each carries a `Diagnostic` with a precise span, a helpful title, and an
  inline hint.
- The CLI catches diagnostic errors and renders them with the offending
  source line. ANSI color is enabled when stderr is a terminal and can be
  disabled with `--no-color` or the standard `NO_COLOR` environment
  variable.
- 19 new tests: renderer correctness (caret alignment, clamping, color
  toggle), lexer token-span correctness, parser-error pathways (missing
  `;`, bad priority, empty `dist`, missing `collapse` method, bad
  top-level statement), and an end-to-end check of the rendered output
  for a realistic mistake.

### Changed

- Missing-semicolon errors point at the end of the previous line instead
  of the next token. That's where the user forgot it.
- The "expected" half of error messages uses human names (`';'`, `'('`,
  `'in'`, `an identifier`) rather than the lexer's internal enum names.
- Empty `dist { }` literals are caught at parse time with a helpful hint.
- Wrong intention-body fields (e.g. `huh:` instead of `trigger:`) now list
  the valid alternatives in the hint.

## [1.1.0] — Distribution literals

The collapse operator finally has something to collapse from source code.
Previously a distribution could only enter the runtime through a mosaic
read; now it can be written directly.

### Added

- **`dist { value: weight, ... }` literals** as a primary expression.
  Empty distributions are rejected at parse time; trailing commas are
  allowed; entries with weight ≤ 0 are dropped at construction.
- **`support(d)`** — returns the list of values in declaration order.
- **`weight_of(d, v)`** — returns the cumulative weight of entries equal
  to `v`, or 0 if `v` is not in the support.
- **`normalize(d)`** — returns a new distribution scaled to total weight 1.
- Pretty-printing for distributions via `to_string(d)` and `send(...)`.
- Two new examples: `weighted_decision.flux` and `belief_update.flux`,
  the latter showing the relationship between mosaic reads and dist
  literals.
- 17 new tests covering parsing, runtime construction, collapse semantics,
  zero-weight dropping, seeded reproducibility, and proportions matching
  weights over 100 samples.

### Changed

- `to_string` now formats distributions as `dist{val:weight, ...}` instead
  of falling through to Python's default `repr`.

## [1.0.1] — Pipeline repair

A ground-up rewrite of the compiler with the same surface intent and
vocabulary as the original. Nothing from the original codebase is reused
verbatim, because nothing in it ran.

### Fixed

- The original `flux_ast.py` used `in:` as a dataclass field name, which is a
  syntax error in Python. The AST is rebuilt with valid identifiers.
- The original parser referred to `TokenType.IN`, which did not exist in the
  lexer's enum. All token types are now used consistently.
- The original `_parse_intentie` could reference `corp` without initialization,
  causing `UnboundLocalError` on intentions without an `execute:` field. All
  parser entry points now initialize their locals.
- The original lexer recognized only the Romanian keyword set, but every
  example file was written in English. The two are now consistent: keywords,
  examples, tests, and documentation are all in English.
- The original VM dispatched on indentation in the bytecode text, which broke
  on any non-trivial control flow. The bytecode is now a flat list of
  instructions with explicit jump offsets.

### Added

- **Duration literals** as first-class tokens and values. `5s`, `10ms`,
  `500us`, `250ns`, and `3cycles` parse into a single `DURATION` token
  carrying the value in nanoseconds. The VM's `Duration` type supports
  addition, subtraction, comparison, and scaling by a number.
- **Real collapse semantics**: `max_weight`, `mean`, `weighted_random`,
  `random`, `first`. The collapse operator now accepts both scalars (treated
  as point distributions) and weighted distributions (produced internally by
  mosaic reads).
- **Causal mosaic** as a working key-value store with weighted branches and
  a default `most_probable` read policy.
- **Pluggable input/output**: `InputProvider` makes `listen()` deterministic
  and testable; `OutputSink(capture=True)` captures emitted sensations
  without printing.
- **Intention scheduling by priority** at module start; `trigger` and
  `condition` are now actually evaluated.
- **User-defined functions** with parameters, return values, and recursion.
- **Iteration**: `for x in [a, b]` desugars to an iterator protocol; `while`
  is fully supported.
- A **91-test** unit and end-to-end suite that runs in under 0.2 seconds.

### Changed

- Concatenation is `++` (not `+`), so it never collides with numeric
  addition.
- `collapse` works both as a statement (result discarded) and as an
  expression (`let x = collapse(...)`).
- Function declarations require typed parameters and an optional `-> type`
  return type.

### Removed

- The decorative Verilog files (`paradox_unit.v`, `quantum_memory.v`,
  `temporal_clock.v`). They did not correspond to anything real in the
  implementation and could mislead readers into thinking there was hardware
  support.
- The empty placeholder tests in the original `tests/unit/` directory.

## [1.0.0] — Original release

The original Flux. Documented as working; did not, in fact, run.
