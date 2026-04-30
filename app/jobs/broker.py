import asyncio
import logging

import aio_pika
import aio_pika.abc

from app.jobs.schemas import Job

_log = logging.getLogger(__name__)

_connection: aio_pika.RobustConnection | None = None
_exchange: aio_pika.abc.AbstractExchange | None = None

_EXCHANGE_NAME = "notes.jobs"
_QUEUE_NAME = "notes.jobs.work"


async def connect() -> None:
    global _connection, _exchange

    from app.config import get_settings

    settings = get_settings()
    if not settings.RABBITMQ_URL:
        _log.info("RABBITMQ_URL not set — running in asyncio fallback mode")
        return

    try:
        _connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
        channel = await _connection.channel()
        exchange = await channel.declare_exchange(
            _EXCHANGE_NAME, aio_pika.ExchangeType.TOPIC, durable=True
        )
        work_queue = await channel.declare_queue(_QUEUE_NAME, durable=True)
        await work_queue.bind(exchange, routing_key="job.*")
        await channel.declare_queue("notes.jobs.dlq", durable=True)
        _exchange = exchange
        _log.info("Connected to RabbitMQ at %s", settings.RABBITMQ_URL)
    except Exception:
        _log.warning(
            "RabbitMQ connection failed — falling back to asyncio mode", exc_info=True
        )
        _exchange = None


async def disconnect() -> None:
    global _connection, _exchange

    _exchange = None
    if _connection is not None:
        try:
            await _connection.close()
        except Exception:
            pass
        _connection = None


async def enqueue(job_type: str, payload: dict) -> None:
    if _exchange is None:
        from app.jobs.handlers import HANDLERS

        handler = HANDLERS.get(job_type)
        if handler:
            asyncio.create_task(handler(payload))
        return

    job = Job(job_type=job_type, payload=payload)  # type: ignore[arg-type]
    try:
        await _exchange.publish(
            aio_pika.Message(
                body=job.model_dump_json().encode(),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            ),
            routing_key=f"job.{job_type}",
        )
    except Exception:
        _log.warning(
            "Publish to RabbitMQ failed, falling back to asyncio", exc_info=True
        )
        from app.jobs.handlers import HANDLERS

        handler = HANDLERS.get(job_type)
        if handler:
            asyncio.create_task(handler(payload))
