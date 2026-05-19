import ast
import sys

import scripts.generate_aiograpi_coverage as coverage_script
from scripts.generate_aiograpi_coverage import (
    DOC_PATH,
    ClientMethod,
    SourceAnalyzer,
    build_markdown,
    classify_method,
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


def test_aiograpi_coverage_classifies_methods_by_rest_relevance():
    methods = client_methods()
    covered = {
        method
        for route in route_coverage()
        for method in route.client_methods
    }

    assert classify_method(methods["user_about_v1"], covered).status == "exposed"
    assert classify_method(methods["collections"], covered).status == "candidate"
    assert classify_method(methods["collection_medias"], covered).status == "candidate"
    assert classify_method(methods["collection_medias_v1"], covered).status == "duplicate"
    assert classify_method(methods["direct_message_like"], covered).status == "exposed"
    assert classify_method(methods["direct_message_search"], covered).status == "exposed"
    assert classify_method(methods["reels"], covered).status == "exposed"
    assert classify_method(methods["friends_reels"], covered).status == "exposed"
    assert classify_method(methods["explore_reels"], covered).status == "exposed"
    assert classify_method(methods["reels_timeline_media"], covered).status == "exposed"
    assert classify_method(methods["comment_likers_gql"], covered).status == "candidate"
    assert classify_method(methods["comment_likers_gql_chunk"], covered).status == "duplicate"
    assert classify_method(methods["hashtag_medias_a1"], covered).status == "duplicate"
    assert classify_method(methods["media_info_gql"], covered).status == "duplicate"
    assert classify_method(methods["user_followers_gql"], covered).status == "duplicate"
    assert classify_method(methods["photo_configure"], covered).status == "internal"
    assert classify_method(methods["graphql_request"], covered).status == "internal"
    assert classify_method(methods["signup"], covered).status == "internal"


def test_aiograpi_coverage_classifies_paginated_variants_and_exact_internal_helpers():
    covered: set[str] = set()
    method_names = {"thing", "thing_paginated", "set_app", "stream_paginated", "stream_paginated_v1"}

    assert classify_method(
        ClientMethod("thing_paginated", "aiograpi.mixins.media", "(self)"),
        covered,
        method_names,
    ).status == "duplicate"
    assert classify_method(
        ClientMethod("stream_paginated", "aiograpi.mixins.media", "(self)"),
        covered,
        method_names,
    ).status == "candidate"
    assert classify_method(
        ClientMethod("stream_paginated_v1", "aiograpi.mixins.media", "(self)"),
        covered,
        method_names,
    ).status == "duplicate"
    assert classify_method(
        ClientMethod("set_app", "aiograpi.mixins.media", "(self)"),
        covered,
        method_names,
    ).status == "internal"


def test_aiograpi_coverage_markdown_summarizes_candidate_backlog():
    markdown = build_markdown()

    assert "## REST Relevance" in markdown
    assert "## Candidate Backlog By Area" in markdown
    assert "| `collection` |" in markdown
    assert "`collections`" in markdown
    assert "`collection_medias_v1`" not in markdown.split("## Full Method Matrix", 1)[0]
    assert "`direct_message_like`" in markdown
    assert "`comment_likers_gql`" in markdown
    assert "| `media_info_gql" in markdown
    assert "`duplicate`" in markdown
    assert "`internal`" in markdown


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
