#!/usr/bin/env python3
"""CI and `task dev:smoke` run the same smoke script against a tagged image."""

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "tasks" / "smoke.sh"


def _read(relative):
    return (ROOT / relative).read_text(encoding="utf-8")


class TestSmokeScript:
    def test_exists_and_is_executable(self):
        assert SCRIPT.is_file()
        assert SCRIPT.stat().st_mode & 0o111

    def test_parses_as_posix_shell(self):
        subprocess.run(["sh", "-n", str(SCRIPT)], check=True)

    def test_polls_with_a_cap_and_no_fixed_sleep(self):
        text = SCRIPT.read_text(encoding="utf-8")
        assert "sleep" not in text
        assert "--retry" in text
        assert "--max-time" in text

    def test_checks_health_feed_and_dropped_user(self):
        text = SCRIPT.read_text(encoding="utf-8")
        assert "/healthz" in text
        assert "/smoke.xml" in text
        assert "stat -c %u" in text

    def test_serves_a_real_audio_fixture_and_checks_its_duration(self):
        text = SCRIPT.read_text(encoding="utf-8")
        assert "tests/fixtures/audio/cbr.mp3" in text
        assert (ROOT / "tests" / "fixtures" / "audio" / "cbr.mp3").is_file()
        assert "<itunes:duration>0:01</itunes:duration>" in text

    def test_removes_its_containers_on_exit(self):
        text = SCRIPT.read_text(encoding="utf-8")
        assert "trap" in text
        assert "docker rm -f" in text
        assert 'stop "$NAME"' in text
        assert 'stop "$INDEX_NAME"' in text

    def test_checks_the_index_is_404_by_default_and_served_when_enabled(self):
        text = SCRIPT.read_text(encoding="utf-8")
        assert '[ "$code" = "404" ]' in text
        assert "-e PUBLISH_INDEX=true" in text
        assert '/smoke.xml" "$WORK/index.html"' in text

    def test_takes_image_from_argument(self):
        text = SCRIPT.read_text(encoding="utf-8")
        assert "podcastify-podcastify" not in text
        assert '"$1"' in text


class TestCallers:
    def test_ci_smokes_the_image_it_just_built(self):
        text = _read(".github/workflows/ci.yml")
        assert "tasks/smoke.sh local/podcastify:${{ github.sha }}" in text

    def test_ci_smoke_runs_before_the_scan(self):
        text = _read(".github/workflows/ci.yml")
        assert text.index("tasks/smoke.sh") < text.index("Trivy scan")

    def test_local_task_builds_an_explicit_tag_and_uses_the_script(self):
        text = _read("tasks/dev.yml")
        assert "docker build -t podcastify:smoke -f docker/podcastify/Dockerfile ." in text
        assert "tasks/smoke.sh podcastify:smoke" in text
        assert "podcastify-podcastify" not in text
        assert "sleep" not in text
