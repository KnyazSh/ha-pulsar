from datetime import timedelta
import enum

from homeassistant.const import (
    Platform
)

DOMAIN = "pulsar"

DATA_PULSAR = "pulsar"
DATA_PULSAR_CONFIG = "pulsar_device_config"
DATA_PULSAR_MANAGER = "pulsar_manager"

CONF_ACTION = "action"
CONF_ADD_DEVICE = "add_device"
CONF_CHANGE_PORT = "change_port"
CONF_EDIT_DEVICE = "edit_device"
CONF_ENTITIES = "entities"
CONF_CONNECTOR = "connector"
CONF_DEVICE_CONFIG = "device_config"
CONF_DEVICE = "device"
CONF_DEVICE_OR_ADDRESS = "device_or_address"
CONF_ID = "id"
CONF_MANUAL_PATH = "Enter Manually"
CONF_NAME = "name"
CONF_SERIAL_ID = "serial_id"
CONF_TYPE = "type"

STEP_ADD_DEVICE = "add_device"
STEP_CONFIGURE_DEVICE = "configure_device"
STEP_COMPLETE = "complete"

PULSAR_DISCOVERY_NEW = "pulsar_discovery_new"

DEFAULT_SCAN_INTERVAL = timedelta(seconds=60)

DATA_KEY_CURRENT_WATER_CONSUMPTION_CH1 = "current_water_consumption_ch1"
DATA_KEY_SYSTEM_TIME = "system_time"
DATA_KEY_DEVICE_TEMPERATURE = "device_temperature"
DATA_KEY_BATTERY_VOLTAGE = "battery_voltage"

PLATFORMS = [
    # Platform.ALARM_CONTROL_PANEL,
    # Platform.BINARY_SENSOR,
    # Platform.BUTTON,
    # Platform.CAMERA,
    # Platform.CLIMATE,
    # Platform.COVER,
    # Platform.FAN,
    # Platform.HUMIDIFIER,
    # Platform.LIGHT,
    # Platform.NUMBER,
    # Platform.SCENE,
    # Platform.SELECT,
    Platform.SENSOR,
    # Platform.SIREN,
    # Platform.SWITCH,
    # Platform.VACUUM,
]


class PulsarType(enum.Enum):
    """Possible options for device type"""

    pulsar_m_water = "pulsar-m-water"
