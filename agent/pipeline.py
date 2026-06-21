"""End-to-end Kusoma scan: RTS → classify → curriculum → route → Slack DM."""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass

import anthropic
from slack_sdk.web.async_client import AsyncWebClient

from agent.curriculum import fetch_curriculum_row, fetch_mentor_for_topic
from agent.models import ClassificationResult, CurriculumRow, RoutedAction
from agent.kusoma import classify_message, route
from agent.rts import MessageFetchResult, fetch_learner_messages, format_classifier_context
from agent.slack_actions import deliver_action, format_scan_log, post_to_log_channel


@dataclass
class ScanResult:
    learner_id: str
    row: CurriculumRow
    classification: ClassificationResult
    action: RoutedAction | None
    history_context: str
    current_message: str
    message_count: int
    fetch: MessageFetchResult | None = None


async def scan_learner(
    learner_id: str,
    slack_client: AsyncWebClient,
    *,
    anthropic_client: anthropic.Anthropic | None = None,
    action_token: str | None = None,
) -> ScanResult:
    fetch = await fetch_learner_messages(
        slack_client,
        learner_id,
        action_token=action_token,
    )
    history_context, current_message = format_classifier_context(fetch.messages)

    ai = anthropic_client or anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    classification = await asyncio.to_thread(
        classify_message,
        ai,
        learner_id,
        history_context,
        current_message,
    )
    row = fetch_curriculum_row(learner_id)
    action = route(classification, row, mentor_for_topic_fn=fetch_mentor_for_topic)

    return ScanResult(
        learner_id=learner_id,
        row=row,
        classification=classification,
        action=action,
        history_context=history_context,
        current_message=current_message,
        message_count=len(fetch.messages),
        fetch=fetch,
    )


async def run_scan_and_deliver(
    learner_id: str,
    slack_client: AsyncWebClient,
    *,
    action_token: str | None = None,
) -> ScanResult:
    result = await scan_learner(learner_id, slack_client, action_token=action_token)

    log_text = format_scan_log(
        result.learner_id,
        result.row,
        result.classification,
        result.action,
        fetch=result.fetch,
        history_context=result.history_context,
        current_message=result.current_message,
    )
    await post_to_log_channel(slack_client, log_text)

    if result.action:
        await deliver_action(slack_client, result.action, result.row)

    return result
