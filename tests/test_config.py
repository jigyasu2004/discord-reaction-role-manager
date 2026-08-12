import argparse

import pytest

from discord_role_manager.config import parse_message_url


def test_parse_message_url() -> None:
    assert parse_message_url("https://discord.com/channels/111/222/333") == (111, 222, 333)


@pytest.mark.parametrize(
    "value",
    [
        "https://example.com/channels/111/222/333",
        "https://discord.com/channels/@me/222/333",
        "not-a-url",
    ],
)
def test_parse_message_url_rejects_invalid_values(value: str) -> None:
    with pytest.raises(argparse.ArgumentTypeError):
        parse_message_url(value)
