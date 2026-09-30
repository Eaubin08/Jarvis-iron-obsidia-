# runtime_wiring/source_runtime/runtime_inventory_builder.py
# P37 — Inventaire statique AST du repo Obsidia X-108.
# Scan Python files via ast.parse — ZERO exécution, ZERO import dynamique.
# KX108_ONLY. No ACT. No write. Readonly.
from __future__ import annotations

import ast
import pathlib
from typing import Any, Dict, List, Optional, Tuple

# ── Repo root (3 niveaux au-dessus de ce fichier) ────────────────────────────
_THIS_FILE = pathlib.Path(__file__).resolve()
_REPO_ROOT = _THIS_FILE.parent.parent.parent

# ── Répertoires à scanner ─────────────────────────────────────────────────────
_PY_SCAN_ROOTS: List[str] = [
    "runtime_wiring",
    "apps/obsidia_api/routes",
    "apps/obsidia_api",
]
_TEST_ROOTS: List[str] = [
    "tests",
    "tests/api",
]
_DOC_ROOTS: List[str] = [
    "docs/real_engine",
    "docs/source_packs",
]

# ── Risk patterns dans le source (scan textuel) ────────────────────────────────
_RISK_TOKENS = {
    "subprocess": "SUBPROCESS_RISK",
    "eval(": "EVAL_RISK",
    "__import__": "DYNAMIC_IMPORT_RISK",
    "os.system": "SHELL_RISK",
    "runtime_allowed_now=True": "RUNTIME_ALLOWED_NOW_TRUE",
    "emits_act=True": "EMITS_ACT_TRUE",
}

# ── Router prefixes connus (pour reconstruire les routes complètes) ────────────
_KNOWN_PREFIXES: Dict[str, str] = {
    "source_runtime_status": "/api/runtime-wiring/source-runtime",
    "brody": "/api/brody",
    "os_trad_ir_reverse": "/api/runtime-wiring/os-trad",
    "runtime_wiring_preview": "/api/runtime-wiring",
    "status": "/api",
    "os3": "/api/os3",
    "x108": "/api/x108",
    "memory": "/api/memory",
    "graphiti": "/api/graphiti",
    "gencoin": "/api/gencoin",
    "audit": "/api/audit",
    "blockchain": "/api/blockchain",
    "bus": "/api/bus",
    "context": "/api/context",
    "periphery_ops": "/api/periphery",
    "runtime_freeze": "/api/runtime-freeze",
    "sigma_monitoring": "/api/sigma",
    "translation": "/api/translation",
    "worldcalls": "/api/worldcalls",
}


# ── Helpers AST ───────────────────────────────────────────────────────────────

def _safe_unparse(node: ast.expr) -> str:
    """ast.unparse (Python 3.9+) avec fallback."""
    try:
        return ast.unparse(node)
    except Exception:
        if isinstance(node, ast.Constant):
            return repr(node.value)
        if isinstance(node, ast.Attribute):
            return f"{_safe_unparse(node.value)}.{node.attr}"
        if isinstance(node, ast.Name):
            return node.id
        return "<expr>"


def _extract_route_path(decorator_str: str) -> Optional[str]:
    """Extrait le chemin de route depuis une string de décorateur type '@router.get("/foo")'."""
    for sep in ['("', "('", '("/']:
        if sep in decorator_str:
            start = decorator_str.index(sep) + len(sep) - 1
            end_char = '"' if '"' in sep else "'"
            end = decorator_str.find(end_char, start + 1)
            if end > start:
                return decorator_str[start:end + 1].strip('"').strip("'")
    return None


def _get_prefix_for_file(stem: str) -> str:
    """Retourne le prefix APIRouter connu pour un fichier routes/."""
    return _KNOWN_PREFIXES.get(stem, "/api")


def _detect_risk_flags(source_text: str) -> List[str]:
    flags = []
    for token, flag in _RISK_TOKENS.items():
        if token in source_text:
            flags.append(flag)
    return flags


def _first_line(text: str) -> str:
    if not text:
        return ""
    return text.strip().split("\n")[0].strip()


# ── Scanner Python ─────────────────────────────────────────────────────────────

