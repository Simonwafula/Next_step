#!/usr/bin/env python3
"""Generate a Telethon StringSession for non-interactive Telegram ingestion.

Usage:
  TELEGRAM_API_ID=... TELEGRAM_API_HASH=... python scripts/telegram_create_session.py

This will prompt for your phone number and login code once, then print a session
string. Store it as TELEGRAM_SESSION in /home/nextstep.co.ke/.env on production.
"""

from __future__ import annotations

import os
import sys


def main() -> int:
    try:
        from telethon import TelegramClient
        from telethon.sessions import StringSession
    except Exception as exc:  # pragma: no cover
        print(f"Error: telethon is required ({exc})", file=sys.stderr)
        return 2

    api_id = int(os.getenv("TELEGRAM_API_ID") or "0")
    api_hash = str(os.getenv("TELEGRAM_API_HASH") or "").strip()
    if api_id <= 0 or not api_hash:
        print(
            "Missing TELEGRAM_API_ID / TELEGRAM_API_HASH in environment.",
            file=sys.stderr,
        )
        return 2

    with TelegramClient(StringSession(), api_id, api_hash) as client:
        # This will prompt for phone + code if not already authorized.
        client.start()
        session_str = client.session.save()

    print(session_str)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
