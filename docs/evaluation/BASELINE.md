# Aanya — Phase 1 Baseline & Test Isolation Report

**Date:** 10 November 2026, Asia/Kolkata  
**Project:** Aanya — Multilingual Voice AI Health Companion  
**Repository:** `C:\Users\harsh\Desktop\Gnani\Aanya-AI-Health-Agent`  
**Remote:** `https://github.com/HarshitD0501/Sahayika.git`  
**Status:** PHASE 1 COMPLETE — Baseline verified, dependencies isolated, test suite guarded.

---

## 1. System & Toolchain Inventory

| Component | Tool / Package | Verified Version | Notes |
| :--- | :--- | :--- | :--- |
| **Python** | CPython | `3.12.12` | Isolated virtualenv via `uv` |
| **Package Manager (Python)** | uv | `0.12.3` | All packages pinned in `uv.lock` |
| **Voice Framework** | livekit-agents | `1.8.11` | Standard agent architecture |
| **Gnani Plugin** | livekit-plugins-gnani | `1.8.11` | Installed & verified in virtual environment |
| **Node.js** | Node | `v22.22.3` | LTS runtime |
| **Package Manager (Frontend)** | pnpm | `10.23.0` | Frontend package manager |
| **Frontend Framework** | Next.js / React | `15.x / 18.x` | LiveKit Agents UI components |

---

## 2. Credential & Entitlement Audit (Zero Secret Exposure)

*Checked by presence only; no secrets logged, printed or committed:*

| Credential | Status | Constraint / Action Required |
| :--- | :--- | :--- |
| `GNANI_API_KEY` | **MISSING** | Required for Phase 2 live Prisma STT & Timbre TTS requests. To be configured securely in `.env.local`. |
| `GEMINI_API_KEY` | **PRESENT (53 chars)** | Key present in environment. Must verify free-tier billing status before streaming LLM tokens. |
| `GOOGLE_API_KEY` | **MISSING** | Will alias from `GEMINI_API_KEY` in session setup. |
| `LIVEKIT_URL` | **MISSING** | Required for live WebRTC room token generation & client connection. |
| `LIVEKIT_API_KEY` | **MISSING** | Required for token generation. |
| `LIVEKIT_API_SECRET` | **MISSING** | Required for token generation. |
| `OPENAI_API_KEY` | **MISSING** | Not required for runtime. Offline unit tests guarded against unmetered judge calls. |
| `DEEPGRAM_API_KEY` | **MISSING** | Deprecated / to be replaced by Gnani Prisma STT in Phase 2. |
| `MURF_API_KEY` | **MISSING** | Deprecated / to be replaced by Gnani Timbre TTS in Phase 2. |

---

## 3. Test Isolation & Guarding (`conftest.py`)

To ensure robust CI/CD execution and prevent unmetered external API calls or network dependencies during offline test runs:
1. **Integration Test Marker (`@pytest.mark.integration`):**
   - Tests that invoke live LLM judges or live cloud models (e.g., `test_agent.py` calling `openai/gpt-4.1-mini`) are marked with `@pytest.mark.integration`.
   - **Default behavior:** Skipped automatically.
   - **Opt-in command:** `uv run pytest --run-integration`.
2. **External Network Marker (`@pytest.mark.external_network`):**
   - Tests that invoke live external HTTP services (e.g., Nominatim OSM lookups in `test_day5_tools.py`) are marked with `@pytest.mark.external_network`.
   - **Default behavior:** Skipped automatically.
   - **Opt-in command:** `uv run pytest --run-external`.
3. **Offline Unit & Logic Suite:**
   - 100% offline, zero network requests, zero cloud token burn.
   - Fully covers SQLite memory, appointment planning, retry classifiers, phone normalization, escalation scrubbing, and Linphone SIP routing.

---

## 4. Staging Demo Mode Policy (`demo_policy.py`)

A dedicated enforcement module `src/demo_policy.py` was created to guarantee system privacy and demonstration safety:
* `DEMO_MODE=true` by default.
* **Synthetic Data Only:** Redirects all SQLite persistence to `synthetic_demo.db` during demo mode, ensuring zero exposure of real patient health data or phone numbers.
* **Gated Outbound Telephony:** Blocks SIP trunk dialing to live PSTN carriers during demonstration runs.
* **Gated Escalations:** Disables real webhook dispatch to external Slack/Discord channels.
* **Gated Memory Collection:** Prevents persistent health memory storage for non-synthetic demonstration calls.
* Unit test coverage established in `tests/test_demo_policy.py` (3 tests passed).

---

## 5. Summary of Baseline Test Suite Execution

| Test Module | Total Tests | Passed | Skipped | Notes |
| :--- | :--- | :--- | :--- | :--- |
| `tests/test_demo_policy.py` | 3 | 3 | 0 | Staging demo policy & isolation verified |
| `tests/test_day4_memory.py` | 4 | 4 | 0 | SQLite caller memory & consent tests |
| `tests/test_day5_tools.py` | 5 | 3 | 2 | Emergency helplines passed; live OSM tests guarded |
| `tests/test_day6_outbound.py` | 90 | 90 | 0 | Reminder state machines & retry logic |
| `tests/test_day7_escalation.py` | 27 | 25 | 2 | Scrubber & payload logic passed; live LLM judge guarded |
| `tests/test_day8_analytics.py` | 29 | 29 | 0 | Session metrics & call classification |
| `tests/test_day9_handoff.py` | 11 | 9 | 2 | Clinic specialist transitions |
| `tests/test_day9_linphone.py` | 74 | 74 | 0 | SIP trunk routing & URI resolution |
| `tests/test_agent.py` | 3 | 0 | 3 | Live LLM evaluation tests guarded |
| **Total** | **246** | **237** | **9** | **237 passed, 9 safely skipped offline** |

