#!/usr/bin/env python3
"""The configuration reference is generated from the models and the committed page is current."""

import runpy
import sys
from pathlib import Path

import pytest

from podcastify.parser import EpisodeManager, EpisodeModel, PodcastChannelModel, validate_podcast_config
from tools.config_reference import ConfigReference, MarkersError, main

ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / "docs" / "configuration.md"
BEGIN = ConfigReference.BEGIN
END = ConfigReference.END


def _rows(table):
    rows = {}
    for line in table.splitlines()[2:]:
        cells = [cell.strip() for cell in line.strip().strip("|").split(" | ")]
        rows[cells[0].strip("`")] = cells
    return rows


@pytest.fixture
def reference():
    return ConfigReference(PAGE)


@pytest.fixture
def page(tmp_path):
    target = tmp_path / "page.md"
    target.write_text(f"intro\n\n{BEGIN}\n\nold\n\n{END}\n\noutro\n", encoding="utf-8")
    return target


class TestCommittedPage:
    def test_region_equals_the_generated_text(self, reference):
        assert reference.is_current(), "docs/configuration.md is stale; run `task docs:reference`"

    def test_markers_appear_exactly_once(self):
        text = PAGE.read_text(encoding="utf-8")
        assert text.count(BEGIN) == 1
        assert text.count(END) == 1
        assert text.index(BEGIN) < text.index(END)

    def test_hand_written_field_tables_are_gone(self):
        text = PAGE.read_text(encoding="utf-8")
        outside = text[: text.index(BEGIN)] + text[text.index(END) :]
        assert "| Field | Type | Required |" not in outside

    def test_headings_keep_their_anchors(self):
        text = PAGE.read_text(encoding="utf-8")
        assert "### Channel Fields" in text
        assert "### Episode Fields" in text


class TestRender:
    def test_is_deterministic(self, reference):
        assert reference.render() == reference.render()

    def test_has_one_table_per_model(self, reference):
        body = reference.render()
        assert body.count("| Key | Type | Required | Default | Description |") == 2
        assert body.index("### Channel Fields") < body.index("### Episode Fields")

    @pytest.mark.parametrize("model", [PodcastChannelModel, EpisodeModel], ids=["channel", "episode"])
    def test_every_field_is_documented_in_declaration_order(self, reference, model):
        keys = list(_rows(reference.table(model)))
        expected = [field.alias or name for name, field in model.model_fields.items()]
        assert keys == expected

    def test_aliases_are_the_yaml_keys(self, reference):
        channel = _rows(reference.table(PodcastChannelModel))
        episode = _rows(reference.table(EpisodeModel))
        assert {"author-name", "author-email"} <= set(channel)
        assert "author-name" in episode
        assert not {"author_name", "author_email"} & set(channel)

    def test_required_flags_follow_the_models(self, reference):
        channel = _rows(reference.table(PodcastChannelModel))
        assert {key for key, cells in channel.items() if cells[2] == "Yes"} == {"title", "description"}
        episode = _rows(reference.table(EpisodeModel))
        assert {key for key, cells in episode.items() if cells[2] == "Yes"} == {"file"}

    def test_defaults_follow_the_models(self, reference):
        channel = _rows(reference.table(PodcastChannelModel))
        assert channel["language"][3] == "`en`"
        assert channel["explicit"][3] == "`false`"
        assert channel["listed"][3] == "`true`"
        assert channel["title"][3] == "-"
        assert channel["image"][3] == "-"

    @pytest.mark.parametrize(
        "key, type_",
        [
            ("title", "string"),
            ("explicit", "boolean"),
            ("categories", "string, list or mapping"),
            ("episodes", "list of episode"),
        ],
    )
    def test_channel_types(self, reference, key, type_):
        assert _rows(reference.table(PodcastChannelModel))[key][1] == type_

    @pytest.mark.parametrize(
        "key, type_", [("file", "string"), ("pub_date", "date-time"), ("season", "integer"), ("explicit", "boolean")]
    )
    def test_episode_types(self, reference, key, type_):
        assert _rows(reference.table(EpisodeModel))[key][1] == type_

    def test_legacy_author_is_deprecated_in_favour_of_author_name(self, reference):
        channel = _rows(reference.table(PodcastChannelModel))
        assert channel["author"][4].startswith("**Deprecated**, use `author-name`.")
        assert "Deprecated" not in channel["author-name"][4]

    def test_pipes_in_descriptions_cannot_break_the_table(self, reference, monkeypatch):
        monkeypatch.setattr(PodcastChannelModel.model_fields["title"], "description", "a | b")
        assert "a \\| b" in reference.table(PodcastChannelModel)

    def test_unsupported_type_is_an_error(self, reference):
        with pytest.raises(TypeError):
            reference.type_name(bytes)


