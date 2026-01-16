# Dockerfile для Telegram бота
FROM python:3.11-slim

WORKDIR /app

# Копируем зависимости
COPY requirements.txt .

# Устанавливаем Python зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код проекта
COPY . .

# Создаем non-root пользователя
RUN useradd -m -u 1001 -s /bin/bash bot_user && \
    chown -R bot_user:bot_user /app

USER bot_user

# Команда запуска бота
CMD ["python", "manage.py", "runbot"]
