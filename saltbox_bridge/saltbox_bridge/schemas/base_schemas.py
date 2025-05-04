from __future__ import annotations

import hashlib

from pydantic import BaseModel, ConfigDict

from saltbox_bridge.config import SETTINGS


class AuthMessage(BaseModel):
    master: str
    secret: str


class BaseMessage(BaseModel):
    master: str | None = None
    checksum: str | None = None

    def _get_checksum(self, secret: str) -> str:
        message = self.model_dump_json(exclude={'checksum'})

        return hashlib.sha256(f'{self.master}_{message}_{secret}'.encode()).hexdigest()


class BaseInAbstractMessage(BaseMessage):
    checksum: str

    def check_checksum(self, secret: str | None = None) -> bool:
        if secret is None:
            secret = SETTINGS.master_secret

        return self.checksum == self._get_checksum(secret)

    model_config = ConfigDict(extra='allow')


class BaseInMessage(BaseInAbstractMessage):
    model_config = ConfigDict(extra='ignore')


class BaseOutMessage(BaseMessage):
    master: str

    def fill_checksum(self, secret: str | None = None) -> None:
        if secret is None:
            secret = SETTINGS.master_secret

        self.checksum = self._get_checksum(secret)
