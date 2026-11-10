"""
demo_policy.py - Privacy Boundaries & Staging Demo Isolation for Aanya.

Provides strict privacy controls and staging isolation:
1. Synthetic data separation - Prevents pollution of production data.
2. Personal memory collection gated during live public demonstrations.
3. Telephony / outbound SIP dialing guarded in staging/demo runs.
4. External escalation webhooks (Slack/Discord) guarded in staging/demo runs.
5. Background scheduling / worker dispatch guarded.
6. Offline evaluation isolation - Prevents unmetered token consumption.
"""

import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger("demo_policy")


def is_demo_mode() -> bool:
    """Return True if DEMO_MODE is active (defaults to True for safe evaluation)."""
    raw = os.getenv("DEMO_MODE") or os.getenv("APP_DEMO_MODE") or "true"
    val = raw.strip().lower()
    return val in ("1", "true", "yes", "on")


def allow_personal_memory_collection() -> bool:
    """Personal memory collection is disabled in demo mode to protect privacy."""
    return not is_demo_mode()


def allow_outbound_calls() -> bool:
    """Outbound SIP calls to real carriers are blocked in demo mode."""
    return not is_demo_mode()


def allow_escalation_delivery() -> bool:
    """External webhooks to Slack/Discord are disabled in demo mode."""
    return not is_demo_mode()


def allow_hosted_model_judging() -> bool:
    """Offline/CI test suites must not burn cloud credits on LLM judging."""
    return not is_demo_mode()


def get_database_path(default_filename: str = "health_memory.db") -> Path:
    """
    Return path to SQLite database.
    In demo mode, strictly returns an isolated synthetic database ('synthetic_demo.db')
    to prevent reading or writing into real user databases.
    """
    base_dir = Path(__file__).resolve().parent.parent
    if is_demo_mode():
        return base_dir / "synthetic_demo.db"
    return base_dir / default_filename


def get_demo_policy_status() -> dict[str, Any]:
    """Return audit report of active policy constraints."""
    demo = is_demo_mode()
    return {
        "demo_mode": demo,
        "personal_memory_collection": not demo,
        "outbound_telephony_enabled": not demo,
        "escalation_webhooks_enabled": not demo,
        "database_target": str(get_database_path().name),
        "synthetic_data_enforced": demo,
    }
