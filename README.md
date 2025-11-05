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

## Ітерація 3
- Додано логіку ретраїв
- Додано pull heartbeat-логіку: master періодично шле запити на secondaries, щоб зрозуміти їхній статус. Параметри хартбітів винесені в конфігурацію (`main.settings.HEARTBEAT_*`)
- Додано логіку кворуму: якщо кількість живих нод в кластері менша за кворум - реплікація не відбувається, клієнту повертається повідомлення. В поточній реалізації залишився непокритим корнер-кейс: якщо ноди впали, і мастер ще не зрозумів, що вони впали - запити на реплікацію з write_concern < quorum пройдуть успішно

## Запуск і перевірка
1. Термінал 1: запуск додатку
    ```bash
    docker compose up --build
    ```

2. Термінал 2: зупинка secondary2
    ```bash
    docker ps -q --filter "name=secondary2" | xargs -r docker pause
    ```

3. Термінал 2: відсилаємо перші три повідомлення. Після write_concern == 3 термінал буде заблоковано очікуванням:
    ```bash
    curl -X POST "localhost:8000/messages" \
        -H "Content-Type: application/json" \
        -d '{"message": "msg1", "write_concern": 1}'

    curl -X POST "localhost:8000/messages" \
        -H "Content-Type: application/json" \
        -d '{"message": "msg2", "write_concern": 2}'

    curl -X POST "localhost:8000/messages" \
        -H "Content-Type: application/json" \
        -d '{"message": "msg3", "write_concern": 3}'
    ```

4. Термінал 3: msg4, w=1:
    ```bash
    curl -X POST "localhost:8000/messages" \
        -H "Content-Type: application/json" \
        -d '{"message": "msg4", "write_concern": 1}'
    ```

5. Піднімаємо secondary2:
    ```bash
    docker ps -q --filter "name=secondary2" | xargs -r docker unpause
    ```

6. Чекаємо кілька секунд, перевіряємо реплікацію:
    ```bash
    # master
    $ curl localhost:8000/messages
    ["msg1","msg2","msg3","msg4"]

    # secondary1
    $ curl localhost:8001/messages
    ["msg1","msg2","msg3","msg4"]

    # secondary2
    $ curl localhost:8002/messages
    ["msg1","msg2","msg3","msg4"]
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

