"""ESP32 REST API client for DripDrop irrigation controller."""

import logging
import requests

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 5
MODULE_READ_TIMEOUT = 5


class DripDropAPI:
    """HTTP client for the DripDrop ESP32 REST API."""

    def __init__(self, host: str, port: int):
        self.base_url = f"http://{host}:{port}"

    def _get(self, path: str, timeout: int = DEFAULT_TIMEOUT):
        """Make a GET request and return parsed JSON."""
        url = f"{self.base_url}{path}"
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
        return resp.json()

    def ping(self) -> bool:
        """Return True if the device is reachable."""
        try:
            self._get("/system/ping")
            return True
        except Exception:
            return False

    def get_system_status(self) -> dict:
        return self._get("/system/status")

    def get_system_name(self) -> str:
        data = self._get("/system/name")
        return data.get("message", "dripdrop")

    def get_valves(self) -> list[dict]:
        return self._get("/valves")

    def get_timers(self) -> list[dict]:
        return self._get("/timers")

    def get_scenarios(self) -> list[dict]:
        return self._get("/scenarios")

    def get_modules(self) -> list[dict]:
        return self._get("/modules")

    def get_module_reading(self, uid: str) -> float | None:
        """Read a single module sensor value. Returns None on error."""
        try:
            data = self._get(f"/modules/{uid}/reading", timeout=MODULE_READ_TIMEOUT)
            return data.get("value")
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code in (404, 422):
                logger.warning("Module %s read failed: %s", uid, e)
            else:
                logger.warning("Module %s HTTP error: %s", uid, e)
            return None
        except Exception as e:
            logger.warning("Module %s read exception: %s", uid, e)
            return None
