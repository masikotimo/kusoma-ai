"""Fetch cohort messages via Slack Real-Time Search API (with channel-history fallback)."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from slack_sdk.web.async_client import AsyncWebClient

from agent.curriculum import load_sandbox_config

_channel_id_cache: dict[str, str] = {}


@dataclass
class MessageFetchResult:
    messages: list[dict[str, Any]]
    rts_query: str | None = None
    rts_count: int = 0
    history_count: int = 0
    source_used: str = "none"
    rts_error: str | None = None
    channel_breakdown: dict[str, int] = field(default_factory=dict)


def _message_text(message: dict[str, Any]) -> str:
    text = message.get("text", "")
    if text:
        return text
    blocks = message.get("blocks") or []
    parts: list[str] = []
    for block in blocks:
        for element in block.get("elements") or []:
            for item in element.get("elements") or []:
                if item.get("type") == "text":
                    parts.append(item.get("text", ""))
    return " ".join(parts).strip()


def _message_from_user(message: dict[str, Any], slack_user_id: str) -> bool:
    for key in ("user", "user_id", "author_user_id", "sender_user_id", "uploader_user_id"):
        if message.get(key) == slack_user_id:
            return True
    return False


def _merge_messages(*sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str]] = set()
    merged: list[dict[str, Any]] = []
    for source in sources:
        for message in source:
            key = (message.get("ts", ""), message.get("text", "")[:80])
            if key in seen:
                continue
            seen.add(key)
            merged.append(message)
    merged.sort(key=lambda item: float(item["ts"]))
    return merged


def _count_by_channel(messages: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for message in messages:
        channel = message.get("channel", "?")
        counts[channel] = counts.get(channel, 0) + 1
    return counts


async def _resolve_channel_id(client: AsyncWebClient, channel_name: str) -> str | None:
    name = channel_name.lstrip("#")
    if name in _channel_id_cache:
        return _channel_id_cache[name]

    cursor: str | None = None
    while True:
        response = await client.conversations_list(
            types="public_channel",
            limit=200,
            cursor=cursor,
        )
        for channel in response.get("channels", []):
            if channel.get("name") == name:
                _channel_id_cache[name] = channel["id"]
                return channel["id"]
        cursor = response.get("response_metadata", {}).get("next_cursor")
        if not cursor:
            break
    return None


async def _fetch_via_channel_history(
    client: AsyncWebClient,
    slack_user_id: str,
    channel_names: list[str],
    limit: int = 50,
) -> list[dict[str, Any]]:
    collected: list[dict[str, Any]] = []
    for channel_name in channel_names:
        channel_id = await _resolve_channel_id(client, channel_name)
        if not channel_id:
            continue
        response = await client.conversations_history(channel=channel_id, limit=limit)
        for message in response.get("messages", []):
            if message.get("user") != slack_user_id:
                continue
            if message.get("subtype"):
                continue
            text = _message_text(message)
            if not text:
                continue
            collected.append(
                {
                    "text": text,
                    "ts": message["ts"],
                    "channel": channel_name,
                }
            )
    collected.sort(key=lambda item: float(item["ts"]))
    return collected[-limit:]


async def _fetch_via_rts(
    client: AsyncWebClient,
    slack_user_id: str,
    channel_names: list[str],
    limit: int = 20,
    action_token: str | None = None,
) -> tuple[list[dict[str, Any]], str]:
    channels_query = " ".join(f"in:{name}" for name in channel_names)
    query = f"from:<@{slack_user_id}> {channels_query}".strip()

    kwargs: dict[str, Any] = {
        "query": query,
        "content_types": ["messages"],
        "channel_types": ["public_channel"],
        "include_context_messages": True,
        "limit": limit,
    }
    if action_token:
        kwargs["action_token"] = action_token

    response = await client.api_call("assistant.search.context", http_verb="POST", json=kwargs)
    if not response.get("ok"):
        raise RuntimeError(response.get("error", "assistant.search.context failed"))

    collected: list[dict[str, Any]] = []
    for item in response.get("messages", []):
        if not _message_from_user(item, slack_user_id):
            continue
        text = _message_text(item)
        if not text:
            continue
        channel_name = item.get("channel_name") or item.get("channel") or "unknown"
        if isinstance(channel_name, str) and channel_name.startswith("C"):
            for name in channel_names:
                if name in channel_name:
                    channel_name = name
                    break
        collected.append(
            {
                "text": text,
                "ts": item.get("ts") or item.get("timestamp") or str(time.time()),
                "channel": channel_name,
            }
        )
    collected.sort(key=lambda item: float(item["ts"]))
    return collected, query


async def fetch_learner_messages(
    client: AsyncWebClient,
    learner_id: str,
    *,
    user_token_client: AsyncWebClient | None = None,
    action_token: str | None = None,
    window_messages: int = 20,
) -> MessageFetchResult:
    """
    Fetch learner messages from channel history (primary) and RTS (supplement).

    Channel history is reliable for the hackathon demo; RTS is merged when available.
    """
    config = load_sandbox_config()
    learner = config["learners"][learner_id]
    slack_user_id = learner["slack_user_id"]
    channel_names = config.get("cohort_channels", [])

    history_msgs = await _fetch_via_channel_history(
        client,
        slack_user_id,
        channel_names,
        limit=window_messages,
    )

    rts_msgs: list[dict[str, Any]] = []
    rts_query: str | None = None
    rts_error: str | None = None

    user_token = os.environ.get("SLACK_USER_TOKEN")
    rts_client = user_token_client or (AsyncWebClient(token=user_token) if user_token else client)

    try:
        rts_msgs, rts_query = await _fetch_via_rts(
            rts_client,
            slack_user_id,
            channel_names,
            limit=window_messages,
            action_token=action_token,
        )
    except Exception as exc:
        rts_error = str(exc)

    merged = _merge_messages(history_msgs, rts_msgs)[-window_messages:]

    if history_msgs and rts_msgs:
        source_used = "channel_history+rts"
    elif history_msgs:
        source_used = "channel_history"
    elif rts_msgs:
        source_used = "rts"
    else:
        source_used = "none"

    return MessageFetchResult(
        messages=merged,
        rts_query=rts_query,
        rts_count=len(rts_msgs),
        history_count=len(history_msgs),
        source_used=source_used,
        rts_error=rts_error,
        channel_breakdown=_count_by_channel(merged),
    )


def format_classifier_context(messages: list[dict[str, Any]]) -> tuple[str, str]:
    """Build history_context and current_message strings for the classifier."""
    if not messages:
        return (
            "No messages found in cohort channels for this learner.",
            "(no messages in cohort channels)",
        )

    sorted_msgs = sorted(messages, key=lambda item: float(item["ts"]))
    now = time.time()
    latest = sorted_msgs[-1]
    latest_age_days = (now - float(latest["ts"])) / 86400

    transcript_lines: list[str] = []
    for msg in sorted_msgs:
        dt = datetime.fromtimestamp(float(msg["ts"]), tz=timezone.utc)
        transcript_lines.append(
            f"{dt:%Y-%m-%d %H:%M} [{msg.get('channel', '?')}] — {msg.get('text', '')}"
        )
    history_context = "\n".join(transcript_lines)

    if latest_age_days >= 2:
        current_message = "(no messages in the current week — learner has gone quiet)"
    else:
        current_message = latest.get("text") or "(empty message)"

    return history_context, current_message
