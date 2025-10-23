from typing import Tuple, Union
import grpc
import asyncio
from common import replication_pb2, replication_pb2_grpc
import logging as log

from common.dto import MessageDto


class ReplicationManager:
    def __init__(self, addresses: list[str]):
        log.info(f'Initializing with secondaries: { addresses }')
        self.destinations: list = []
        for address in addresses:
            self.destinations.append({ 'address': address })

    async def connect(self):
        for dest in self.destinations:
            dest['channel'] = grpc.aio.insecure_channel(dest['address'])
            dest['stub'] = replication_pb2_grpc.ReplicationServiceStub(dest['channel'])
            log.info(f"Connected to: { dest['address'] }")

    async def close(self):
        for dest in self.destinations:
            await dest['channel'].close()
        log.info("Closed all connections")

    async def replicate_message(self, message_dto: MessageDto, write_concern: int):
        request = replication_pb2.ReplicationRequest(
            message_id=message_dto.message_id, 
            message_body=message_dto.message_body
        )

        tasks = [
            asyncio.create_task(self.call_replica(dest, request)) 
            for dest in self.destinations
        ]

        if write_concern == 1:
            log.info(f'write_concern is 1. Replicating on the background')
            return write_concern

        success_count = 1

        for replication in asyncio.as_completed(tasks):
            result = await replication
            print(f'result: {result}')
            if result:
                success_count += 1
                if success_count >= write_concern:
                    log.info(f'Success count {success_count} has reached the write_concern of {write_concern}')
                    return success_count
        return success_count


    async def call_replica(self, dest, request) -> Tuple[str, Union[Exception, object]]:
        """
        Send replication request to one destination.
        Returns (address, response) or (address, Exception).
        """
        try:
            response = await dest['stub'].ReplicateMessage(request)
            return dest['address'], response
        except Exception as e:
            log.error(f"Replication to {dest['address']} failed: {e}")
            return dest['address'], e
        