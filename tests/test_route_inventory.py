from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app"


def _decorator_routes(tree: ast.AST):
    routes = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for decorator in node.decorator_list:
            if not isinstance(decorator, ast.Call):
                continue
            if not isinstance(decorator.func, ast.Attribute):
                continue
            name = decorator.func.attr
            if name not in {"route", "get", "post", "put", "patch", "delete", "options", "head"}:
                continue
            if not decorator.args or not isinstance(decorator.args[0], ast.Constant):
                continue
            path = decorator.args[0].value
            if not isinstance(path, str):
                continue

            if name == "route":
                methods = {"GET"}
                for kw in decorator.keywords:
                    if kw.arg == "methods" and isinstance(kw.value, (ast.List, ast.Tuple, ast.Set)):
                        methods = {
                            item.value.upper()
                            for item in kw.value.elts
                            if isinstance(item, ast.Constant) and isinstance(item.value, str)
                        }
            else:
                methods = {name.upper()}

            for method in methods:
                routes.append((path, method, str(node.name), str(node.lineno)))
    return routes


def test_no_duplicate_static_routes():
    files = sorted((APP / "routes").glob("*.py")) + [APP / "legacy.py"]
    seen: dict[tuple[str, str], tuple[str, str]] = {}
    duplicates = []

    for path in files:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for route, method, function, line in _decorator_routes(tree):
            key = (route, method)
            location = (str(path.relative_to(ROOT)), f"{function}:{line}")
            if key in seen:
                duplicates.append((key, seen[key], location))
            else:
                seen[key] = location

    assert not duplicates, "Duplicate HTTP routes found: " + "; ".join(
        f"{method} {route}: {first[0]}:{first[1]} and {second[0]}:{second[1]}"
        for (route, method), first, second in duplicates
    )
