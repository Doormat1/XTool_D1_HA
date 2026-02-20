"""Constants for the xTool Laser integration."""

DOMAIN = "xtool_laser"
DEFAULT_NAME = "xTool Laser"
DEFAULT_PORT = 8080
DEFAULT_WS_PORT = 8081
DEFAULT_SCAN_INTERVAL = 3
DEFAULT_DISCOVERY_TIMEOUT = 3

CONF_SCAN_INTERVAL = "scan_interval"
CONF_USE_WEBSOCKET = "use_websocket"

ATTR_ENTRY_ID = "entry_id"

SERVICE_PAUSE_JOB = "pause_job"
SERVICE_RESUME_JOB = "resume_job"
SERVICE_STOP_JOB = "stop_job"

ATTR_WORKING_MS = "working"
ATTR_PROGRESS = "progress"
ATTR_LINE = "line"
ATTR_WORKING_STATE = "working_state"
ATTR_MACHINE_TYPE = "machine_type"
ATTR_PERIPHERAL_STATUS = "peripheral_status"
ATTR_WS_STATE = "ws_state"
