#!/usr/bin/env python3
"""The env contract (ADR 0002 and 0004) agrees across compose, .env.example and docs."""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
PATH_VARS = ("PODCASTS_ROOT", "PUBLIC_ROOT", "CACHE_ROOT")


def _read(relative):
    return (ROOT / relative).read_text(encoding="utf-8")


def _adr_variables():
    return set(re.findall(r"^\| `([A-Z_]+)` \|", _read("docs/adr/0002-env-var-contract.md"), re.M))


def _compose_variables():
    return set(re.findall(r"^\s+- ([A-Z_]+)(?:=|$)", _read("docker-compose.yml"), re.M))


def _env_example_variables():
    return set(re.findall(r"^([A-Z_]+)=", _read(".env.example"), re.M))


def _deployment_variables():
    return set(re.findall(r"^\| `([A-Z_]+)` \|", _read("docs/deployment.md"), re.M))


class TestPathVariablesAreInternal:
    @pytest.mark.parametrize("relative", ["docker-compose.yml", ".env.example", "docs/deployment.md", "README.md"])
    def test_not_offered_as_settings(self, relative):
        text = _read(relative)
        for name in PATH_VARS:
            assert name not in text, f"{name} still mentioned in {relative}"

    def test_not_in_adr_0002_table(self):
        assert not set(PATH_VARS) & _adr_variables()

    def test_dockerfile_keeps_the_defaults(self):
        text = _read("docker/podcastify/Dockerfile")
        for default in ("PODCASTS_ROOT=/app/podcasts", "PUBLIC_ROOT=/app/public", "CACHE_ROOT=/app/.cache"):
            assert default in text

    def test_adr_0004_records_the_decision(self):
        text = _read("docs/adr/0004-path-env-vars-are-internal.md")
        assert "Accepted" in text
        for name in PATH_VARS:
            assert name in text


class TestComposeCarriesNoDuplicatedDefaults:
    @pytest.mark.parametrize(
        "name", ["SERVICE_PORT", "RUN_ON_START", "GENERATE_INTERVAL", "PUBLISH_XML", "LOG_LEVEL", "PUID", "PGID"]
    )
    def test_user_setting_is_a_bare_pass_through(self, name):
        assert re.search(rf"^\s+- {name}$", _read("docker-compose.yml"), re.M)

    def test_public_base_url_keeps_its_host_port_default(self):
        assert "PUBLIC_BASE_URL=${PUBLIC_BASE_URL:-http://localhost:${HOST_PORT:-8080}}" in _read("docker-compose.yml")

    def test_volumes_have_no_redundant_rw_suffix(self):
        assert ":rw" not in _read("docker-compose.yml")


class TestProxyDocsShowLocalhostBinding:
    @pytest.mark.parametrize("relative", ["docs/deployment.md", "README.md"])
    def test_binding_is_shown(self, relative):
        assert '"127.0.0.1:${HOST_PORT:-8080}:${SERVICE_PORT:-8080}"' in _read(relative)


class TestSurfacesAgree:
    def test_compose_variables_are_in_adr_0002(self):
        assert _compose_variables() <= _adr_variables()

    def test_env_example_variables_are_in_adr_0002(self):
        assert _env_example_variables() <= _adr_variables()

    def test_deployment_variables_are_in_adr_0002(self):
        assert _deployment_variables() <= _adr_variables()
