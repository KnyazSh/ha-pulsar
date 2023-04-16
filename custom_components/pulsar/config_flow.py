"""Config flow for Pulsar."""
from __future__ import annotations

import logging
import uuid
import datetime
from typing import Any

import serial.tools.list_ports
import voluptuous as vol

import homeassistant.helpers.config_validation as cv

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowHandler, FlowResult

from .connector import Connector

from .const import (
    CONF_DEVICE_CONFIG,
    CONF_DEVICE_OR_ADDRESS,
    CONF_MANUAL_PATH,
    CONF_NAME,
    CONF_SERIAL_ID,
    CONF_TYPE,
    DOMAIN,
    STEP_ADD_MENU,
    STEP_CHANGE_PORT,
    STEP_CHOOSE_SERIAL_PORT,
    STEP_COMPLETE,
    STEP_CONFIGURE_DEVICE,
    STEP_CONFIGURE_MENU,
    STEP_EDIT_DEVICE,
    STEP_MANUAL_PORT_CONFIG,
    PulsarType
)

_LOGGER = logging.getLogger(__name__)

DEVICE_CONFIG_SCHEMA_ENTRY = vol.Schema(
    {
        vol.Required(CONF_NAME): cv.string,
        vol.Required(CONF_SERIAL_ID): cv.positive_int,
        vol.Required(CONF_TYPE): vol.In([e.value for e in PulsarType])
    }
)

SELECTED_DEVICE = "selected_device"


def schema_defaults(schema, dps_list=None, **defaults):
    """Create a new schema with default values filled in."""
    copy = schema.extend({})
    for field, field_type in copy.schema.items():
        if isinstance(field_type, vol.In):
            value = None
            for dps in dps_list or []:
                if dps.startswith(f"{defaults.get(field)} "):
                    value = dps
                    break

            if value in field_type.container:
                field.default = vol.default_factory(value)
                continue

        if field.schema in defaults:
            field.default = vol.default_factory(defaults[field])
    return copy


