# Discord Reaction & Poll Role Manager

A safe, one-shot command-line tool that adds or removes a Discord role for everyone who:

- reacted to a specific message, or
- voted for any answer in that message's Discord poll.

Users are deduplicated across reactions and poll answers. The program logs every change, skips users who are already in the requested state, excludes bots by default, and exits when the run is complete. It is **not** a continuously running bot.

## Features

- `ADD` and `REMOVE` actions
- reactions and native Discord poll votes
- message URL or individual server/channel/message IDs
- `.env` support with no credential printed to logs
- confirmation before role changes
- `--dry-run` preview mode
- role hierarchy and permission checks
- clear per-user logs and final summary
- graceful handling when a user left the server or an API request fails

## Requirements

- Python 3.10+
- a Discord application with a bot
- bot installed in the target server
- bot permissions: **View Channel**, **Read Message History**, and **Manage Roles**
- target role positioned below the bot's highest role
- **Server Members Intent** and **Message Content Intent** enabled in the Developer Portal

Discord only permits a bot to manage roles lower than its own highest role.

## Discord setup

1. Open the [Discord Developer Portal](https://discord.com/developers/applications) and create an application.
2. Open **Bot**, create the bot, and enable **Server Members Intent** and **Message Content Intent**.
3. Copy/reset the bot token and save it only in your local `.env` file.
4. Open **OAuth2 > URL Generator**. Select `bot`, then select **View Channels**, **Read Message History**, and **Manage Roles**.
5. Open the generated URL, install the bot in your server, and place its bot role above the role you want to manage.
6. In Discord, enable **Developer Mode** under User Settings > Advanced. You can then right-click a server, channel, message, or role and choose **Copy ID**. For a message, **Copy Message Link** is even easier.

## Install

```bash
git clone https://github.com/jigyasu2004/discord-reaction-role-manager.git
cd discord-reaction-role-manager
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\\Scripts\\activate
python -m pip install -e .
cp .env.example .env
```

Edit `.env` and set the bot token:

```dotenv
DISCORD_BOT_TOKEN=your_bot_token_here
```

The real `.env` file is ignored by Git. Never commit or share a Discord bot token.

## Usage

The simplest form uses a copied Discord message link:

```bash
discord-role-manager \
  --message-url "https://discord.com/channels/SERVER_ID/CHANNEL_ID/MESSAGE_ID" \
  --role-id ROLE_ID \
  --action ADD \
  --dry-run
```

Review the preview, then remove `--dry-run` for the real run:

```bash
discord-role-manager \
  --message-url "https://discord.com/channels/SERVER_ID/CHANNEL_ID/MESSAGE_ID" \
  --role-id ROLE_ID \
  --action ADD
```

To remove the role:

```bash
discord-role-manager \
  --guild-id SERVER_ID \
  --channel-id CHANNEL_ID \
  --message-id MESSAGE_ID \
  --role-id ROLE_ID \
  --action REMOVE
```

All IDs and the action can also be stored in `.env`:

```dotenv
DISCORD_GUILD_ID=123456789012345678
DISCORD_CHANNEL_ID=123456789012345678
DISCORD_MESSAGE_ID=123456789012345678
DISCORD_ROLE_ID=123456789012345678
DISCORD_ACTION=ADD
```

Then run:

```bash
discord-role-manager --dry-run
discord-role-manager
```

Use `--yes` to skip the prompt, or `--include-bots` if bot accounts should also receive the role.

## Example output

```text
INFO     Connected as RoleDemo#1234
INFO     Found 3 unique eligible user(s) from reactions and poll votes
INFO     ADDED  alice (111111111111111111)
INFO     SKIP   bob (222222222222222222) role already present
INFO     ADDED  carol (333333333333333333)
INFO     Summary: discovered=3 changed=2 skipped=1 failed=0
```

Exit codes are `0` for success/cancel/no-op, `1` for setup or connection errors, and `2` when one or more user updates failed.

## Tests

```bash
python -m pip install -e '.[dev]'
pytest -q
ruff check .
```

The tests cover message-link parsing, reactor/poll-voter deduplication, bot exclusion, ADD/REMOVE planning, already-present role handling, and dry-run safety.

## Security notes

- The bot token is read from `DISCORD_BOT_TOKEN` and is never logged.
- Give the bot only the permissions listed above.
- Keep the bot's role below administrator/moderator roles.
- Run `--dry-run` before changing roles in a production server.
- Reset the token immediately if it is ever exposed.

## License

MIT
