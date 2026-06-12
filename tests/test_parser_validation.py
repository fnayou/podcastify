#!/usr/bin/env python3
"""Tests for Pydantic config validation."""

import yaml

from podcastify.parser import validate_podcast_config


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
