"""
Standalone RabbitMQ consumer. Run with:
    python -m app.worker
"""

import asyncio
import logging

import aio_pika
import aio_pika.abc

from app.jobs.handlers import HANDLERS
from app.jobs.schemas import Job

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s"
)
_log = logging.getLogger(__name__)

_EXCHANGE_NAME = "notes.jobs"
_QUEUE_NAME = "notes.jobs.work"
_DLQ_NAME = "notes.jobs.dlq"


async def _requeue(exchange: aio_pika.abc.AbstractExchange, job: Job) -> None:
    job.attempt += 1
    await asyncio.sleep(5)
    await exchange.publish(
        aio_pika.Message(
            body=job.model_dump_json().encode(),
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        ),
        routing_key=f"job.{job.job_type}",
    )


async def _send_dlq(dlq: aio_pika.abc.AbstractQueue, job: Job) -> None:
    await dlq.channel.default_exchange.publish(
        aio_pika.Message(
            body=job.model_dump_json().encode(),
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        ),
        routing_key=_DLQ_NAME,
    )


def _make_processor(
    exchange: aio_pika.abc.AbstractExchange,
    dlq: aio_pika.abc.AbstractQueue,
):
    async def process_message(message: aio_pika.abc.AbstractIncomingMessage) -> None:
        async with message.process(requeue=False):
            job = Job.model_validate_json(message.body)
            handler = HANDLERS.get(job.job_type)
            if handler is None:
                _log.warning("Unknown job_type %s, dropping", job.job_type)
                return
            try:
                await handler(job.payload)
            except Exception:
                _log.exception("Job %s attempt %d failed", job.job_type, job.attempt)
                if job.attempt < 2:
                    await _requeue(exchange, job)
                else:
                    await _send_dlq(dlq, job)

    return process_message


async def main() -> None:
    from app.config import get_settings

    settings = get_settings()
    if not settings.RABBITMQ_URL:
        _log.error("RABBITMQ_URL is not set. Worker requires a RabbitMQ connection.")
        return

    connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
    channel = await connection.channel()
    await channel.set_qos(prefetch_count=10)

    exchange = await channel.declare_exchange(
        _EXCHANGE_NAME, aio_pika.ExchangeType.TOPIC, durable=True
    )
    work_queue = await channel.declare_queue(_QUEUE_NAME, durable=True)
    await work_queue.bind(exchange, routing_key="job.*")
    dlq = await channel.declare_queue(_DLQ_NAME, durable=True)

    await work_queue.consume(_make_processor(exchange, dlq))
    _log.info("Worker started, consuming from %s", _QUEUE_NAME)

    await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
