"""
Kusoma AI — core agent logic.

Lives in the Bolt scaffold under agent/kusoma.py. Framework-agnostic on purpose:
no slack_bolt imports so routing/classification logic is unit-testable without
a live Slack connection. Wire handle_message_batch into your Bolt event listener.

Pipeline: RTS read -> classify -> MCP curriculum lookup -> route -> Slack message.

Reference docs (schemas, traces, seed data) are in docs/.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import anthropic

CLASSIFIER_MODEL = "claude-sonnet-4-6"

_DOCS_DIR = Path(__file__).resolve().parent.parent / "docs"
CLASSIFIER_SYSTEM_PROMPT = (_DOCS_DIR / "classifier_system_prompt.md").read_text()


# ---------------------------------------------------------------------------
# Data shapes
# ---------------------------------------------------------------------------

@dataclass
class CurriculumRow:
    learner_id: str
    display_name: str
    expected_module: int
    current_module: int
    last_submission_date: str
    prior_experience: str
    assigned_mentor: str
    coordinator: str

    @property
    def behind(self) -> bool:
        return self.current_module < self.expected_module


@dataclass
class ClassificationResult:
    learner_id: str
    message_excerpt: str
    risk_types: list[str]
    confidence: str  # "low" | "medium" | "high" | "n/a"
    reasoning: str


@dataclass
class RoutedAction:
    audience: str          # "mentor" | "coordinator" | "none"
    recipient: str          # mentor/coordinator id
    message: str
    risk_types: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Step 1 — RTS read (stubbed interface; wire to the real RTS call in Bolt)
# ---------------------------------------------------------------------------

def fetch_recent_messages(channel: str, learner_id: str, window_messages: int = 10) -> list[dict]:
    """
    Stub for the real RTS query. In the live Bolt app this becomes a call to
    Slack's Real-Time Search API scoped to public cohort channels, filtered to
    one learner's messages plus a small surrounding window for context.

    Expected real shape (per Slack RTS docs): a list of {text, ts, channel} dicts
    for messages the requesting app/user has access to. Keep this function as the
    single seam between "live Slack" and "everything else" so the rest of the
    pipeline is testable without a workspace connection.
    """
    raise NotImplementedError("Wire this to the live RTS API call inside Bolt.")


# ---------------------------------------------------------------------------
# Step 2 — Classification (Slack AI / Claude call)
# ---------------------------------------------------------------------------

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
    # Classifier is instructed to return strict JSON; strip any stray fencing
    # defensively in case the model wraps it in ```json fences.
    cleaned = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    parsed = json.loads(cleaned)
    return ClassificationResult(
        learner_id=parsed["learner_id"],
        message_excerpt=parsed.get("message_excerpt", ""),
        risk_types=parsed.get("risk_types", []),
        confidence=parsed.get("confidence", "n/a"),
        reasoning=parsed.get("reasoning", ""),
    )


# ---------------------------------------------------------------------------
# Step 3 — Curriculum MCP lookup (stubbed interface; wire to real MCP client)
# ---------------------------------------------------------------------------

def fetch_curriculum_row(learner_id: str) -> CurriculumRow:
    """
    Stub for the real MCP read against the cohort_tracker sheet (see
    curriculum_mcp_schema.md). In the live app this is an MCP tool call, not a
    direct API call — the Bolt agent framework handles the MCP client wiring;
    this function is the seam where that result lands.
    """
    raise NotImplementedError("Wire this to the live curriculum MCP read.")


def fetch_mentor_for_topic(topic: str, fallback_mentor: str) -> str:
    """
    Stub for the mentor_strengths MCP read. Returns the best-matched mentor for
    a topic, falling back to the learner's assigned mentor if no topic-specific
    match exists yet.
    """
    raise NotImplementedError("Wire this to the live mentor_strengths MCP read.")


# ---------------------------------------------------------------------------
# Step 4 — Fusion & routing (pure logic — fully testable, no I/O)
# ---------------------------------------------------------------------------

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
    mentor_for_topic_fn=fetch_mentor_for_topic,
) -> Optional[RoutedAction]:
    """Step 2 of fusion_routing_logic.md — one routing path per risk type.

    If multiple risk types are present, builds one combined coordinator message
    (Step 3) rather than firing multiple separate alerts, UNLESS the only type
    present is "academic" alone, which routes to the mentor instead.
    """
    if not should_escalate(result, row):
        return None

    types = set(result.risk_types)

    # Pure academic, single type -> mentor path
    if types == {"academic"}:
        topic = result.message_excerpt  # in production: extract topic via the
                                         # classifier's reasoning field or a
                                         # second lightweight extraction call
        mentor = mentor_for_topic_fn(topic, row.assigned_mentor)
        message = (
            f"{row.display_name} has asked about {topic} more than once and is "
            f"currently on module {row.current_module} vs an expected "
            f"{row.expected_module}. You've helped others with this before — "
            f"might be worth a quick check-in."
        )
        return RoutedAction(audience="mentor", recipient=mentor, message=message,
                             risk_types=result.risk_types)

    # Everything else (overload, confidence, isolation, withdrawal, or any
    # academic+other combination) routes to the coordinator, combined into one
    # message per Step 3 of the routing doc.
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


# ---------------------------------------------------------------------------
# Step 4b — Cohort-level pattern check (the curriculum-quality signal)
# ---------------------------------------------------------------------------

def check_cohort_pattern(
    topic_flags_this_week: dict[str, list[str]],  # topic -> [learner_ids]
    topic: str,
    threshold: int = 2,
) -> Optional[str]:
    """
    If 2+ learners have been flagged academic on the same topic in the same
    window, returns a coordinator message suggesting a group session instead of
    (or alongside) individual mentor pings. Returns None if below threshold.
    """
    learners = topic_flags_this_week.get(topic, [])
    if len(learners) >= threshold:
        return (
            f"{topic} has come up as a point of confusion for {len(learners)} "
            f"learners this week — might be worth revisiting in a group session "
            f"rather than one-on-one."
        )
    return None


# ---------------------------------------------------------------------------
# Orchestration entry point (called from the Bolt event handler)
# ---------------------------------------------------------------------------

def handle_message_batch(
    client: anthropic.Anthropic,
    channel: str,
    learner_id: str,
    history_context: str,
    current_message: str,
) -> Optional[RoutedAction]:
    result = classify_message(client, learner_id, history_context, current_message)
    row = fetch_curriculum_row(learner_id)
    return route(result, row)
