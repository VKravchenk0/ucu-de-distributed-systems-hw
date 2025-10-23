import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Body
from typing import Dict, List
import logging as log
import asyncio

from pydantic import BaseModel

from common.dto import MessageDto
from master.src.replication import ReplicationManager
import master.src.settings as settings

log.basicConfig(level=log.INFO, 
                format='%(asctime)s,%(msecs)03d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                datefmt='%Y-%m-%dT%H:%M:%S')

message_id_seq = 0

messages: List[MessageDto] = []
messages_lock = asyncio.Lock()

replication_manager = ReplicationManager(settings.SECONDARY_ADDRESSES)

def get_and_increment_message_id():
    global message_id_seq
    message_id = message_id_seq
    message_id_seq += 1
    return message_id

@asynccontextmanager
async def lifespan(app: FastAPI):
    await replication_manager.connect()
    yield
    await replication_manager.close()

class MessageAppendRequest(BaseModel):
    message: str
    write_concern: int

def create_app() -> FastAPI:
    app = FastAPI(lifespan=lifespan)

    @app.post("/messages")
    async def append_message(request: MessageAppendRequest) -> Dict[str, str]:
        async with messages_lock:
            previous_message_id = messages[-1].message_id if messages else None
            message_id = get_and_increment_message_id()
            message_dto = MessageDto(previous_message_id, message_id, request.message)
            messages.append(message_dto)

        log.info(f"Message append request: {request}")
        await replication_manager.replicate_message(message_dto, request.write_concern)
        return {
            "status": "replicated"
        }
    
    @app.get("/messages")
    def get_messages() -> List[str]:
        return map(lambda m: m.message_body, messages)

    return app

app = create_app()

