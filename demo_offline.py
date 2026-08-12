"""Deterministic offline demo of the same collection and role-update core.

This is useful for reviewers who do not want to provide a Discord token. It does
not replace the real-server setup described in README.md.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field

from discord_role_manager.config import Action
from discord_role_manager.manager import apply_to_users, collect_eligible_users


@dataclass(slots=True)
class DemoRole:
    id: int
    name: str


@dataclass(slots=True)
class DemoUser:
    id: int
    name: str
    bot: bool = False

    def __str__(self) -> str:
        return self.name


@dataclass(slots=True)
class DemoMember:
    user: DemoUser
    roles: list[DemoRole] = field(default_factory=list)

    async def add_roles(self, role: DemoRole, *, reason: str) -> None:
        self.roles.append(role)

    async def remove_roles(self, role: DemoRole, *, reason: str) -> None:
        self.roles.remove(role)


class DemoSource:
    def __init__(self, users: list[DemoUser]) -> None:
        self._users = users

    async def _iterate(self):
        for user in self._users:
            yield user

    def users(self, *, limit: int | None):
        return self._iterate()

    def voters(self, *, limit: int | None):
        return self._iterate()


class DemoGuild:
    def __init__(self, members: list[DemoMember]) -> None:
        self.members = {member.user.id: member for member in members}

    def get_member(self, user_id: int) -> DemoMember | None:
        return self.members.get(user_id)


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)-8s %(message)s")
    role = DemoRole(9001, "Poll Participant")
    alice = DemoUser(101, "alice")
    bob = DemoUser(102, "bob")
    carol = DemoUser(103, "carol")
    helper_bot = DemoUser(104, "helper-bot", bot=True)

    message = type(
        "DemoMessage",
        (),
        {
            "reactions": [DemoSource([alice, bob, helper_bot])],
            "poll": type("DemoPoll", (), {"answers": [DemoSource([bob, carol])]})(),
        },
    )()
    guild = DemoGuild(
        [
            DemoMember(alice),
            DemoMember(bob, roles=[role]),
            DemoMember(carol),
        ]
    )

    print("Discord Role Manager - offline deterministic demo")
    print("Input: one reaction list + one poll answer; bob appears in both")
    users = await collect_eligible_users(message, include_bots=False)
    print(f"Collected unique humans: {', '.join(str(user) for user in users.values())}")
    summary = await apply_to_users(
        guild,
        role,
        users,
        action=Action.ADD,
        dry_run=False,
    )
    print(
        "Result: "
        f"discovered={summary.discovered} changed={summary.changed} "
        f"skipped={summary.skipped} failed={summary.failed}"
    )
    print("Final role holders: alice, bob, carol")


if __name__ == "__main__":
    asyncio.run(main())
