"""
Deterministic Safety, Triage and Medical Boundary Module for Aanya.

Provides rule-based, deterministic red-flag emergency detection across Hindi, English,
and Roman Hindi (Hinglish) without requiring LLM or network availability.
Also enforces strict medical boundaries (no prescriptions, dosage calculations, or clinical diagnosis).
"""

from __future__ import annotations

import dataclasses
import logging
import re
from typing import Final

logger = logging.getLogger("agent.safety")

# Verified National Helplines (Emergency Response Support System & Ambulance)
EMERGENCY_ERSS: Final[str] = "112"
EMERGENCY_AMBULANCE: Final[str] = "108"

DETERMINISTIC_EMERGENCY_GUIDANCE: Final[str] = (
    "यह एक मेडिकल इमरजेंसी हो सकती है। कृपया तुरंत 112 या 108 पर कॉल करें या नजदीकी अस्पताल जाएं। "
    "This may be a medical emergency. Please call 112 or 108 immediately or reach the nearest hospital emergency room. "
    "Do not delay for online advice."
)

MEDICAL_BOUNDARY_MESSAGE: Final[str] = (
    "मैं आन्या हूँ, आपकी स्वास्थ्य मार्गदर्शिका। मैं सामान्य स्वास्थ्य जानकारी दे सकती हूँ, "
    "परंतु दवा की सलाह (prescription), खुराक (dosage) या बीमारी की पुष्टि (diagnosis) नहीं कर सकती। "
    "कृपया उचित जांच और उपचार के लिए नजदीकी डॉक्टर या प्राथमिक स्वास्थ्य केंद्र (PHC) से संपर्क करें।"
)


@dataclasses.dataclass(frozen=True)
class TriageResult:
    is_emergency: bool
    category: str | None = None
    reason: str | None = None
    guidance_message: str = ""
    emergency_numbers: list[str] = dataclasses.field(
        default_factory=lambda: ["112", "108"]
    )


# Negation terms across English and Hindi/Roman Hindi
_NEGATION_PREFIXES = (
    r"\b(no|not|don't have|dont have|do not have|without|free of|never had)\b",
    r"\b(nahi hai|nhi h|nhi hai|nahi|koi\s+\w+\s+nahi)\b",
)

# Emergency category keywords and regexes
_EMERGENCY_PATTERNS: dict[str, list[re.Pattern[str]]] = {
    "cardiac": [
        re.compile(
            r"\b(chest pain|heart attack|chest tightness|chest pressure|radiating pain to left arm)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"(सीने में दर्द|दिल का दौरा|सीने में दबाव|छाती में दर्द|सीने में भारीपन)", re.IGNORECASE
        ),
        re.compile(
            r"\b(seene? mein? dard|sine me dard|dil ka daura|chhati me dard|seene me jalan aur dard)\b",
            re.IGNORECASE,
        ),
    ],
    "respiratory": [
        re.compile(
            r"\b(cannot breathe|can't breathe|cant breathe|difficulty breathing|shortness of breath|choking|severe asthma attack|gasping for air)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"(साँस लेने में दिक्कत|सांस नहीं आ रही|दम घुट रहा|सांस फूल रही|सांस रुकना)",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b(saans lene me(in)? dikkat|saans? nahi aa rahi|dam ghut raha|saans ruk rahi|choking)\b",
            re.IGNORECASE,
        ),
    ],
    "stroke": [
        re.compile(
            r"\b(stroke|face\s+(is\s+)?drooping|slurred\s+speech|speech\s+(is\s+)?slurred|sudden\s+paralysis|one\s+sided\s+weakness|facial\s+droop)\b",
            re.IGNORECASE,
        ),
        re.compile(r"(स्ट्रोक|लकवा|चेहरा लटकना|आधा शरीर सुन्न|बोलने में असमर्थ)", re.IGNORECASE),
        re.compile(
            r"\b(stroke|lakwa|chehra tedha|aadha sharir sunn|bolne me dikkat)\b",
            re.IGNORECASE,
        ),
    ],
    "trauma_bleeding": [
        re.compile(
            r"\b(severe bleeding|uncontrolled bleeding|heavy bleeding|heavy blood loss|head injury|severe burn|skull fracture)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"(भारी रक्तस्राव|खून बहना बंद नहीं|सिर में गंभीर चोट|गंभीर रूप से जल गया)",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b(severe bleeding|khoon beh raha hai|bahut jyada khoon|sar me(in)? chot|jal gaya)\b",
            re.IGNORECASE,
        ),
    ],
    "poisoning": [
        re.compile(
            r"\b(swallowed poison|poisoning|chemical ingestion|drug overdose|drank pesticide)\b",
            re.IGNORECASE,
        ),
        re.compile(r"(जहर खा लिया|विषाक्तता|कीटनाशक पी लिया|ओवरडोज)", re.IGNORECASE),
        re.compile(
            r"\b(zehar kha liya|poison pee liya|keetnashak|dawa overdose)\b",
            re.IGNORECASE,
        ),
    ],
    "unconsciousness": [
        re.compile(
            r"\b(unconscious|passed out|unresponsive|not waking up|severe seizure)\b",
            re.IGNORECASE,
        ),
        re.compile(r"(बेहोश हो गया|अचेत|होश नहीं आ रहा|दौरा पड़ रहा)", re.IGNORECASE),
        re.compile(
            r"\b(behosh|hosh nahi(n)? hai|faint ho gaya|seizure aa gaya)\b",
            re.IGNORECASE,
        ),
    ],
}

