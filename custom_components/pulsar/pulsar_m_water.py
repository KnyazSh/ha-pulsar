"""Represent Pulsar Water M"""
from __future__ import annotations

import datetime
from typing import Any
from typing_extensions import override

from .connector import Connector
from .pulsardevice import PulsarDevice

from .const import (
    DATA_KEY_BATTERY_VOLTAGE,
    DATA_KEY_CURRENT_WATER_CONSUMPTION_CH1,
    DATA_KEY_SYSTEM_TIME,
    DATA_KEY_DEVICE_TEMPERATURE,
    PulsarType
)


class PulsarM(PulsarDevice):

    FUNCTION_READ_CURRENT_WATER_CONSUMPTION_READING = b'\x01'
    FUNCTION_READ_ARCHIVE = b'\x06'
    FUNCTION_READ_SYSTEM_TIME = b'\x04'
    FUNCTION_WRITE_SYSTEM_TIME = b'\x05'
    FUNCTION_READ_PARAMETERS = b'\x0A'
    FUNCTION_WRITE_PARAMETERS = b'\x0B'

    def __init__(self, connector: Connector, name: str, addr: int) -> None:
        super().__init__(connector, PulsarType.pulsar_m_water.value, name, addr)

    def read_current_water_consumption_reading(self) -> int:
        payload_size = 4
        response_payload_size = 4

        mask_ch = 1
        payload = bytearray(payload_size)
        payload = self.write_hex(mask_ch, payload, payload_size, 0, False)
        response_payload = self.send_payload(
            payload,
            self.FUNCTION_READ_CURRENT_WATER_CONSUMPTION_READING,
            self._addr,
            self.next_request_id(),
            response_payload_size)

        result = self.read_int_from_hex(
            response_payload, payload_size, 0, False)
        return result

    def read_sys_time(self) -> datetime:
        payload_size = 0
        response_payload_size = 6
        payload = bytes(payload_size)

        response_payload = self.send_payload(
            payload,
            self.FUNCTION_READ_SYSTEM_TIME,
            self._addr,
            self.next_request_id(),
            response_payload_size)

        year_byte = response_payload[0]
        month_byte = response_payload[1]
        day_byte = response_payload[2]
        hour_byte = response_payload[3]
        minute_byte = response_payload[4]
        seconds_byte = response_payload[5]

        result = datetime.datetime(
            2000 + year_byte,
            month_byte,
            day_byte,
            hour_byte,
            minute_byte,
            seconds_byte)

        return result

    def read_diag_params(self):
        payload_size = 2
        response_payload_size = 8

        param_code = 6
        payload = bytearray(payload_size)
        payload = self.write_hex(param_code, payload, payload_size, 0, False)
        response_payload = self.send_payload(
            payload,
            self.FUNCTION_READ_PARAMETERS,
            self._addr,
            self.next_request_id(),
            response_payload_size)

        param_val = bin(response_payload[0])

        return param_val

    def read_batt_voltage(self) -> float:
        payload_size = 2
        response_payload_size = 8

        param_code = 10  # \x000A
        payload = bytearray(payload_size)
        payload = self.write_hex(param_code, payload, payload_size, 0, False)
        response_payload = self.send_payload(
            payload,
            self.FUNCTION_READ_PARAMETERS,
            self._addr,
            self.next_request_id(),
            response_payload_size)

        param_val = self.read_float_from_hex(response_payload, 4, 0, False)
        return param_val

    def read_temp(self) -> float:
        payload_size = 2
        response_payload_size = 8

        param_code = 11  # \x000B
        payload = bytearray(payload_size)
        payload = self.write_hex(param_code, payload, payload_size, 0, False)
        response_payload = self.send_payload(
            payload,
            self.FUNCTION_READ_PARAMETERS,
            self._addr,
            self.next_request_id(),
            response_payload_size)

        param_val = self.read_float_from_hex(response_payload, 4, 0, False)
        return param_val

    def read_daylight_saving_time(self) -> bool:
        """Read the sign of automatic transition to daylight saving time"""
        payload_size = 2
        response_payload_size = 8

        param_code = 1  # \x0001
        payload = bytearray(payload_size)
        payload = self.write_hex(param_code, payload, payload_size, 0, False)
        response_payload = self.send_payload(
            payload,
            self.FUNCTION_READ_PARAMETERS,
            self._addr,
            self.next_request_id(),
            response_payload_size)

        param_val = bool(response_payload[0])
        return param_val

    @override
    def getdata(self, key: str) -> Any:

        if key == DATA_KEY_CURRENT_WATER_CONSUMPTION_CH1:
            return self.read_current_water_consumption_reading()
        elif key == DATA_KEY_SYSTEM_TIME:
            return self.read_sys_time()
        elif key == DATA_KEY_DEVICE_TEMPERATURE:
            return self.read_temp()
        elif key == DATA_KEY_BATTERY_VOLTAGE:
            return self.read_batt_voltage()

        return None
