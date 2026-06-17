"""Unit tests for agent.kusoma routing logic — no live API or Slack needed."""

import pytest

from agent.kusoma import (
    ClassificationResult,
    CurriculumRow,
    check_cohort_pattern,
    route,
    should_escalate,
)


def mentor_stub(topic, fallback):
    return "sam"


@pytest.fixture
def felix_row():
    return CurriculumRow("felix", "Felix T.", 4, 4, "2026-06-12", "some", "priya", "jane")


@pytest.fixture
def aida_row():
    return CurriculumRow("aida", "Aida K.", 4, 2, "2026-06-09", "none", "sam", "jane")


@pytest.fixture
def daniel_row():
    return CurriculumRow("daniel", "Daniel M.", 4, 4, "2026-06-12", "experienced", "priya", "jane")


@pytest.fixture
def carmen_row():
    return CurriculumRow("carmen", "Carmen R.", 4, 4, "2026-06-12", "none", "priya", "jane")


@pytest.fixture
def brian_row():
    return CurriculumRow("brian", "Brian O.", 4, 3, "2026-06-11", "some", "sam", "jane")


@pytest.fixture
def esther_row():
    return CurriculumRow("esther", "Esther N.", 4, 2, "2026-05-20", "none", "sam", "jane")


class TestFelixControl:
    def test_does_not_escalate(self, felix_row):
        result = ClassificationResult("felix", "lol this module wrecked me", [], "n/a", "no signal detected")
        assert should_escalate(result, felix_row) is False

    def test_route_returns_none(self, felix_row):
        result = ClassificationResult("felix", "lol this module wrecked me", [], "n/a", "no signal detected")
        assert route(result, felix_row, mentor_stub) is None


class TestAidaAcademic:
    def test_escalates(self, aida_row):
        result = ClassificationResult("aida", "closures", ["academic"], "high", "repeated, unresolved")
        assert should_escalate(result, aida_row) is True

    def test_routes_to_mentor(self, aida_row):
        result = ClassificationResult("aida", "closures", ["academic"], "high", "repeated, unresolved")
        action = route(result, aida_row, mentor_stub)
        assert action.audience == "mentor"
        assert action.recipient == "sam"
        assert "module 2" in action.message and "expected 4" in action.message


class TestDanielIsolation:
    def test_escalates_despite_on_track(self, daniel_row):
        result = ClassificationResult("daniel", "", ["isolation"], "medium", "no engagement despite on-time submissions")
        assert should_escalate(result, daniel_row) is True

    def test_routes_to_coordinator(self, daniel_row):
        result = ClassificationResult("daniel", "", ["isolation"], "medium", "no engagement despite on-time submissions")
        action = route(result, daniel_row, mentor_stub)
        assert action.audience == "coordinator"
        assert action.recipient == "jane"


class TestCarmenConfidence:
    def test_routes_to_coordinator_with_on_track_note(self, carmen_row):
        result = ClassificationResult("carmen", "not cut out for this", ["confidence"], "high", "comparison language, self-doubt")
        action = route(result, carmen_row, mentor_stub)
        assert action.audience == "coordinator"
        assert "on track" in action.message


class TestBrianOverload:
    def test_routes_to_coordinator(self, brian_row):
        result = ClassificationResult("brian", "kid's been sick", ["overload"], "high", "time/life pressure, no content confusion")
        action = route(result, brian_row, mentor_stub)
        assert action.audience == "coordinator"
        assert "module" not in action.message.lower() or "deadline" in action.message.lower()


class TestEstherWithdrawal:
    def test_routes_to_coordinator_with_personal_outreach(self, esther_row):
        result = ClassificationResult("esther", "", ["withdrawal"], "high", "highly active week 1, silent since week 3")
        action = route(result, esther_row, mentor_stub)
        assert action.audience == "coordinator"
        assert "personal" in action.message.lower()


class TestCombinedFlags:
    def test_academic_plus_overload_routes_to_coordinator(self, brian_row):
        result = ClassificationResult("brian", "stuck and also no time", ["academic", "overload"], "medium", "both signals present")
        action = route(result, brian_row, mentor_stub)
        assert action.audience == "coordinator"
        assert "deadline" in action.message.lower() and "sam" in action.message


class TestCohortPattern:
    def test_fires_at_threshold(self):
        pattern_flags = {"closures": ["aida", "another_learner"]}
        pattern_msg = check_cohort_pattern(pattern_flags, "closures", threshold=2)
        assert pattern_msg is not None
        assert "group session" in pattern_msg

    def test_does_not_fire_below_threshold(self):
        below_threshold = check_cohort_pattern({"closures": ["aida"]}, "closures", threshold=2)
        assert below_threshold is None
