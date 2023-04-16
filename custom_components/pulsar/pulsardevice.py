"""Represent Pulsar device"""
from __future__ import annotations

import struct
from .connector import Connector


class PulsarDevice(object):

    ADDR_SIZE = 4
    FUNC_SIZE = 1
    LEN_SIZE = 1
    ID_SIZE = 2
    CRC_SIZE = 2
    SERVICE_SIZE = ADDR_SIZE + FUNC_SIZE + LEN_SIZE + ID_SIZE + CRC_SIZE

    def __init__(self, connector: Connector, type: str, name: str, addr: int) -> None:
        self._connector = connector
        self._type = type
        self._name = name
        self._addr = addr
        self._request_id = 0

    def calculate_crc16(self, buf: bytearray, size: int, offset: int) -> int:
        """CRC-16-ModBus Algorithm"""
        poly = 0xA001
        crc = 0xFFFF
        for i in range(size):
            crc ^= (0xFF & buf[i + offset])
            for _ in range(0, 8):
                if (crc & 0x0001):
                    crc = ((crc >> 1) & 0xFFFF) ^ poly
                else:
                    crc = ((crc >> 1) & 0xFFFF)
        return crc

    def write_bcd(self, val: int, buf: bytearray, size: int, offset: int, big_endian: bool) -> bytearray:
        for i in range(size):
            byte = int(val % 10)
            val /= 10
            byte |= int(val % 10) << 4
            val /= 10
            buf[size - i - 1 + offset if big_endian else i + offset] = byte
        return buf

    def write_hex(self, val: int, buf: bytearray, size: int, offset: int, big_endian: bool) -> bytearray:
        for i in range(size):
            buf[size - i - 1 + offset if big_endian else i + offset] = val & 0xFF
            val >>= 8
        return buf

    def read_bcd(self, buf: bytearray, size: int, offset: int, big_endian: bool) -> int:
        res = 0
        for i in range(size):
            res *= 100
            bcd_byte = buf[i + offset if big_endian else size - i - 1 + offset]
            dec_byte = (bcd_byte & 0x0F) + 10 * ((bcd_byte >> 4) & 0x0F)
            res += dec_byte
        return res

    def read_int_from_hex(self, buf: bytearray, size: int, offset: int, big_endian: bool) -> int:
        res = 0
        for i in range(size):
            res <<= 8
            res |= buf[i + offset if big_endian else size - i - 1 + offset]
        return res

    def read_float_from_hex(self, buf: bytearray, size: int, offset: int, big_endian: bool) -> float:
        if big_endian:
            format = '>'
        else:
            format = '<'

        if size == 4:
            format += 'f'
        elif size == 8:
            format += 'd'
        elif size == 2:
            format += 'e'
        else:
            raise Exception("unreachable size")

        val = struct.unpack(format, buf[offset:size + offset])

        if len(val) == 1:
            return val[0]
        elif len(val) == 0:
            return None
        else:
            return val

    def send_request(self, message: bytes, response_size: int) -> bytes:
        addr = self.read_bcd(message, self.ADDR_SIZE, 0, True)
        request_id = self.read_int_from_hex(message, self.ID_SIZE, len(
            message) - self.ID_SIZE - self.CRC_SIZE, False)
        expected_response_size = response_size

        response = self._connector.send(message, response_size)

        self.check_response(response, expected_response_size, addr, request_id)

        return response

    def send_payload(self, payload: bytes, function: bytes, addr: int, request_id: int, expected_payload_size: int) -> bytes:
        request = self.prepare_request(payload, function, addr, request_id)
        response = self.send_request(
            request, expected_payload_size + self.SERVICE_SIZE)
        start_ind = self.ADDR_SIZE + self.FUNC_SIZE + self.LEN_SIZE
        end_ind = 0 - self.ID_SIZE - self.CRC_SIZE
        return response[start_ind:end_ind]

    def check_response(self, response: bytes, expected_response_size: int, addr: int, request_id: int) -> bool:

        response_size = len(response)

        if response_size < self.SERVICE_SIZE:
            raise Exception("frame is too short")

        if response_size != expected_response_size:
            raise Exception("unexpected end of frame")

        if expected_response_size != response[5]:
            raise Exception("unexpected frame length")

        # check crc16
        response_crc = self.read_int_from_hex(
            response, self.CRC_SIZE, response_size - self.CRC_SIZE, False)
        calc_response_crc = self.calculate_crc16(
            response, response_size - self.CRC_SIZE, 0)
        if response_crc != calc_response_crc:
            raise Exception("CRC mismatch")

        # check address
        response_addr = self.read_bcd(response, self.ADDR_SIZE, 0, True)
        if response_addr != addr:
            raise Exception("address mismatch")

        # check request id
        response_request_id = self.read_int_from_hex(
            response, self.ID_SIZE, response_size - self.ID_SIZE - self.CRC_SIZE, False)
        if response_request_id != request_id:
            raise Exception("request ID mismatch")

        return True

    def prepare_request(self, payload: bytes, function: bytes, addr: int, request_id: int) -> bytes:

        if len(function) != 1:
            raise Exception("wrong function param")

        payload_size = len(payload)
        request_size = payload_size + self.SERVICE_SIZE

        request = bytearray(request_size)

        request = self.write_bcd(addr, request, 4, 0, True)

        # function and size
        request[4] = function[0]
        request[5] = request_size

        # payload
        offset = self.ADDR_SIZE + self.FUNC_SIZE + self.LEN_SIZE
        request[offset:offset+payload_size] = payload

        # request ID
        request = self.write_hex(
            request_id, request, 2, request_size - 4, False)

        # CRC16
        crc = self.calculate_crc16(request, request_size - 2, 0)
        request = self.write_hex(crc, request, 2, request_size - 2, False)

        return request

    @property
    def name(self) -> str:
        return self._name

    @property
    def type(self) -> str:
        return self._type

    def next_request_id(self) -> int:
        self._request_id = + 1
        if self._request_id > 65535:
            self._request_id = 0
        return self._request_id

    def getdata(self, key: str):
        return None
