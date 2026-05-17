import json
import re
import tomllib
from importlib.metadata import PackageNotFoundError
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
NODE24_ACTION_VERSIONS = {
    "actions/checkout": "v6.0.2",
    "actions/setup-python": "v6.2.0",
    "docker/build-push-action": "v7.1.0",
    "docker/login-action": "v4.1.0",
    "docker/metadata-action": "v6.0.0",
    "docker/setup-buildx-action": "v4.0.0",
    "docker/setup-qemu-action": "v4.0.0",
    "softprops/action-gh-release": "v3.0.0",
}


def project_version() -> str:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text())
    return pyproject["project"]["version"]


def test_pyproject_replaces_requirements_txt():
    assert not (ROOT / "requirements.txt").exists()
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text())
    deps = pyproject["project"]["dependencies"]
    assert "aiograpi==0.9.7" in deps
    assert pyproject["project"]["requires-python"] == ">=3.13"
    assert pyproject["project"]["name"] == "aiograpi-rest"
    assert re.fullmatch(r"\d+\.\d+\.\d+", pyproject["project"]["version"])
    assert pyproject["project"]["urls"]["Repository"] == "https://github.com/subzeroid/aiograpi-rest"


def test_app_version_is_single_sourced_from_pyproject():
    import main

    version = project_version()
    assert main.APP_VERSION == version
    assert main._app_version() == version
    assert 'APP_VERSION = "' not in (ROOT / "main.py").read_text()
    assert "Current API version: `" not in (ROOT / "README.md").read_text()


def test_project_version_can_be_read_from_explicit_pyproject(tmp_path):
    import main

    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "aiograpi-rest"\nversion = "9.8.7"\n')

    assert main._project_version(pyproject) == "9.8.7"
    assert main._project_version(tmp_path / "missing.toml") is None


def test_app_version_falls_back_to_distribution_metadata(monkeypatch):
    import main

    monkeypatch.setattr(main, "_project_version", lambda: None)
    monkeypatch.setattr(main, "package_version", lambda name: "9.9.9")

    assert main._app_version() == "9.9.9"


def test_app_version_returns_unknown_when_metadata_is_missing(monkeypatch):
    import main

    def missing_version(name):
        raise PackageNotFoundError(name)

    monkeypatch.setattr(main, "_project_version", lambda: None)
    monkeypatch.setattr(main, "package_version", missing_version)

    assert main._app_version() == "0+unknown"


def test_dockerfile_uses_python_313_and_pyproject_install():
    dockerfile = (ROOT / "Dockerfile").read_text()
    assert "FROM python:3.13-slim" in dockerfile
    assert "APP_VERSION" not in dockerfile
    assert "requirements.txt" not in dockerfile
    assert "pip install ." in dockerfile
    assert "pip install \".[test,docs]\"" in dockerfile
    assert "apt-get install" not in dockerfile
    assert "ffmpeg" not in dockerfile
    assert "gcc" not in dockerfile
    assert "ARG GIT_SHA=" in dockerfile
    assert "ARG BUILD_TIME=" in dockerfile
    assert "ENV GIT_SHA=${GIT_SHA}" in dockerfile
    assert "ENV BUILD_TIME=${BUILD_TIME}" in dockerfile
    assert "org.opencontainers.image.source=\"https://github.com/subzeroid/aiograpi-rest\"" in dockerfile
    assert "chown -R aiograpi:aiograpi /app" in dockerfile
    assert "USER aiograpi" in dockerfile
    assert "HEALTHCHECK" in dockerfile
    assert "http://127.0.0.1:8000/health" in dockerfile


def test_compose_runs_api_service_on_8000():
    compose = yaml.safe_load((ROOT / "docker-compose.yml").read_text())
    assert compose["name"] == "aiograpi-rest"
    api = compose["services"]["api"]
    assert api["build"] == {"context": ".", "target": "runtime"}
    assert "8000:8000" in api["ports"]
    test = compose["services"]["test"]
    assert test["build"] == {"context": ".", "target": "test"}
    assert test["profiles"] == ["test"]


