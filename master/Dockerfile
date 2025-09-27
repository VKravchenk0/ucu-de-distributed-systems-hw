FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# в контейнер копіюються зайві файли (Dockerfile, proto). Залишив як є, щоб не ускладнювати код
COPY common ./common
COPY master ./master

CMD ["uvicorn", "master.src.main:app", "--host", "0.0.0.0", "--port", "8000"]
