"""Platform publisher adapters.

Each adapter exposes a single `publish(account_name, title, body)` contract.
Sandbox/dry-run implementations log the action; production adapters would
call the real platform APIs with the decrypted credential. Adding a real
platform = implement one class + register it in PUBLISHERS.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PublishResult:
    ok: bool
    external_id: str = ""
    error: str = ""


class BasePublisher:
    platform = "base"

    def publish(self, account_name: str, title: str, body: str) -> PublishResult:
        raise NotImplementedError


class DryRunPublisher(BasePublisher):
    """Safe default: records intent without touching any real API."""

    def __init__(self, platform: str):
        self.platform = platform

    def publish(self, account_name: str, title: str, body: str) -> PublishResult:
        logger.info("[dry-run] %s -> %s: %s", self.platform, account_name, title[:60])
        return PublishResult(ok=True, external_id=f"dryrun-{self.platform}")


PUBLISHERS: dict[str, BasePublisher] = {
    "facebook": DryRunPublisher("facebook"),
    "x": DryRunPublisher("x"),
    "youtube": DryRunPublisher("youtube"),
    "instagram": DryRunPublisher("instagram"),
}


def get_publisher(platform: str) -> BasePublisher:
    try:
        return PUBLISHERS[platform]
    except KeyError as e:
        raise ValueError(f"Unsupported platform: {platform}") from e