def test_release_workflow_publishes_packages_images_and_artifacts():
    assert not (ROOT / ".github" / "workflows" / "docker.yml").exists()
    workflow = yaml.load((ROOT / ".github" / "workflows" / "release.yml").read_text(), Loader=yaml.BaseLoader)
    assert workflow["name"] == "Release"
    assert workflow["env"]["FORCE_JAVASCRIPT_ACTIONS_TO_NODE24"] == "true"
    assert workflow["on"]["push"]["tags"] == ["[0-9]+.[0-9]+.[0-9]+", "v[0-9]+.[0-9]+.[0-9]+"]
    assert workflow["env"]["DOCKERHUB_IMAGE"] == "subzeroid/aiograpi-rest"
    assert workflow["env"]["GHCR_IMAGE"] == "ghcr.io/subzeroid/aiograpi-rest"
    assert workflow["jobs"]["publish"]["permissions"] == {
        "contents": "write",
        "id-token": "write",
        "packages": "write",
    }

    steps = workflow["jobs"]["publish"]["steps"]
    run_commands = "\n".join(step.get("run", "") for step in steps)
    assert "ruff check ." in run_commands
    assert "python scripts/generate_aiograpi_coverage.py --check" in run_commands
    assert "pytest --cov=. --cov-report=term-missing --cov-fail-under=100" in run_commands
    assert "mkdocs build --strict" in run_commands
    assert "python scripts/export_openapi.py release/openapi.json" in run_commands
    assert "python -m build" in run_commands

    dockerhub_login = next(step for step in steps if step.get("name") == "Log in to Docker Hub")
    assert dockerhub_login["uses"] == "docker/login-action@v4.1.0"
    assert dockerhub_login["with"]["username"] == "subzeroid"

    ghcr_login = next(step for step in steps if step.get("name") == "Log in to GitHub Container Registry")
    assert ghcr_login["uses"] == "docker/login-action@v4.1.0"
    assert ghcr_login["with"]["registry"] == "ghcr.io"

    assert any(step.get("uses") == "docker/build-push-action@v7.1.0" for step in steps)

    metadata_step = next(step for step in steps if step.get("uses") == "docker/metadata-action@v6.0.0")
    assert "${{ env.DOCKERHUB_IMAGE }}" in metadata_step["with"]["images"]
    assert "${{ env.GHCR_IMAGE }}" in metadata_step["with"]["images"]

    build_step = next(step for step in steps if step.get("uses") == "docker/build-push-action@v7.1.0")
    assert build_step["with"]["target"] == "runtime"
    assert build_step["with"]["platforms"] == "linux/amd64,linux/arm64"
    assert build_step["with"]["push"] == "true"
    assert build_step["with"]["provenance"] == "false"
    assert "APP_VERSION" not in build_step["with"].get("build-args", "")
    assert "GIT_SHA=${{ github.sha }}" in build_step["with"]["build-args"]
    assert "BUILD_TIME=${{ steps.build_time.outputs.value }}" in build_step["with"]["build-args"]

    pypi_step = next(step for step in steps if step.get("uses") == "pypa/gh-action-pypi-publish@release/v1")
    assert "with" not in pypi_step

    release_step = next(step for step in steps if step.get("uses") == "softprops/action-gh-release@v3.0.0")
    assert "release/openapi.json" in release_step["with"]["files"]
    assert "dist/*.whl" in release_step["with"]["files"]
    assert "dist/*.tar.gz" in release_step["with"]["files"]


def test_release_workflow_verifies_published_artifacts():
    workflow = yaml.load((ROOT / ".github" / "workflows" / "release.yml").read_text(), Loader=yaml.BaseLoader)
    assert workflow["jobs"]["publish"]["outputs"]["tag"] == "${{ github.ref_name }}"
    assert workflow["jobs"]["publish"]["outputs"]["version"] == "${{ steps.version.outputs.value }}"

    steps = workflow["jobs"]["publish"]["steps"]
    version_step = next(step for step in steps if step.get("name") == "Normalize release version")
    assert version_step["id"] == "version"
    assert "GITHUB_REF_NAME#v" in version_step["run"]

    verify = workflow["jobs"]["verify"]
    assert verify["needs"] == "publish"
    assert verify["env"]["RELEASE_TAG"] == "${{ needs.publish.outputs.tag }}"
    assert verify["env"]["VERSION"] == "${{ needs.publish.outputs.version }}"
    assert verify["permissions"] == {"contents": "read"}

    run_commands = "\n".join(step.get("run", "") for step in verify["steps"])
    assert "https://pypi.org/pypi/aiograpi-rest/json" in run_commands
    assert 'docker buildx imagetools inspect "$DOCKERHUB_IMAGE:$VERSION"' in run_commands
    assert 'docker buildx imagetools inspect "$GHCR_IMAGE:$VERSION"' in run_commands
    assert 'gh release view "$RELEASE_TAG"' in run_commands
    assert 'os.environ["VERSION"]' in run_commands
    assert "docker run --pull always" in run_commands
    assert "http://127.0.0.1:18080/health" in run_commands
    assert "http://127.0.0.1:18080/build" in run_commands


