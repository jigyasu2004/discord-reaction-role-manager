from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from discord_role_manager.config import Action
from discord_role_manager.manager import (
    Outcome,
    apply_to_users,
    collect_eligible_users,
    desired_outcome,
)


class AsyncUsers:
    def __init__(self, users):
        self._users = users

    def __aiter__(self):
        return self._iterate()

    async def _iterate(self):
        for user in self._users:
            yield user


class Source:
    def __init__(self, users):
        self._users = users

    def users(self, *, limit):
        assert limit is None
        return AsyncUsers(self._users)

    def voters(self, *, limit):
        assert limit is None
        return AsyncUsers(self._users)


def user(user_id: int, *, bot: bool = False):
    return SimpleNamespace(id=user_id, bot=bot)


@pytest.mark.asyncio
async def test_collects_reactors_and_poll_voters_once_and_excludes_bots() -> None:
    human_one = user(1)
    human_two = user(2)
    bot = user(3, bot=True)
    message = SimpleNamespace(
        reactions=[Source([human_one, human_two, bot])],
        poll=SimpleNamespace(answers=[Source([human_two, bot])]),
    )

    users = await collect_eligible_users(message, include_bots=False)

    assert set(users) == {1, 2}


@pytest.mark.parametrize(
    ("action", "has_role", "expected"),
    [
        (Action.ADD, False, Outcome.CHANGED),
        (Action.ADD, True, Outcome.SKIPPED),
        (Action.REMOVE, True, Outcome.CHANGED),
        (Action.REMOVE, False, Outcome.SKIPPED),
    ],
)
def test_desired_outcome(action, has_role, expected) -> None:
    assert desired_outcome(action, has_role) is expected


@pytest.mark.asyncio
async def test_add_changes_missing_role_and_skips_existing_role() -> None:
    role = SimpleNamespace(id=99)
    member_one = SimpleNamespace(
        roles=[], add_roles=AsyncMock(), remove_roles=AsyncMock()
    )
    member_two = SimpleNamespace(
        roles=[role], add_roles=AsyncMock(), remove_roles=AsyncMock()
    )
    guild = SimpleNamespace(
        get_member=lambda user_id: {1: member_one, 2: member_two}[user_id]
    )
    users = {1: user(1), 2: user(2)}

    summary = await apply_to_users(
        guild, role, users, action=Action.ADD, dry_run=False
    )

    member_one.add_roles.assert_awaited_once()
    member_two.add_roles.assert_not_awaited()
    assert (summary.discovered, summary.changed, summary.skipped, summary.failed) == (2, 1, 1, 0)


@pytest.mark.asyncio
async def test_dry_run_never_modifies_roles() -> None:
    role = SimpleNamespace(id=99)
    member = SimpleNamespace(roles=[], add_roles=AsyncMock(), remove_roles=AsyncMock())
    guild = SimpleNamespace(get_member=lambda _user_id: member)

    summary = await apply_to_users(
        guild, role, {1: user(1)}, action=Action.ADD, dry_run=True
    )

    member.add_roles.assert_not_awaited()
    assert summary.changed == 1

