"""
Turn-Level Latency & Pipeline Telemetry Module for Sahayika.

Instruments speech-end, transcript-final, deterministic decision, LLM first token/completion,
and TTS first audio metrics without logging or retaining sensitive user transcripts or PII.
"""

from __future__ import annotations

import collections
import dataclasses
import logging
import statistics
import time
from typing import Any

logger = logging.getLogger("agent.telemetry")


@dataclasses.dataclass
class TurnMetrics:
    turn_id: str
    session_id: str
    created_at: float = dataclasses.field(default_factory=time.time)

    # Monotonic timestamps (seconds)
    user_speech_stopped_at: float | None = None
    transcript_received_at: float | None = None
    decision_completed_at: float | None = None
    llm_start_at: float | None = None
    llm_first_token_at: float | None = None
    llm_completed_at: float | None = None
    tts_first_chunk_at: float | None = None
    tts_completed_at: float | None = None

    # Flags
    is_emergency: bool = False
    is_boundary: bool = False
    is_short_circuit: bool = False

    @property
    def stt_delay_ms(self) -> float | None:
        """Time from user speech end to final transcript receipt."""
        if self.transcript_received_at and self.user_speech_stopped_at:
            return round(max(0.0, (self.transcript_received_at - self.user_speech_stopped_at) * 1000.0), 2)
        return None

    @property
    def decision_delay_ms(self) -> float | None:
        """Time spent in deterministic safety & boundary triage."""
        if self.decision_completed_at and self.transcript_received_at:
            return round(max(0.0, (self.decision_completed_at - self.transcript_received_at) * 1000.0), 2)
        return None

    @property
    def ttft_ms(self) -> float | None:
        """Time to First Token (TTFT) from transcript receipt."""
        if self.llm_first_token_at and self.transcript_received_at:
            return round(max(0.0, (self.llm_first_token_at - self.transcript_received_at) * 1000.0), 2)
        return None

    @property
    def ttfa_ms(self) -> float | None:
        """Time to First Audio (TTFA) from transcript receipt."""
        if self.tts_first_chunk_at and self.transcript_received_at:
            return round(max(0.0, (self.tts_first_chunk_at - self.transcript_received_at) * 1000.0), 2)
        return None

    @property
    def total_turn_latency_ms(self) -> float | None:
        """End-to-end voice latency from speech end to first audio response."""
        if self.tts_first_chunk_at and self.user_speech_stopped_at:
            return round(max(0.0, (self.tts_first_chunk_at - self.user_speech_stopped_at) * 1000.0), 2)
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "turn_id": self.turn_id,
            "session_id": self.session_id,
            "created_at": self.created_at,
            "stt_delay_ms": round(self.stt_delay_ms, 2) if self.stt_delay_ms is not None else None,
            "decision_delay_ms": round(self.decision_delay_ms, 2) if self.decision_delay_ms is not None else None,
            "ttft_ms": round(self.ttft_ms, 2) if self.ttft_ms is not None else None,
            "ttfa_ms": round(self.ttfa_ms, 2) if self.ttfa_ms is not None else None,
            "total_turn_latency_ms": round(self.total_turn_latency_ms, 2) if self.total_turn_latency_ms is not None else None,
            "is_emergency": self.is_emergency,
            "is_boundary": self.is_boundary,
            "is_short_circuit": self.is_short_circuit,
        }


class PipelineTelemetryTracker:
    """Thread-safe, bounded rolling tracker for pipeline turn metrics."""

    def __init__(self, max_history: int = 200) -> None:
        self._history: collections.deque[TurnMetrics] = collections.deque(maxlen=max_history)
        self._active_turns: dict[str, TurnMetrics] = {}

    def start_turn(self, turn_id: str, session_id: str = "default") -> TurnMetrics:
        metrics = TurnMetrics(turn_id=turn_id, session_id=session_id)
        self._active_turns[turn_id] = metrics
        return metrics

    def get_turn(self, turn_id: str) -> TurnMetrics | None:
        return self._active_turns.get(turn_id)

    def complete_turn(self, turn_id: str) -> TurnMetrics | None:
        metrics = self._active_turns.pop(turn_id, None)
        if metrics:
            self._history.append(metrics)
            logger.info(
                f"Turn {turn_id} completed: TTFT={metrics.ttft_ms}ms, "
                f"TTFA={metrics.ttfa_ms}ms, Total={metrics.total_turn_latency_ms}ms, "
                f"Emergency={metrics.is_emergency}"
            )
        return metrics

    def record_completed_metric(self, metrics: TurnMetrics) -> None:
        self._history.append(metrics)

    def get_summary(self) -> dict[str, Any]:
        """Compute statistical summary across recorded turns."""
        turns = list(self._history)
        if not turns:
            return {
                "count": 0,
                "p50_ttfa_ms": 0.0,
                "p90_ttfa_ms": 0.0,
                "p95_ttfa_ms": 0.0,
                "mean_ttfa_ms": 0.0,
                "mean_decision_delay_ms": 0.0,
            }

        ttfa_values = [t.ttfa_ms for t in turns if t.ttfa_ms is not None]
        decision_values = [t.decision_delay_ms for t in turns if t.decision_delay_ms is not None]

        def _percentile(data: list[float], p: float) -> float:
            if not data:
                return 0.0
            data_sorted = sorted(data)
            k = (len(data_sorted) - 1) * (p / 100.0)
            f = int(k)
            c = min(f + 1, len(data_sorted) - 1)
            d0 = data_sorted[f] * (c - k)
            d1 = data_sorted[c] * (k - f)
            return round(d0 + d1, 2)

        return {
            "count": len(turns),
            "ttfa_samples": len(ttfa_values),
            "p50_ttfa_ms": _percentile(ttfa_values, 50),
            "p90_ttfa_ms": _percentile(ttfa_values, 90),
            "p95_ttfa_ms": _percentile(ttfa_values, 95),
            "mean_ttfa_ms": round(statistics.mean(ttfa_values), 2) if ttfa_values else 0.0,
            "mean_decision_delay_ms": round(statistics.mean(decision_values), 2) if decision_values else 0.0,
            "emergency_turns": sum(1 for t in turns if t.is_emergency),
            "short_circuit_turns": sum(1 for t in turns if t.is_short_circuit),
        }

    def clear(self) -> None:
        self._history.clear()
        self._active_turns.clear()


# Global singleton tracker instance
telemetry_tracker = PipelineTelemetryTracker()
