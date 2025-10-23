# Replicated log homework. Iteration 1.

Рішення побудоване на python, з використанням FastAPI для публічних ендпойнтів і gRPC для міжсервісної комунікації.

Проект містить три модулі:
- master
- secondary
- common - містить gRPC-код, який підключається в master i secondary

Адреси secondary-серверів задаються на мастері через змінну середовища `SECONDARY_ADDRESSES`.

## Інструкція з запуску

1. Створюємо і активуємо venv (Python 3.13.5)
2. Встановлюємо залежності
    ```bash
    pip install -r requirements.txt
    ```
3. Компілюємо proto-файли
    ```bash
    python -m grpc_tools.protoc -I./common/protos --python_out=./common --grpc_python_out=./common ./common/protos/replication.proto
    ```
4. Виправляємо імпорти в скомпільованому файлі (`common/replication_pb2_grpc.py`). Щодо причини - див. https://github.com/protocolbuffers/protobuf/issues/1491.
    ```python
    import replication_pb2 as replication__pb2
    # виправляємо на
    import common.replication_pb2 as replication__pb2
    ```
5. Запуск в docker:
    ```bash
    docker-compose up --build
    ```
6. Надсилаємо повідомлення
    ```bash
    $ curl -X POST "localhost:8000/messages" \
        -H "Content-Type: application/json" \
        -d '{"message": "msg5", "write_concern": 2}'
    {"status":"replicated"}
    ```
    <details>
        <summary>Лог</summary>

        master-1      | 2025-09-27T20:43:20,604 INFO     [main.py:46] Message append request: msg1
        secondary2-1  | 2025-09-27T20:43:20,608 INFO     [main.py:28] Received grpc request. message_id: 0 | message_body: msg1
        secondary2-1  | 2025-09-27T20:43:20,608 INFO     [main.py:23] Introducing 4 seconds of delay
        secondary1-1  | 2025-09-27T20:43:20,620 INFO     [main.py:28] Received grpc request. message_id: 0 | message_body: msg1
        secondary1-1  | 2025-09-27T20:43:20,620 INFO     [main.py:23] Introducing 5 seconds of delay
        secondary2-1  | 2025-09-27T20:43:24,612 INFO     [main.py:36] Added message {"message_id": 0, "message_body": msg1} to replicated list
        secondary1-1  | 2025-09-27T20:43:25,621 INFO     [main.py:36] Added message {"message_id": 0, "message_body": msg1} to replicated list
        master-1      | 2025-09-27T20:43:25,622 INFO     [replication.py:38] Message 0 replicated to secondary1:50051: SUCCESS
        master-1      | 2025-09-27T20:43:25,622 INFO     [replication.py:38] Message 0 replicated to secondary2:50051: SUCCESS
        master-1      | INFO:     172.20.0.1:32982 - "POST /messages HTTP/1.1" 200 OK
    </details>
7. Перевіряємо реплікацію
    ```bash
    # master
    $ curl localhost:8000/messages
    ["msg1"]

    # secondary1
    $ curl localhost:8001/messages
    ["msg1"]

    # secondary2
    $ curl localhost:8002/messages
    ["msg1"]
    ```
8. Надсилаємо друге повідомлення
    ```bash
    $ curl -X POST localhost:8000/messages -d 'msg2'
    {"status":"replicated"}
    ```
    <details>
        <summary>Лог</summary>

        master-1      | 2025-09-27T20:45:19,870 INFO     [main.py:46] Message append request: msg2
        secondary2-1  | 2025-09-27T20:45:19,871 INFO     [main.py:28] Received grpc request. message_id: 1 | message_body: msg2
        secondary1-1  | 2025-09-27T20:45:19,871 INFO     [main.py:28] Received grpc request. message_id: 1 | message_body: msg2
        secondary1-1  | 2025-09-27T20:45:19,871 INFO     [main.py:23] Introducing 4 seconds of delay
        secondary2-1  | 2025-09-27T20:45:19,871 INFO     [main.py:23] Introducing 6 seconds of delay
        secondary1-1  | 2025-09-27T20:45:23,878 INFO     [main.py:36] Added message {"message_id": 1, "message_body": msg2} to replicated list
        secondary2-1  | 2025-09-27T20:45:25,873 INFO     [main.py:36] Added message {"message_id": 1, "message_body": msg2} to replicated list
        master-1      | 2025-09-27T20:45:25,874 INFO     [replication.py:38] Message 1 replicated to secondary1:50051: SUCCESS
        master-1      | 2025-09-27T20:45:25,874 INFO     [replication.py:38] Message 1 replicated to secondary2:50051: SUCCESS
        master-1      | INFO:     172.20.0.1:59812 - "POST /messages HTTP/1.1" 200 OK
    </details>
9. Перевіряємо реплікацію
    ```bash
    # master
    $ curl localhost:8000/messages
    ["msg1","msg2"]

    # secondary1
    $ curl localhost:8001/messages
    ["msg1","msg2"]

    # secondary2
    $ curl localhost:8002/messages
    ["msg1","msg2"]
    ```

## Додаток
Запуск без докеру:
```bash
uvicorn master.src.main:app
uvicorn --port 8001 secondary.src.main:app
```