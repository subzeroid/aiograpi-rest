from __future__ import annotations

import argparse
import ast
import inspect
from collections import defaultdict
from dataclasses import dataclass
from importlib.metadata import version as package_version
from pathlib import Path

from aiograpi import Client

ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = ROOT / "docs" / "aiograpi-coverage.md"
SOURCE_PATHS = [
    *sorted((ROOT / "aiograpi_rest" / "routers").glob("*.py")),
    ROOT / "aiograpi_rest" / "helpers.py",
    ROOT / "aiograpi_rest" / "storages.py",
]


@dataclass(frozen=True)
class ClientMethod:
    name: str
    module: str
    signature: str

    @property
    def area(self) -> str:
        parts = self.module.split(".")
        if "mixins" in parts:
            return parts[-1]
        return parts[-1]


@dataclass(frozen=True)
class RouteCoverage:
    method: str
    path: str
    client_methods: tuple[str, ...]


@dataclass(frozen=True)
class MethodClassification:
    status: str
    reason: str


INTERNAL_AREAS = {
    "auth",
    "bloks",
    "challenge",
    "graphql",
    "password",
    "private",
    "public",
    "signup",
}
INTERNAL_EXACT_METHODS = {
    "fetch_fb_dtsg",
    "init",
    "inject_sessionid_to_public",
    "login_flow",
    "one_tap_app_login",
    "parse_authorization",
    "pre_login_flow",
    "public_head",
    "request_log",
    "set_app",
    "set_country",
    "set_country_code",
    "set_ig_u_rur",
    "set_ig_www_claim",
    "small_delay",
    "very_small_delay",
    "with_query_params",
}
INTERNAL_PREFIXES = (
    "check_",
    "dump_",
    "gen_",
    "generate_",
    "handle_",
    "load_",
    "password_",
    "private_graphql_",
    "private_request",
    "public_",
    "send_signup_",
)
INTERNAL_FRAGMENTS = (
    "_configure",
    "_rupload",
    "_upload_to_cutout_sticker",
    "download_origin",
    "graphql_request",
)
VARIANT_SUFFIXES = (
    "_paginated_v1",
    "_threaded_gql_chunk",
    "_threaded_gql",
    "_gql_chunk",
    "_a1_chunk",
    "_v1_chunk",
    "_chunk",
    "_paginated",
    "_v2_gql",
    "_v2",
    "_v1",
    "_gql",
    "_a1",
)


