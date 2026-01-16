# Dockerfile для Celery
FROM python:3.11-slim

WORKDIR /app

# Копируем зависимости
COPY requirements.txt .

# Устанавливаем Python зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код проекта
COPY . .

# Создаем non-root пользователя
RUN useradd -m -u 1002 -s /bin/bash celery_user && \
    chown -R celery_user:celery_user /app

USER celery_user

# Команда будет переопределена в docker-compose
CMD ["celery", "--help"]