def test_live_tests_workflow_runs_nightly_against_real_session_flow():
    workflow = yaml.load((ROOT / ".github" / "workflows" / "live-tests.yml").read_text(), Loader=yaml.BaseLoader)

    assert workflow["name"] == "Live Tests"
    assert workflow["env"]["FORCE_JAVASCRIPT_ACTIONS_TO_NODE24"] == "true"
    assert workflow["on"]["workflow_dispatch"] == {}
    assert workflow["on"]["schedule"] == [{"cron": "17 3 * * *"}]

    job = workflow["jobs"]["live"]
    assert job["if"] == "github.repository == 'subzeroid/aiograpi-rest'"
    assert job["timeout-minutes"] == "30"
    assert job["env"]["TEST_ACCOUNTS_URL"] == "${{ secrets.TEST_ACCOUNTS_URL }}"
    assert job["env"]["TEST_ACCOUNTS_COUNT"] == "25"
    assert job["env"]["LIVE_ACCOUNT_TIMEOUT"] == "90"
    assert job["env"]["LIVE_STORY_ACCOUNTS_COUNT"] == "5"
    assert job["env"]["LIVE_STORY_TIMEOUT"] == "240"
    assert job["env"]["LIVE_API_BASE_URL"] == "http://127.0.0.1:8000"

    steps = job["steps"]
    assert any(step.get("uses") == "actions/checkout@v6.0.2" for step in steps)
    assert any(step.get("uses") == "actions/setup-python@v6.2.0" for step in steps)

    run_commands = "\n".join(step.get("run", "") for step in steps)
    assert "docker compose up -d api" in run_commands
    assert "curl -fsS http://127.0.0.1:8000/health" in run_commands
    assert "pytest tests/live -m live -o addopts='' -v" in run_commands
    assert "::notice::TEST_ACCOUNTS_URL is not configured; skipping live tests." in run_commands
    assert "docker compose logs api" in run_commands


def test_workflows_opt_into_node24_actions():
    for path in sorted((ROOT / ".github" / "workflows").glob("*.yml")):
        workflow = yaml.load(path.read_text(), Loader=yaml.BaseLoader)
        assert workflow.get("env", {}).get("FORCE_JAVASCRIPT_ACTIONS_TO_NODE24") == "true", path.name


def test_workflows_use_node24_native_action_versions():
    for path in sorted((ROOT / ".github" / "workflows").glob("*.yml")):
        workflow = yaml.load(path.read_text(), Loader=yaml.BaseLoader)
        for job in workflow["jobs"].values():
            for step in job.get("steps", []):
                uses = step.get("uses", "")
                action, separator, version = uses.partition("@")
                if action in NODE24_ACTION_VERSIONS:
                    assert separator == "@", uses
                    assert version == NODE24_ACTION_VERSIONS[action], uses


def test_export_openapi_script_writes_artifact(tmp_path):
    from scripts import export_openapi

    output = export_openapi.export_openapi(tmp_path / "nested" / "openapi.json")

    data = json.loads(output.read_text())
    assert data["info"]["title"] == "aiograpi-rest"
    assert data["info"]["version"] == project_version()


def test_export_openapi_main_writes_artifact(tmp_path):
    from scripts import export_openapi

    output = tmp_path / "openapi.json"
    export_openapi.main([str(output)])

    assert json.loads(output.read_text())["info"]["version"] == project_version()


def test_export_openapi_script_requires_output_argument():
    from scripts import export_openapi

    with pytest.raises(SystemExit, match="Usage: export_openapi.py OUTPUT"):
        export_openapi.main([])


def test_app_manifest_uses_aiograpi_rest_identity():
    manifest = json.loads((ROOT / "app.json").read_text())
    assert manifest["name"] == "aiograpi-rest"
    assert manifest["repository"] == "https://github.com/subzeroid/aiograpi-rest"
    assert "aiograpi-rest" in manifest["keywords"]


def test_readme_documents_rename_reason():
    readme = (ROOT / "README.md").read_text()
    assert readme.startswith("# aiograpi-rest")
    assert "Renamed from `instagrapi-rest` to `aiograpi-rest` in v1.0.0" in readme
    assert "`aiograpi-rest` starts its own semver line at `1.0.0`" in readme
    assert "the service is now powered by `aiograpi`" in readme
    assert "docker run --rm -p 8000:8000 subzeroid/aiograpi-rest" in readme
    assert "docker run -p 8000:8000 ghcr.io/subzeroid/aiograpi-rest" in readme
    assert "PyPI and GitHub Release artifacts are published from the same tag workflow" in readme


def test_quickstart_documents_real_session_flow():
    readme = (ROOT / "README.md").read_text()
    getting_started = (ROOT / "docs" / "getting-started.md").read_text()
    for document in (readme, getting_started):
        assert "docker run --rm -p 8000:8000 subzeroid/aiograpi-rest" in document
        assert "SESSIONID=$(curl -fsS -X POST http://localhost:8000/auth/login" in document
        assert "POST /auth/login/by/sessionid" in document
        assert "Authorize" in document
        assert 'curl "http://localhost:8000/user/about?user_id=25025320"' in document
        assert '-H "X-Session-ID: $SESSIONID"' in document


def test_github_docs_are_configured():
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text())
    assert "mkdocs-material>=9.6,<10" in pyproject["project"]["optional-dependencies"]["docs"]

    mkdocs = yaml.safe_load((ROOT / "mkdocs.yml").read_text())
    assert mkdocs["site_name"] == "aiograpi-rest Documentation"
    assert mkdocs["repo_name"] == "subzeroid/aiograpi-rest"
    assert "aiograpi-coverage.md" in str(mkdocs["nav"])

    docs_workflow = (ROOT / ".github" / "workflows" / "docs.yml").read_text()
    assert "python scripts/generate_aiograpi_coverage.py --check" in docs_workflow
    assert "mkdocs build --strict" in docs_workflow
    assert "mkdocs gh-deploy --force" in docs_workflow
