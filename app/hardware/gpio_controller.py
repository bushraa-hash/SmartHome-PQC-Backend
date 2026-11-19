
class MockGPIOController:
    """
    Simulated GPIO controller for Windows development.
    This does not control real hardware.
    """

    def __init__(self):
        self.device_states = {
            17: False,
            22: False,
        }

    def turn_on(self, pin: int):
        if pin not in self.device_states:
            raise ValueError("Unsupported GPIO output pin")

        self.device_states[pin] = True

        return {
            "pin": pin,
            "state": "ON",
        }

    def turn_off(self, pin: int):
        if pin not in self.device_states:
            raise ValueError("Unsupported GPIO output pin")

        self.device_states[pin] = False

        return {
            "pin": pin,
            "state": "OFF",
        }

    def get_state(self, pin: int):
        if pin not in self.device_states:
            raise ValueError("Unsupported GPIO output pin")

        return self.device_states[pin]

    def cleanup(self):
        self.device_states = {
            17: False,
            22: False,
        }
