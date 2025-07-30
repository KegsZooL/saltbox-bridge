from __future__ import annotations

from pydantic_settings import BaseSettings


class MetricSettings(BaseSettings):
    port: int = 8004
    addr: str = '0.0.0.0'  # noqa: S104
    certfile: str | None = None
    keyfile: str | None = None
    client_cafile: str | None = None
    client_capath: str | None = None
    client_auth_required: bool = False

