FROM python:3.12-alpine

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN addgroup --system --gid 10001 bot \
    && adduser --system --disabled-password --no-create-home \
        --uid 10001 --ingroup bot bot

COPY requirements.txt .
RUN pip install --no-cache-dir --requirement requirements.txt

COPY --chown=bot:bot bot.py .

RUN mkdir --parents /app/data /app/logs \
    && chown --recursive bot:bot /app/data /app/logs

USER bot

CMD ["python", "bot.py"]
