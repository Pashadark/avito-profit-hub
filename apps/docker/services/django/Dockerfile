# Упрощенный Dockerfile для Windows
FROM python:3.11-slim

WORKDIR /app

# Устанавливаем пути Python
ENV PYTHONPATH=/app:/app/apps:$PYTHONPATH
ENV DJANGO_SETTINGS_MODULE=core.settings


# Копируем зависимости
COPY requirements.txt .

# Устанавливаем Python зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код проекта
COPY . .

# Создаем директории
RUN mkdir -p /app/static /app/media /app/logs

# Создаем пользователя
RUN useradd -m -u 1000 -s /bin/bash django_user && \
    chown -R django_user:django_user /app

USER django_user

EXPOSE 8000

CMD ["sh", "-c", "python manage.py migrate && python manage.py runserver 0.0.0.0:8000"]