def _scan_python_file(file_path: pathlib.Path) -> Dict[str, Any]:
    """Parse un fichier .py avec AST et retourne son inventaire."""
    rel = file_path.relative_to(_REPO_ROOT).as_posix()
    stem = file_path.stem

    try:
        source = file_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return {
            "module_path": rel, "status": "READ_ERROR",
            "functions": [], "classes": [], "routes": [], "imports_summary": [],
            "risk_flags": [], "docstring_first": "",
        }

    try:
        tree = ast.parse(source, filename=str(file_path))
    except SyntaxError as exc:
        return {
            "module_path": rel, "status": f"PARSE_ERROR:{exc.msg}",
            "functions": [], "classes": [], "routes": [], "imports_summary": [],
            "risk_flags": _detect_risk_flags(source), "docstring_first": "",
        }

    prefix = _get_prefix_for_file(stem)
    risk_flags = _detect_risk_flags(source)

    module_doc = ast.get_docstring(tree) or ""
    doc_first = _first_line(module_doc)

    functions: List[Dict[str, Any]] = []
    classes: List[Dict[str, Any]] = []
    routes: List[Dict[str, Any]] = []
    imports_summary: List[str] = []

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            if isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                names = [alias.name for alias in node.names]
                imports_summary.append(f"from {mod} import {', '.join(names[:3])}")
            else:
                imports_summary.append(f"import {', '.join(a.name for a in node.names[:3])}")

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            decorators: List[str] = []
            route_rel_path: Optional[str] = None

            for dec in node.decorator_list:
                dec_str = _safe_unparse(dec)
                decorators.append(dec_str)
                if any(m in dec_str for m in (".get(", ".post(", ".put(", ".delete(", ".patch(")):
                    rpath = _extract_route_path(dec_str)
                    if rpath:
                        route_rel_path = rpath

            fn_doc = ast.get_docstring(node) or ""
            fn_doc_first = _first_line(fn_doc)

            functions.append({
                "name": node.name,
                "module_path": rel,
                "line": node.lineno,
                "docstring_first": fn_doc_first,
                "decorators": decorators,
                "is_async": isinstance(node, ast.AsyncFunctionDef),
                "is_test": node.name.startswith("test_"),
                "risk_flags": [],
            })

            if route_rel_path:
                full_path = prefix.rstrip("/") + "/" + route_rel_path.lstrip("/")
                routes.append({
                    "path": full_path,
                    "relative_path": route_rel_path,
                    "function": node.name,
                    "module_path": rel,
                    "line": node.lineno,
                    "method": _detect_method(decorators),
                })

        elif isinstance(node, ast.ClassDef):
            cls_doc = ast.get_docstring(node) or ""
            cls_doc_first = _first_line(cls_doc)
            classes.append({
                "name": node.name,
                "module_path": rel,
                "line": node.lineno,
                "docstring_first": cls_doc_first,
            })

    return {
        "module_path": rel,
        "stem": stem,
        "status": "OK",
        "docstring_first": doc_first,
        "functions": functions,
        "classes": classes,
        "routes": routes,
        "imports_summary": imports_summary[:10],
        "risk_flags": risk_flags,
    }


def _detect_method(decorators: List[str]) -> str:
    for d in decorators:
        for method in ("post", "get", "put", "delete", "patch"):
            if f".{method}(" in d:
                return method.upper()
    return "GET"


# ── Scanner Docs ──────────────────────────────────────────────────────────────

def _scan_doc_file(file_path: pathlib.Path) -> Dict[str, Any]:
    rel = file_path.relative_to(_REPO_ROOT).as_posix()
    try:
        lines = file_path.read_text(encoding="utf-8", errors="replace").splitlines()
        first_line = ""
        for line in lines:
            stripped = line.strip().lstrip("#").strip()
            if stripped:
                first_line = stripped
                break
    except OSError:
        first_line = ""
    return {
        "doc_path": rel,
        "stem": file_path.stem,
        "first_line": first_line,
        "extension": file_path.suffix,
    }


# ── Scanner Test ──────────────────────────────────────────────────────────────

def _scan_test_file(file_path: pathlib.Path) -> Dict[str, Any]:
    base = _scan_python_file(file_path)
    rel = file_path.relative_to(_REPO_ROOT).as_posix()
    test_functions = [f["name"] for f in base["functions"] if f.get("is_test")]
    # Heuristic: guess the module being tested from the filename
    stem = file_path.stem  # e.g. test_capability_path_router_p36
    covered_module_hint = _guess_covered_module(stem)
    return {
        "test_path": rel,
        "stem": file_path.stem,
        "status": base["status"],
        "test_functions": test_functions,
        "test_count": len(test_functions),
        "covered_module_hint": covered_module_hint,
        "risk_flags": base.get("risk_flags", []),
    }


def _guess_covered_module(test_stem: str) -> str:
    """Infère le module couvert depuis le nom d'un fichier test."""
    name = test_stem
    if name.startswith("test_"):
        name = name[5:]
    # Remove trailing _pXX palier suffix
    import re
    name = re.sub(r"_p\d+$", "", name)
    # Map to known module paths
    _KNOWN_MODULE_HINTS: Dict[str, str] = {
        "capability_path_router": "runtime_wiring/source_runtime/capability_path_router.py",
        "capability_path_preview": "apps/obsidia_api/routes/source_runtime_status.py",
        "runtime_inventory_graph": "runtime_wiring/source_runtime/runtime_inventory_graph.py",
        "runtime_inventory_preview": "apps/obsidia_api/routes/source_runtime_status.py",
        "reverse_os_interlanguage_runtime_extension": "runtime_wiring/source_runtime/reverse_os_interlanguage_index.py",
        "reverse_os_interlanguage_preview": "apps/obsidia_api/routes/source_runtime_status.py",
        "source_runtime_status": "apps/obsidia_api/routes/source_runtime_status.py",
        "os_trad_reverse_preview": "apps/obsidia_api/routes/source_runtime_status.py",
    }
    return _KNOWN_MODULE_HINTS.get(name, f"runtime_wiring/source_runtime/{name}.py")


