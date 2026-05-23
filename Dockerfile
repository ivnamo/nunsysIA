FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN python -m pip install --upgrade pip \
    && python -m pip install -r requirements.txt

COPY app ./app
COPY chainlit_app ./chainlit_app
COPY chainlit.md ./chainlit.md
COPY .chainlit ./.chainlit
COPY public ./public
COPY production_mock ./production_mock
COPY data ./data
COPY scripts ./scripts
COPY docker-compose.yml ./docker-compose.yml
COPY query.json ./query.json

EXPOSE 8000 8001 8002

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
