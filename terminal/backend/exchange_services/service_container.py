from typing import Dict, List

from exchange_services.exchange import ExchangeService
from exchange_services.okx_service import OkxService


class ServiceContainer:

    def __init__(self):
        self.services: Dict[str, ExchangeService] = {}
        self.available_services: List[str] = ["okx"]

    def get_service(self, service_name: str) -> ExchangeService:
        if service_name not in self.available_services:
            raise ValueError(
                f"Service '{service_name}' not available. Options: {self.available_services}"
            )
        if service_name not in self.services:
            self.services[service_name] = self._create_service(service_name)
        return self.services[service_name]

    def _create_service(self, service_name: str) -> ExchangeService:
        if service_name == "okx":
            return OkxService(base_url="https://us.okx.com", simulated=True)
        raise ValueError(f"No factory registered for service: {service_name}")
