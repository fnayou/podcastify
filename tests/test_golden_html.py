from pathlib import Path

import pytest

from podcastify.cli import PodcastProcessor

GOLDEN = Path(__file__).parent / "golden" / "index.html"

CONFIGS = {
    "basic": """
title: Basic Show
description: A basic show
image: cover.jpg
episodes:
  - file: episode1.mp3
  - file: episode2.mp3
""",
    "fish-chips": """
title: "Fish & Chips <script>alert(1)</script>"
description: Hostile title
episodes:
  - file: one.mp3
""",
    "hidden": """
title: Hidden Show
description: Not on the page
listed: false
episodes:
  - file: one.mp3
""",
}


@pytest.mark.usefixtures("frozen_clock", "fixed_duration")
class TestGoldenHTML:
    def _generate(self, golden_roots, monkeypatch):
        podcasts, public = golden_roots
        monkeypatch.setattr("podcastify.config.Config.PUBLISH_INDEX", True)
        for name, config in CONFIGS.items():
            media = public / name
            media.mkdir()
            for episode in ("episode1.mp3", "episode2.mp3", "one.mp3"):
                (media / episode).write_bytes(b"\x00" * 1000)
            (podcasts / f"{name}-podcast.yaml").write_text(config, encoding="utf-8")
        (public / "basic" / "cover.jpg").write_bytes(b"\xff")
        assert PodcastProcessor().process_all_podcasts() == 0
        return (public / "index.html").read_text(encoding="utf-8")

    def test_output_matches_snapshot(self, golden_roots, monkeypatch):
        assert self._generate(golden_roots, monkeypatch) == GOLDEN.read_text(encoding="utf-8")

    def test_snapshot_uses_the_frozen_feed_build_date(self, golden_roots, monkeypatch):
        html = self._generate(golden_roots, monkeypatch)
        assert '<time datetime="2030-01-02T03:04:05+00:00">2030-01-02</time>' in html
