from typing import Dict, List

from dotenv import load_dotenv

from exchange_services.exchange import ExchangeService
from exchange_services.okx_service import OkxService
from exchange_services.kraken_service import KrakenService
from exchange_services.proxy_session import ProxySession

load_dotenv()


class ServiceContainer:

    def __init__(self):
        self.services: Dict[str, ExchangeService] = {}
        self.available_services: List[str] = ["okx", "kraken"]
        # One credential for the whole process. OKX rides this; Kraken still
        # holds its own key directly until its migration.
        self._proxy = ProxySession.from_env()

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
            return OkxService(self._proxy)
        if service_name == "kraken":
            return KrakenService(base_url="https://api.kraken.com")
        raise ValueError(f"No factory registered for service: {service_name}")

    async def aclose(self) -> None:
        """Release the Proxy session's connection pools. Called from the
        app's lifespan teardown."""
        await self._proxy.aclose()
