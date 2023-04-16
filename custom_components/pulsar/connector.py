"""For communicate with devices with serial connection"""
from __future__ import annotations

import logging
import serial
import time


DEFAULT_BAUDRATE = 9600
DEFAULT_BYTESIZE = serial.EIGHTBITS
DEFAULT_PARITY = serial.PARITY_NONE
DEFAULT_STOPBITS = serial.STOPBITS_ONE

logging.basicConfig(level=logging.ERROR)
_LOGGER = logging.getLogger(__name__)


class Connector(object):
    """Represent connector"""

    def __init__(self, device_or_ipaddress, name: str):
        # device_or_ipaddress in the form
        #  127.0.0.1:1024
        # or
        #  /dev/ttyUSB0
        self._device_or_ipaddress = device_or_ipaddress
        self._name = name
        self._serport = None
        self._init_serial()
        self._busy = False

    def _init_serial(self):
        """
        Initialises the serial port (or tcp connection) and tries to open it
        Returns True if successful
        """
        try:
            if self._serport is not None and self._serport.is_open:
                self._serport.close()
                self._serport = None

            if self._device_or_ipaddress.startswith("/") or self._device_or_ipaddress.startswith("C"):
                # assume direct serial
                self._serport = serial.Serial(self._device_or_ipaddress)
            else:
                # assume serial over IP via socket
                self._serport = serial.serial_for_url(
                    f"socket://{self._device_or_ipaddress}")
            # Ensures that the serial port has not
            # been left hanging around by a previous process.

            if self._serport.is_open:
                self._serport.close()
            self._serport.baudrate = DEFAULT_BAUDRATE
            self._serport.bytesize = DEFAULT_BYTESIZE
            self._serport.parity = DEFAULT_PARITY
            self._serport.stopbits = DEFAULT_STOPBITS
            self._serport.timeout = 3
            self._serport.open()
            _LOGGER.info(f"Serial device {self._device_or_ipaddress} opened")
            return True

        except serial.SerialException as se:
            _LOGGER.error(
                f"Unable to initialise serial port on {self._device_or_ipaddress}, error {se}")
            self._serport = None
            return False

    def send(self, message: bytes, response_size: int):
        """
        Sends a message to the device
        Attempts to reopen the serial port if it is not open
        If there are any errors or no reply an empty list is returned
        Returns the response as a List, empty list if no response or False if error
        """

        if self._serport is None:
            if not self._init_serial():
                raise Exception("port cannot init")

        if self._serport is not None:
            # port successfully opened
            if self._serport.is_open:
                # All should be good to communicate via the serial port
                try:
                    sleep_count = 0
                    while self._busy:
                        _LOGGER.debug(f"Sleeping {sleep_count}...")
                        time.sleep(0.5)
                        sleep_count += 1
                    _LOGGER.debug(f"Sending {message}")
                    serial_message = bytes(message)
                    self._busy = True
                    self._serport.write(serial_message)  # Write a string

                except serial.SerialTimeoutException:
                    _LOGGER.error(
                        f"Timeout writing to {self._device_or_ipaddress}")
                    self._busy = False
                    return datalist

                except serial.SerialException as se:
                    _LOGGER.error(
                        f"Error writing to {self._device_or_ipaddress}: {se}")
                    self._serport.close()
                    self._serport = None
                    self._busy = False
                    return datalist

                # write went well so
                # now wait for reply
                try:
                    _LOGGER.debug(
                        f"Reading serial port {self._device_or_ipaddress}")
                    byteread = self._serport.read(response_size)
                    datalist = byteread

                except serial.SerialException as se:
                    _LOGGER.error(
                        f"Unable to read serial port {self._device_or_ipaddress}: {se}")
                    self._serport.close()
                    self._serport = None
                self._busy = False
            else:
                _LOGGER.debug(
                    f"Serial port {self._device_or_ipaddress} has been created but is not open, resetting...")
                self._serport = None

        if len(datalist) < 1:
            _LOGGER.debug(f"No response from {self._device_or_ipaddress}")
        else:
            _LOGGER.debug(
                f"Received from {self._device_or_ipaddress}: {datalist}")
        return datalist

    def name(self) -> str:
        """Returns the name of serial device"""
        return self._name

    def disconnect(self):
        """disconnects from the serial port or tcp connection"""
        if self._serport is not None and self._serport.is_open:
            self._serport.close()
            self._serport = None
            _LOGGER.info(f"Closed serial port {self._device_or_ipaddress}")

    def __del__(self):
        """Destructor"""
        self.disconnect()
