from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any

import discord

from .config import Action, Config

LOGGER = logging.getLogger("discord_role_manager")


class Outcome(str, Enum):
    CHANGED = "changed"
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclass(slots=True)
class Summary:
    discovered: int = 0
    changed: int = 0
    skipped: int = 0
    failed: int = 0


class RoleManagerError(RuntimeError):
    """An actionable error that should be shown without a traceback."""


def desired_outcome(action: Action, has_role: bool) -> Outcome:
    if action is Action.ADD:
        return Outcome.SKIPPED if has_role else Outcome.CHANGED
    return Outcome.CHANGED if has_role else Outcome.SKIPPED


async def collect_eligible_users(message: Any, *, include_bots: bool) -> dict[int, Any]:
    """Collect and deduplicate reactors and poll voters by Discord user ID."""
    users: dict[int, Any] = {}

    for reaction in message.reactions:
        async for user in reaction.users(limit=None):
            if include_bots or not user.bot:
                users[user.id] = user

    poll = getattr(message, "poll", None)
    if poll is not None:
        for answer in poll.answers:
            async for user in answer.voters(limit=None):
                if include_bots or not user.bot:
                    users[user.id] = user

    return users


def validate_permissions(channel: Any, bot_member: Any, role: Any) -> None:
    permissions = channel.permissions_for(bot_member)
    if not permissions.view_channel or not permissions.read_message_history:
        raise RoleManagerError(
            "the bot needs View Channel and Read Message History in the target channel"
        )
    if not bot_member.guild_permissions.manage_roles:
        raise RoleManagerError("the bot needs the Manage Roles server permission")
    if role.is_default():
        raise RoleManagerError("the @everyone role cannot be assigned or removed")
    if role >= bot_member.top_role:
        raise RoleManagerError(
            "the target role must be below the bot's highest role in Server Settings > Roles"
        )


async def resolve_member(guild: Any, user_id: int) -> Any:
    member = guild.get_member(user_id)
    if member is not None:
        return member
    return await guild.fetch_member(user_id)


async def apply_to_users(
    guild: Any,
    role: Any,
    users: dict[int, Any],
    *,
    action: Action,
    dry_run: bool,
) -> Summary:
    summary = Summary(discovered=len(users))
    verb = "add" if action is Action.ADD else "remove"

    for user_id, user in sorted(users.items()):
        label = f"{user} ({user_id})"
        try:
            member = await resolve_member(guild, user_id)
            outcome = desired_outcome(action, role in member.roles)
            if outcome is Outcome.SKIPPED:
                state = "present" if action is Action.ADD else "absent"
                LOGGER.info("SKIP   %-32s role already %s", label, state)
                summary.skipped += 1
                continue

            if dry_run:
                LOGGER.info("DRY-RUN %-30s would %s role", label, verb)
            elif action is Action.ADD:
                await member.add_roles(role, reason="Reaction/poll role manager one-shot run")
                LOGGER.info("ADDED  %s", label)
            else:
                await member.remove_roles(role, reason="Reaction/poll role manager one-shot run")
                LOGGER.info("REMOVED %s", label)
            summary.changed += 1
        except discord.NotFound:
            LOGGER.warning("FAILED %-30s user is no longer in the server", label)
            summary.failed += 1
        except (discord.Forbidden, discord.HTTPException) as exc:
            LOGGER.error("FAILED %-30s %s", label, exc)
            summary.failed += 1

    return summary


async def prepare(client: discord.Client, config: Config) -> tuple[Any, Any, dict[int, Any]]:
    guild = client.get_guild(config.guild_id)
    if guild is None:
        raise RoleManagerError(
            f"server {config.guild_id} is unavailable; confirm the bot is installed in it"
        )

    channel = client.get_channel(config.channel_id)
    if channel is None:
        try:
            channel = await client.fetch_channel(config.channel_id)
        except (discord.NotFound, discord.Forbidden) as exc:
            raise RoleManagerError(
                f"channel {config.channel_id} is unavailable to the bot"
            ) from exc
    if not isinstance(channel, (discord.TextChannel, discord.Thread)):
        raise RoleManagerError("the target channel must be a server text channel or thread")
    if channel.guild.id != guild.id:
        raise RoleManagerError("the channel does not belong to the configured server")

    try:
        message = await channel.fetch_message(config.message_id)
    except (discord.NotFound, discord.Forbidden) as exc:
        raise RoleManagerError(
            f"message {config.message_id} is unavailable; check the ID and channel permissions"
        ) from exc

    role = guild.get_role(config.role_id)
    if role is None:
        roles = await guild.fetch_roles()
        role = next((candidate for candidate in roles if candidate.id == config.role_id), None)
    if role is None:
        raise RoleManagerError(f"role {config.role_id} does not exist in the configured server")

    bot_member = guild.me or await guild.fetch_member(client.user.id)
    validate_permissions(channel, bot_member, role)
    users = await collect_eligible_users(message, include_bots=config.include_bots)
    return guild, role, users
