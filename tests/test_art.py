#!/usr/bin/env python3
"""Tests for the generated brand art: freshness of the committed SVGs, determinism and the command line."""

import re
import shutil
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from tools.art.cli import IMAGES, ArtCli
from tools.art.facts import Facts, FactsError, FactsReader
from tools.art.render import Renderer

ROOT = Path(__file__).resolve().parent.parent
SVG_NS = "{http://www.w3.org/2000/svg}"
COPIED = ("podcastify", "AGENTS.md", ".env.example", ".github/workflows/release.yml", "docker/podcastify/Dockerfile")
VIEW_BOXES = {
    "podcastify-logo": "0 0 512 512",
    "favicon": "0 0 64 64",
    "podcastify-readme-banner": "0 0 1280 400",
    "podcastify-social-preview": "0 0 1280 640",
}


@pytest.fixture(scope="module")
def facts() -> Facts:
    return FactsReader(ROOT).read()


@pytest.fixture
def repo(tmp_path):
    for item in COPIED:
        source = ROOT / item
        target = tmp_path / item
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            shutil.copytree(source, target, ignore=shutil.ignore_patterns("__pycache__"))
        else:
            shutil.copy(source, target)
    return tmp_path


def _cli(root):
    lines, errors = [], []
    return ArtCli(root, out=lines.append, err=errors.append), lines, errors


COMMITTED = [o for o in ArtCli.OUTPUTS if o.committed]


class TestCommittedImages:
    @pytest.mark.parametrize("output", COMMITTED, ids=lambda o: o.name)
    def test_committed_svg_is_current(self, output, facts):
        path = ROOT / IMAGES / f"{output.base}.svg"
        assert path.is_file(), f"{path} is missing; run `task art:build`"
        assert path.read_text(encoding="utf-8") == output.make(facts), f"{path.name} is stale; run `task art:build`"

    def test_check_command_passes_on_the_repository(self):
        cli, _, errors = _cli(ROOT)
        assert cli.check() == 0
        assert errors == []

    def test_every_png_has_an_svg_with_the_same_base_name(self):
        images = ROOT / IMAGES
        assert all(png.with_suffix(".svg").exists() for png in images.glob("*.png"))

    @pytest.mark.parametrize("output", ArtCli.OUTPUTS, ids=lambda o: o.name)
    def test_svg_is_well_formed_with_the_expected_view_box(self, output, facts):
        root = ET.fromstring(output.make(facts))
        assert root.tag == f"{SVG_NS}svg"
        width, height = root.get("width"), root.get("height")
        assert width and height
        assert root.get("viewBox") == VIEW_BOXES.get(output.base, f"0 0 {width} {height}")

    @pytest.mark.parametrize("output", ArtCli.OUTPUTS, ids=lambda o: o.name)
    def test_output_is_deterministic(self, output, facts):
        assert output.make(facts) == output.make(FactsReader(ROOT).read())

    @pytest.mark.parametrize("output", ArtCli.OUTPUTS, ids=lambda o: o.name)
    def test_output_uses_no_external_resource_and_no_build_identity(self, output, facts):
        markup = output.make(facts)
        assert re.findall(r'\b(?:href|src|xlink:href)="[^"]*"', markup) == []
        assert re.findall(r'xmlns(?::\w+)?="[^"]*"', markup) == ['xmlns="http://www.w3.org/2000/svg"']
        assert "url(http" not in markup and "@import" not in markup
        assert not re.search(r"\b[0-9a-f]{40}\b", markup)
        assert not re.search(r"\b20\d\d-\d\d-\d\d\b", markup)

    def test_only_palette_colours_are_used(self, facts):
        from tools.art.palette import C

        allowed = set(C.values())
        for output in ArtCli.OUTPUTS:
            used = set(re.findall(r"#[0-9a-fA-F]{6}\b", output.make(facts)))
            assert used <= allowed, f"{output.name}: {sorted(used - allowed)}"

    def test_the_accent_is_blue(self, facts):
        for output in ArtCli.OUTPUTS:
            assert "#8aadf4" in output.make(facts)


