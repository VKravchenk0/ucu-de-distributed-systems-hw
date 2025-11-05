import asyncio
import time
import logging as log
from common import replication_pb2
from common.dto import MessageDto
import master.src.settings as settings

from dataclasses import dataclass, field
import grpc
import time
from common import replication_pb2_grpc
from google.protobuf import empty_pb2

from math import ceil

@dataclass
class Secondary:
    address: str
    channel: grpc.aio.Channel = field(default=None, init=False)
    stub: replication_pb2_grpc.ReplicationServiceStub = field(default=None, init=False)
    status: str = field(default="healthy", init=False)
    last_heartbeat_timestamp: float = field(default_factory=time.time)
    failed_heartbeats: int = field(default=0, init=False)
    is_healthy_condition: asyncio.Condition = field(default_factory=asyncio.Condition, init=False)

    async def connect(self):
        self.channel = grpc.aio.insecure_channel(self.address)
        self.stub = replication_pb2_grpc.ReplicationServiceStub(self.channel)

    async def close(self):
        await self.channel.close()
        self.stub = None

    async def wait_until_healthy(self):
        async with self.is_healthy_condition:
            await self.is_healthy_condition.wait_for(lambda: self.status == "healthy")


class ReplicationManager:
    def __init__(self, addresses: list[str]):
        log.info(f"Initializing with secondaries: {addresses}")
        self.secondaries: list[Secondary] = [Secondary(address=a) for a in addresses]
        self.quorum_value = ceil((len(self.secondaries) + 1)/2)

    def get_secondaries_status(self) -> list[dict[str, str]]:
        return [{"address": s.address, "status": s.status} for s in self.secondaries]

    async def connect(self):
        for s in self.secondaries:
            await s.connect()
        log.info("Connected to all secondaries.")
        asyncio.create_task(self._heartbeat_loop())

    async def close(self):
        for s in self.secondaries:
            await s.close()
        log.info("Closed all channels.")

    def has_quorum(self):
        healthy_nodes_count = 1 + len([s for s in self.secondaries if s.status == "healthy"])
        return healthy_nodes_count >= self.quorum_value

    async def _heartbeat_loop(self):
        while True:
            await asyncio.gather(*(self._send_heartbeat(s) for s in self.secondaries))
            await asyncio.sleep(settings.HEARTBEAT_INTERVAL_SEC)

    async def _send_heartbeat(self, secondary: Secondary):
        try:
            response = await asyncio.wait_for(
                secondary.stub.Ping(empty_pb2.Empty()),
                timeout=settings.HEARTBEAT_TIMEOUT_SEC,
            )
            if response.alive:
                secondary.failed_heartbeats = 0
                old_status = secondary.status
                secondary.status = "healthy"
                secondary.last_heartbeat_timestamp = time.time()
                if old_status != "healthy":
                    async with secondary.is_healthy_condition:
                        secondary.is_healthy_condition.notify_all()
        except Exception as e:
            secondary.failed_heartbeats += 1
            if secondary.failed_heartbeats >= settings.HEARTBEAT_FAILURE_THRESHOLD:
                secondary.status = "unhealthy"
            else:
                secondary.status = "suspected"
            log.warning(
                f"Heartbeat failed for {secondary.address}: "
                f"status={secondary.status}, failures={secondary.failed_heartbeats}"
            )

    async def replicate_message(self, message_dto: MessageDto, write_concern: int):
        log.info(f'Replicating message dto: {message_dto}')
        request = replication_pb2.ReplicationRequest(
            previous_message_id=message_dto.previous_message_id,
            message_id=message_dto.message_id,
            message_body=message_dto.message_body,
        )

        tasks = [
            asyncio.create_task(self._send_with_retry(s, request))
            for s in self.secondaries
        ]

        if write_concern == 1:
            log.info("write_concern is 1. Replicating on the background")
            return 1

        success_count = 1
        for task in asyncio.as_completed(tasks):
            addr, result = await task
            log.info(f"Finished waiting for the task from {addr}. Result: {result}")
            if not isinstance(result, Exception):
                success_count += 1
                if success_count >= write_concern:
                    log.info(f'Success count {success_count} has reached the write_concern of {write_concern}')
                    return success_count
        return success_count

    async def _send_with_retry(self, secondary: Secondary, request) -> tuple[str, Exception | object]:
        retries = 0
        while True:
            if secondary.status == "unhealthy":
                log.info(f"{secondary.address} is unhealthy. Waiting for recovery")
                await secondary.wait_until_healthy()

            try:
                log.info(f'Attempting to replicate message {request} to {secondary.address}. Attempt number: {retries} ')
                response = await secondary.stub.ReplicateMessage(request)
                log.info(f"Replication to {secondary.address} succeeded.")
                return secondary.address, response
            except Exception as e:
                retries += 1
                log.warning(f"Replication to {secondary.address} failed (attempt {retries}): {e}")
