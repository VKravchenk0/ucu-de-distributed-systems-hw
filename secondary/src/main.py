import asyncio
import contextlib
from typing import List
import grpc
from fastapi import FastAPI
from common import replication_pb2_grpc
import logging as log

from common.dto import MessageDto
from secondary.src.replication import ReplicationService

log.basicConfig(level=log.INFO, 
                format='%(asctime)s,%(msecs)03d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                datefmt='%Y-%m-%dT%H:%M:%S')

replicated_messages: List[MessageDto] = []

async def serve_grpc(server: grpc.aio.Server):
    replication_pb2_grpc.add_ReplicationServiceServicer_to_server(ReplicationService(replicated_messages), server)
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