class TestFacts:
    def test_modules_cover_every_module_of_the_package(self, facts):
        expected = sorted(p.stem for p in (ROOT / "podcastify").glob("*.py") if p.name != "__init__.py")
        assert [m.name for m in facts.modules] == expected

    def test_roles_come_from_the_architecture_table(self, facts):
        roles = {m.name: m.role for m in facts.modules}
        assert roles["rss"] == "iTunes RSS XML"
        classes = {m.name: m.classes for m in facts.modules}
        assert {"ConfigurationManager", "EpisodeManager"} <= set(classes["parser"])

    def test_media_types_are_read_from_config(self, facts):
        from podcastify.config import Config

        assert facts.media_types == tuple(sorted(Config.MEDIA_TYPES))

    def test_settings_come_from_env_example_without_the_host_port(self, facts):
        keys = [k for k, _ in facts.settings]
        assert keys == sorted(keys)
        assert "PUBLISH_INDEX" in keys and "PUID" in keys
        assert "HOST_PORT" not in keys

    def test_container_facts_come_from_the_dockerfile(self, facts):
        assert facts.port == 8080
        assert facts.base_image.startswith("python:")
        assert facts.caddy_image.startswith("caddy:")
        assert facts.public_root == "/app/public" and facts.podcasts_root == "/app/podcasts"
        assert facts.entrypoint[-1] == "/entrypoint.sh"

    def test_image_and_pitch_come_from_the_release_workflow(self, facts):
        assert facts.image == "fnayou/podcastify" and facts.name == "podcastify"
        assert facts.pitch.startswith("Tiny self-hosted podcast RSS generator")

    def test_pitch_is_split_after_the_colon(self, facts):
        assert facts.pitch_lines == (
            "Tiny self-hosted podcast RSS generator",
            "Private feeds from your own audio files.",
        )

    def test_run_hint_uses_the_container_paths(self, facts):
        assert facts.run_hint[0] == "docker run -d -p 8080:8080 \\"
        assert "-v ./public:/app/public" in facts.run_hint[2]
        assert facts.run_hint[-1].strip() == "fnayou/podcastify"

    def test_pitch_without_a_colon_stays_one_line(self, facts):
        assert Facts.__dict__["pitch_lines"].fget(_with(facts, pitch="Just one sentence.")) == ("Just one sentence.",)

    def test_missing_file_is_reported(self, tmp_path):
        with pytest.raises(FactsError, match="release.yml not found"):
            FactsReader(tmp_path).read()

    def test_missing_pattern_is_reported(self, repo):
        release = repo / ".github/workflows/release.yml"
        release.write_text("env:\n", encoding="utf-8")
        with pytest.raises(FactsError, match="IMAGE_NAME"):
            FactsReader(repo).read()

    def test_missing_media_types_are_reported(self, repo):
        (repo / "podcastify/config.py").write_text("class Config:\n    pass\n", encoding="utf-8")
        with pytest.raises(FactsError, match="MEDIA_TYPES not found"):
            FactsReader(repo).read()

    def test_a_package_with_one_module_is_read(self, repo):
        for module in (repo / "podcastify").glob("*.py"):
            if module.name not in ("__init__.py", "config.py"):
                module.unlink()
        facts = FactsReader(repo).read()
        assert [m.name for m in facts.modules] == ["config"]

    def test_role_falls_back_to_the_module_docstring(self, repo):
        (repo / "podcastify/extra.py").write_text(
            '"""Does extra things."""\n\nclass Extra:\n    pass\n', encoding="utf-8"
        )
        modules = {m.name: m for m in FactsReader(repo).read().modules}
        assert modules["extra"].role == "Does extra things."
        assert modules["extra"].classes == ("Extra",)

    def test_role_is_empty_without_a_table_row_or_docstring(self, repo):
        (repo / "podcastify/bare.py").write_text("X = 1\n", encoding="utf-8")
        assert {m.name: m.role for m in FactsReader(repo).read().modules}["bare"] == ""


