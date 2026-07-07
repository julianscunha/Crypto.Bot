# -*- coding: utf-8 -*-

import inspect

from collections import (
    defaultdict
)

from core.utils.console_logger import (
    log
)

# =====================================================
# EVENT BUS
# =====================================================

class EventBus:

    def __init__(
        self
    ):

        # =================================================
        # SUBSCRIBERS
        # =================================================

        self.subscribers = []

        # =================================================
        # TELEMETRY
        # =================================================

        self.total_published_messages = 0

        self.total_failed_deliveries = 0

        self.total_successful_deliveries = 0

        self.delivery_failures = (
            defaultdict(int)
        )

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

            log(
                "EVENTBUS",
                (
                    "INVALID_SUBSCRIBER "
                    f"{subscriber.__class__.__name__}"
                ),
                "WARNING"
            )

            return

        self.subscribers.append(
            subscriber
        )

        log(
            "EVENTBUS",
            (
                "SUBSCRIBED "
                f"{subscriber.__class__.__name__}"
            ),
            "INFO"
        )

    # =====================================================
    # UNSUBSCRIBE
    # =====================================================

    def unsubscribe(
        self,
        subscriber
    ):

        if subscriber not in self.subscribers:

            return

        self.subscribers.remove(
            subscriber
        )

        log(
            "EVENTBUS",
            (
                "UNSUBSCRIBED "
                f"{subscriber.__class__.__name__}"
            ),
            "INFO"
        )

    # =====================================================
    # PUBLISH
    # =====================================================

    async def publish(
        self,
        message
    ):

        self.total_published_messages += 1

        message_name = (
            message.__class__.__name__
        )

        # =================================================
        # DELIVERY
        # =================================================

        for subscriber in list(
            self.subscribers
        ):

            subscriber_name = (
                subscriber.__class__.__name__
            )

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

                self.total_successful_deliveries += 1

            # =================================================
            # ISOLATED FAILURE
            # =================================================

            except Exception as error:

                self.total_failed_deliveries += 1

                self.delivery_failures[
                    subscriber_name
                ] += 1

                log(
                    "EVENTBUS",
                    (
                        f"DELIVERY_FAILED "
                        f"message={message_name} "
                        f"subscriber={subscriber_name}"
                    ),
                    "ERROR"
                )

                log(
                    "EVENTBUS",
                    str(error),
                    "ERROR"
                )

    # =====================================================
    # TELEMETRY
    # =====================================================

    def get_telemetry(
        self
    ):

        return {

            "subscribers":

                [

                    subscriber.__class__.__name__

                    for subscriber in self.subscribers
                ],

            "total_subscribers":
                len(self.subscribers),

            "total_published_messages":
                self.total_published_messages,

            "total_successful_deliveries":
                self.total_successful_deliveries,

            "total_failed_deliveries":
                self.total_failed_deliveries,

            "delivery_failures":
                dict(self.delivery_failures)
        }

    # =====================================================
    # RESET TELEMETRY
    # =====================================================

    def reset_telemetry(
        self
    ):

        self.total_published_messages = 0

        self.total_successful_deliveries = 0

        self.total_failed_deliveries = 0

        self.delivery_failures.clear()


event_bus = (
    EventBus()
)