# Negation window check
_NEGATION_WORDS = {
    "no",
    "not",
    "dont",
    "don't",
    "never",
    "without",
    "nahi",
    "nhi",
    "nahin",
    "na",
}

# Boundary checks for prescription and clinical diagnosis requests
_PRESCRIPTION_PATTERNS = [
    re.compile(
        r"\b(prescribe|prescription|which medicine should i take|what tablet to take|give me medicine for)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(dosage|how many tablets|how many mg|kitni goli|kitni khurak|dawa ka dose)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(stop taking|increase dose|change medication|dawa band kar du|dawa badal lu)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"(कौन सी दवाई लूँ|दवा का नाम बताओ|कितनी गोली खानी है|दवाई प्रिस्क्राइब करो)",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(kaun si dawa|dawai batao|kitni goli khani hai|dawa suggest karo)\b",
        re.IGNORECASE,
    ),
]

_DIAGNOSIS_PATTERNS = [
    re.compile(
        r"\b(diagnose me|confirm my disease|do i have cancer|tell me what disease i have)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"(क्या मुझे कैंसर है|मेरी बीमारी का निदान करो|मुझे कौन सा रोग है)", re.IGNORECASE
    ),
    re.compile(
        r"\b(kya mujhe typhoid hai|kya mujhe cancer hai|bimari batao confirm karke)\b",
        re.IGNORECASE,
    ),
]


def _tokenize_window(window: str) -> list[str]:
    """Tokenize window safely preserving Unicode words and stripping punctuation."""
    return [w.strip(" ,.!?।:;\"'") for w in window.split() if w.strip(" ,.!?।:;\"'")]


def _is_negated(text: str, match_start: int, match_end: int) -> bool:
    """
    Check if a matched symptom term is negated in the immediate vicinity
    (either within preceding words or directly succeeding words).
    """
    negation_tokens = _NEGATION_WORDS | {"नहीं", "ना", "नही", "nahin", "nhi"}

    # Preceding context (up to 40 characters)
    pre_window = text[max(0, match_start - 40) : match_start].lower()
    pre_tokens = _tokenize_window(pre_window)
    if any(token in negation_tokens or "नह" in token for token in pre_tokens[-3:]):
        return True

    # Check for direct post-negation (e.g. 'chest pain nahi hai' or 'सीने में दर्द नहीं है')
    post_window = text[match_end : match_end + 30].lower()
    post_tokens = _tokenize_window(post_window)
    return any(token in negation_tokens or "नह" in token for token in post_tokens[:3])


