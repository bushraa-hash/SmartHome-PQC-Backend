
class MockSensorController:
    """
    Simulated sensor controller for Windows development.
    """

    def read_dht22(self):
        return {
            "temperature": 25.0,
            "humidity": 50.0,
        }

    def read_pir(self):
        return {
            "motion": False,
        }
