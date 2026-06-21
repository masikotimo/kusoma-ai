"""Tests for learner name resolution."""

from agent.curriculum import resolve_learner_id


def test_resolve_by_learner_id():
    assert resolve_learner_id("aida") == "aida"
    assert resolve_learner_id("brian") == "brian"
    assert resolve_learner_id("carmen") == "carmen"
    assert resolve_learner_id("esther") == "esther"


def test_resolve_by_display_name():
    assert resolve_learner_id("Aida K.") == "aida"
    assert resolve_learner_id("@Aida K.") == "aida"
    assert resolve_learner_id("Brian O.") == "brian"
    assert resolve_learner_id("@Brian O.") == "brian"
    assert resolve_learner_id("Carmen R.") == "carmen"
    assert resolve_learner_id("Esther N.") == "esther"


def test_resolve_by_slack_username():
    assert resolve_learner_id("@aida_k") == "aida"
    assert resolve_learner_id("brian_o") == "brian"
    assert resolve_learner_id("carmen_r") == "carmen"
    assert resolve_learner_id("esther_n") == "esther"


def test_resolve_by_slack_user_id():
    assert resolve_learner_id("U0BBUA2QFC5") == "aida"
    assert resolve_learner_id("<@U0BBUA2QFC5>") == "aida"
    assert resolve_learner_id("<@U0BBUA2QFC5|Aida K.>") == "aida"
    assert resolve_learner_id("<@U0BBVKNLF0E|Brian O.>") == "brian"
    assert resolve_learner_id("<@U0BBXMWT2RY|Carmen R.>") == "carmen"
    assert resolve_learner_id("<@U0BCS0Q1S56|Esther N.>") == "esther"


def test_resolve_partial_names():
    assert resolve_learner_id("@Aida") == "aida"
    assert resolve_learner_id("Aida K") == "aida"
    assert resolve_learner_id("Brian") == "brian"
    assert resolve_learner_id("Carmen") == "carmen"


def test_resolve_unknown():
    assert resolve_learner_id("unknown") is None
    assert resolve_learner_id("@jane") is None
