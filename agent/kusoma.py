"""
Kusoma AI — core agent logic.

Lives in the Bolt scaffold under agent/kusoma.py. Framework-agnostic on purpose:
no slack_bolt imports so routing/classification logic is unit-testable without
a live Slack connection. Wire handle_message_batch into your Bolt event listener.

Pipeline: RTS read -> classify -> MCP curriculum lookup -> route -> Slack message.

Reference docs (schemas, traces, seed data) are in docs/.
"""

import json
import re
from pathlib import Path
from typing import Any, Optional

import anthropic

from agent.models import ClassificationResult, CurriculumRow, RoutedAction

CLASSIFIER_MODEL = "claude-sonnet-4-6"

_DOCS_DIR = Path(__file__).resolve().parent.parent / "docs"
CLASSIFIER_SYSTEM_PROMPT = (_DOCS_DIR / "classifier_system_prompt.md").read_text()


def parse_classifier_response(text: str) -> dict[str, Any]:
    """Extract the first JSON object from a classifier response."""
    cleaned = text.strip()

    fence = re.search(r"```(?:json)?\s*(\{.*)", cleaned, re.DOTALL)
    if fence:
        cleaned = fence.group(1).split("```", 1)[0].strip()

    start = cleaned.find("{")
    if start == -1:
        raise ValueError(f"No JSON object in classifier response: {text[:200]!r}")

    obj, _ = json.JSONDecoder().raw_decode(cleaned[start:])
    return obj


# Re-export models for existing imports/tests
__all__ = [
    "ClassificationResult",
    "CurriculumRow",
    "RoutedAction",
    "classify_message",
    "should_escalate",
    "route",
    "check_cohort_pattern",
    "handle_message_batch",
]


def fetch_recent_messages(channel: str, learner_id: str, window_messages: int = 10) -> list[dict]:
    """Sync stub kept for tests. Live scans use agent.pipeline.scan_learner()."""
    raise NotImplementedError("Use agent.pipeline.scan_learner() for live Slack scans.")


def classify_message(
    client: anthropic.Anthropic,
    learner_id: str,
    history_context: str,
    current_message: str,
) -> ClassificationResult:
    user_content = (
        f"Learner: {learner_id}\n"
        f"Recent history/context: {history_context}\n"
        f"Current message: {current_message}"
    )
    response = client.messages.create(
        model=CLASSIFIER_MODEL,
        max_tokens=300,
        system=CLASSIFIER_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_content}],
    )
    text = "".join(
        block.text for block in response.content if getattr(block, "type", None) == "text"
    )
    parsed = parse_classifier_response(text)
    return ClassificationResult(
        learner_id=parsed["learner_id"],
        message_excerpt=parsed.get("message_excerpt", ""),
        risk_types=parsed.get("risk_types", []),
        confidence=parsed.get("confidence", "n/a"),
        reasoning=parsed.get("reasoning", ""),
    )


def should_escalate(result: ClassificationResult, row: CurriculumRow) -> bool:
    """Step 1 of fusion_routing_logic.md — the gate."""
    if not result.risk_types:
        return False
    if result.risk_types == ["academic"] and result.confidence == "low" and not row.behind:
        return False
    return True


def route(
    result: ClassificationResult,
    row: CurriculumRow,
    mentor_for_topic_fn=None,
) -> Optional[RoutedAction]:
    """Step 2 of fusion_routing_logic.md — one routing path per risk type."""
    if mentor_for_topic_fn is None:
        from agent.curriculum import fetch_mentor_for_topic

        mentor_for_topic_fn = fetch_mentor_for_topic

    if not should_escalate(result, row):
        return None

    types = set(result.risk_types)

    if types == {"academic"}:
        topic = result.message_excerpt
        mentor = mentor_for_topic_fn(topic, row.assigned_mentor)
        message = (
            f"{row.display_name} has asked about {topic} more than once and is "
            f"currently on module {row.current_module} vs an expected "
            f"{row.expected_module}. You've helped others with this before — "
            f"might be worth a quick check-in."
        )
        return RoutedAction(
            audience="mentor",
            recipient=mentor,
            message=message,
            risk_types=result.risk_types,
        )

    fragments = []
    if "overload" in types:
        fragments.append(
            f"{row.display_name} has mentioned time pressure outside the course "
            f"recently. Worth checking whether they need a deadline adjustment."
        )
    if "confidence" in types:
        track_note = "on track" if not row.behind else "behind schedule"
        fragments.append(
            f"{row.display_name} has expressed self-doubt comparing themselves to "
            f"peers. Note: they're actually {track_note} "
            f"({row.current_module}/{row.expected_module}) — this looks like a "
            f"confidence gap, not a skills gap."
        )
    if "isolation" in types:
        fragments.append(
            f"{row.display_name} is keeping up with submissions but hasn't engaged "
            f"socially in cohort channels lately. Not urgent, but might be worth a "
            f"casual check-in."
        )
    if "withdrawal" in types:
        fragments.append(
            f"{row.display_name} was previously active and has gone notably quiet "
            f"compared to their own earlier pattern. Probably worth a direct, "
            f"personal message."
        )
    if "academic" in types and len(types) > 1:
        fragments.append(
            f"They've also been stuck on the same topic without resolution — "
            f"worth flagging to their mentor ({row.assigned_mentor}) separately."
        )

    return RoutedAction(
        audience="coordinator",
        recipient=row.coordinator,
        message=" ".join(fragments),
        risk_types=result.risk_types,
    )


def check_cohort_pattern(
    topic_flags_this_week: dict[str, list[str]],
    topic: str,
    threshold: int = 2,
) -> Optional[str]:
    learners = topic_flags_this_week.get(topic, [])
    if len(learners) >= threshold:
        return (
            f"{topic} has come up as a point of confusion for {len(learners)} "
            f"learners this week — might be worth revisiting in a group session "
            f"rather than one-on-one."
        )
    return None


def handle_message_batch(
    client: anthropic.Anthropic,
    channel: str,
    learner_id: str,
    history_context: str,
    current_message: str,
) -> Optional[RoutedAction]:
    from agent.curriculum import fetch_curriculum_row

    result = classify_message(client, learner_id, history_context, current_message)
    row = fetch_curriculum_row(learner_id)
    return route(result, row)
