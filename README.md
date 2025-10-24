# Replicated log homework.

## Ітерація 1
Рішення побудоване на python, з використанням FastAPI для публічних ендпойнтів і gRPC для міжсервісної комунікації.

Проект містить три модулі:
- master
- secondary
- common - містить gRPC-код, який підключається в master i secondary

Адреси secondary-серверів задаються на мастері через змінну середовища `SECONDARY_ADDRESSES`.

## Ітерація 2
- Додано параметр write_concern
- Додано дедублікацію повідомлень
- Ордерінг повідомлень: зроблено за вимогами ітерації 3 - додано тимчасовий буфер, в якому тримаються повідомлення, що отримані поза чергою

## Запуск і перевірка
1. Запуск в docker:
    ```bash
    docker compose up --build
    ```
2. Надсилаємо повідомлення, write_concern == 2 (Master + один secondary)
    ```bash
    $ curl -X POST "localhost:8000/messages" \
        -H "Content-Type: application/json" \
        -d '{"message": "msg1", "write_concern": 2}'
    {"status":"replicated"}
    ```
    <details>
        <summary>Лог</summary>

        master-1      | 2025-10-24T10:13:30,606 INFO     [main.py:52] Message append request: message='msg1' write_concern=2
        master-1      | 2025-10-24T10:13:30,607 INFO     [replication.py:29] Replicating message dto: MessageDto(previous_message_id=None, message_id=0, message_body='msg1')
        secondary2-1  | 2025-10-24T10:13:30,610 INFO     [main.py:42] Received request to replicate message MessageDto(previous_message_id=None, message_id=0, message_body='msg1')
        secondary1-1  | 2025-10-24T10:13:30,610 INFO     [main.py:42] Received request to replicate message MessageDto(previous_message_id=None, message_id=0, message_body='msg1')
        secondary2-1  | 2025-10-24T10:13:30,610 INFO     [main.py:25] Introducing 2 seconds of delay
        secondary1-1  | 2025-10-24T10:13:30,610 INFO     [main.py:25] Introducing 3 seconds of delay
        secondary2-1  | 2025-10-24T10:13:32,613 INFO     [main.py:56] Message 0 replicated
        master-1      | 2025-10-24T10:13:32,615 INFO     [replication.py:49] Replication result: ('secondary2:50051', status: SUCCESS
        master-1      | )
        master-1      | 2025-10-24T10:13:32,615 INFO     [replication.py:53] Success count 2 has reached the write_concern of 2
        master-1      | INFO:     172.20.0.1:47118 - "POST /messages HTTP/1.1" 200 OK ## Мастер повернув 200 клієнту
        secondary1-1  | 2025-10-24T10:13:33,619 INFO     [main.py:56] Message 0 replicated
    </details>
3. Перевіряємо реплікацію
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
4. Надсилаємо друге повідомлення, write_concern == 1 (тільки Master)
    ```bash
    $ curl -X POST "localhost:8000/messages" \
        -H "Content-Type: application/json" \
        -d '{"message": "msg2", "write_concern": 1}'
    {"status":"replicated"}
    ```
    <details>
        <summary>Лог</summary>

        master-1      | 2025-10-24T10:16:01,667 INFO     [main.py:52] Message append request: message='msg2' write_concern=1
        master-1      | 2025-10-24T10:16:01,667 INFO     [replication.py:29] Replicating message dto: MessageDto(previous_message_id=0, message_id=1, message_body='msg2')
        master-1      | 2025-10-24T10:16:01,668 INFO     [replication.py:42] write_concern is 1. Replicating on the background
        master-1      | INFO:     172.20.0.1:35664 - "POST /messages HTTP/1.1" 200 OK ## Мастер повернув 200 клієнту
        secondary2-1  | 2025-10-24T10:16:01,670 INFO     [main.py:42] Received request to replicate message MessageDto(previous_message_id=0, message_id=1, message_body='msg2')
        secondary1-1  | 2025-10-24T10:16:01,669 INFO     [main.py:42] Received request to replicate message MessageDto(previous_message_id=0, message_id=1, message_body='msg2')
        secondary1-1  | 2025-10-24T10:16:01,669 INFO     [main.py:25] Introducing 3 seconds of delay
        secondary2-1  | 2025-10-24T10:16:01,670 INFO     [main.py:25] Introducing 4 seconds of delay
        secondary1-1  | 2025-10-24T10:16:03,676 INFO     [main.py:56] Message 1 replicated
        secondary2-1  | 2025-10-24T10:16:04,686 INFO     [main.py:56] Message 1 replicated
    </details>
5. Перевіряємо реплікацію
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
6. Надсилаємо друге повідомлення, write_concern == 1 (тільки Master)
    ```bash
    $ curl -X POST "localhost:8000/messages" \
        -H "Content-Type: application/json" \
        -d '{"message": "msg3", "write_concern": 3}'
    {"status":"replicated"}
    ```
    <details>
        <summary>Лог</summary>

        master-1      | 2025-10-24T10:19:23,720 INFO     [main.py:52] Message append request: message='msg3' write_concern=3
        master-1      | 2025-10-24T10:19:23,721 INFO     [replication.py:29] Replicating message dto: MessageDto(previous_message_id=1, message_id=2, message_body='msg3')
        secondary1-1  | 2025-10-24T10:19:23,722 INFO     [main.py:42] Received request to replicate message MessageDto(previous_message_id=1, message_id=2, message_body='msg3')
        secondary1-1  | 2025-10-24T10:19:23,722 INFO     [main.py:25] Introducing 4 seconds of delay
        secondary2-1  | 2025-10-24T10:19:23,722 INFO     [main.py:42] Received request to replicate message MessageDto(previous_message_id=1, message_id=2, message_body='msg3')
        secondary2-1  | 2025-10-24T10:19:23,722 INFO     [main.py:25] Introducing 4 seconds of delay
        secondary1-1  | 2025-10-24T10:19:26,721 INFO     [main.py:56] Message 2 replicated
        secondary2-1  | 2025-10-24T10:19:26,721 INFO     [main.py:56] Message 2 replicated
        master-1      | 2025-10-24T10:19:26,723 INFO     [replication.py:49] Replication result: ('secondary1:50051', status: SUCCESS
        master-1      | )
        master-1      | 2025-10-24T10:19:26,723 INFO     [replication.py:49] Replication result: ('secondary2:50051', status: SUCCESS
        master-1      | )
        master-1      | 2025-10-24T10:19:26,724 INFO     [replication.py:53] Success count 3 has reached the write_concern of 3
        master-1      | INFO:     172.20.0.1:43496 - "POST /messages HTTP/1.1" 200 OK
    </details>
7. Перевіряємо реплікацію
    ```bash
    # master
    $ curl localhost:8000/messages
    ["msg1","msg2","msg3"]

    # secondary1
    $ curl localhost:8001/messages
    ["msg1","msg2","msg3"]

    # secondary2
    $ curl localhost:8002/messages
    ["msg1","msg2","msg3"]
    ```

## Локальний запуск

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
5. Запуск:
    ```bash
    uvicorn master.src.main:app
    uvicorn --port 8001 secondary.src.main:app
    ```
