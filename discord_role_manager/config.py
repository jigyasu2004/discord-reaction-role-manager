from __future__ import annotations

import argparse
import os
import re
from dataclasses import dataclass
from enum import Enum

from dotenv import load_dotenv


class Action(str, Enum):
    ADD = "ADD"
    REMOVE = "REMOVE"


MESSAGE_URL_RE = re.compile(
    r"^https?://(?:canary\.|ptb\.)?discord(?:app)?\.com/channels/"
    r"(?P<guild>\d+)/(?P<channel>\d+)/(?P<message>\d+)/?$"
)


@dataclass(frozen=True, slots=True)
class Config:
    token: str
    guild_id: int
    channel_id: int
    message_id: int
    role_id: int
    action: Action
    dry_run: bool
    yes: bool
    include_bots: bool


def parse_message_url(value: str) -> tuple[int, int, int]:
    match = MESSAGE_URL_RE.fullmatch(value.strip())
    if not match:
        raise argparse.ArgumentTypeError(
            "message URL must look like https://discord.com/channels/GUILD/CHANNEL/MESSAGE"
        )
    return tuple(int(match.group(name)) for name in ("guild", "channel", "message"))


def _positive_snowflake(value: str, label: str) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be a numeric Discord ID") from exc
    if parsed <= 0:
        raise ValueError(f"{label} must be a positive Discord ID")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="discord-role-manager",
        description=(
            "Add or remove a role for every user who reacted to a message "
            "or voted in its poll. The program exits after one run."
        ),
    )
    location = parser.add_argument_group("message location")
    location.add_argument(
        "--message-url",
        type=parse_message_url,
        metavar="URL",
        help="Discord message link; replaces --guild-id, --channel-id and --message-id",
    )
    location.add_argument("--guild-id", help="Discord server/guild ID")
    location.add_argument("--channel-id", help="channel containing the message")
    location.add_argument("--message-id", help="target message ID")

    parser.add_argument("--role-id", help="role to add or remove")
    parser.add_argument(
        "--action",
        choices=[member.value for member in Action],
        type=str.upper,
        help="ADD or REMOVE",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="show what would change without modifying any role",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="skip the confirmation prompt (useful for automation)",
    )
    parser.add_argument(
        "--include-bots",
        action="store_true",
        help="include bot accounts; bots are excluded by default",
    )
    return parser


def config_from_args(argv: list[str] | None = None) -> Config:
    load_dotenv()
    parser = build_parser()
    args = parser.parse_args(argv)

    token = os.getenv("DISCORD_BOT_TOKEN", "").strip()
    if not token or token == "replace_me":
        parser.error("DISCORD_BOT_TOKEN is missing; set it in the environment or .env")

    if args.message_url:
        guild_id, channel_id, message_id = args.message_url
    else:
        raw_guild = args.guild_id or os.getenv("DISCORD_GUILD_ID")
        raw_channel = args.channel_id or os.getenv("DISCORD_CHANNEL_ID")
        raw_message = args.message_id or os.getenv("DISCORD_MESSAGE_ID")
        missing = [
            name
            for name, value in (
                ("guild ID", raw_guild),
                ("channel ID", raw_channel),
                ("message ID", raw_message),
            )
            if not value
        ]
        if missing:
            parser.error("missing " + ", ".join(missing) + "; pass --message-url or IDs")
        try:
            guild_id = _positive_snowflake(raw_guild, "guild ID")
            channel_id = _positive_snowflake(raw_channel, "channel ID")
            message_id = _positive_snowflake(raw_message, "message ID")
        except ValueError as exc:
            parser.error(str(exc))

    raw_role = args.role_id or os.getenv("DISCORD_ROLE_ID")
    raw_action = args.action or os.getenv("DISCORD_ACTION")
    if not raw_role:
        parser.error("missing role ID; pass --role-id or set DISCORD_ROLE_ID")
    if not raw_action:
        parser.error("missing action; pass --action ADD|REMOVE or set DISCORD_ACTION")
    try:
        role_id = _positive_snowflake(raw_role, "role ID")
        action = Action(raw_action.upper())
    except ValueError as exc:
        parser.error(str(exc))

    return Config(
        token=token,
        guild_id=guild_id,
        channel_id=channel_id,
        message_id=message_id,
        role_id=role_id,
        action=action,
        dry_run=args.dry_run,
        yes=args.yes,
        include_bots=args.include_bots,
    )

