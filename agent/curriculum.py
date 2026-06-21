"""Load sandbox roster and curriculum data (JSON fallback or Google Sheet CSV)."""

from __future__ import annotations

import csv
import io
import json
import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.request import urlopen

from agent.models import CurriculumRow

_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "sandbox_members.json"


def _normalize_key(value: str) -> str:
    """Lowercase alphanumeric key for fuzzy name matching."""
    return re.sub(r"[^a-z0-9]", "", value.lower())


def _clean_user_ref(user_ref: str) -> tuple[str | None, str]:
    """
    Parse slash-command user text into (optional slack_user_id, display fragment).

    Handles: aida, @Aida K., <@U0BBUA2QFC5>, <@U0BBUA2QFC5|Aida K.>
    """
    ref = user_ref.strip()
    slack_user_id: str | None = None

    if ref.startswith("<@") and ref.endswith(">"):
        inner = ref[2:-1]
        if "|" in inner:
            uid, label = inner.split("|", 1)
            slack_user_id = uid.strip().upper()
            ref = label.strip()
        else:
            slack_user_id = inner.strip().upper()
            ref = inner.strip()

    ref = ref.removeprefix("@").strip()
    if ref.upper().startswith("U0"):
        slack_user_id = ref.upper()
        if not slack_user_id.startswith("U"):
            slack_user_id = "U" + slack_user_id[1:]

    return slack_user_id, ref


def _aliases_for_person(learner_id: str, person: dict[str, Any]) -> set[str]:
    """Build matchable aliases from learner_id, display_name, and config aliases."""
    aliases: set[str] = {learner_id, person["slack_user_id"], person["display_name"]}
    aliases.update(person.get("aliases", []))

    display = person["display_name"]
    # Strip role suffix e.g. "Jane K. (Coordinator)" -> "Jane K."
    display_base = display.split("(")[0].strip()
    aliases.add(display_base)

    parts = display_base.replace(".", "").split()
    if parts:
        first = parts[0]
        aliases.add(first)
        if len(parts) >= 2:
            last_initial = parts[1][0] if parts[1] else ""
            aliases.update(
                {
                    f"{first} {parts[1]}",
                    f"{first} {last_initial}",
                    f"{first} {last_initial}.",
                    f"{first}_{last_initial}",
                    f"{first}.{last_initial}",
                }
            )

    return aliases


@lru_cache(maxsize=1)
def _learner_alias_map() -> dict[str, str]:
    config = load_sandbox_config()
    mapping: dict[str, str] = {}
    for learner_id, learner in config["learners"].items():
        for alias in _aliases_for_person(learner_id, learner):
            mapping[_normalize_key(alias)] = learner_id
    return mapping


@lru_cache(maxsize=1)
def _learner_by_slack_id() -> dict[str, str]:
    config = load_sandbox_config()
    return {learner["slack_user_id"]: learner_id for learner_id, learner in config["learners"].items()}


@lru_cache(maxsize=1)
def load_sandbox_config() -> dict[str, Any]:
    return json.loads(_CONFIG_PATH.read_text())


def _row_from_dict(data: dict[str, Any], learner_id: str) -> CurriculumRow:
    return CurriculumRow(
        learner_id=learner_id,
        display_name=str(data["display_name"]),
        expected_module=int(data["expected_module"]),
        current_module=int(data["current_module"]),
        last_submission_date=str(data.get("last_submission_date", "")),
        prior_experience=str(data.get("prior_experience", "none")),
        assigned_mentor=str(data["assigned_mentor"]),
        coordinator=str(data["coordinator"]),
    )


def _sheet_id_from_env() -> str | None:
    raw = os.environ.get("GOOGLE_SHEET_ID", "").strip().strip("/")
    return raw or None


def _sheet_csv_url(sheet_id: str, gid: int = 0) -> str:
    return f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"


def _fetch_csv_rows(sheet_id: str, gid: int = 0) -> list[dict[str, str]]:
    url = _sheet_csv_url(sheet_id, gid)
    with urlopen(url, timeout=10) as response:
        text = response.read().decode("utf-8")
    return list(csv.DictReader(io.StringIO(text)))


def _curriculum_row_from_config(learner_id: str) -> CurriculumRow:
    config = load_sandbox_config()
    learner = config["learners"].get(learner_id)
    if not learner:
        raise KeyError(f"learner_id {learner_id!r} not found in sandbox config")
    return _row_from_dict(learner, learner_id)


def fetch_curriculum_row(learner_id: str) -> CurriculumRow:
    sheet_id = _sheet_id_from_env()
    if sheet_id:
        try:
            for row in _fetch_csv_rows(sheet_id, gid=0):
                if row.get("learner_id") == learner_id:
                    return _row_from_dict(row, learner_id)
            raise KeyError(f"learner_id {learner_id!r} not found in Google Sheet cohort_tracker")
        except Exception as exc:
            import logging

            logging.getLogger(__name__).warning(
                "Google Sheet fetch failed (%s); using config/sandbox_members.json",
                exc,
            )
            return _curriculum_row_from_config(learner_id)

    return _curriculum_row_from_config(learner_id)


def fetch_mentor_for_topic(topic: str, fallback_mentor: str) -> str:
    topic_lower = topic.lower()
    sheet_id = _sheet_id_from_env()
    matches: list[tuple[str, int]] = []

    if sheet_id:
        mentor_gid = int(os.environ.get("GOOGLE_SHEET_MENTOR_GID", "1"))
        try:
            for row in _fetch_csv_rows(sheet_id, gid=mentor_gid):
                row_topic = row.get("topic", "")
                if row_topic and row_topic.lower() in topic_lower:
                    matches.append(
                        (row["mentor"], int(row.get("times_successfully_explained", 0)))
                    )
        except Exception:
            pass

    if not matches:
        for row in load_sandbox_config().get("mentor_strengths", []):
            if row["topic"].lower() in topic_lower:
                matches.append((row["mentor"], int(row["times_successfully_explained"])))

    if matches:
        matches.sort(key=lambda item: item[1], reverse=True)
        return matches[0][0]
    return fallback_mentor


def resolve_learner_id(user_ref: str) -> str | None:
    """Map Slack user ID, @mention, display name, or learner_id to learner_id."""
    slack_user_id, label = _clean_user_ref(user_ref)

    if slack_user_id:
        match = _learner_by_slack_id().get(slack_user_id)
        if match:
            return match

    for candidate in (label, user_ref.strip().removeprefix("@")):
        if not candidate:
            continue
        match = _learner_alias_map().get(_normalize_key(candidate))
        if match:
            return match

    return None


def list_scan_targets() -> str:
    """Human-readable list of valid scan targets for help text."""
    config = load_sandbox_config()
    lines = []
    for learner_id, learner in config["learners"].items():
        lines.append(f"• `{learner_id}` or `{learner['display_name']}`")
    return "\n".join(lines)


def staff_slack_user_id(logical_id: str) -> str:
    config = load_sandbox_config()
    staff = config["staff"].get(logical_id)
    if not staff:
        raise KeyError(f"Unknown staff id {logical_id!r}")
    return staff["slack_user_id"]
