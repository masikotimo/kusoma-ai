"""Tests for RTS history formatting."""

import time

from agent.rts import format_classifier_context


def test_format_empty_messages():
    history, current = format_classifier_context([])
    assert "No messages found" in history
    assert "no messages" in current


def test_format_recent_messages_use_latest_as_current():
    now = time.time()
    messages = [
        {"text": "first question about closures", "ts": str(now - 3600), "channel": "module-help"},
        {"text": "still confused about closures", "ts": str(now - 60), "channel": "module-help"},
    ]
    history, current = format_classifier_context(messages)
    assert "first question" in history
    assert "still confused" in history
    assert current == "still confused about closures"


def test_format_full_transcript_in_history():
    now = time.time()
    messages = [
        {"text": "message one", "ts": str(now - 120), "channel": "general"},
        {"text": "message two", "ts": str(now - 60), "channel": "standup"},
    ]
    history, current = format_classifier_context(messages)
    assert "message one" in history
    assert "message two" in history
    assert current == "message two"


def test_format_stale_latest_triggers_withdrawal_style_current():
    now = time.time()
    messages = [
        {"text": "excited to start!", "ts": str(now - 86400 * 5), "channel": "module-help"},
        {"text": "loving module 1", "ts": str(now - 86400 * 4), "channel": "general"},
    ]
    history, current = format_classifier_context(messages)
    assert "gone quiet" in current
    assert "excited to start" in history
