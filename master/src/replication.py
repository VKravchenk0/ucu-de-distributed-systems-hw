import grpc
import asyncio
from common import replication_pb2, replication_pb2_grpc
import logging as log


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

    async def replicate_message(self, message: str):
        request = replication_pb2.ReplicationRequest(message=message)

        tasks = [
            dest['stub'].ReplicateMessage(request)
            for dest in self.destinations
        ]

        responses = await asyncio.gather(*tasks)

        for dest, response in zip(self.destinations, responses):
            log.info(
                f"Message replicated to {dest['address']}: "
                f"{replication_pb2.Status.Name(response.status)}"
            )

        return responses
        