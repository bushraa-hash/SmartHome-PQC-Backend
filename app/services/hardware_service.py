
from app.hardware.hardware_factory import (
    gpio_controller,
    sensor_controller,
)


def turn_device_on(pin: int):
    return gpio_controller.turn_on(pin)


def turn_device_off(pin: int):
    return gpio_controller.turn_off(pin)


def get_device_state(pin: int):
    return gpio_controller.get_state(pin)


def read_temperature_and_humidity():
    return sensor_controller.read_dht22()


def read_motion():
    return sensor_controller.read_pir()
