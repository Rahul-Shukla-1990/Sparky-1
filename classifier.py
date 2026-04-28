import re
from app.nlp.taxonomy import INCIDENT_CATEGORIES, MARITIME_RELEVANCE_TERMS, IOR_REGION_TERMS


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").lower()).strip()


def score_terms(text: str, terms: list[str]) -> int:
    t = normalize(text)
    return sum(1 for term in terms if term in t)


def maritime_relevance_score(text: str) -> float:
    maritime_hits = score_terms(text, MARITIME_RELEVANCE_TERMS)
    region_hits = score_terms(text, IOR_REGION_TERMS)

    score = min(60, maritime_hits * 10) + min(40, region_hits * 10)
    return float(min(100, score))


def classify_incident(text: str) -> tuple[str, float]:
    t = normalize(text)
    best_category = "Maritime Incidents"
    best_hits = 0

    for category, keywords in INCIDENT_CATEGORIES.items():
        hits = sum(1 for kw in keywords if kw in t)
        if hits > best_hits:
            best_category = category
            best_hits = hits

    if best_hits == 0:
        return "Maritime Incidents", 25.0

    confidence = min(85.0, 35.0 + best_hits * 12.0)
    return best_category, confidence


def determine_alert_level(category: str, text: str, confidence: float) -> str:
    t = normalize(text)

    critical_terms = [
        "hijack", "hijacked", "missile", "drone attack", "mine", "seized vessel",
        "vessel seizure", "kidnapped", "hostage", "ransomware", "major oil spill",
        "fatalities", "killed", "explosion"
    ]
    high_terms = [
        "boarding", "armed robbery", "fired upon", "suspicious approach",
        "narcotics", "collision", "grounding", "oil spill", "apprehended"
    ]

    if confidence >= 70 and any(term in t for term in critical_terms):
        return "Critical"
    if confidence >= 55 and (category in ["Piracy & Armed Robbery", "Maritime Security Threats"] or any(term in t for term in high_terms)):
        return "High"
    if confidence >= 45:
        return "Medium"
    return "Low"


def verification_status(confidence: float) -> str:
    if confidence >= 90:
        return "Confirmed"
    if confidence >= 75:
        return "High confidence"
    if confidence >= 56:
        return "Probable"
    if confidence >= 31:
        return "Unverified"
    return "Low confidence"
