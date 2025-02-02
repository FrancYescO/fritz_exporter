from fritzexporter.fritzcapabilities import FritzCapabilities
import logging
import sys

from fritzconnection import FritzConnection
from fritzconnection.core.exceptions import FritzActionError, FritzServiceError
from requests.exceptions import ConnectionError

logger = logging.getLogger("fritzexporter.fritzdevice")


class FritzDevice:
    def __init__(
        self, host: str, user: str, password: str, name: str, host_info: bool = False
    ) -> None:
        self.host: str = host
        self.serial: str = "n/a"
        self.model: str = "n/a"
        self.friendly_name: str = name
        self.host_info: bool = host_info

        if len(password) > 32:
            logger.warning(
                "Password is longer than 32 characters! Login may not succeed, please see README!"
            )

        try:
            self.fc: FritzConnection = FritzConnection(address=host, user=user, password=password)
        except ConnectionError as e:
            logger.exception(f"unable to connect to {host}: {str(e)}", exc_info=True)
            sys.exit(1)

        logger.info(f"Connection to {host} successful, reading capabilities")
        self.capabilities = FritzCapabilities(self, host_info)

        self.getDeviceInfo()
        logger.info(
            f"Read capabilities for {host}, got serial " f"{self.serial}, model name {self.model}"
        )
        if host_info:
            logger.warn(
                f"HostInfo Capability enabled on device {host}. "
                "This may consume a lot of resources and will cause very slow requests!"
            )
        if self.capabilities.empty():
            logger.critical(f"Device {host} has no detected capabilities. Exiting. ")
            sys.exit(1)

    def getDeviceInfo(self):
        try:
            device_info: dict[str, str] = self.fc.call_action("DeviceInfo", "GetInfo")
            self.serial: str = device_info["NewSerialNumber"]
            self.model: str = device_info["NewModelName"]

        except (FritzServiceError, FritzActionError):
            logger.exception(
                f"Fritz Device {self.host} does not provide basic device "
                "info (Service: DeviceInfo1, Action: GetInfo)."
                "Serial number and model name will be unavailable.",
                exc_info=True,
            )


class FritzCollector:
    def __init__(self):
        self.devices: list[FritzDevice] = []
        self.capabilities: FritzCapabilities = FritzCapabilities(host_info=True)

    def register(self, fritzdev):
        self.devices.append(fritzdev)
        logger.debug(f"registered device {fritzdev.host} ({fritzdev.model}) to collector")
        self.capabilities.merge(fritzdev.capabilities)

    def collect(self):
        if not self.devices:
            logger.critical("No devices registered in collector! Exiting.")
            sys.exit(1)

        for name, capa in self.capabilities.items():
            capa.createMetrics()
            yield from capa.getMetrics(self.devices, name)


# Copyright 2019-2022 Patrick Dreker <patrick@dreker.de>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