def _with(facts: Facts, **changes) -> Facts:
    from dataclasses import replace

    return replace(facts, **changes)


class TestBuild:
    def test_build_writes_every_svg(self, repo):
        cli, lines, _ = _cli(repo)
        assert cli.run(["build", "--no-png"]) == 0
        written = sorted(p.name for p in (repo / IMAGES).glob("*.svg"))
        assert written == sorted(f"{o.base}.svg" for o in ArtCli.OUTPUTS)
        assert all(line.startswith("wrote ") for line in lines)

    def test_build_output_equals_the_committed_files(self, repo):
        _cli(repo)[0].run(["build", "--no-png"])
        for output in ArtCli.OUTPUTS:
            built = (repo / IMAGES / f"{output.base}.svg").read_text(encoding="utf-8")
            assert built == (ROOT / IMAGES / f"{output.base}.svg").read_text(encoding="utf-8")

    def test_only_builds_the_named_images(self, repo):
        _cli(repo)[0].run(["build", "--only", "banner,favicon", "--no-png"])
        assert sorted(p.name for p in (repo / IMAGES).glob("*")) == ["favicon.svg", "podcastify-readme-banner.svg"]

    def test_logo_command_builds_the_logo_and_the_favicon(self, repo):
        cli, lines, _ = _cli(repo)
        assert cli.run(["logo"]) == 0
        assert [line.split()[1] for line in lines] == ["podcastify-logo.svg", "favicon.svg"]

    def test_png_is_skipped_with_a_message_without_rsvg(self, repo, monkeypatch):
        monkeypatch.setenv("PATH", str(repo))
        cli, lines, _ = _cli(repo)
        assert cli.run(["build", "--only", "logo"]) == 0
        assert lines == [f"wrote podcastify-logo.svg  ({Renderer.SKIPPED})"]
        assert not list((repo / IMAGES).glob("*.png"))

    def test_unknown_image_is_an_error(self, repo):
        cli, _, errors = _cli(repo)
        assert cli.run(["build", "--only", "nope"]) == 1
        assert "unknown image 'nope'" in errors[0]

    def test_unknown_option_is_an_error(self, repo):
        cli, _, errors = _cli(repo)
        assert cli.run(["build", "--fast"]) == 1
        assert "unknown option '--fast'" in errors[0]

    def test_unknown_command_and_missing_command(self, repo):
        cli, _, errors = _cli(repo)
        assert cli.run(["dance"]) == 2
        assert cli.run([]) == 2
        assert "unknown command 'dance'" in errors[0]
        assert errors[1].startswith("usage:")

    def test_missing_source_file_is_a_clear_error(self, tmp_path):
        cli, _, errors = _cli(tmp_path)
        assert cli.run(["build"]) == 1
        assert "release.yml not found" in errors[0]


class TestCheck:
    def test_stale_and_missing_svgs_are_reported(self, repo):
        cli, _, errors = _cli(repo)
        cli.run(["build", "--no-png"])
        (repo / IMAGES / "podcastify-logo.svg").write_text("changed", encoding="utf-8")
        (repo / IMAGES / "favicon.svg").unlink()
        assert cli.run(["check"]) == 1
        assert "stale: website/assets/images/podcastify-logo.svg" in errors
        assert "stale: website/assets/images/favicon.svg" in errors
        assert errors[-1] == "Regenerate with: task art:build"

    def test_check_is_read_only(self, repo):
        cli, _, _ = _cli(repo)
        cli.run(["check"])
        assert not (repo / IMAGES).exists()

    def test_a_changed_source_fact_makes_the_banner_stale(self, repo):
        cli, _, errors = _cli(repo)
        cli.run(["build", "--no-png"])
        release = repo / ".github/workflows/release.yml"
        release.write_text(release.read_text(encoding="utf-8").replace("Tiny", "Small"), encoding="utf-8")
        assert cli.run(["check"]) == 1
        assert "stale: website/assets/images/podcastify-readme-banner.svg" in errors


