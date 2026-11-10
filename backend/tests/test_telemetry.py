"""
Unit Tests for Telemetry and Pipeline Timing Module (Sahayika).
Verifies metrics collection, calculation of TTFT, TTFA, STT delay,
percentiles, and privacy safety (no transcript or PII retention).
"""

import time

from telemetry import PipelineTelemetryTracker, TurnMetrics


def test_turn_metrics_calculations():
    t0 = 1000.0
    metrics = TurnMetrics(
        turn_id="turn_123",
        session_id="sess_abc",
        user_speech_stopped_at=t0,
        transcript_received_at=t0 + 0.35,  # 350ms STT
        decision_completed_at=t0 + 0.36,  # 10ms triage
        llm_start_at=t0 + 0.36,
        llm_first_token_at=t0 + 0.85,  # 500ms TTFT
        llm_completed_at=t0 + 1.20,
        tts_first_chunk_at=t0 + 1.10,  # 750ms TTFA
        tts_completed_at=t0 + 1.80,
    )

    assert metrics.stt_delay_ms == 350.0
    assert metrics.decision_delay_ms == 10.0
    assert metrics.ttft_ms == 500.0
    assert metrics.ttfa_ms == 750.0
    assert metrics.total_turn_latency_ms == 1100.0


def test_telemetry_tracker_summary():
    tracker = PipelineTelemetryTracker(max_history=50)

    # Turn 1
    m1 = tracker.start_turn("t1", "s1")
    m1.user_speech_stopped_at = 100.0
    m1.transcript_received_at = 100.2
    m1.tts_first_chunk_at = 101.0  # TTFA = 800ms
    tracker.complete_turn("t1")

    # Turn 2
    m2 = tracker.start_turn("t2", "s1")
    m2.user_speech_stopped_at = 200.0
    m2.transcript_received_at = 200.2
    m2.tts_first_chunk_at = 201.2  # TTFA = 1000ms
    tracker.complete_turn("t2")

    summary = tracker.get_summary()
    assert summary["count"] == 2
    assert summary["ttfa_samples"] == 2
    assert summary["p50_ttfa_ms"] == 900.0
    assert summary["p90_ttfa_ms"] == 980.0
    assert summary["mean_ttfa_ms"] == 900.0


def test_telemetry_privacy_guarantee():
    tracker = PipelineTelemetryTracker()
    m = tracker.start_turn("t_priv", "sess_priv")
    m.user_speech_stopped_at = time.time()
    m.transcript_received_at = time.time() + 0.1
    m.tts_first_chunk_at = time.time() + 0.5
    d = m.to_dict()

    # Verify no PII or text fields exist in output dict
    assert "transcript" not in d
    assert "text" not in d
    assert "user_name" not in d
    assert "phone" not in d
    assert d["turn_id"] == "t_priv"
