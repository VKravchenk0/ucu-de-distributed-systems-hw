import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Body
from typing import Dict, List
import logging as log
import asyncio

from common.dto import MessageDto
from master.src.replication import ReplicationManager
import master.src.settings as settings

log.basicConfig(level=log.INFO, 
                format='%(asctime)s,%(msecs)03d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                datefmt='%Y-%m-%dT%H:%M:%S')

latest_message_id = 0
latest_message_id_lock = asyncio.Lock()

messages: List[MessageDto] = []
replication_manager = ReplicationManager(settings.SECONDARY_ADDRESSES)

# чекаю релізу python 3.14, щоб замінити на uuid v7
async def get_and_increment_message_id():
    async with latest_message_id_lock:
            global latest_message_id
            message_id = str(latest_message_id)
            latest_message_id += 1
            return message_id

@asynccontextmanager
async def lifespan(app: FastAPI):
    await replication_manager.connect()
    yield
    await replication_manager.close()

def create_app() -> FastAPI:
    app = FastAPI(lifespan=lifespan)

    @app.post("/messages")
    async def append_message(message: str = Body(..., embed=False)) -> Dict[str, str]:
        message_id = await get_and_increment_message_id()
        message_dto = MessageDto(message_id, message)

        messages.append(message_dto)

        log.info(f"Message append request: {message}")
        await replication_manager.replicate_message(message_dto)
        return {
            "status": "replicated"
        }
    
    @app.get("/messages")
    def get_messages() -> List[str]:
        return map(lambda m: m.message_body, messages)

    return app

app = create_app()

