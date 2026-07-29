FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

ARG INSTALL_DEV_DEPS=false

RUN groupadd --gid 10001 btsp \
    && useradd --uid 10001 --gid btsp --create-home btsp \
    && mkdir -p /data/attachments /data/purchase-order-exports /data/analytics-reports /data/invoice-intake \
    && chown -R btsp:btsp /data

COPY requirements.txt .
COPY requirements-dev.txt .
RUN python -m pip install --no-cache-dir --upgrade pip==26.1.2 \
    && pip install --no-cache-dir -r requirements.txt \
    && if [ "$INSTALL_DEV_DEPS" = "true" ]; then pip install --no-cache-dir -r requirements-dev.txt; fi

COPY --chown=btsp:btsp . .

USER btsp

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