class TestSplice:
    def test_replaces_only_the_region(self, page):
        spliced = ConfigReference(page).splice(page.read_text(encoding="utf-8"))
        assert spliced.startswith(f"intro\n\n{BEGIN}\n\n### Channel Fields")
        assert spliced.endswith(f"\n\n{END}\n\noutro\n")
        assert "old" not in spliced

    def test_is_idempotent(self, page):
        reference = ConfigReference(page)
        once = reference.splice(page.read_text(encoding="utf-8"))
        assert reference.splice(once) == once

    @pytest.mark.parametrize(
        "text",
        [
            "no markers\n",
            f"{BEGIN}\nonly begin\n",
            f"{END}\nonly end\n",
            f"{BEGIN}\n{BEGIN}\n{END}\n",
            f"{BEGIN}\n{END}\n{END}\n",
            f"{END}\n{BEGIN}\n",
        ],
        ids=["none", "no-end", "no-begin", "two-begins", "two-ends", "reversed"],
    )
    def test_bad_markers_give_a_clear_error(self, tmp_path, text):
        target = tmp_path / "page.md"
        target.write_text(text, encoding="utf-8")
        with pytest.raises(MarkersError, match="exactly once"):
            ConfigReference(target).splice(text)


class TestWrite:
    def test_rewrites_a_stale_page(self, page):
        reference = ConfigReference(page)
        assert reference.is_current() is False
        reference.write()
        assert reference.is_current() is True
        assert page.read_text(encoding="utf-8").endswith("outro\n")

    def test_leaves_a_current_page_untouched(self, page):
        reference = ConfigReference(page)
        reference.write()
        mtime = page.stat().st_mtime_ns
        reference.write()
        assert page.stat().st_mtime_ns == mtime


class TestCommand:
    def test_writes_the_region(self, page, capsys):
        assert main(["--page", str(page)]) == 0
        assert ConfigReference(page).is_current()
        assert "Updated" in capsys.readouterr().out

    def test_check_passes_on_a_current_page(self, page, capsys):
        ConfigReference(page).write()
        assert main(["--page", str(page), "--check"]) == 0
        assert capsys.readouterr().err == ""

    def test_check_fails_on_a_stale_page_with_a_diff_hint(self, page, capsys):
        before = page.read_text(encoding="utf-8")
        assert main(["--page", str(page), "--check"]) == 1
        err = capsys.readouterr().err
        assert "task docs:reference" in err
        assert "-old" in err
        assert page.read_text(encoding="utf-8") == before

    def test_page_without_markers_is_a_clear_error(self, tmp_path, capsys):
        target = tmp_path / "page.md"
        target.write_text("# Page\n", encoding="utf-8")
        assert main(["--page", str(target)]) == 2
        assert "exactly once" in capsys.readouterr().err
        assert target.read_text(encoding="utf-8") == "# Page\n"

    def test_missing_page_is_a_clear_error(self, tmp_path, capsys):
        assert main(["--page", str(tmp_path / "missing.md")]) == 2
        assert "missing.md" in capsys.readouterr().err

    def test_default_page_is_the_configuration_page(self, mocker):
        reference = mocker.patch("tools.config_reference.ConfigReference")
        reference.return_value.is_current.return_value = True
        assert main(["--check"]) == 0
        assert reference.call_args.args[0] == PAGE

    def test_runs_as_a_script(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["config_reference.py", "--check"])
        with pytest.raises(SystemExit) as exit_:
            runpy.run_path(str(ROOT / "tools" / "config_reference.py"), run_name="__main__")
        assert exit_.value.code == 0


class TestRulesTheSchemaCannotExpress:
    def test_page_explains_that_a_non_empty_episodes_list_turns_discovery_off(self):
        text = PAGE.read_text(encoding="utf-8")
        assert "A non-empty `episodes:` list turns auto-discovery off" in text

    def test_non_empty_episodes_list_turns_discovery_off(self, tmp_path, monkeypatch):
        monkeypatch.setattr("podcastify.config.Config.PUBLIC_ROOT", tmp_path)
        show = tmp_path / "show"
        show.mkdir()
        for name in ("listed.mp3", "other.mp3"):
            (show / name).write_bytes(b"\x00")
        channel, err = validate_podcast_config({"title": "T", "description": "D", "episodes": [{"file": "listed.mp3"}]})
        assert err is None
        assert [e.path.name for e in EpisodeManager.discover_episodes("show", channel)] == ["listed.mp3"]

    def test_empty_episodes_list_keeps_discovery_on(self, tmp_path, monkeypatch):
        monkeypatch.setattr("podcastify.config.Config.PUBLIC_ROOT", tmp_path)
        show = tmp_path / "show"
        show.mkdir()
        (show / "a.mp3").write_bytes(b"\x00")
        channel, err = validate_podcast_config({"title": "T", "description": "D", "episodes": []})
        assert err is None
        assert [e.path.name for e in EpisodeManager.discover_episodes("show", channel)] == ["a.mp3"]

    def test_page_explains_that_unknown_keys_warn(self):
        text = PAGE.read_text(encoding="utf-8")
        assert "a warning names it" in text
        assert "Unknown config key 'episodes[2].pubdate' ignored; check its spelling" in text

    def test_unknown_key_warns_with_the_documented_message(self, caplog):
        validate_podcast_config(
            {"title": "T", "description": "D", "episodes": [{"file": "a.mp3"}, {"file": "b.mp3", "pubdate": "x"}]}
        )
        assert "Unknown config key 'episodes[2].pubdate' ignored; check its spelling" in caplog.messages
