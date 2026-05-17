# -*- coding: utf-8 -*-

import inspect

from core.utils.console_logger import (
    log
)


class EventBus:

    def __init__(self):

        self.subscribers = []

    # =====================================================
    # SUBSCRIBE
    # =====================================================

    def subscribe(
        self,
        subscriber
    ):

        # =================================================
        # SAFETY
        # =================================================

        if subscriber in self.subscribers:

            return

        if not hasattr(
            subscriber,
            "on_message"
        ):

            return

        self.subscribers.append(
            subscriber
        )

    # =====================================================
    # PUBLISH
    # =====================================================

    async def publish(
        self,
        message
    ):

        for subscriber in list(
            self.subscribers
        ):

            try:

                result = (
                    subscriber.on_message(
                        message
                    )
                )

                # =============================================
                # ASYNC SUPPORT
                # =============================================

                if inspect.isawaitable(
                    result
                ):

                    await result

            # =================================================
            # ISOLATED FAILURE
            # =================================================

            except Exception as error:

                log(
                    "EVENTBUS",
                    (
                        f"FAILED "
                        f"{subscriber.__class__.__name__}"
                    ),
                    "ERROR"
                )

                log(
                    "EVENTBUS",
                    str(error),
                    "ERROR"
                )