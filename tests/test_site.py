#!/usr/bin/env python3
"""The public site: explicit navigation, nothing internal published, shared snippets that cannot drift."""

import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
WEBSITE = ROOT / "website"
PAGES = [
    "index.md",
    "getting-started.md",
    "deployment.md",
    "configuration.md",
    "how-it-works.md",
    "troubleshooting.md",
]
INTERNAL = ["adr", "agents", "audit", "architecture-notes.md", "architecture.md", "runtime.md", "contributing.md"]
SITE_URL = "https://fnayou.github.io/podcastify/"


def _config():
    return yaml.safe_load((ROOT / "mkdocs.yml").read_text(encoding="utf-8"))


def _read(path):
    return Path(path).read_text(encoding="utf-8")


def _docker_run(text):
    blocks = re.findall(r"```bash\n(docker run.*?)```", text, re.S)
    assert len(blocks) == 1
    return blocks[0]


class TestNavigation:
    def test_docs_dir_is_the_website_folder(self):
        assert _config()["docs_dir"] == "website"

    def test_navigation_lists_the_six_pages_in_order(self):
        nav = _config()["nav"]
        assert [next(iter(item.values())) for item in nav] == PAGES

    def test_every_page_exists(self):
        assert all((WEBSITE / page).is_file() for page in PAGES)

    def test_no_page_outside_the_navigation(self):
        found = sorted(p.name for p in WEBSITE.glob("*.md"))
        assert found == sorted(PAGES)

    def test_site_url_is_the_pages_address(self):
        assert _config()["site_url"] == SITE_URL

    @pytest.mark.parametrize("name", INTERNAL)
    def test_internal_material_is_not_in_the_website(self, name):
        assert not (WEBSITE / name).exists()
        assert (ROOT / "docs" / name).exists()


class TestLinks:
    @pytest.mark.parametrize("page", PAGES)
    def test_relative_links_point_at_published_pages(self, page):
        text = _read(WEBSITE / page)
        for target in re.findall(r"\]\((?!https?://|#)([^)#]+\.md)(?:#[^)]*)?\)", text):
            assert (WEBSITE / target).is_file(), f"{page} links to {target}"

    @pytest.mark.parametrize("page", PAGES)
    def test_relative_anchors_exist(self, page):
        text = _read(WEBSITE / page)
        for target, anchor in re.findall(r"\]\((?!https?://)([^)#]*\.md)#([^)]+)\)", text):
            headings = re.findall(r"^#+ (.+)$", _read(WEBSITE / target), re.M)
            slugs = {re.sub(r"[^\w\- ]", "", h.lower()).strip().replace(" ", "-") for h in headings}
            assert anchor in slugs, f"{page} links to {target}#{anchor}"

    def test_readme_links_to_the_site_with_absolute_urls(self):
        text = _read(ROOT / "README.md")
        assert not re.findall(r"\]\((?!https?://|#)[^)]+\)", text)
        for page in ("getting-started", "deployment", "configuration", "how-it-works", "troubleshooting"):
            assert f"]({SITE_URL}{page}/)" in text


class TestSharedContent:
    def test_the_docker_snippet_is_the_same_on_home_and_getting_started(self):
        assert _docker_run(_read(WEBSITE / "index.md")) == _docker_run(_read(WEBSITE / "getting-started.md"))

    def test_the_readme_snippet_is_the_same_too(self):
        assert _docker_run(_read(ROOT / "README.md")) == _docker_run(_read(WEBSITE / "getting-started.md"))

    def test_the_example_feed_is_the_generated_golden_feed(self):
        text = _read(WEBSITE / "index.md")
        block = re.search(r"```xml\n(.*?)\n    ```", text, re.S)
        assert block
        shown = "\n".join(line[4:] for line in block.group(1).splitlines())
        assert shown.strip() == _read(ROOT / "tests" / "golden" / "basic.xml").strip()

    def test_the_example_is_labelled_and_not_a_live_sample(self):
        text = _read(WEBSITE / "index.md")
        assert "not a live sample" in text

    @pytest.mark.parametrize("page", ["index.md", "getting-started.md", "deployment.md"])
    def test_the_main_tracking_notice_is_beside_the_commands(self, page):
        text = _read(WEBSITE / page)
        assert "This site tracks `main`" in text
        assert "https://github.com/fnayou/podcastify/releases" in text
