from typing import Dict, List

from dotenv import load_dotenv

from exchange_services.exchange import ExchangeService
from exchange_services.okx_service import OkxService
from exchange_services.kraken_service import KrakenService
from exchange_services.proxy_session import ProxySession
from exchange_services.reporting_session import ProxyConfigError, ReportingSession

load_dotenv()


class ServiceContainer:

    def __init__(self):
        self.services: Dict[str, ExchangeService] = {}
        self.available_services: List[str] = ["okx", "kraken"]
        # One credential for the whole process. OKX rides this; Kraken still
        # holds its own key directly until its migration.
        self._proxy = ProxySession.from_env()
        # Optional: the audit-reporting API is a separate service that may
        # not be stood up yet on every deployment. Unlike ProxySession, its
        # absence must not stop the terminal from trading — routes/reporting.py
        # returns 503 when this is None instead.
        try:
            self.reporting: ReportingSession | None = ReportingSession.from_env()
        except ProxyConfigError:
            self.reporting = None

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
        """Release the Proxy (and reporting, if configured) session's
        connection pools. Called from the app's lifespan teardown."""
        await self._proxy.aclose()
        if self.reporting is not None:
            await self.reporting.aclose()
