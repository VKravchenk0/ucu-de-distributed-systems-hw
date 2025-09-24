FROM python:3.13-slim
# TODO поправити версію python

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY common ./common
# TODO: копіювати тільки .py-файли
COPY master ./master

CMD ["uvicorn", "master.src.main:app", "--host", "0.0.0.0", "--port", "8000"]
