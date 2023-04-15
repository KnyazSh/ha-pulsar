"""Support for Pulsar devices."""
from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    UnitOfTemperature,
    UnitOfVolume,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType

from . import HomeAssistantPulsarData

from .const import (
    DATA_KEY_CURRENT_WATER_CONSUMPTION_CH1,
    DATA_KEY_SYSTEM_TIME,
    DATA_KEY_DEVICE_TEMPERATURE,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    PULSAR_DISCOVERY_NEW
)

from .pulsardevice import PulsarDevice

from .entity import BasePulsarEntity

SCAN_INTERVAL = DEFAULT_SCAN_INTERVAL


@dataclass
class PulsarSensorEntityDescription(SensorEntityDescription):
    """Describes Pulsar sensor entity."""

    subkey: str | None = None


SENSORS: dict[str, tuple[PulsarSensorEntityDescription, ...]] = {
    "pulsar-m-water": (
        PulsarSensorEntityDescription(
            key=DATA_KEY_CURRENT_WATER_CONSUMPTION_CH1,
            name="Current water consumption",
            translation_key=DATA_KEY_CURRENT_WATER_CONSUMPTION_CH1,
            device_class=SensorDeviceClass.WATER,
            state_class=SensorStateClass.TOTAL_INCREASING,
            native_unit_of_measurement=UnitOfVolume.LITERS,
            has_entity_name=True
        ),
        PulsarSensorEntityDescription(
            key=DATA_KEY_SYSTEM_TIME,
            name="System time",
            translation_key=DATA_KEY_SYSTEM_TIME,
            has_entity_name=True
        ),
        PulsarSensorEntityDescription(
            key=DATA_KEY_DEVICE_TEMPERATURE,
            name="Temperature of meter",
            translation_key=DATA_KEY_DEVICE_TEMPERATURE,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            has_entity_name=True
        )
    )
}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Pulsar sensor dynamically"""
    hass_data: HomeAssistantPulsarData = hass.data[DOMAIN][entry.entry_id]

    @callback
    def async_discover_device(device_ids: list[int]) -> None:
        """Discover and add a discovered Pulsar sensor."""
        entities: list[PulsarSensorEntity] = []
        for device_id in device_ids:
            device = hass_data.device_manager.get_device(device_id)
            if descriptions := SENSORS.get(device._type):
                for description in descriptions:
                    entities.append(
                        PulsarSensorEntity(
                            device_id,
                            device,
                            description
                        )
                    )

        async_add_entities(entities)

    async_discover_device([*hass_data.device_manager._devices])

    entry.async_on_unload(
        async_dispatcher_connect(
            hass, PULSAR_DISCOVERY_NEW, async_discover_device)
    )


class PulsarSensorEntity(BasePulsarEntity, SensorEntity):
    """Pulsar Sensor Entity."""

    def __init__(
            self,
            unique_id: str,
            pulsar_device: PulsarDevice,
            description: PulsarSensorEntityDescription) -> None:
        super().__init__(unique_id, pulsar_device)

        self.entity_description = description
        internal_unique_id = (
            f"{super().unique_id}.{description.key}"
        )
        self._attr_unique_id = internal_unique_id
        self.entity_id = internal_unique_id

    @property
    def native_value(self) -> StateType:
        """Return the value reported by the sensor."""

        # Raw value
        value = self._pulsar_device.getdata(self.entity_description.key)
        if value is None:
            return None

        return value
