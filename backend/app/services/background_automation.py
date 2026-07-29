import asyncio
import logging

from app.core.config import settings
from app.db.session import SessionLocal
from app.services.event_staff_task_service import enqueue_due_task_reminders

logger = logging.getLogger(__name__)


def process_event_task_reminders() -> None:
    with SessionLocal() as db:
        enqueue_due_task_reminders(db)


async def event_task_reminder_loop() -> None:
    initial_delay = min(10, settings.event_task_reminder_interval_seconds)
    await asyncio.sleep(initial_delay)
    while True:
        try:
            await asyncio.to_thread(process_event_task_reminders)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Event staff task reminder automation failed")
        await asyncio.sleep(settings.event_task_reminder_interval_seconds)
