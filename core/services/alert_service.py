# -*- coding: utf-8 -*-

"""
Generic webhook alerting for CRITICAL-severity events that need a
human to notice them outside of console output/log files -- an
unprotected live position, a reconciliation gap between the exchange
and the local database, etc.

Configured via WEBHOOK_ALERT_URL (core/config/settings.py); empty/unset
disables alerting entirely, no-op. Deliberately fire-and-forget: every
call site here already logs locally (console_logger.log, CRITICAL)
before calling this, so a webhook delivery failure must never affect
the caller's own error handling -- it's a best-effort notification
layer on top of the log, not a replacement for it.
"""

from datetime import (
    datetime,
    timezone
)

import aiohttp

from core.config.settings import settings
from core.utils.console_logger import log


WEBHOOK_TIMEOUT_SECONDS = 5


async def send_alert(
    level: str,
    message: str,
    **context
) -> None:

    webhook_url = settings.WEBHOOK_ALERT_URL

    if not webhook_url:
        return

    payload = {

        "level": level,

        "message": message,

        "context": context,

        "timestamp": (
            datetime.now(timezone.utc)
            .isoformat()
        )
    }

    try:

        async with aiohttp.ClientSession() as session:

            async with session.post(

                webhook_url,

                json=payload,

                timeout=aiohttp.ClientTimeout(
                    total=WEBHOOK_TIMEOUT_SECONDS
                )

            ) as response:

                if response.status >= 400:

                    log(
                        "ALERT",
                        (
                            f"Webhook de alerta retornou status "
                            f"{response.status}"
                        ),
                        "WARNING"
                    )

    except Exception as error:

        # Deliberately broad -- network errors, DNS failures, bad
        # URLs, timeouts. The alert is best-effort; the caller's own
        # local log line (already emitted before this was called) is
        # the source of truth regardless of whether this succeeds.
        log(
            "ALERT",
            f"Falha ao enviar alerta via webhook: {error}",
            "WARNING"
        )