class BaseFlow(FlowHandler):

    def __init__(self, config_entry: ConfigEntry | None = None) -> None:
        """Initialize flow instance."""
        super().__init__()
        self._config_entry = config_entry
        self._device_or_address: str | None = None
        self._device_data: dict[str, dict[str, Any]] = {}
        self.selected_device = None
        self.editing_device = False

    async def _async_create_or_update_entry(self) -> FlowResult:
        """Create a config entry with the current flow state."""
        assert self._title is not None
        assert self._device_or_address is not None
        assert len(self._device_data) > 0

        data = {
            CONF_DEVICE_OR_ADDRESS: self._device_or_address,
            CONF_DEVICE_CONFIG: self._device_data
        }

        if self._config_entry is not None:

            # Just for trigger async_update_listener
            options = {
                **self._config_entry.options,
                "CONF_UPD_DATE": datetime.datetime.now(),
            }

            self.hass.config_entries.async_update_entry(
                self._config_entry,
                data=data,
                options=options)

            return self.async_create_entry(
                title="",
                data={}
            )
        else:
            return self.async_create_entry(
                title="Pulsar",
                data=data
            )

    async def async_step_choose_serial_port(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Choose a serial port."""

        ports = await self.hass.async_add_executor_job(serial.tools.list_ports.comports)
        list_of_ports = [
            f"{p}, s/n: {p.serial_number or 'n/a'}"
            + (f" - {p.manufacturer}" if p.manufacturer else "")
            for p in ports
        ]

        if not list_of_ports:
            return await self.async_step_manual_port_config()

        list_of_ports.append(CONF_MANUAL_PATH)

        if user_input is not None:
            user_selection = user_input[CONF_DEVICE_OR_ADDRESS]

            if user_selection == CONF_MANUAL_PATH:
                return await self.async_step_manual_port_config()

            port = ports[list_of_ports.index(user_selection)]

            self._device_or_address = port.device

            self._title = (
                f"{port.description}, s/n: {port.serial_number or 'n/a'}"
                f" - {port.manufacturer}"
                if port.manufacturer
                else ""
            )

            return await self.async_step_configure_device()

        default_port = CONF_MANUAL_PATH

        schema = vol.Schema(
            {
                vol.Required(CONF_DEVICE_OR_ADDRESS, default=default_port): vol.In(
                    list_of_ports
                )
            }
        )

        return self.async_show_form(
            step_id=STEP_CHOOSE_SERIAL_PORT,
            data_schema=schema
        )

    async def async_step_manual_port_config(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Enter port settings."""
        errors = {}

        if user_input is not None:
            device_or_address = user_input[CONF_DEVICE_OR_ADDRESS]
            self._title = device_or_address
            self._device_or_address = device_or_address

            if Connector(device_or_address, "connector"):
                if len(self._device_data) > 0:
                    return await self.async_step_add_menu()
                else:
                    return await self.async_step_configure_device()

            errors["base"] = "cannot_connect"

        if user_input is None:
            user_input = {}

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_DEVICE_OR_ADDRESS, vol.UNDEFINED
                ): str
            }
        )

        return self.async_show_form(
            step_id=STEP_MANUAL_PORT_CONFIG,
            data_schema=schema,
            errors=errors,
        )

    async def async_step_configure_device(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Add or edit device."""
        errors = {}

        dev_name = self.selected_device
        edit_dev_conf_id: str | None = None

        if user_input is not None:

            device_conf = {
                CONF_NAME: user_input[CONF_NAME],
                CONF_SERIAL_ID: user_input[CONF_SERIAL_ID],
                CONF_TYPE: user_input[CONF_TYPE]
            }

            if self.editing_device:

                for dev_conf_id in self._device_data:
                    dev_conf = self._device_data[dev_conf_id]
                    if dev_conf[CONF_NAME] == dev_name:
                        edit_dev_conf_id = dev_conf_id

                prev_dev_data = self._device_data[edit_dev_conf_id]

                for dev_conf_id in self._device_data:

                    dev_conf = self._device_data[dev_conf_id]

                    if prev_dev_data[CONF_SERIAL_ID] != dev_conf[CONF_SERIAL_ID] \
                            and dev_conf[CONF_SERIAL_ID] == device_conf[CONF_SERIAL_ID]:
                        return self.async_abort(
                            reason="address_already_configured"
                        )

                    if prev_dev_data[CONF_NAME] != dev_conf[CONF_NAME] \
                            and dev_conf[CONF_NAME] == device_conf[CONF_NAME]:
                        return self.async_abort(
                            reason="name_already_exists"
                        )

                self._device_data[edit_dev_conf_id] = device_conf

                self.editing_device = False
                self.selected_device = None

            else:

                for dev_conf_id in self._device_data:

                    dev_conf = self._device_data[dev_conf_id]

                    if dev_conf[CONF_SERIAL_ID] == device_conf[CONF_SERIAL_ID]:
                        return self.async_abort(
                            reason="address_already_configured"
                        )

                    if dev_conf[CONF_NAME] == device_conf[CONF_NAME]:
                        return self.async_abort(
                            reason="name_already_exists"
                        )

                new_dev_conf_id = uuid.uuid4().hex
                self._device_data[new_dev_conf_id] = device_conf

            return await self.async_step_add_menu()

        if user_input is None:
            user_input = {}

        types = [e.value for e in PulsarType]

        base_defaults = {}
        base_defaults[CONF_NAME] = ""
        base_defaults[CONF_SERIAL_ID] = ""
        base_defaults[CONF_TYPE] = types[0]

        defaults = {}

        if self.editing_device and dev_name is not None:
            for dev_conf_id in self._device_data:
                dev_conf = self._device_data[dev_conf_id]
                if dev_conf[CONF_NAME] == dev_name:
                    edit_dev_conf_id = dev_conf_id

            # If selected device exists as a config entry, load config from it
            if (edit_dev_conf_id is not None):
                defaults = self._device_data[edit_dev_conf_id].copy()
            else:
                defaults = base_defaults
            placeholders = {"for_device": f" for device `{dev_name}`"}
        else:
            defaults = base_defaults
            placeholders = {"for_device": ""}

        schema = schema_defaults(DEVICE_CONFIG_SCHEMA_ENTRY, **defaults)

        return self.async_show_form(
            step_id=STEP_CONFIGURE_DEVICE,
            data_schema=schema,
            errors=errors,
            description_placeholders=placeholders
        )

    async def async_step_complete(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Complete"""

        return await self._async_create_or_update_entry()

    async def async_step_add_menu(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Add device."""
        options = [STEP_CONFIGURE_DEVICE, STEP_COMPLETE]

        return self.async_show_menu(
            step_id=STEP_ADD_MENU,
            menu_options=options
        )


class ConfigFlow(BaseFlow, config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Pulsar."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlowHandler:
        """Return the options flow."""
        return OptionsFlowHandler(config_entry)

    def __init__(self):
        """Initialize the config flow."""
        super().__init__()

    async def async_step_user(self, user_input=None) -> FlowResult:
        """Handle the initial step."""
        return await self.async_step_choose_serial_port()


class OptionsFlowHandler(BaseFlow, config_entries.OptionsFlow):
    """Handle a option flow for Pulsar."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize the option flow."""
        super().__init__(config_entry)
        self._config_entry = config_entry
        self._device_or_address = self._config_entry.data[CONF_DEVICE_OR_ADDRESS]
        self._device_data: dict = self._config_entry.data[CONF_DEVICE_CONFIG]
        self._title = config_entry.title
        self.device_data = None
        self.selected_device = None
        self.editing_device = False

    async def async_step_init(
            self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle the initial step."""

        return await self.async_step_configure_menu()

    async def async_step_configure_menu(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        options = [STEP_CONFIGURE_DEVICE, STEP_EDIT_DEVICE,
                   STEP_CHANGE_PORT]

        return self.async_show_menu(
            step_id=STEP_CONFIGURE_MENU,
            menu_options=options
        )

    async def async_step_change_port(self, user_input=None) -> FlowResult:
        """Handle change port"""
        return await self.async_step_choose_serial_port()

    async def async_step_edit_device(self, user_input=None) -> FlowResult:
        """Handle editing a device."""
        errors = {}

        self.editing_device = True

        if user_input is not None:
            self.selected_device = user_input[SELECTED_DEVICE]

            return await self.async_step_configure_device()

        devices = [self._device_data[dev_id][CONF_NAME]
                   for dev_id in self._device_data]

        devices_schema = vol.Schema(
            {vol.Required(SELECTED_DEVICE): vol.In(devices)})

        return self.async_show_form(
            step_id=STEP_EDIT_DEVICE,
            data_schema=devices_schema,
            errors=errors
        )
