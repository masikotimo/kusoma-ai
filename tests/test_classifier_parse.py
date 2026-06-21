"""Tests for classifier JSON parsing."""

from agent.kusoma import parse_classifier_response


def test_parse_plain_json():
    text = '{"learner_id": "aida", "risk_types": ["academic"], "confidence": "high", "reasoning": "x", "message_excerpt": "closures"}'
    parsed = parse_classifier_response(text)
    assert parsed["learner_id"] == "aida"
    assert parsed["risk_types"] == ["academic"]


def test_parse_fenced_json():
    text = """Here is the result:
```json
{
  "learner_id": "aida",
  "risk_types": ["academic"],
  "confidence": "high",
  "reasoning": "repeated confusion",
  "message_excerpt": "closures"
}
```
"""
    parsed = parse_classifier_response(text)
    assert parsed["learner_id"] == "aida"


def test_parse_json_with_trailing_text():
    text = """{
  "learner_id": "aida",
  "risk_types": ["academic"],
  "confidence": "high",
  "reasoning": "repeated confusion",
  "message_excerpt": "closures"
}
Note: this learner appears behind on curriculum."""
    parsed = parse_classifier_response(text)
    assert parsed["learner_id"] == "aida"
    assert parsed["risk_types"] == ["academic"]
