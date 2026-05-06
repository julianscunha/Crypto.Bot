import asyncio
import inspect


class EventBus:

    def __init__(self):
        self.subscribers = []

    def subscribe(self, subscriber):
        self.subscribers.append(subscriber)

    async def publish(self, message):

        for subscriber in self.subscribers:

            try:

                if inspect.iscoroutinefunction(
                    subscriber.on_message
                ):
                    await subscriber.on_message(message)

                else:
                    subscriber.on_message(message)

            except Exception as e:
                print(
                    f"[BUS ERROR] "
                    f"{subscriber.__class__.__name__}: {e}"
                )