#!/usr/bin/env python3
"""
test_decorated.py — lint de la amenaza #5: toda tool con efectos debe estar decorada.

Estatico (AST), sin ejecutar el modulo. Para cada modulo de tools listado, exige que
TODA funcion de nivel superior (que no empiece por '_') este envuelta por @gated. Asi,
si alguien añade una tool y olvida la puerta, el CI falla.

Amplia TOOL_MODULES con tus propios ficheros de tools.

Ejecuta:  python3 tests/test_decorated.py
"""
import os, sys, ast

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ficheros que registran tools MCP; toda funcion publica debe ir @gated
TOOL_MODULES = ["mcp/example_tools.py"]

# helpers internos permitidos sin @gated (prefijo '_' ya se ignora; añade nombres aqui)
ALLOW_UNDECORATED = set()


def _is_gated(node):
    for dec in node.decorator_list:
        # admite @gated y @gated("name", ...)
        if isinstance(dec, ast.Name) and dec.id == "gated":
            return True
        if isinstance(dec, ast.Call) and isinstance(dec.func, ast.Name) and dec.func.id == "gated":
            return True
        if isinstance(dec, ast.Attribute) and dec.attr == "gated":
            return True
    return False


def main():
    failures = []
    for rel in TOOL_MODULES:
        path = os.path.join(ROOT, rel)
        tree = ast.parse(open(path).read(), filename=rel)
        funcs = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
        for fn in funcs:
            if fn.name.startswith("_") or fn.name in ALLOW_UNDECORATED:
                continue
            ok = _is_gated(fn)
            print(("  ok  " if ok else " FAIL ") + f"{rel}:{fn.name} @gated={ok}")
            if not ok:
                failures.append(f"{rel}:{fn.name}")

    print()
    if failures:
        print(f"TOOLS SIN @gated (amenaza #5): {failures}")
        sys.exit(1)
    print("TODAS LAS TOOLS CON EFECTOS ESTAN DECORADAS")


if __name__ == "__main__":
    main()