def _is_pure_educational_query(text: str) -> bool:
    """
    Detect if the user is asking a purely educational definition rather than reporting
    an immediate symptom (e.g. 'What is the definition of heart attack?').
    If the utterance also contains personal pronouns ('I', 'my father', 'mere'),
    it is treated as personal symptom report.
    """
    lowered = text.lower()
    has_personal_pronoun = any(
        p in lowered
        for p in (
            "i have",
            "i'm",
            "im having",
            "my",
            "mere",
            "mujhe",
            "hamare",
            "meri",
            "father",
            "mother",
            "bhai",
        )
    )
    if has_personal_pronoun:
        return False

    edu_prefixes = [
        "what is the definition of",
        "what does",
        "define",
        "meaning of",
        "kise kehte hain",
        "ka matlab kya hota hai",
    ]
    return any(p in lowered for p in edu_prefixes)


def evaluate_emergency(text: str) -> TriageResult:
    """
    Deterministically evaluates user transcript text for red-flag emergency symptoms.
    Does not require network access, LLM, or external database.
    """
    cleaned = (text or "").strip()
    if not cleaned:
        return TriageResult(is_emergency=False)

    if _is_pure_educational_query(cleaned):
        return TriageResult(is_emergency=False)

    for category, patterns in _EMERGENCY_PATTERNS.items():
        for pattern in patterns:
            for match in pattern.finditer(cleaned):
                if _is_negated(cleaned, match.start(), match.end()):
                    continue
                matched_phrase = match.group(0)
                logger.warning(
                    f"Deterministic safety gate matched red flag [{category}]: '{matched_phrase}' in input."
                )
                return TriageResult(
                    is_emergency=True,
                    category=category,
                    reason=f"Matched red flag symptom '{matched_phrase}' under {category}",
                    guidance_message=DETERMINISTIC_EMERGENCY_GUIDANCE,
                    emergency_numbers=[EMERGENCY_ERSS, EMERGENCY_AMBULANCE],
                )

    return TriageResult(is_emergency=False)


def check_medical_boundary(text: str) -> tuple[bool, str | None]:
    """
    Check if user query crosses medical boundaries:
    - Requests prescription or specific drug recommendation
    - Requests exact dosage calculations
    - Requests authoritative clinical diagnosis

    Returns (is_boundary_violation, refusal_message).
    """
    cleaned = (text or "").strip()
    if not cleaned:
        return False, None

    for pattern in _PRESCRIPTION_PATTERNS:
        if pattern.search(cleaned):
            return True, MEDICAL_BOUNDARY_MESSAGE

    for pattern in _DIAGNOSIS_PATTERNS:
        if pattern.search(cleaned):
            return True, MEDICAL_BOUNDARY_MESSAGE

    return False, None


# Curated, source-attributed health guidance for safe wellness queries
CURATED_HEALTH_TOPICS: dict[str, dict[str, str]] = {
    "hydration": {
        "title": "Daily Hydration Guidelines",
        "summary": "Adults should aim for roughly 2 to 3 liters of water daily, adjusted for climate and physical activity. Staying hydrated prevents fatigue and kidney strain.",
        "source": "Ministry of Health & Family Welfare (MoHFW) / WHO Hydration Guidelines",
    },
    "mild_fever_support": {
        "title": "Supportive Care for Mild Fever",
        "summary": "Rest adequately, stay hydrated with fluids and oral rehydration solution, and apply a light damp cloth to the forehead. If fever exceeds 102°F or persists for more than 48 hours, consult a physician.",
        "source": "National Health Portal of India (NHP)",
    },
    "cold_cough_support": {
        "title": "Home Supportive Measures for Mild Cold",
        "summary": "Warm saline gargles, steam inhalation, and warm fluids like ginger tea or clear broth help soothe an irritated throat. Seek medical consultation if symptoms include high fever or chest pain.",
        "source": "AIIMS Patient Education Guidelines",
    },
    "routine_vaccination": {
        "title": "Universal Immunization Programme (UIP)",
        "summary": "India provides free immunization against preventable childhood illnesses at government Primary Health Centres and sub-centres under Mission Indradhanush.",
        "source": "National Health Mission (NHM) Immunization Schedule",
    },
}
