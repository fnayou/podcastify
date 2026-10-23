#!/usr/bin/env python3
"""Tests for Pydantic config validation."""

from datetime import datetime, timedelta, timezone

import pytest
import yaml

from podcastify.parser import validate_podcast_config

UTC = timezone.utc


def _pub_date(raw):
    model, err = validate_podcast_config(
        {"title": "T", "description": "D", "episodes": [{"file": "a.mp3", "pub_date": raw}]}
    )
    assert err is None
    return model.episodes[0].pub_date


def _validate_episodes(episodes):
    return validate_podcast_config({"title": "T", "description": "D", "episodes": episodes})


class TestEpisodeFile:
    @pytest.mark.parametrize("name", ["", ".", "..", "a/..", "../", "/"])
    def test_rejects_non_filenames(self, name):
        model, err = _validate_episodes([{"file": name}])
        assert model is None
        assert "file" in err

    @pytest.mark.parametrize("name", ["ep.mp3", "/some/path/ep.mp3", "Q&A #1.mp3"])
    def test_accepts_plain_filenames(self, name):
        model, err = _validate_episodes([{"file": name}])
        assert err is None
        assert model.episodes[0].file == name


class TestDuplicateEpisodes:
    def test_duplicate_file_names_both_entries(self):
        model, err = _validate_episodes([{"file": "a.mp3"}, {"file": "b.mp3"}, {"file": "a.mp3"}])
        assert model is None
        assert "duplicate episode file 'a.mp3'" in err
        assert "episodes 1 and 3" in err

    def test_duplicate_file_with_different_directories(self):
        model, err = _validate_episodes([{"file": "x/a.mp3"}, {"file": "y/a.mp3"}])
        assert model is None
        assert "duplicate episode file 'a.mp3'" in err

    def test_duplicate_guid_names_both_entries(self):
        model, err = _validate_episodes(
            [{"file": "a.mp3", "guid": "g"}, {"file": "b.mp3"}, {"file": "c.mp3", "guid": "g"}]
        )
        assert model is None
        assert "duplicate episode guid 'g'" in err
        assert "episodes 1 and 3" in err

    def test_distinct_entries_pass(self):
        model, err = _validate_episodes(
            [{"file": "a.mp3", "guid": "g1"}, {"file": "b.mp3", "guid": "g2"}, {"file": "c.mp3"}]
        )
        assert err is None
        assert len(model.episodes) == 3

    def test_no_episodes_passes(self):
        model, err = validate_podcast_config({"title": "T", "description": "D"})
        assert err is None


class TestPubDate:
    @pytest.mark.parametrize(
        "raw, expected",
        [
            ("2025-01-01T08:00:00Z", datetime(2025, 1, 1, 8, tzinfo=UTC)),
            ("2025-01-01T08:00:00+02:00", datetime(2025, 1, 1, 8, tzinfo=timezone(timedelta(hours=2)))),
            ("2025-01-01T08:00:00", datetime(2025, 1, 1, 8, tzinfo=UTC)),
            ("2025-01-01", datetime(2025, 1, 1, tzinfo=UTC)),
            (datetime(2025, 1, 1, 8), datetime(2025, 1, 1, 8, tzinfo=UTC)),
            (datetime(2025, 1, 1, 8, tzinfo=UTC), datetime(2025, 1, 1, 8, tzinfo=UTC)),
            (datetime(2025, 1, 1).date(), datetime(2025, 1, 1, tzinfo=UTC)),
        ],
    )
    def test_accepted_forms(self, raw, expected):
        value = _pub_date(raw)
        assert value == expected
        assert value.tzinfo is not None

    def test_unquoted_yaml_values(self):
        cfg = yaml.safe_load(
            "title: T\ndescription: D\nepisodes:\n"
            "  - {file: a.mp3, pub_date: 2025-01-01}\n"
            "  - {file: b.mp3, pub_date: 2025-01-01T08:00:00Z}\n"
            "  - {file: c.mp3, pub_date: 2025-01-01T08:00:00}\n"
        )
        model, err = validate_podcast_config(cfg)
        assert err is None
        assert [e.pub_date for e in model.episodes] == [
            datetime(2025, 1, 1, tzinfo=UTC),
            datetime(2025, 1, 1, 8, tzinfo=UTC),
            datetime(2025, 1, 1, 8, tzinfo=UTC),
        ]

    def test_naive_value_ignores_host_timezone(self, monkeypatch):
        import time

        monkeypatch.setenv("TZ", "Asia/Tokyo")
        time.tzset()
        try:
            assert _pub_date("2025-01-01T08:00:00") == datetime(2025, 1, 1, 8, tzinfo=UTC)
        finally:
            monkeypatch.undo()
            time.tzset()

    @pytest.mark.parametrize("raw", [None, "", "not a date", 5])
    def test_missing_or_invalid_becomes_none(self, raw):
        assert _pub_date(raw) is None

    def test_invalid_value_is_logged(self, caplog):
        _pub_date("not a date")
        assert any("pub_date" in r.message for r in caplog.records)


class TestValidatePodcastConfig:
    def test_valid_flat_config(self, sample_flat_config):
        model, err = validate_podcast_config(sample_flat_config)
        assert err is None
        assert model is not None
        assert model.title == "My Show"

    def test_valid_nested_config(self, sample_nested_config):
        model, err = validate_podcast_config(sample_nested_config)
        assert err is None
        assert model.title == "Nested Show"
        assert model.author_name == "Nested Author"

    def test_channel_defaults(self):
        model, err = validate_podcast_config({"title": "T", "description": "D"})
        assert err is None
        assert model.language == "en"
        assert model.explicit is False

    def test_missing_description(self):
        _, err = validate_podcast_config({"title": "Only Title"})
        assert err is not None

    def test_invalid_type_value(self):
        cfg = {
            "title": "Show",
            "description": "Desc",
            "type": "invalid",
        }
        _, err = validate_podcast_config(cfg)
        assert err is not None

    def test_legacy_author_field(self, sample_legacy_config):
        cfg = {**sample_legacy_config, "description": "Legacy desc"}
        model, err = validate_podcast_config(cfg)
        assert err is None
        assert model is not None
        assert model.author_name == "Legacy Author"