class SourceAnalyzer(ast.NodeVisitor):
    def __init__(self, client_method_names: set[str]) -> None:
        self.client_method_names = client_method_names
        self.client_calls: dict[str, set[str]] = defaultdict(set)
        self.function_calls: dict[str, set[str]] = defaultdict(set)
        self.routes: list[tuple[str, str, str]] = []
        self._current_function: str | None = None
        self._router_prefixes: dict[str, str] = {}

    def visit_Assign(self, node: ast.Assign) -> None:
        if isinstance(node.value, ast.Call) and _call_name(node.value) == "APIRouter":
            prefix = ""
            for keyword in node.value.keywords:
                if keyword.arg == "prefix" and isinstance(keyword.value, ast.Constant):
                    prefix = str(keyword.value.value)
            for target in node.targets:
                if isinstance(target, ast.Name):
                    self._router_prefixes[target.id] = prefix
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_function(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_function(node)

    def visit_Call(self, node: ast.Call) -> None:
        if self._current_function:
            client_method = _client_method_name(node)
            if client_method in self.client_method_names:
                self.client_calls[self._current_function].add(client_method)
            if isinstance(node.func, ast.Name):
                self.function_calls[self._current_function].add(node.func.id)
        self.generic_visit(node)

    def _visit_function(self, node: ast.AsyncFunctionDef | ast.FunctionDef) -> None:
        previous = self._current_function
        self._current_function = node.name
        for decorator in node.decorator_list:
            route = self._route_from_decorator(decorator)
            if route:
                self.routes.append((route[0], route[1], node.name))
        self.generic_visit(node)
        self._current_function = previous

    def _route_from_decorator(self, decorator: ast.expr) -> tuple[str, str] | None:
        if not isinstance(decorator, ast.Call):
            return None
        func = decorator.func
        if not isinstance(func, ast.Attribute) or not isinstance(func.value, ast.Name):
            return None
        if func.value.id not in self._router_prefixes or func.attr not in {"delete", "get", "patch", "post", "put"}:
            return None
        if any(
            keyword.arg == "include_in_schema"
            and isinstance(keyword.value, ast.Constant)
            and keyword.value.value is False
            for keyword in decorator.keywords
        ):
            return None
        if not decorator.args or not isinstance(decorator.args[0], ast.Constant):
            return None
        suffix = str(decorator.args[0].value)
        return func.attr.upper(), f"{self._router_prefixes[func.value.id]}{suffix}"


def _call_name(node: ast.Call) -> str | None:
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    return None


def _client_method_name(node: ast.Call) -> str | None:
    if not isinstance(node.func, ast.Attribute):
        return None
    value = node.func.value
    if isinstance(value, ast.Name) and value.id in {"cl", "client"}:
        return node.func.attr
    if isinstance(value, ast.Call) and _call_name(value) == "Client":
        return node.func.attr
    return None


def client_methods() -> dict[str, ClientMethod]:
    methods: dict[str, ClientMethod] = {}
    for name, value in inspect.getmembers(Client):
        if name.startswith("_"):
            continue
        if not (inspect.isfunction(value) or inspect.ismethoddescriptor(value)):
            continue
        try:
            signature = str(inspect.signature(value))
        except (TypeError, ValueError):
            signature = "(...)"
        methods[name] = ClientMethod(
            name=name,
            module=getattr(value, "__module__", ""),
            signature=signature,
        )
    return dict(sorted(methods.items()))


def analyze_sources() -> tuple[dict[str, set[str]], dict[str, set[str]], list[tuple[str, str, str]]]:
    methods = client_methods()
    client_calls: dict[str, set[str]] = defaultdict(set)
    function_calls: dict[str, set[str]] = defaultdict(set)
    routes: list[tuple[str, str, str]] = []

    for path in SOURCE_PATHS:
        analyzer = SourceAnalyzer(set(methods))
        analyzer.visit(ast.parse(path.read_text(), filename=str(path)))
        for function, calls in analyzer.client_calls.items():
            client_calls[function].update(calls)
        for function, calls in analyzer.function_calls.items():
            function_calls[function].update(calls)
        routes.extend(analyzer.routes)
    return client_calls, function_calls, routes


def resolve_function_methods(
    function_name: str,
    client_calls: dict[str, set[str]],
    function_calls: dict[str, set[str]],
    seen: frozenset[str] = frozenset(),
) -> set[str]:
    if function_name in seen:
        return set()
    seen = seen | {function_name}
    methods = set(client_calls.get(function_name, set()))
    for child in function_calls.get(function_name, set()):
        methods.update(resolve_function_methods(child, client_calls, function_calls, seen))
    return methods


def route_coverage() -> list[RouteCoverage]:
    client_calls, function_calls, routes = analyze_sources()
    coverage = [
        RouteCoverage(
            method=method,
            path=path,
            client_methods=tuple(sorted(resolve_function_methods(function_name, client_calls, function_calls))),
        )
        for method, path, function_name in routes
    ]
    return sorted(coverage, key=lambda item: (item.path, item.method))


def classify_method(
    method: ClientMethod,
    covered_methods: set[str],
    method_names: set[str] | None = None,
) -> MethodClassification:
    if method.name in covered_methods:
        return MethodClassification("exposed", "used by at least one public REST route")

    if _is_internal_method(method):
        return MethodClassification("internal", "low-level aiograpi helper or unsafe generic surface")

    method_names = method_names or set(client_methods())
    root_name = _canonical_method_root(method.name)
    covered_roots = {_canonical_method_root(name) for name in covered_methods}
    if root_name in covered_roots:
        return MethodClassification("duplicate", f"variant of already exposed `{root_name}` route family")

    group_names = {
        name
        for name in method_names
        if _canonical_method_root(name) == root_name
    }
    primary_name = _primary_candidate_name(root_name, group_names)
    if method.name != primary_name:
        return MethodClassification("duplicate", f"variant of candidate `{primary_name}`")

    return MethodClassification("candidate", "potential user-facing REST endpoint")


def _canonical_method_root(name: str) -> str:
    current = name
    changed = True
    while changed:
        changed = False
        for suffix in VARIANT_SUFFIXES:
            if current.endswith(suffix):
                current = current[: -len(suffix)]
                changed = True
                break
    if name.endswith("_by_url_origin"):
        return name.removesuffix("_origin")
    if current.endswith("_infos"):
        return current.removesuffix("s")
    return current


def _primary_candidate_name(root_name: str, group_names: set[str]) -> str:
    if root_name in group_names:
        return root_name
    return min(group_names, key=lambda name: (_variant_score(name), len(name), name))


def _variant_score(name: str) -> int:
    if name.endswith("_chunk") or "_chunk_" in name:
        return 3
    if name.endswith(("_a1", "_gql", "_v1", "_v2")) or any(
        marker in name for marker in ("_a1_", "_gql_", "_v1_", "_v2_")
    ):
        return 2
    if name.endswith("_paginated") or "_paginated_" in name:
        return 1
    return 0


def _is_internal_method(method: ClientMethod) -> bool:
    name = method.name
    if method.area in INTERNAL_AREAS:
        return True
    if name in INTERNAL_EXACT_METHODS:
        return True
    if name.startswith(INTERNAL_PREFIXES):
        return True
    return any(fragment in name for fragment in INTERNAL_FRAGMENTS)


def build_markdown() -> str:
    methods = client_methods()
    routes = route_coverage()
    endpoints_by_method: dict[str, list[str]] = defaultdict(list)
    for route in routes:
        endpoint = f"`{route.method} {route.path}`"
        for method in route.client_methods:
            endpoints_by_method[method].append(endpoint)

    covered = {method for method, endpoints in endpoints_by_method.items() if endpoints}
    classifications = {
        method.name: classify_method(method, covered, set(methods))
        for method in methods.values()
    }
    by_area: dict[str, list[str]] = defaultdict(list)
    for method in methods.values():
        by_area[method.area].append(method.name)
    by_status: dict[str, list[str]] = defaultdict(list)
    for method_name, classification in classifications.items():
        by_status[classification.status].append(method_name)

    lines = [
        "# aiograpi Method Coverage",
        "",
        "<!-- Generated by scripts/generate_aiograpi_coverage.py. Do not edit manually. -->",
        "",
        f"`aiograpi-rest` wraps a focused subset of `aiograpi=={package_version('aiograpi')}`.",
        "It does not expose every public `aiograpi.Client` method. This page is generated from",
        "the installed `aiograpi.Client` class and the local FastAPI router implementation.",
        "",
        "## Summary",
        "",
        f"- Public `aiograpi.Client` methods: **{len(methods)}**",
        f"- Methods reached by REST routes: **{len(covered)}**",
        f"- Methods not exposed as REST routes: **{len(methods) - len(covered)}**",
        f"- Candidate REST backlog: **{len(by_status['candidate'])}**",
        "",
        "## REST Relevance",
        "",
        "| Status | Methods | Meaning |",
        "|---|---:|---|",
        f"| `exposed` | {len(by_status['exposed'])} | Already used by public REST routes. |",
        f"| `candidate` | {len(by_status['candidate'])} | Likely useful as a future user-facing REST endpoint. |",
        f"| `duplicate` | {len(by_status['duplicate'])} | Variant of an already exposed method, such as `_v1`, `_gql`, `_a1`, chunk, or origin helpers. |",
        f"| `internal` | {len(by_status['internal'])} | Low-level auth/request/configuration/signup/challenge helpers that should not be mirrored blindly. |",
        "",
        "## Coverage By Area",
        "",
        "| Area | Exposed | Candidates | Duplicates | Internal | Total |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for area in sorted(by_area):
        total = len(by_area[area])
        area_statuses = [classifications[method].status for method in by_area[area]]
        exposed_count = area_statuses.count("exposed")
        candidate_count = area_statuses.count("candidate")
        duplicate_count = area_statuses.count("duplicate")
        internal_count = area_statuses.count("internal")
        lines.append(
            f"| `{area}` | {exposed_count} | {candidate_count} | "
            f"{duplicate_count} | {internal_count} | {total} |"
        )

    lines.extend([
        "",
        "## Candidate Backlog By Area",
        "",
        "| Area | Candidate methods |",
        "|---|---|",
    ])
    for area in sorted(by_area):
        candidates = [
            f"`{method}`"
            for method in by_area[area]
            if classifications[method].status == "candidate"
        ]
        if candidates:
            lines.append(f"| `{area}` | {', '.join(candidates)} |")

    lines.extend([
        "",
        "## REST Routes To aiograpi Methods",
        "",
        "| REST endpoint | aiograpi methods used |",
        "|---|---|",
    ])
    for route in routes:
        methods_text = ", ".join(f"`{method}`" for method in route.client_methods) or "-"
        lines.append(f"| `{route.method} {route.path}` | {methods_text} |")

    lines.extend([
        "",
        "## Full Method Matrix",
        "",
        "| aiograpi method | Area | REST endpoint(s) | Status | Notes |",
        "|---|---|---|---|---|",
    ])
    for method in methods.values():
        endpoints = endpoints_by_method.get(method.name, [])
        endpoint_text = "<br>".join(endpoints) if endpoints else "-"
        classification = classifications[method.name]
        lines.append(
            f"| `{method.name}{method.signature}` | `{method.area}` | {endpoint_text} | "
            f"`{classification.status}` | {classification.reason} |"
        )

    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="Fail if the generated docs are out of date.")
    args = parser.parse_args()

    content = build_markdown()
    if args.check:
        current = DOC_PATH.read_text() if DOC_PATH.exists() else ""
        if current != content:
            print(f"{DOC_PATH} is out of date. Run scripts/generate_aiograpi_coverage.py.")
            return 1
        return 0

    DOC_PATH.parent.mkdir(parents=True, exist_ok=True)
    DOC_PATH.write_text(content)
    print(f"Wrote {DOC_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
