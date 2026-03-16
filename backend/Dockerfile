FROM mcr.microsoft.com/playwright/python:v1.56.0-jammy

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/backend:/app \
    PORT=8000

WORKDIR /app

COPY backend/requirements.txt /tmp/requirements.txt

RUN python -m pip install --upgrade pip && \
    python -m pip install --no-cache-dir -r /tmp/requirements.txt

RUN mkdir -p /app && chown -R pwuser:pwuser /app

COPY --chown=pwuser:pwuser backend /app/backend
COPY --chown=pwuser:pwuser scripts /app/scripts

USER pwuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