class TestRemind:
    def _stale_repo(self, repo, monkeypatch, files):
        cli, lines, errors = _cli(repo)
        monkeypatch.setattr(cli, "_changed_files", lambda args: files)
        return cli, lines, errors

    def test_silent_when_no_art_input_changed(self, repo, monkeypatch):
        cli, lines, _ = self._stale_repo(repo, monkeypatch, ["docs/contributing.md"])
        assert cli.run(["remind"]) == 0
        assert lines == []

    def test_silent_when_the_svgs_are_current(self, repo, monkeypatch):
        cli, lines, _ = self._stale_repo(repo, monkeypatch, ["podcastify/media.py"])
        cli.run(["build", "--no-png"])
        lines.clear()
        assert cli.run(["remind"]) == 0
        assert lines == []

    def test_prints_the_fix_when_an_input_changed_and_an_svg_is_stale(self, repo, monkeypatch):
        cli, lines, _ = self._stale_repo(repo, monkeypatch, ["podcastify/media.py"])
        assert cli.run(["remind"]) == 0
        assert lines[0].startswith("MANUAL STEP: the generated art is out of date (")
        assert "  task art:build" in lines
        assert "  git add website/assets/images" in lines

    def test_never_fails(self, repo, monkeypatch):
        cli, lines, _ = _cli(repo)

        def boom(args):
            raise RuntimeError("no git")

        monkeypatch.setattr(cli, "_changed_files", boom)
        assert cli.run(["remind"]) == 0
        assert lines == []

    def test_bad_usage_is_silent(self, repo):
        cli, lines, errors = _cli(repo)
        assert cli.run(["remind", "--bogus"]) == 0
        assert lines == [] and errors == []

    def test_changed_files_reads_git(self, monkeypatch):
        calls = []

        class Result:
            stdout = "a.py\n\nb.py\n"

        def fake_run(command, **kwargs):
            calls.append(command)
            return Result()

        monkeypatch.setattr("tools.art.cli.subprocess.run", fake_run)
        cli, _, _ = _cli(ROOT)
        assert cli._changed_files(["--staged"]) == ["a.py", "b.py"]
        cli._changed_files(["--working"])
        cli._changed_files(["--range", "a..b"])
        cli._changed_files(["--range", "a...b"])
        assert calls == [
            ["git", "diff", "--cached", "--name-only"],
            ["git", "diff", "HEAD", "--name-only"],
            ["git", "diff", "--name-only", "a...b"],
            ["git", "diff", "--name-only", "a...b"],
        ]


def _architecture(facts) -> str:
    return next(o for o in ArtCli.OUTPUTS if o.name == "architecture").make(facts)


