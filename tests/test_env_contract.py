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
    return set(re.findall(r"^\s+- ([A-Z_]+)=", _read("docker-compose.yml"), re.M))


def _env_example_variables():
    return set(re.findall(r"^([A-Z_]+)=", _read(".env.example"), re.M))


def _deployment_variables():
    return set(re.findall(r"^\| `([A-Z_]+)` \|", _read("docs/deployment.md"), re.M))


class TestPathVariablesAreInternal:
    @pytest.mark.parametrize(
        "relative", ["docker-compose.yml", ".env.example", "docs/deployment.md", "README.md"]
    )
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


class TestSurfacesAgree:
    def test_compose_variables_are_in_adr_0002(self):
        assert _compose_variables() <= _adr_variables()

    def test_env_example_variables_are_in_adr_0002(self):
        assert _env_example_variables() <= _adr_variables()

    def test_deployment_variables_are_in_adr_0002(self):
        assert _deployment_variables() <= _adr_variables()
