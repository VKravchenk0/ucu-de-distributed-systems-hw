from random import randint
from time import sleep

import asyncio
from typing import List
from common import replication_pb2, replication_pb2_grpc
import logging as log

from common.dto import MessageDto

log.basicConfig(level=log.INFO, 
                format='%(asctime)s,%(msecs)03d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                datefmt='%Y-%m-%dT%H:%M:%S')

def random_delay():
    delay_sec = randint(2,10)
    log.info(f"Introducing { delay_sec } seconds of delay")
    sleep(delay_sec)

class ReplicationService(replication_pb2_grpc.ReplicationServiceServicer):

    def __init__(self, replicated_messages: List[int]):
        self.replicated_messages = replicated_messages
        self.replication_lock = asyncio.Lock()
        self.received_messages_ids: List[int] = []
        self.replication_buffer: List[MessageDto] = []

    async def ReplicateMessage(self, request, context):
        message_dto = MessageDto(
                request.previous_message_id if request.HasField("previous_message_id") else None, 
                request.message_id, 
                request.message_body
        )
        log.info(f"Received request to replicate message {message_dto}")
        
        random_delay()
        
        async with self.replication_lock:
            if self._message_is_duplicate(message_dto.message_id):
                log.info(f'Message {message_dto.message_id} was already received. Skipping')
                return replication_pb2.ReplicationResponse(status=replication_pb2.Status.SUCCESS)

            self.received_messages_ids.append(message_dto.message_id)

            if self._incoming_message_in_correct_order(message_dto):
                self.replicated_messages.append(message_dto)
                self._process_replication_buffer(message_dto)
                log.info(f'Message {message_dto.message_id} replicated')
            else:
                self.replication_buffer.append(message_dto)
                log.info(f'Message {message_dto.message_id} is out of order. Appended to the replication_buffer')

        return replication_pb2.ReplicationResponse(status=replication_pb2.Status.SUCCESS)
    
    def _message_is_duplicate(self, message_id: int) -> bool:
        return self.received_messages_ids and message_id in self.received_messages_ids

    def _incoming_message_in_correct_order(self, message_dto: MessageDto) -> bool:
        return message_dto.previous_message_id is None or \
            (self.replicated_messages and message_dto.previous_message_id == self.replicated_messages[-1].message_id)
    
    def _process_replication_buffer(self, message_dto: MessageDto):
        """
        Рекурсивний метод для обробки повідомлень, які прийшли поза чергою.
        Перевіряє, чи вхідне повідомлення передує нульовому повідомленню з replication_buffer. Якщо так - 
        значить повідомлення з буферу дочекалось своєї черги, і можна переносити його в replicated_messages.
        В разі успіху - рекурсивно викликаємо метод, поки буфер не очиститься, або поки не дійдемо до повідомлення, 
        яке все ще поза чергою
        """
        if self.replication_buffer:
            message_from_buffer = self.replication_buffer[0]

            if message_from_buffer.previous_message_id == message_dto.message_id:
                self.replication_buffer.pop(0)
                self.replicated_messages.append(message_from_buffer)
                self._process_replication_buffer(message_from_buffer)