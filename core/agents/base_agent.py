class BaseAgent:
    def __init__(self, name, bus):
        self.name = name
        self.bus = bus
        self.bus.subscribe(self)

    def publish(self, message):
        self.bus.publish(message)

    def on_message(self, message):
        raise NotImplementedError
