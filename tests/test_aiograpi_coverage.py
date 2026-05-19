import ast
import sys

import scripts.generate_aiograpi_coverage as coverage_script
from scripts.generate_aiograpi_coverage import (
    DOC_PATH,
    SourceAnalyzer,
    build_markdown,
    client_methods,
    resolve_function_methods,
    route_coverage,
)


def test_aiograpi_coverage_doc_is_current():
    assert DOC_PATH.read_text() == build_markdown()


def test_rest_routes_reference_existing_aiograpi_methods():
    methods = set(client_methods())
    missing = {
        method
        for route in route_coverage()
        for method in route.client_methods
        if method not in methods
    }
    assert missing == set()


def test_aiograpi_rest_documents_partial_client_coverage():
    methods = set(client_methods())
    covered = {
        method
        for route in route_coverage()
        for method in route.client_methods
    }
    assert covered < methods
    assert {"login", "user_about_v1", "photo_upload", "video_upload_to_story"} <= covered


def test_source_analyzer_ignores_non_route_decorators():
    analyzer = SourceAnalyzer({"login"})
    assert analyzer._route_from_decorator(ast.Name(id="decorator", ctx=ast.Load())) is None
    assert analyzer._route_from_decorator(ast.parse("router_factory().get('/x')").body[0].value) is None
    assert analyzer._route_from_decorator(ast.parse("other.get('/x')").body[0].value) is None
    assert analyzer._route_from_decorator(ast.parse("router.websocket('/x')").body[0].value) is None
    assert analyzer._route_from_decorator(ast.parse("router.get()").body[0].value) is None
    analyzer._router_prefixes["router"] = ""
    assert analyzer._route_from_decorator(ast.parse("router.get()").body[0].value) is None
    assert analyzer._route_from_decorator(ast.parse("router.get(path)").body[0].value) is None
    assert coverage_script._call_name(ast.parse("factory['x']()").body[0].value) is None


def test_source_analyzer_tracks_prefixes_per_router_variable():
    analyzer = SourceAnalyzer({"login"})
    source = """
from fastapi import APIRouter

router = APIRouter(prefix="/media")
user_router = APIRouter(prefix="/user")

@router.get("")
async def media_info():
    pass

@user_router.get("/posts")
async def user_medias():
    pass

@router.get("/hidden", include_in_schema=False)
async def hidden_alias():
    pass
"""
    analyzer.visit(ast.parse(source))

    assert ("GET", "/media", "media_info") in analyzer.routes
    assert ("GET", "/user/posts", "user_medias") in analyzer.routes
    assert ("GET", "/media/hidden", "hidden_alias") not in analyzer.routes


def test_client_methods_falls_back_when_signature_is_unavailable(monkeypatch):
    def fake_getmembers(_client):
        return [
            ("_private", lambda: None),
            ("broken_signature", lambda: None),
            ("not_method", object()),
        ]

    def fake_signature(_value):
        raise ValueError("signature unavailable")

    monkeypatch.setattr(coverage_script.inspect, "getmembers", fake_getmembers)
    monkeypatch.setattr(coverage_script.inspect, "signature", fake_signature)

    methods = coverage_script.client_methods()

    assert set(methods) == {"broken_signature"}
    assert methods["broken_signature"].signature == "(...)"


def test_resolve_function_methods_handles_cycles():
    methods = resolve_function_methods(
        "parent",
        client_calls={"parent": {"login"}},
        function_calls={"parent": {"child"}, "child": {"parent"}},
    )
    assert methods == {"login"}


def test_coverage_generator_main_writes_and_checks_docs(monkeypatch, tmp_path, capsys):
    doc_path = tmp_path / "docs" / "aiograpi-coverage.md"
    monkeypatch.setattr(coverage_script, "ROOT", tmp_path)
    monkeypatch.setattr(coverage_script, "DOC_PATH", doc_path)
    monkeypatch.setattr(coverage_script, "build_markdown", lambda: "generated\n")

    monkeypatch.setattr(sys, "argv", ["generate_aiograpi_coverage.py"])
    assert coverage_script.main() == 0
    assert doc_path.read_text() == "generated\n"
    assert "Wrote" in capsys.readouterr().out

    monkeypatch.setattr(sys, "argv", ["generate_aiograpi_coverage.py", "--check"])
    assert coverage_script.main() == 0

    doc_path.write_text("stale\n")
    assert coverage_script.main() == 1
    assert "out of date" in capsys.readouterr().out
