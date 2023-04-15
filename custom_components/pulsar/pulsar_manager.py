"""Represent manager of devices"""

from typing import Any, List

from .const import (
    CONF_DEVICE_CONFIG,
    CONF_DEVICE_OR_ADDRESS,
    CONF_NAME,
    CONF_SERIAL_ID,
    CONF_TYPE
)

from .pulsar_m_water import PulsarM

from .connector import Connector
from .pulsardevice import PulsarDevice

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant


class PulsarManager():

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        self._hass = hass
        self.config_entry = config_entry
        self._devices: dict[str, dict[str, Any]] = {}

        device_or_ipaddress: str = config_entry.data[CONF_DEVICE_OR_ADDRESS]

        self._connector = Connector(device_or_ipaddress, "connector")

        device_confs: dict[str, dict[str, Any]
                           ] = config_entry.data[CONF_DEVICE_CONFIG]

        for dev_id in device_confs:
            device_conf = device_confs[dev_id]
            device_type = device_conf[CONF_TYPE]
            if device_type == "pulsar-m-water":
                device = PulsarM(
                    self._connector, device_conf[CONF_NAME], device_conf[CONF_SERIAL_ID])
                self.add_device(dev_id, device)

    def get_device(self, device_id: str) -> PulsarDevice:
        device = self._devices.get(device_id, None)
        return device

    def get_devices(self, device_ids: List[str] | None) -> dict[str, PulsarDevice]:
        if device_ids is None:
            return self._devices
        return self._devices.fromkeys(device_ids)

    def add_device(self, dev_id: str, device: PulsarDevice) -> None:
        if dev_id in self._devices:
            raise Exception("device already exist")

        self._devices[dev_id] = device

    def remove_device(self, device_id: str) -> None:
        if device_id not in self._devices:
            raise Exception("device does not exist")

        self._devices.pop(device_id)
