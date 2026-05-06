# -*- coding: utf-8 -*-

class EventBus:

    def __init__(self):
        self.subscribers = []

    def subscribe(self, agent):
        self.subscribers.append(agent)

    def publish(self, message):

        for subscriber in self.subscribers:

            try:
                subscriber.on_message(message)

            except Exception as e:
                print(f"[BUS ERROR] {subscriber.__class__.__name__}: {e}")