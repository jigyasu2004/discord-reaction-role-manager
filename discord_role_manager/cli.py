from __future__ import annotations

import asyncio
import logging
import sys

import discord

from .config import Config, config_from_args
from .manager import RoleManagerError, apply_to_users, prepare

LOGGER = logging.getLogger("discord_role_manager")


def configure_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)-8s %(message)s")


def confirm(config: Config, count: int) -> bool:
    if config.dry_run or config.yes:
        return True
    answer = input(
        f"{config.action.value} role {config.role_id} for {count} eligible user(s)? [y/N] "
    )
    return answer.strip().lower() in {"y", "yes"}


async def run(config: Config) -> int:
    intents = discord.Intents.default()
    intents.members = True
    intents.message_content = True
    client = discord.Client(intents=intents)
    result_code = 1

    @client.event
    async def on_ready() -> None:
        nonlocal result_code
        LOGGER.info("Connected as %s", client.user)
        try:
            guild, role, users = await prepare(client, config)
            LOGGER.info(
                "Found %d unique eligible user(s) from reactions and poll votes",
                len(users),
            )
            if not users:
                LOGGER.info("Nothing to do")
                result_code = 0
                return
            if not confirm(config, len(users)):
                LOGGER.info("Cancelled; no roles were changed")
                result_code = 0
                return
            summary = await apply_to_users(
                guild,
                role,
                users,
                action=config.action,
                dry_run=config.dry_run,
            )
            LOGGER.info(
                "Summary: discovered=%d changed=%d skipped=%d failed=%d%s",
                summary.discovered,
                summary.changed,
                summary.skipped,
                summary.failed,
                " (dry run)" if config.dry_run else "",
            )
            result_code = 2 if summary.failed else 0
        except RoleManagerError as exc:
            LOGGER.error("%s", exc)
            result_code = 1
        except discord.LoginFailure:
            LOGGER.error("Discord rejected the bot token")
            result_code = 1
        finally:
            await client.close()

    try:
        await client.start(config.token)
    except discord.LoginFailure:
        LOGGER.error("Discord rejected the bot token")
        return 1
    except discord.PrivilegedIntentsRequired:
        LOGGER.error(
            "enable Server Members Intent and Message Content Intent "
            "on the bot's Developer Portal page"
        )
        return 1
    return result_code


def main(argv: list[str] | None = None) -> None:
    configure_logging()
    config = config_from_args(argv)
    try:
        raise SystemExit(asyncio.run(run(config)))
    except KeyboardInterrupt:
        LOGGER.info("Interrupted; exiting")
        raise SystemExit(130) from None


if __name__ == "__main__":
    main(sys.argv[1:])
