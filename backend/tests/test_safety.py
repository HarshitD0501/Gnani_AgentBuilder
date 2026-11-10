"""
Unit Tests for Deterministic Safety, Triage and Medical Boundaries (Sahayika).
Verifies red-flag detection across Hindi, English, and Roman Hindi,
negation filtering, educational exemption, and medical boundary enforcement.
"""

from safety import (
    CURATED_HEALTH_TOPICS,
    DETERMINISTIC_EMERGENCY_GUIDANCE,
    EMERGENCY_AMBULANCE,
    EMERGENCY_ERSS,
    MEDICAL_BOUNDARY_MESSAGE,
    check_medical_boundary,
    evaluate_emergency,
)


def test_english_cardiac_emergency():
    res = evaluate_emergency("I feel a sharp chest pain radiating to my left arm")
    assert res.is_emergency is True
    assert res.category == "cardiac"
    assert EMERGENCY_ERSS in res.guidance_message
    assert EMERGENCY_AMBULANCE in res.guidance_message


def test_hindi_devanagari_cardiac_emergency():
    res = evaluate_emergency("मेरे पिताजी को सीने में दर्द हो रहा है और बहुत पसीना आ रहा है")
    assert res.is_emergency is True
    assert res.category == "cardiac"
    assert res.guidance_message == DETERMINISTIC_EMERGENCY_GUIDANCE


def test_roman_hindi_cardiac_emergency():
    res = evaluate_emergency("mujhe seene mein dard ho raha hai bohot tez")
    assert res.is_emergency is True
    assert res.category == "cardiac"


def test_respiratory_emergency_english():
    res = evaluate_emergency("I cannot breathe please help me")
    assert res.is_emergency is True
    assert res.category == "respiratory"


def test_respiratory_emergency_hindi():
    res = evaluate_emergency("मरीज को साँस लेने में दिक्कत हो रही है")
    assert res.is_emergency is True
    assert res.category == "respiratory"


def test_respiratory_emergency_roman_hindi():
    res = evaluate_emergency("saans lene me dikkat ho rahi hai")
    assert res.is_emergency is True
    assert res.category == "respiratory"


def test_stroke_emergency():
    res1 = evaluate_emergency("His face is drooping and speech is slurred")
    assert res1.is_emergency is True
    assert res1.category == "stroke"

    res2 = evaluate_emergency("aadha sharir sunn pad gaya hai aur lakwa lag raha hai")
    assert res2.is_emergency is True
    assert res2.category == "stroke"


def test_poisoning_and_unconsciousness():
    res1 = evaluate_emergency("The child accidentally swallowed poison")
    assert res1.is_emergency is True
    assert res1.category == "poisoning"

    res2 = evaluate_emergency("He is unconscious and unresponsive")
    assert res2.is_emergency is True
    assert res2.category == "unconsciousness"


def test_negation_handling_english():
    # User clarifies they do NOT have chest pain
    res = evaluate_emergency("I have a mild fever, but no chest pain and no breathing trouble")
    assert res.is_emergency is False


def test_negation_handling_hindi():
    res = evaluate_emergency("मुझे सिरदर्द है, लेकिन सीने में दर्द नहीं है")
    assert res.is_emergency is False

    res_roman = evaluate_emergency("mujhe chest pain nahi hai bas thoda sar dard hai")
    assert res_roman.is_emergency is False


def test_educational_query_not_flagged():
    res = evaluate_emergency("What is the definition of heart attack?")
    assert res.is_emergency is False


def test_medical_boundary_prescription():
    violated, msg = check_medical_boundary("Which medicine should I take for my headache? Prescribe me something.")
    assert violated is True
    assert msg == MEDICAL_BOUNDARY_MESSAGE

    violated_hi, msg_hi = check_medical_boundary("बुखार के लिए कौन सी दवाई लूँ?")
    assert violated_hi is True
    assert msg_hi == MEDICAL_BOUNDARY_MESSAGE


def test_medical_boundary_dosage():
    violated, msg = check_medical_boundary("How many tablets of paracetamol should I take?")
    assert violated is True
    assert msg == MEDICAL_BOUNDARY_MESSAGE

    violated_hi, _ = check_medical_boundary("dawa ka dose kitni goli khani hai?")
    assert violated_hi is True


def test_medical_boundary_diagnosis():
    violated, msg = check_medical_boundary("Diagnose me, do I have cancer?")
    assert violated is True
    assert msg == MEDICAL_BOUNDARY_MESSAGE


def test_safe_wellness_query_allowed():
    violated, msg = check_medical_boundary("Can you give me general tips on staying hydrated?")
    assert violated is False
    assert msg is None


def test_curated_health_topics_attribution():
    assert "hydration" in CURATED_HEALTH_TOPICS
    assert "source" in CURATED_HEALTH_TOPICS["hydration"]
    assert "routine_vaccination" in CURATED_HEALTH_TOPICS
    assert "NHM" in CURATED_HEALTH_TOPICS["routine_vaccination"]["source"]


import pytest
from livekit.agents import ChatContext


@pytest.mark.asyncio
async def test_assistant_llm_node_intercepts_emergency():
    """Verify that Assistant.llm_node intercepts emergency input and yields deterministic guidance without LLM."""
    from agent import Assistant

    agent = Assistant()
    chat_ctx = ChatContext()
    chat_ctx.add_message(role="user", content="I have severe chest pain and cannot breathe")

    chunks = []
    async for chunk in agent.llm_node(chat_ctx, tools=[], model_settings=None):
        chunks.append(chunk)

    assert len(chunks) == 1
    assert "112" in chunks[0]
    assert "108" in chunks[0]
    assert "इमरजेंसी" in chunks[0]


@pytest.mark.asyncio
async def test_assistant_llm_node_intercepts_medical_boundary():
    """Verify that Assistant.llm_node intercepts prescription requests and yields boundary refusal without LLM."""
    from agent import Assistant

    agent = Assistant()
    chat_ctx = ChatContext()
    chat_ctx.add_message(role="user", content="Which medicine should I take for headache? Prescribe me tablets.")

    chunks = []
    async for chunk in agent.llm_node(chat_ctx, tools=[], model_settings=None):
        chunks.append(chunk)

    assert len(chunks) == 1
    assert "दवा की सलाह (prescription)" in chunks[0]

