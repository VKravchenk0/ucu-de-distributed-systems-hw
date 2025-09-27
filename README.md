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
    $ curl -X POST localhost:8000/messages -d 'msg1'
    {"status":"replicated"}
    ```
    <details>
        <summary>Лог</summary>

        master-1      | 2025-09-24T21:41:56,563 INFO     [main.py:30] Message append request: msg1
        secondary1-1  | 2025-09-24T21:41:56,567 INFO     [main.py:20] Received: msg1
        secondary1-1  | 2025-09-24T21:41:56,567 INFO     [main.py:22] Introducing 5 seconds of delay
        secondary1-1  | 2025-09-24T21:42:01,568 INFO     [main.py:25] Added message msg1 to replicated list
        master-1      | 2025-09-24T21:42:01,570 INFO     [replication.py:27] Message replicated to secondary1:50051: SUCCESS
        secondary2-1  | 2025-09-24T21:42:01,576 INFO     [main.py:20] Received: msg1
        secondary2-1  | 2025-09-24T21:42:01,576 INFO     [main.py:22] Introducing 6 seconds of delay
        secondary2-1  | 2025-09-24T21:42:07,577 INFO     [main.py:25] Added message msg1 to replicated list
        master-1      | 2025-09-24T21:42:07,578 INFO     [replication.py:27] Message replicated to secondary2:50051: SUCCESS
        master-1      | INFO:     172.20.0.1:40374 - "POST /messages HTTP/1.1" 200 OK
    </details>
7. Перевіряємо реплікацію
    ```bash
    # master
    $ curl localhost:8000/messages
    {"messages":["msg1"]}

    # secondary1
    $ curl localhost:8001/messages
    {"messages":["msg1"]}

    # secondary2
    $ curl localhost:8002/messages
    {"messages":["msg1"]}
    ```
8. Надсилаємо друге повідомлення
    ```bash
    $ curl -X POST localhost:8000/messages -d 'msg2'
    {"status":"replicated"}
    ```
    <details>
        <summary>Лог</summary>

        master-1      | 2025-09-24T21:43:11,208 INFO     [main.py:30] Message append request: msg2
        secondary1-1  | 2025-09-24T21:43:11,210 INFO     [main.py:20] Received: msg2
        secondary1-1  | 2025-09-24T21:43:11,210 INFO     [main.py:22] Introducing 5 seconds of delay
        secondary1-1  | 2025-09-24T21:43:16,210 INFO     [main.py:25] Added message msg2 to replicated list
        master-1      | 2025-09-24T21:43:16,212 INFO     [replication.py:27] Message replicated to secondary1:50051: SUCCESS
        secondary2-1  | 2025-09-24T21:43:16,214 INFO     [main.py:20] Received: msg2
        secondary2-1  | 2025-09-24T21:43:16,214 INFO     [main.py:22] Introducing 5 seconds of delay
        secondary2-1  | 2025-09-24T21:43:21,214 INFO     [main.py:25] Added message msg2 to replicated list
        master-1      | 2025-09-24T21:43:21,215 INFO     [replication.py:27] Message replicated to secondary2:50051: SUCCESS
        master-1      | INFO:     172.20.0.1:46156 - "POST /messages HTTP/1.1" 200 OK
    </details>
9. Перевіряємо реплікацію
    ```bash
    # master
    $ curl localhost:8000/messages
    {"messages":["msg1","msg2"]}

    # secondary1
    $ curl localhost:8001/messages
    {"messages":["msg1","msg2"]}

    # secondary2
    $ curl localhost:8002/messages
    {"messages":["msg1","msg2"]}
    ```

## Додаток
Запуск без докеру:
```bash
uvicorn master.src.main:app
uvicorn --port 8001 secondary.src.main:app
```