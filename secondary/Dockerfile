FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY common ./common
# TODO: копіювати тільки .py-файли
COPY secondary ./secondary

CMD ["uvicorn", "secondary.src.main:app", "--host", "0.0.0.0", "--port", "8001"]