"""Support for Pulsar meters."""

import logging
from typing import NamedTuple

import homeassistant.helpers.entity_registry as er

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceEntry
from homeassistant.helpers.typing import ConfigType

from .pulsar_manager import PulsarManager

from .const import (
    CONF_DEVICE_CONFIG,
    DATA_PULSAR,
    DATA_PULSAR_CONFIG,
    DOMAIN,
    PLATFORMS
)

UNSUB_LISTENER = "unsub_listener"


class HomeAssistantPulsarData(NamedTuple):
    """Pulsar data stored in the Home Assistant data object."""

    device_manager: PulsarManager


# Internal definitions
_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up Pulsar from config."""
    hass.data[DATA_PULSAR] = {}

    if DOMAIN in config:
        conf = config[DOMAIN]
        hass.data[DATA_PULSAR][DATA_PULSAR_CONFIG] = conf

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Pulsar."""

    device_manager = PulsarManager(hass, entry)

    hass.data[DOMAIN][entry.entry_id] = HomeAssistantPulsarData(
        device_manager=device_manager
    )

    devices = device_manager.get_devices(None)

    device_registry = dr.async_get(hass)
    for device_id in devices:
        device = devices[device_id]
        device_registry.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={(DOMAIN, device_id)},
            manufacturer="Pulsar",
            name=device.name,
            model=device._type
        )

    entry.async_on_unload(entry.add_update_listener(async_update_listener))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_update_listener(hass: HomeAssistant, config_entry: ConfigEntry):
    """Update listener."""
    await hass.config_entries.async_reload(config_entry.entry_id)


async def async_remove_config_entry_device(
    hass: HomeAssistant, config_entry: ConfigEntry, device_entry: DeviceEntry
) -> bool:
    """Remove a config entry from a device."""
    dev_id = list(device_entry.identifiers)[0][1]
    ent_reg = er.async_get(hass)
    entities = {
        ent.unique_id: ent.entity_id
        for ent in er.async_entries_for_config_entry(ent_reg, config_entry.entry_id)
        if dev_id in ent.unique_id
    }
    for entity_id in entities.values():
        ent_reg.async_remove(entity_id)

    if dev_id not in config_entry.data[CONF_DEVICE_CONFIG]:
        _LOGGER.info(
            "Device %s not found in config entry: finalizing device removal", dev_id
        )
        return True

    new_data = config_entry.data.copy()
    new_data[CONF_DEVICE_CONFIG].pop(dev_id)

    hass.config_entries.async_update_entry(
        config_entry,
        data=new_data,
    )

    _LOGGER.info("Device %s removed.", dev_id)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

        if not hass.config_entries.async_entries(DOMAIN):
            hass.data.pop(DOMAIN)

    return unload_ok