class TestArchitecture:
    def test_mentions_every_module_of_the_package(self, facts):
        svg = _architecture(facts)
        for path in (ROOT / "podcastify").glob("*.py"):
            if path.name != "__init__.py":
                assert f"{path.stem}.py" in svg, path.name

    def test_shows_the_pipeline_the_container_and_the_settings(self, facts):
        svg = _architecture(facts)
        for expected in (
            "sources",
            "feeds",
            "caddy",
            "tini",
            "entrypoint.sh",
            ":8080",
            facts.base_image,
            facts.caddy_image,
        ):
            assert expected in svg, expected
        for key, _ in facts.settings:
            assert key in svg, key
        for media_type in facts.media_types:
            assert media_type in svg

    def test_shows_the_roles_from_the_architecture_table(self, facts):
        svg = _architecture(facts)
        assert "iTunes RSS XML" in svg and "tinytag duration," in svg

    def test_is_well_formed_and_taller_than_wide_enough_to_hold_three_bands(self, facts):
        root = ET.fromstring(_architecture(facts))
        assert root.get("width") == "1920" and int(root.get("height")) > 900

    def test_a_new_module_shows_up_without_a_code_change(self, repo):
        (repo / "podcastify/zeta.py").write_text('"""Zeta things."""\n\nclass Zeta:\n    pass\n', encoding="utf-8")
        svg = _architecture(FactsReader(repo).read())
        assert "zeta.py" in svg and "Zeta things." in svg

    def test_without_support_modules_the_support_row_is_absent(self, facts):
        chain_only = tuple(m for m in facts.modules if m.name in ("parser", "media", "rss", "cli"))
        svg = _architecture(_with(facts, modules=chain_only))
        assert "SUPPORT" not in svg and "config.py" not in svg

    def test_a_missing_stage_module_is_left_out(self, facts):
        without_media = tuple(m for m in facts.modules if m.name != "media")
        svg = _architecture(_with(facts, modules=without_media))
        assert "media.py" not in svg and "parser.py" in svg

    def test_is_git_ignored(self):
        lines = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
        assert "website/assets/images/podcastify-architecture.svg" in lines

    def test_is_not_committed_and_not_checked(self, repo):
        assert _tracked("podcastify-architecture.svg") is False
        cli, _, errors = _cli(repo)
        cli.run(["build", "--only", "architecture", "--no-png"])
        assert cli.check() == 1
        assert all("architecture" not in e for e in errors)

    def test_never_gets_a_png(self, repo, monkeypatch):
        fake = repo / "bin"
        fake.mkdir()
        exe = fake / "rsvg-convert"
        exe.write_text('#!/bin/sh\necho png > "$5"\n', encoding="utf-8")
        exe.chmod(0o755)
        monkeypatch.setenv("PATH", str(fake))
        cli, lines, _ = _cli(repo)
        cli.run(["build", "--only", "architecture,logo"])
        assert (repo / IMAGES / "podcastify-logo.png").exists()
        assert not (repo / IMAGES / "podcastify-architecture.png").exists()
        assert lines == ["wrote podcastify-architecture.svg", "wrote podcastify-logo.svg + podcastify-logo.png"]


def _tracked(name: str) -> bool:
    try:
        result = subprocess.run(
            ["git", "ls-files", "--error-unmatch", f"{IMAGES}/{name}"], cwd=ROOT, capture_output=True, text=True
        )
    except FileNotFoundError:
        pytest.skip("git is not installed")
    return result.returncode == 0


class TestWiring:
    def test_taskfile_includes_the_art_tasks(self):
        assert "taskfile: ./tasks/art.yml" in (ROOT / "Taskfile.yml").read_text(encoding="utf-8")
        tasks = (ROOT / "tasks" / "art.yml").read_text(encoding="utf-8")
        for name in ("build", "logo", "check", "remind"):
            assert re.search(rf"^  {name}:$", tasks, re.MULTILINE)

    def test_readme_shows_the_banner_with_an_absolute_url(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        url = "https://raw.githubusercontent.com/fnayou/podcastify/main/website/assets/images/podcastify-readme-banner.svg"
        assert f"]({url})" in readme
        assert (ROOT / IMAGES / "podcastify-readme-banner.svg").is_file()


class TestEntryPoint:
    def test_main_runs_the_command(self, monkeypatch, capsys):
        from tools.art import cli

        monkeypatch.setattr(cli, "ROOT", ROOT)
        assert cli.main(["check"]) == 0
        assert cli.main(["dance"]) == 2
        assert "unknown command" in capsys.readouterr().err

    def test_module_entry_point(self, monkeypatch):
        import runpy

        monkeypatch.setattr("sys.argv", ["tools.art", "check"])
        with pytest.raises(SystemExit) as exit_info:
            runpy.run_module("tools.art", run_name="__main__")
        assert exit_info.value.code == 0
