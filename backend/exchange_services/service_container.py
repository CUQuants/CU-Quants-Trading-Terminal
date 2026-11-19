from typing import Dict, List

from exchange_services.exchange import ExchangeService
from exchange_services.okx_service import OkxService
from exchange_services.kraken_service import KrakenService
from exchange_services.proxy_session import ProxySession
from exchange_services.reporting_session import ReportingSession


class ServiceContainer:
    """One signed-in trader's services.

    Built by `routes/auth.py` at sign-in, from the trader's own gateway
    credential, and owned by that trader's `auth.sessions.UserSession`. There
    is no process-wide container any more: every request the terminal makes
    is signed as, and attributed in the gateway's audit log to, the trader
    who made it.
    """

    def __init__(self, proxy: ProxySession, reporting: ReportingSession | None = None):
        self.services: Dict[str, ExchangeService] = {}
        self.available_services: List[str] = ["okx", "kraken"]
        # OKX and Kraken (the club's Prime account, as gateway exchange
        # `kraken_prime`) both ride this one trader's credential.
        self._proxy = proxy
        # Optional: the audit-reporting API is a separate service that may
        # not be stood up yet on every deployment. Its absence must not stop
        # the terminal from trading — routes/reporting.py returns 503 when
        # this is None instead.
        self.reporting = reporting

    @property
    def proxy(self) -> ProxySession:
        """This trader's gateway session (for calls that aren't an exchange
        service's, like PnL)."""
        return self._proxy

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
            return KrakenService(self._proxy)
        raise ValueError(f"No factory registered for service: {service_name}")

    async def aclose(self) -> None:
        """Release the Proxy (and reporting, if configured) session's
        connection pools. Called when the trader's session ends."""
        await self._proxy.aclose()
        if self.reporting is not None:
            await self.reporting.aclose()
