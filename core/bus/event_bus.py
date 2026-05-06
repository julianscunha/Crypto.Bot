# -*- coding: utf-8 -*-

import inspect


class EventBus:

    def __init__(self):

        self.subscribers = []

    def subscribe(self, subscriber):

        self.subscribers.append(subscriber)

    async def publish(self, message):

        for subscriber in self.subscribers:

            if not hasattr(subscriber, "on_message"):
                continue

            try:

                result = subscriber.on_message(message)

                if inspect.isawaitable(result):
                    await result

            except Exception as e:

                print(
                    f"[BUS ERROR] "
                    f"{subscriber.__class__.__name__}: {e}"
                )