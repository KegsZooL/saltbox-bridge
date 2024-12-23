import json
import logging

from redis.asyncio import Redis
from salt.client import LocalClient
from salt.exceptions import SaltException

from exceptions import CreateJobError


LOGGER = logging.getLogger(__name__)


async def create_job_from_redis(hash_name: str, redis_client: Redis, salt_client: LocalClient) -> str:
    job_data: dict[bytes, bytes] = await redis_client.hgetall(hash_name)

    jid: str = job_data[b'jid'].decode()
    tgt: str = job_data[b'tgt'].decode()
    tgt_type: str = job_data[b'tgt_type'].decode()
    fun: str = job_data[b'fun'].decode()
    arg: list | None = json.loads(job_data[b'arg']) if b'arg' in job_data else None
    kwarg: dict | None = json.loads(job_data[b'kwarg']) if b'kwarg' in job_data else None

    try:
        jid: str = salt_client.cmd_async(
            tgt=tgt,
            tgt_type=tgt_type,
            fun=fun,
            arg=arg,
            kwarg=kwarg,
            jid=jid
        )
    except SaltException as err:
        LOGGER.error(err)
        raise CreateJobError(str(err)) from err

    await redis_client.delete(hash_name)

    return jid


async def create_all_jobs_from_redis(redis_client: Redis, salt_client: LocalClient) -> list[str]:
    hash_names = await redis_client.keys('job_create:*')
    jobs_jid: list[str] = []

    for hash_name in hash_names:
        try:
            jobs_jid.append(await create_job_from_redis(hash_name, redis_client, salt_client))
        except CreateJobError:
            continue

    return jobs_jid
