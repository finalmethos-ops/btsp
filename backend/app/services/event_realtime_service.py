import asyncio
import json
from collections import defaultdict
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import WebSocket
from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.core.config import settings

REALTIME_CHANNEL = "btsp:event-realtime"


class EventRealtimeHub:
    def __init__(self) -> None:
        self._connections: dict[str, set[WebSocket]] = defaultdict(set)
        self._instance_id = str(uuid4())
        self._redis = Redis.from_url(settings.redis_url, decode_responses=True)
        self._listener_task: asyncio.Task | None = None
        self._listener_lock = asyncio.Lock()

    async def _ensure_listener(self) -> None:
        if self._listener_task and not self._listener_task.done():
            return
        async with self._listener_lock:
            if not self._listener_task or self._listener_task.done():
                self._listener_task = asyncio.create_task(self._listen())

    async def _listen(self) -> None:
        while True:
            pubsub = self._redis.pubsub()
            try:
                await pubsub.subscribe(REALTIME_CHANNEL)
                async for message in pubsub.listen():
                    if message.get("type") != "message":
                        continue
                    payload = json.loads(message["data"])
                    if payload.get("publisher") == self._instance_id:
                        continue
                    await self._deliver(str(payload.get("sub_event_id")), payload)
            except (RedisError, OSError, json.JSONDecodeError):
                await asyncio.sleep(1)
            finally:
                await pubsub.aclose()

    async def connect(self, sub_event_id: str, websocket: WebSocket, protocol: str) -> None:
        await self._ensure_listener()
        await websocket.accept(subprotocol=protocol)
        self._connections[sub_event_id].add(websocket)

    def disconnect(self, sub_event_id: str, websocket: WebSocket) -> None:
        connections = self._connections.get(sub_event_id)
        if connections is None:
            return
        connections.discard(websocket)
        if not connections:
            self._connections.pop(sub_event_id, None)

    async def _deliver(self, sub_event_id: str, payload: dict[str, str]) -> None:
        if not sub_event_id:
            return
        stale: list[WebSocket] = []
        for websocket in tuple(self._connections.get(sub_event_id, set())):
            try:
                await websocket.send_json(payload)
            except RuntimeError:
                stale.append(websocket)
        for websocket in stale:
            self.disconnect(sub_event_id, websocket)

    async def publish(self, sub_event_id: str, event_type: str) -> None:
        payload = {
            "event_type": event_type,
            "sub_event_id": sub_event_id,
            "occurred_at": datetime.now(UTC).isoformat(),
            "publisher": self._instance_id,
        }
        await self._deliver(sub_event_id, payload)
        try:
            await self._redis.publish(REALTIME_CHANNEL, json.dumps(payload))
        except (RedisError, OSError):
            # Local delivery above keeps a single-node development environment
            # functional while Redis is unavailable.
            return


event_realtime_hub = EventRealtimeHub()
