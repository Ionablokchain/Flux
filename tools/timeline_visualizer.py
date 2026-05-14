#!/usr/bin/env python3
# Simple graphviz output for timelines
import sys

def visualize(timelines):
    print("digraph G {")
    for tl, parent in timelines.items():
        if parent:
            print(f'  "{parent}" -> "{tl}";')
    print("}")

if __name__ == "__main__":
    # Example: read from stdin or arguments
    print("// Run with: python timeline_visualizer.py | dot -Tpng > out.png")
    sample = {"main": None, "fork1": "main", "fork2": "main"}
    visualize(sample)