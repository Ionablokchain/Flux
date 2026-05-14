#!/usr/bin/env python3
import sys
import re

def format_flux(code: str) -> str:
    # Very basic formatter – just ensure indentation
    lines = code.split("\n")
    result = []
    indent = 0
    for line in lines:
        stripped = line.strip()
        if stripped.endswith("}"):
            indent = max(0, indent - 4)
        result.append(" " * indent + stripped)
        if stripped.endswith("{"):
            indent += 4
    return "\n".join(result)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: flux_format.py <file.flux>")
        sys.exit(1)
    with open(sys.argv[1], "r") as f:
        formatted = format_flux(f.read())
    with open(sys.argv[1], "w") as f:
        f.write(formatted)