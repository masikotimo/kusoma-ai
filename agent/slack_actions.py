"""Send routed Kusoma actions to Slack (DMs + log channel)."""

from __future__ import annotations

from slack_sdk.web.async_client import AsyncWebClient

from agent.curriculum import load_sandbox_config, staff_slack_user_id
from agent.models import ClassificationResult, CurriculumRow, RoutedAction
from agent.rts import MessageFetchResult


async def open_dm_channel(client: AsyncWebClient, user_id: str) -> str:
    response = await client.conversations_open(users=user_id)
    return response["channel"]["id"]


async def send_dm(client: AsyncWebClient, user_id: str, text: str) -> None:
    channel = await open_dm_channel(client, user_id)
    await client.chat_postMessage(channel=channel, text=text)


async def post_to_log_channel(client: AsyncWebClient, text: str) -> None:
    config = load_sandbox_config()
    log_channel_name = config.get("log_channel", "kusoma-log")
    from agent.rts import _resolve_channel_id

    channel_id = await _resolve_channel_id(client, log_channel_name)
    if channel_id:
        await client.chat_postMessage(channel=channel_id, text=text)


def format_scan_log(
    learner_id: str,
    row: CurriculumRow,
    result: ClassificationResult,
    action: RoutedAction | None,
    *,
    fetch: MessageFetchResult | None = None,
    history_context: str = "",
    current_message: str = "",
) -> str:
    lines = [
        f"*Kusoma scan — {row.display_name}* (`{learner_id}`)",
        f"• Curriculum: module {row.current_module}/{row.expected_module}",
    ]

    if fetch:
        lines.append(
            f"• *Data fetch:* `{fetch.source_used}` — "
            f"{fetch.history_count} from channel history, "
            f"{fetch.rts_count} from RTS → *{len(fetch.messages)} merged*"
        )
        if fetch.rts_query:
            lines.append(f"• *RTS query:* `{fetch.rts_query}`")
        if fetch.rts_error:
            lines.append(f"• RTS note: _{fetch.rts_error}_ (used channel history)")
        if fetch.channel_breakdown:
            breakdown = ", ".join(f"#{ch}: {n}" for ch, n in fetch.channel_breakdown.items())
            lines.append(f"• Messages by channel: {breakdown}")
        if not fetch.messages:
            lines.append(
                "• :warning: *No messages found* — is @kusoma invited to "
                "#module-help, #standup, #general?"
            )
    elif history_context.startswith("No messages"):
        lines.append("• :warning: *No messages found* for this learner")

    lines.extend(
        [
            f"• Current message: _{current_message[:120]}{'…' if len(current_message) > 120 else ''}_",
            f"• Risk types: {', '.join(result.risk_types) or 'none'} ({result.confidence})",
            f"• Reasoning: {result.reasoning}",
        ]
    )

    if action:
        recipient_id = staff_slack_user_id(action.recipient)
        lines.append(f"• Routed to *{action.audience}* (`{action.recipient}` → <@{recipient_id}>)")
        lines.append(f"• Message: {action.message}")
    else:
        lines.append("• *No escalation* — staying quiet.")
    return "\n".join(lines)


def format_dm(action: RoutedAction, row: CurriculumRow) -> str:
    recipient_label = "mentor" if action.audience == "mentor" else "coordinator"
    header = f":seedling: *Kusoma — {recipient_label} check-in*"
    body = action.message
    footer = (
        f"_Suggested for {row.display_name}. "
        f"Risk signal: {', '.join(action.risk_types)}. "
        f"Never punitive — human decides outreach._"
    )
    return f"{header}\n\n{body}\n\n{footer}"


async def deliver_action(
    client: AsyncWebClient,
    action: RoutedAction,
    row: CurriculumRow,
) -> str:
    """Send DM to mentor or coordinator. Returns recipient Slack user ID."""
    recipient_slack_id = staff_slack_user_id(action.recipient)
    await send_dm(client, recipient_slack_id, format_dm(action, row))
    return recipient_slack_id
