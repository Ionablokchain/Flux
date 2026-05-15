# Flux Language Reference

This document is the working specification of the Flux language as
implemented. Where the implementation and any earlier specification
disagree, the implementation wins.

## Lexical structure

### Comments

`# line comment` and `// line comment` both run to end of line.

### Keywords

```
intention  flow  function  struct  causal_mosaic
let  if  else  for  while  in  return  launch
send  listen  collapse
trigger  priority  condition  execute
true  false
```

### Identifiers

`[A-Za-z_][A-Za-z0-9_]*`. Case-sensitive.

### Literals

| Form                       | Type      | Notes                              |
|---------------------------|-----------|------------------------------------|
| `42`                      | integer   | Stored internally as a float       |
| `3.14`                    | float     |                                    |
| `"text"`                  | string    | Escapes: `\n \t \r \" \\`           |
| `true` / `false`          | bool      |                                    |
| `5s` `10ms` `500us` `250ns` `3cycles` | duration | Normalized to nanoseconds |
| `[a, b, c]`               | list      | Elements evaluated left-to-right   |

Negative literals are written as unary minus: `-3`, `-0.5`.

### Operators (precedence, low to high)

```
||
&&
== !=
< > <= >=
++                  (string concatenation, left-assoc)
+ -
* / %
unary - !
. ( )               (member access, call)
```

All binary operators are left-associative. Use parentheses where the
intent is otherwise.

## Top-level declarations

### Intention

```
intention Name {
    trigger:   <expression>      (optional)
    priority:  <numeric literal> (optional, in [0, 1], default 1.0)
    condition: <expression>      (optional)
    execute: { <statements> }
}
```

Intentions are scheduled in descending order of priority when the module
runs. For each intention, the runtime evaluates `trigger` and `condition`;
the body runs only if both are truthy (or unset). The body is a block of
statements; its value is discarded.

### Function

```
function name(p1: T1, p2: T2) -> R {
    <statements>
}
```

Functions are first-class callable units. Types after the colon and after
`->` are presently informational only; the runtime is dynamically typed.

### Flow

```
flow name(p1, p2) {
    <statements>
}
```

Flows are like functions but without typed parameters. They are intended
as cooperative units that can be launched from intentions.

### Struct

```
struct Point {
    x: int
    y: int
}
```

Structs are declarative shape information; the runtime does not yet
instantiate them. They exist so that programs read like Flux code.

### Causal mosaic

```
causal_mosaic store = sparse_temporal_matrix();
```

A mosaic is a sparse weighted key-value store. Write with
`store.accept(key).write(value, weight)`. Read with
`store.accept(key).read()`, which returns the highest-weighted value
stored at that key, or `nil` if the key has never been written.

## Statements

| Form                                    | Meaning                          |
|-----------------------------------------|----------------------------------|
| `let name = expr;`                      | Declare in current scope         |
| `name = expr;`                          | Assign to existing binding       |
| `if cond { ... } else { ... }`          | Else branch optional; `else if` chains supported |
| `while cond { ... }`                    | Standard while                   |
| `for x in expr { ... }`                 | Iterates lists and `[a, b]` ranges |
| `return expr;` / `return;`              | Return from function/intention   |
| `launch(Name, args...);`                | Run another intention/flow now   |
| `send(kind, content, duration);`        | Emit a sensation                 |
| `collapse(expr, method);`               | Statement form (result dropped)  |
| `expr;`                                 | Expression statement             |

### Scopes

Every block introduces a new scope. Bindings declared with `let` are
visible only inside the block where they appear. An assignment to a name
that has not been declared in any enclosing scope is an error.

## Expressions

### `listen(source, timeout, fallback)`

Reads from an input source. The runtime's input provider may return a
scripted value; otherwise the fallback is returned. The grammar requires
the source to be a bare identifier; `timeout` and `fallback` are optional
trailing arguments.

### `collapse(expression, method)`

Reduces a distribution to a single value. The supported methods are:

- `max_weight` — return the value with the highest weight (default for
  unknown methods).
- `mean` — return the weighted mean if values are numeric, otherwise
  fall back to `max_weight`.
- `weighted_random` (alias `random`) — sample one entry proportional to
  its weight, using the VM's seeded RNG.
- `first` — return the first entry in declaration order.

A scalar passed to `collapse` is treated as a point distribution: its
sole entry has weight 1.

### Distribution literals

Discrete distributions can be written directly:

```flux
let coin = dist { "heads": 0.6, "tails": 0.4 };
let action = collapse(coin, weighted_random);
```

A `dist { ... }` literal must contain at least one entry. Weights may be
any non-negative numeric expression; an entry with zero or negative
weight is dropped at construction. A trailing comma is permitted.

Three built-ins operate on distributions:

| Call                 | Returns                                                  |
|----------------------|----------------------------------------------------------|
| `support(d)`         | A list of the distribution's values in declaration order |
| `weight_of(d, v)`    | The sum of weights of entries equal to `v` (0 if absent) |
| `normalize(d)`       | A new distribution whose weights sum to 1                |

A mosaic read uses the same machinery internally: every `accept(key)` plus
`write(value, weight)` adds a weighted entry under that key, and `read()`
collapses that key's accumulated distribution with `max_weight`.

### Built-in functions

| Name                              | Returns                                     |
|-----------------------------------|---------------------------------------------|
| `on_boot()`, `on_command(s)`, `on_user_intention()` | `true` (always; runtime hook stubs) |
| `now()`                           | A duration that monotonically increases     |
| `to_string(v)`                    | A human-readable string                     |
| `parse_duration(s)`               | Parses `"5s"`, `"10ms"`, etc.               |
| `current_timeline()`              | Name of the current timeline (initially `"primary"`) |
| `create_timeline()`               | Creates and returns a new timeline name     |
| `set_current_timeline(t)`         | Switches the active timeline                |
| `merge_timelines(src, dst)`       | Forgets `src`                               |
| `reset_timeline(t)`               | No-op (stub)                                |
| `generate_paradox()`              | A deterministic unique code (counter-based) |
| `resolve_paradox(p)`              | Returns `p` (identity)                      |
| `estimate_hardening_cost()`       | `0.001`                                     |
| `causal_hardening(d, c)`          | No-op (stub)                                |
| `sleep(d)`                        | Advances the logical clock                  |
| `sparse_temporal_matrix()`        | A marker value used in `causal_mosaic` declarations |
| `print(...)`                      | Prints to stdout                            |

### Special objects

- `causal_void` — supports `.exists()` which returns `true`.
- The name of a declared `causal_mosaic` evaluates to a cursor for that
  mosaic; chain `.accept(key)` to bind a key, then `.write(...)` or
  `.read()`.

## Runtime model

The Temporal VM is a stack machine with one frame per active call and one
or more scopes per frame. There is no GC: Python's reference counting
handles all values. There is no concurrency: intentions run sequentially
in priority order. There is no real I/O: the input provider is in-memory
and seeded.

The point of the runtime is to be faithful to the semantics described
here, not to be fast. A program that compiles is a program that runs.
