from random import randint
from time import sleep

import asyncio
import contextlib
from typing import List
import grpc
from fastapi import FastAPI
from common import replication_pb2, replication_pb2_grpc
import logging as log

from common.dto import MessageDto

log.basicConfig(level=log.INFO, 
                format='%(asctime)s,%(msecs)03d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                datefmt='%Y-%m-%dT%H:%M:%S')

replication_lock = asyncio.Lock()
received_messages_ids: List[int] = []
replication_buffer: List[MessageDto] = []
replicated_messages: List[MessageDto] = []

def random_delay():
    delay_sec = randint(3,7)
    log.info(f"Introducing { delay_sec } seconds of delay")
    sleep(delay_sec)

def message_is_duplicate(message_id: int) -> bool:
    return received_messages_ids and message_id in received_messages_ids

def incoming_message_in_correct_order(message_dto: MessageDto) -> bool:
    return message_dto.previous_message_id is None or \
        (replicated_messages and message_dto.previous_message_id == replicated_messages[-1].message_id)

class ReplicationService(replication_pb2_grpc.ReplicationServiceServicer):
    async def ReplicateMessage(self, request, context):
        message_dto = MessageDto(
                request.previous_message_id if request.HasField("previous_message_id") else None, 
                request.message_id, 
                request.message_body
        )
        log.info(f"Received request to replicate message {message_dto}")
        
        random_delay()
        
        async with replication_lock:
            if message_is_duplicate(message_dto.message_id):
                log.info(f'Message {message_dto.message_id} was already received. Skipping')
                return replication_pb2.ReplicationResponse(status=replication_pb2.Status.SUCCESS)

            received_messages_ids.append(message_dto.message_id)

            if incoming_message_in_correct_order(message_dto):
                replicated_messages.append(message_dto)
                self._process_replication_buffer(message_dto)
                log.info(f'Message {message_dto.message_id} replicated')
            else:
                replication_buffer.append(message_dto)
                log.info(f'Message {message_dto.message_id} is out of order. Appended to the replication_buffer')

        return replication_pb2.ReplicationResponse(status=replication_pb2.Status.SUCCESS)
    
    def _process_replication_buffer(self, message_dto: MessageDto):
        """
        Рекурсивний метод для обробки повідомлень, які прийшли поза чергою.
        Перевіряє, чи вхідне повідомлення передує нульовому повідомленню з replication_buffer. Якщо так - 
        значить повідомлення з буферу дочекалось своєї черги, і можна переносити його в replicated_messages.
        В разі успіху - рекурсивно викликаємо метод, поки буфер не очиститься, або поки не дійдемо до повідомлення, 
        яке все ще поза чергою
        """
        if replication_buffer:
            message_from_buffer = self.replication_buffer[0]

            if message_from_buffer.previous_message_id == message_dto.message_id:
                self.replication_buffer.pop(0)
                self.replicated_messages.append(message_from_buffer)
                self._process_replication_buffer(message_from_buffer)


async def serve_grpc(server: grpc.aio.Server):
    replication_pb2_grpc.add_ReplicationServiceServicer_to_server(ReplicationService(), server)
    server.add_insecure_port("[::]:50051")
    log.info("grpc sever started on 50051")
    await server.start()
    await server.wait_for_termination()


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    grpc_server = grpc.aio.server()
    task = asyncio.create_task(serve_grpc(grpc_server))
    try:
        yield
    finally:
        log.info("Shutting down gRPC server")
        await grpc_server.stop(grace=3)
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task

def create_app() -> FastAPI:
    app = FastAPI(lifespan=lifespan)

    @app.get("/messages")
    async def get_messages() -> List[str]:
        return map(lambda m: m.message_body, replicated_messages)

    return app

app = create_app()
