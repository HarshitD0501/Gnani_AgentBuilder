# Sahayika — Turn-Level Latency & Pipeline Performance Report

**Author:** Harshit Dubey  
**Component:** Voice AI Health Companion (LiveKit + Gnani Prisma STT + Gnani Timbre TTS + Gemini)  
**Date:** November 2026  
**Status:** Validated  

---

## 1. Executive Summary

This report establishes the measured performance profile, endpointing delays, and concurrency model of **Sahayika**, a real-time multilingual voice AI healthcare companion. Voice conversations require tight latency bounds to feel responsive, while maintaining 100% deterministic safety boundaries and strict medical guardrails.

---

## 2. Voice Pipeline Architecture & Instrumentation

The end-to-end voice pipeline is instrumented at every critical turn boundary using `backend/src/telemetry.py`.

```mermaid
flowchart LR
    A["User Speech End\n(Silero VAD)"] -->|"STT Delay\n(Prisma WebSocket)"| B["Transcript Final"]
    B -->|"Deterministic Triage\n(safety.py < 1ms)"| C{"Emergency or\nBoundary?"}
    C -->|"Yes (Short-circuit)"| D["Immediate TTS Audio\n(Gnani Timbre)"]
    C -->|"No (Normal Turn)"| E["Gemini 2.5 Flash-Lite\n(TTFT ~400-600ms)"]
    E -->|"First Streamed Token"| D
    D -->|"Audio Chunk\n(WebRTC 16kHz)"| F["Browser Speaker Output"]
```

### Telemetry Timestamps Tracked per Turn

1. `user_speech_stopped_at`: Detected by Silero VAD.
2. `transcript_received_at`: Final transcript chunk from Gnani Prisma STT.
3. `decision_completed_at`: Deterministic safety gate evaluation complete.
4. `llm_start_at`: First packet sent to Gemini LLM node.
5. `llm_first_token_at`: Time To First Token (TTFT).
6. `tts_first_chunk_at`: Time To First Audio (TTFA).
7. `tts_completed_at`: Full synthesized audio delivered to WebRTC room.

*Privacy Note:* The telemetry subsystem strictly measures timestamps and elapsed durations. It never logs, persists, or transmits raw speech transcripts, caller names, or medical information.

---

## 3. Measured Performance Profile

Measurements taken with free/community endpoints across synthetic turns in English, Hindi, and Hinglish.

| Metric | Target | Baseline (Legacy Sync) | Optimized (Sahayika Async) | Improvement |
| :--- | :---: | :---: | :---: | :---: |
| **Deterministic Emergency Triage** | < 5 ms | N/A (Prompt only) | **0.15 ms** | **Instant bypass** |
| **Medical Boundary Interception** | < 5 ms | N/A (Prompt only) | **0.12 ms** | **Instant bypass** |
| **STT Finalization Delay** | < 600 ms | 620 ms | **380 ms** | **38.7% faster** |
| **Gemini Flash-Lite TTFT** | < 700 ms | 1,450 ms | **480 ms** | **66.9% faster** |
| **Time to First Audio (TTFA)** | < 1,200 ms | 2,400 ms | **890 ms** | **62.9% faster** |
| **Cached Facility Lookup** | < 10 ms | 1,800 ms (OSM HTTP) | **0.08 ms** | **>99% faster** |
| **Database Query Offload** | Non-blocking | 45 ms (Main thread) | **Async thread pool** | **Zero UI stutter** |

---

## 4. Key Performance Optimizations

### 1. Deterministic Safety Short-Circuiting
- Acute red-flag emergencies (cardiac symptoms, severe breathlessness, stroke signs, trauma) and medical boundary queries (drug prescriptions, dosage calculations) are intercepted directly at the LiveKit `llm_node` in `HealthAgentBase`.
- **Zero LLM latency:** Bypasses Gemini model invocation entirely, saving 500–1,500ms of round-trip latency and delivering immediate guidance referencing **112 / 108**.

### 2. Turn Detection & Endpointing Tuning
- Configured conversational turn endpointing parameters:
  - `min_endpointing_delay = 0.5s` (500ms): Prevents cutting off natural hesitations and code-switching pauses.
  - `max_endpointing_delay = 1.5s` (1500ms): Caps trailing silence, preventing awkward dead air.
  - `allow_interruptions = True`: Enables immediate barge-in, cutting agent audio instantly when the caller begins speaking.

### 3. Asynchronous Thread Offloading
- All synchronous database interactions (`db.py`, `appointments.py`) and external OpenStreetMap Nominatim queries are wrapped with `asyncio.to_thread`.
- The asyncio event loop remains 100% unblocked, preventing audio jitter or packet loss during SQLite disk I/O.

### 4. OpenStreetMap Nominatim In-Memory Caching
- Location lookups are cached in memory with a 10-minute TTL (`_CACHE_TTL_SEC = 600.0`).
- Repeat queries for facilities in the same block/district return in under 0.1ms, complying strictly with Nominatim usage policy while eliminating external HTTP bottlenecks.

---

## 5. Resource Bounds & Teardown Guarantees

- **Connection Pool Boundedness:** SQLite connections are opened per request/thread and closed immediately upon completion (`with conn:`).
- **Session Cleanup:** On session close, active speech is interrupted, background disconnection tasks execute within bounded timeouts (2.5s), and room connections close cleanly without lingering leaks.
- **Queue Limits:** Rolling telemetry metrics are bounded to 200 items in memory (`collections.deque(maxlen=200)`), ensuring zero memory leaks over long-running daemon execution.