# ── Collecte des fichiers ─────────────────────────────────────────────────────

def _collect_py_files(roots: List[str], recursive: bool = True) -> List[pathlib.Path]:
    files: List[pathlib.Path] = []
    seen: set = set()
    for root_str in roots:
        root = _REPO_ROOT / root_str
        if not root.exists():
            continue
        pattern = "**/*.py" if recursive else "*.py"
        for f in sorted(root.glob(pattern)):
            if "__pycache__" in f.parts:
                continue
            if f not in seen:
                seen.add(f)
                files.append(f)
    return files


def _collect_doc_files(roots: List[str]) -> List[pathlib.Path]:
    files: List[pathlib.Path] = []
    for root_str in roots:
        root = _REPO_ROOT / root_str
        if not root.exists():
            continue
        for f in sorted(root.glob("**/*.md")):
            files.append(f)
    return files


# ── Point d'entrée principal ──────────────────────────────────────────────────

def build_static_inventory() -> Dict[str, Any]:
    """
    Scan statique AST du repo Obsidia X-108.

    Retourne un inventaire structuré :
    - modules: liste de tous les modules scannés
    - functions: liste de toutes les fonctions
    - classes: liste de toutes les classes
    - routes: liste de toutes les routes API
    - adapters: liste des adapters détectés (heuristique nom)
    - tests: liste de tous les fichiers test
    - docs: liste de tous les fichiers docs

    Invariants : readonly=True, runtime_allowed_now=False, emits_act=False.
    """
    # Scan Python modules
    py_roots = [
        "runtime_wiring",
        "apps/obsidia_api/routes",
        "apps/obsidia_api",
    ]
    py_files = _collect_py_files(py_roots, recursive=True)

    modules: List[Dict[str, Any]] = []
    all_functions: List[Dict[str, Any]] = []
    all_classes: List[Dict[str, Any]] = []
    all_routes: List[Dict[str, Any]] = []
    all_adapters: List[Dict[str, Any]] = []
    risk_modules: List[str] = []

    for f in py_files:
        info = _scan_python_file(f)
        modules.append({
            "module_path": info["module_path"],
            "stem": info.get("stem", f.stem),
            "status": info["status"],
            "docstring_first": info["docstring_first"],
            "function_count": len(info["functions"]),
            "class_count": len(info["classes"]),
            "route_count": len(info["routes"]),
            "risk_flags": info["risk_flags"],
        })
        all_functions.extend(info["functions"])
        all_classes.extend(info["classes"])
        all_routes.extend(info["routes"])
        if info["risk_flags"]:
            risk_modules.append(info["module_path"])

        # Heuristique adapters : fonctions dont le nom finit par _to_context_packet
        for fn in info["functions"]:
            if fn["name"].endswith("_to_context_packet"):
                all_adapters.append({
                    "adapter_name": fn["name"],
                    "module_path": info["module_path"],
                    "line": fn["line"],
                    "docstring_first": fn["docstring_first"],
                })

    # Scan tests
    test_roots = ["tests", "tests/api"]
    test_files_paths = _collect_py_files(test_roots, recursive=False)
    all_tests: List[Dict[str, Any]] = []
    for f in test_files_paths:
        if f.name.startswith("test_"):
            all_tests.append(_scan_test_file(f))

    # Scan docs
    doc_roots = ["docs/real_engine", "docs/source_packs"]
    doc_file_paths = _collect_doc_files(doc_roots)
    all_docs: List[Dict[str, Any]] = []
    for f in doc_file_paths:
        all_docs.append(_scan_doc_file(f))

    return {
        "inventory_status": "READY",
        "repo_root": str(_REPO_ROOT),
        "module_count": len(modules),
        "function_count": len(all_functions),
        "class_count": len(all_classes),
        "route_count": len(all_routes),
        "adapter_count": len(all_adapters),
        "test_file_count": len(all_tests),
        "doc_file_count": len(all_docs),
        "risk_module_count": len(risk_modules),
        "modules": modules,
        "functions": all_functions,
        "classes": all_classes,
        "routes": all_routes,
        "adapters": all_adapters,
        "tests": all_tests,
        "docs": all_docs,
        "risk_modules": risk_modules,
        "readonly": True,
        "runtime_allowed_now": False,
        "emits_act": False,
        "decision_authority": "KX108_ONLY",
    }
