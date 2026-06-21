from logging import Logger

from slack_bolt.context.async_context import AsyncBoltContext
from slack_sdk.web.async_client import AsyncWebClient

from agent.curriculum import _clean_user_ref, list_scan_targets, resolve_learner_id
from agent.pipeline import run_scan_and_deliver


async def _resolve_learner_ref(
    client: AsyncWebClient,
    user_ref: str,
) -> str | None:
    """Resolve learner from config aliases, then Slack users.info as fallback."""
    if learner_id := resolve_learner_id(user_ref):
        return learner_id

    uid, label = _clean_user_ref(user_ref)
    if uid:
        try:
            info = await client.users_info(user=uid)
            user = info.get("user", {})
            profile = user.get("profile", {})
            for candidate in (
                profile.get("display_name"),
                profile.get("real_name"),
                user.get("name"),
                label,
            ):
                if candidate and (match := resolve_learner_id(candidate)):
                    return match
        except Exception:
            pass

    return None


async def handle_kusoma_command(
    ack,
    command: dict,
    client: AsyncWebClient,
    context: AsyncBoltContext,
    logger: Logger,
):
    await ack()

    user_id = context.user_id
    text = (command.get("text") or "").strip()
    parts = text.split(maxsplit=1)

    if not parts or parts[0].lower() != "scan":
        await client.chat_postEphemeral(
            channel=command["channel_id"],
            user=user_id,
            text=(
                "*Usage:* `/kusoma scan @learner`\n\n"
                "Examples:\n"
                "• `/kusoma scan @Aida K.`\n"
                "• `/kusoma scan aida`\n"
                "• `/kusoma scan @Brian O.`\n\n"
                f"{list_scan_targets()}"
            ),
        )
        return

    if len(parts) < 2:
        await client.chat_postEphemeral(
            channel=command["channel_id"],
            user=user_id,
            text="Please specify a learner: `/kusoma scan @Aida`",
        )
        return

    learner_ref = parts[1].strip()
    learner_id = await _resolve_learner_ref(client, learner_ref)
    if not learner_id:
        await client.chat_postEphemeral(
            channel=command["channel_id"],
            user=user_id,
            text=(
                f"Could not map `{learner_ref}` to a cohort learner.\n\n"
                f"{list_scan_targets()}"
            ),
        )
        return

    await client.chat_postEphemeral(
        channel=command["channel_id"],
        user=user_id,
        text=f":mag: Scanning *{learner_id}* — RTS → classify → curriculum → route…",
    )

    try:
        result = await run_scan_and_deliver(learner_id, client)
    except Exception as exc:
        logger.exception("Kusoma scan failed for %s", learner_id)
        await client.chat_postEphemeral(
            channel=command["channel_id"],
            user=user_id,
            text=f":warning: Scan failed: {exc}",
        )
        return

    if result.action:
        summary = (
            f":white_check_mark: *{result.row.display_name}* — "
            f"{', '.join(result.classification.risk_types)} → "
            f"*{result.action.audience}* DM sent. "
            f"({result.message_count} messages fetched via {result.fetch.source_used if result.fetch else 'unknown'})"
        )
    else:
        summary = (
            f":white_check_mark: *{result.row.display_name}* — no escalation "
            f"({result.classification.confidence}, risk: {result.classification.risk_types or 'none'}). "
            f"({result.message_count} messages fetched — check #kusoma-log for RTS details)"
        )

    await client.chat_postEphemeral(
        channel=command["channel_id"],
        user=user_id,
        text=summary,
    )
