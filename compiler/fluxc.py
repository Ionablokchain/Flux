#!/usr/bin/env python3
"""fluxc.py - The Flux compiler / runner.

Usage:
    fluxc <file.flux> [--dump] [--run] [--seed N] [--no-color] [--quiet]

  --dump      Print the compiled bytecode.
  --run       Execute the program on the Temporal VM.
  --seed N    Seed the VM's random number generator (for reproducible runs).
  --no-color  Disable ANSI color in error messages.
  --quiet     Hide non-fatal warnings.
"""
import argparse
import os
import sys

from flux_diagnostics import Diagnostic, SourceFile, FluxDiagnosticError
from flux_lexer import Lexer
from flux_parser import Parser
from flux_semantic import SemanticAnalyzer
from flux_codegen import BytecodeGenerator, disassemble
from tvm import TemporalVM, FluxRuntimeError


def _color_enabled(flag: bool) -> bool:
    if not flag:
        return False
    if os.environ.get("NO_COLOR"):
        return False
    return sys.stderr.isatty()


def _emit(diag: Diagnostic, source: SourceFile, color: bool) -> None:
    print(diag.render(source, color=color), file=sys.stderr)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="fluxc")
    ap.add_argument("file")
    ap.add_argument("--dump", action="store_true", help="print bytecode")
    ap.add_argument("--run", action="store_true", help="execute on the TVM")
    ap.add_argument("--seed", type=int, default=None, help="VM RNG seed")
    ap.add_argument("--quiet", action="store_true", help="hide warnings")
    ap.add_argument("--no-color", action="store_true",
                    help="disable ANSI colors in error messages")
    args = ap.parse_args(argv)

    color = _color_enabled(not args.no_color)

    try:
        with open(args.file, "r", encoding="utf-8") as f:
            text = f.read()
    except OSError as e:
        print(f"error: cannot read {args.file}: {e}", file=sys.stderr)
        return 2

    source = SourceFile(name=args.file, source=text)

    try:
        tokens = Lexer(text).tokenize()
        program = Parser(tokens).parse()
    except FluxDiagnosticError as e:
        _emit(e.diagnostic, source, color)
        return 1

    sa = SemanticAnalyzer()
    diagnostics = sa.analyze(program)
    errors   = [d for d in diagnostics if d.kind == "error"]
    warnings = [d for d in diagnostics if d.kind == "warning"]
    if not args.quiet:
        for w in warnings:
            print(f"warning: {w.message}", file=sys.stderr)
    if errors:
        for e in errors:
            print(f"error: {e.message}", file=sys.stderr)
        return 1

    module = BytecodeGenerator().generate(program)

    if args.dump:
        print(disassemble(module))

    if args.run:
        vm = TemporalVM(module, rng_seed=args.seed)
        vm.install(module)
        try:
            vm.run_module()
        except FluxRuntimeError as e:
            print(f"runtime error: {e}", file=sys.stderr)
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
