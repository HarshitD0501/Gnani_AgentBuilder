"""
Unit tests for voice_providers.py verifying Gnani STT/TTS adapter configuration.
"""

import os
from unittest.mock import patch

from voice_providers import (
    build_gnani_stt,
    build_gnani_tts,
    get_voice_pipeline_attribution,
    validate_gnani_config,
)


def test_validate_gnani_config_missing():
    with patch.dict(os.environ, {}, clear=True):
        valid, msg = validate_gnani_config()
        assert valid is False
        assert "GNANI_API_KEY is not set" in msg


def test_validate_gnani_config_present():
    with patch.dict(os.environ, {"GNANI_API_KEY": "test-key-12345"}, clear=True):
        valid, msg = validate_gnani_config()
        assert valid is True
        assert "valid" in msg


def test_build_gnani_stt_defaults():
    with patch.dict(os.environ, {"GNANI_API_KEY": "test-key-abc"}, clear=True):
        stt = build_gnani_stt(language="en-IN,hi-IN", sample_rate=16000)
        assert stt._opts.language == "en-IN,hi-IN"
        assert stt._opts.sample_rate == 16000
        assert stt._opts.use_streaming is True


def test_build_gnani_tts_female_voice():
    with patch.dict(os.environ, {"GNANI_API_KEY": "test-key-abc"}, clear=True):
        tts = build_gnani_tts(voice="Kaveri", model="timbre-v2.0", sample_rate=16000)
        assert tts._opts.voice == "Kaveri"
        assert tts._opts.model == "timbre-v2.0"
        assert tts._opts.sample_rate == 16000


def test_build_gnani_raises_on_missing_key():
    import pytest

    with (
        patch.dict(os.environ, {}, clear=True),
        pytest.raises(ValueError, match="Gnani API key is required"),
    ):
        build_gnani_stt()


def test_get_voice_pipeline_attribution():
    attr = get_voice_pipeline_attribution()
    assert "Gnani Prisma" in attr["stt_provider"]
    assert "Gnani Timbre" in attr["tts_provider"]
    assert attr["tts_voice"] in ("Kaveri", "Shubhra", "Chetana", "Poorvi")
