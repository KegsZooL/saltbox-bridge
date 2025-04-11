import os

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from salt_box_bridge_service.utils.types import SslCertReqs


class FaststreamRedisConf:
    def __init__(
        self,
        url: str,
        username: str,
        password: str,
        ssl_cert_reqs: SslCertReqs = 'required',
        ssl_ca_certs: str | None = None,
    ):
        self.url = url
        self.username = username
        self.password = password
        self.ssl_cert_reqs = ssl_cert_reqs
        self.ssl_ca_certs = ssl_ca_certs


class Settings(BaseSettings):
    # Redis
    redis_host: str = Field(alias='REDIS_HOST', default='localhost')
    redis_port: int = Field(alias='REDIS_PORT', default=6379)
    redis_username: str = Field(alias='REDIS_USERNAME')
    redis_password: str = Field(alias='REDIS_PASSWORD')
    redis_db: int = Field(alias='REDIS_DB', default=0)
    redis_ssl_use: bool = Field(alias='REDIS_SSL_USE', default=True)
    redis_ssl_cert_reqs: SslCertReqs = Field(alias='REDIS_SSL_CERT_REQS', default='required')
    redis_ssl_ca_certs: str | None = Field(alias='REDIS_SSL_CA_CERTS', default=None)

    # Salt box
    expire: int | None = Field(alias='EXPIRE', default=604800)
    master_secret: str = Field(alias='MASTER_SECRET')

    model_config = SettingsConfigDict(env_file=os.getenv('SALT_BOX_ENV_FILE'))

    @property
    def redis_protocol(self) -> str:
        return 'rediss' if self.redis_ssl_use else 'redis'

    @property
    def faststream_redis_conf(self) -> FaststreamRedisConf:
        return FaststreamRedisConf(
            url=f'{self.redis_protocol}://{self.redis_host}:{self.redis_port}',
            username=self.redis_username,
            password=self.redis_password,
            ssl_cert_reqs=self.redis_ssl_cert_reqs,
            ssl_ca_certs=self.redis_ssl_ca_certs,
        )


SETTINGS = Settings()  # type: ignore
