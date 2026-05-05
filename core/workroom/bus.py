class WorkRoomBus:
    def __init__(self):
        self.subscribers = []

    def subscribe(self, agent):
        self.subscribers.append(agent)

    def publish(self, message):
        for agent in self.subscribers:
            agent.on_message(message)
