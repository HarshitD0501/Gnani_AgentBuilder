"""
Tests for demo_policy.py verifying staging constraints and safe defaults.
"""

import os
from unittest.mock import patch

from demo_policy import (
    allow_escalation_delivery,
    allow_hosted_model_judging,
    allow_outbound_calls,
    allow_personal_memory_collection,
    get_database_path,
    get_demo_policy_status,
    is_demo_mode,
)


def test_demo_mode_default_is_true():
    with patch.dict(os.environ, {}, clear=True):
        assert is_demo_mode() is True
        assert allow_personal_memory_collection() is False
        assert allow_outbound_calls() is False
        assert allow_escalation_delivery() is False
        assert allow_hosted_model_judging() is False
        assert get_database_path().name == "synthetic_demo.db"


def test_demo_mode_explicit_disable():
    with patch.dict(os.environ, {"DEMO_MODE": "false"}, clear=True):
        assert is_demo_mode() is False
        assert allow_personal_memory_collection() is True
        assert allow_outbound_calls() is True
        assert allow_escalation_delivery() is True
        assert allow_hosted_model_judging() is True
        assert get_database_path().name == "health_memory.db"


def test_demo_policy_status_dict():
    with patch.dict(os.environ, {"DEMO_MODE": "true"}, clear=True):
        status = get_demo_policy_status()
        assert status["demo_mode"] is True
        assert status["synthetic_data_enforced"] is True
        assert status["personal_memory_collection"] is False
        assert status["outbound_telephony_enabled"] is False
        assert status["escalation_webhooks_enabled"] is False
        assert status["database_target"] == "synthetic_demo.db"
