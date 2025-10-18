FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

ENV FLASK_APP=app \
    FLASK_RUN_HOST=0.0.0.0 \
    FLASK_RUN_PORT=5001

EXPOSE 5001

CMD ["flask", "run"]
