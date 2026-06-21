FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN groupadd --system --gid 10001 bot \
    && useradd --system --uid 10001 --gid bot --home-dir /app bot

COPY requirements.txt .
RUN pip install --no-cache-dir --requirement requirements.txt

COPY --chown=bot:bot bot.py .

RUN mkdir --parents /app/data /app/logs \
    && chown --recursive bot:bot /app/data /app/logs

USER bot

CMD ["python", "bot.py"]
