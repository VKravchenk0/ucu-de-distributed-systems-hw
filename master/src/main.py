import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from typing import List
import logging as log
from fastapi import Body

from master.src.replication import ReplicationManager
import master.src.settings as settings

log.basicConfig(level=log.INFO, 
                format='%(asctime)s,%(msecs)03d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                datefmt='%Y-%m-%dT%H:%M:%S')

messages: List[str] = []
replication_manager = ReplicationManager(settings.SECONDARY_ADDRESSES)

@asynccontextmanager
async def lifespan(app: FastAPI):
    await replication_manager.connect()
    yield
    await replication_manager.close()

def create_app() -> FastAPI:
    app = FastAPI(lifespan=lifespan)

    @app.post("/messages")
    async def append_message(message: str = Body(..., embed=False)):
        messages.append(message)
        log.info(f"Message append request: {message}")

        await replication_manager.replicate_message(message)
        return {
            "status": "replicated"
        }
    
    @app.get("/messages")
    def get_messages():
        return {"messages": messages}

    return app

app = create_app()

