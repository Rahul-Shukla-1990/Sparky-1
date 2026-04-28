from app.nlp.classifier import classify_incident, maritime_relevance_score
from app.nlp.aoi import coordinate_in_broad_ior, aoi_score


def test_piracy_classification():
    category, confidence = classify_incident("Armed men boarded a tanker near the Gulf of Aden")
    assert category == "Piracy & Armed Robbery"
    assert confidence > 40


def test_relevance():
    score = maritime_relevance_score("A vessel reported distress in the Arabian Sea")
    assert score > 0


def test_aoi_coordinate():
    assert coordinate_in_broad_ior(12.0, 45.0) is True
    assert coordinate_in_broad_ior(52.0, -120.0) is False


def test_aoi_text():
    assert aoi_score("Incident reported in the Gulf of Aden") >= 30
