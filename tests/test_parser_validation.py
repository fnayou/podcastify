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
